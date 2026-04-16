from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

from openai import AsyncOpenAI
from config import settings
from database import get_db

_log = logging.getLogger(__name__)

# Use the same Ollama client as groq_service.py — no separate API key needed
_client = AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama")

# In-process cache: language → list of compiled regex patterns
# Populated from MongoDB on first use, then kept in memory
_pattern_cache: dict[str, list[re.Pattern]] = {}

# Languages confirmed to have no import syntax (skip LLM for these)
_NO_IMPORT_LANGUAGES = {
    "markdown", "text", "plaintext", "image", "binary",
    "json", "yaml", "toml", "xml", "csv", "lock",
}

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a code analysis assistant. Your job is to extract
import/dependency statements from source code and also derive regex patterns
that could find similar imports in other files of the same language.

Always respond with valid JSON only. No explanation, no markdown, no backticks."""

_USER_PROMPT_TEMPLATE = """Analyze this {language} source file and extract all import/dependency statements.

SOURCE FILE:
```
{code_sample}
```

Respond with this exact JSON structure:
{{
  "imports": [
    "path/or/module/name",
    "another/dependency"
  ],
  "patterns": [
    {{
      "regex": "^import\\\\s+([\\\\w.]+)",
      "group": 1,
      "description": "standard import statement"
    }}
  ],
  "notes": "brief note about this language import style"
}}

Rules:
- "imports": list of raw import strings exactly as they appear (file paths, module names)
- "patterns": regex patterns that would find ALL imports of this type in any {language} file
- Each pattern needs "regex" (raw regex string) and "group" (capture group number for the import path)
- Only include actual dependency imports, not variable assignments or other statements
- If the file has no imports, return empty lists
"""

async def _load_language_patterns(language: str) -> list[re.Pattern]:
    if language in _pattern_cache:
        return _pattern_cache[language]

    try:
        db = get_db()
        doc = await db.import_patterns.find_one({"language": language})
        if doc and doc.get("patterns"):
            compiled = []
            for p in doc["patterns"]:
                try:
                    compiled.append({
                        "pattern": re.compile(p["regex"], re.MULTILINE),
                        "group": p.get("group", 1),
                    })
                except re.error:
                    pass
            _pattern_cache[language] = compiled
            _log.debug("Loaded %d cached patterns for %s", len(compiled), language)
            return compiled
    except Exception as e:
        _log.warning("Failed to load patterns for %s: %s", language, e)

    return []


async def _save_language_patterns(language: str, raw_patterns: list[dict]) -> None:
    try:
        db = get_db()
        await db.import_patterns.update_one(
            {"language": language},
            {"$set": {
                "language": language,
                "patterns": raw_patterns,
                "source": "llm_derived",
            }},
            upsert=True,
        )
        _log.debug("Saved %d patterns for %s to cache", len(raw_patterns), language)
        _pattern_cache.pop(language, None)
    except Exception as e:
        _log.warning("Failed to save patterns for %s: %s", language, e)


async def _load_file_cache(content_hash: str) -> Optional[list[str]]:
    try:
        db = get_db()
        doc = await db.import_file_cache.find_one({"hash": content_hash})
        if doc:
            return doc.get("imports", [])
    except Exception as e:
        _log.warning("File cache read failed: %s", e)
    return None


async def _save_file_cache(content_hash: str, language: str, imports: list[str]) -> None:
    try:
        db = get_db()
        await db.import_file_cache.update_one(
            {"hash": content_hash},
            {"$set": {
                "hash": content_hash,
                "language": language,
                "imports": imports,
            }},
            upsert=True,
        )
    except Exception as e:
        _log.warning("File cache write failed: %s", e)

def _extract_with_patterns(content: str, patterns: list[dict]) -> list[str]:
    imports = []
    for p in patterns:
        try:
            for m in p["pattern"].finditer(content):
                val = m.group(p["group"]).strip()
                if val:
                    imports.append(val)
        except (IndexError, AttributeError):
            pass
    return imports

async def _extract_with_llm(language: str, content: str) -> tuple[list[str], list[dict]]:
    code_sample = content[:3000]

    prompt = _USER_PROMPT_TEMPLATE.format(
        language=language,
        code_sample=code_sample,
    )

    try:
        response = await _client.chat.completions.create(
            model=settings.OLLAMA_ANALYSIS_MODEL,
            max_tokens=800,
            temperature=0, 
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()

        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        imports  = [str(i) for i in parsed.get("imports",  []) if i]
        patterns = [p for p in parsed.get("patterns", []) if "regex" in p and "group" in p]

        _log.debug(
            "LLM extracted %d imports and %d patterns for %s",
            len(imports), len(patterns), language,
        )
        return imports, patterns

    except json.JSONDecodeError as e:
        _log.warning("LLM returned invalid JSON for %s: %s", language, e)
        return [], []
    except Exception as e:
        _log.warning("LLM extraction failed for %s: %s", language, e)
        return [], []

async def extract_imports_llm(
    language: str,
    content: str,
    path: str = "",
) -> list[str]:
    if not content.strip():
        return []

    lang_lower = language.lower()

    if lang_lower in _NO_IMPORT_LANGUAGES:
        return []

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    cached = await _load_file_cache(content_hash)
    if cached is not None:
        _log.debug("File cache hit for %s (%s)", path, language)
        return cached

    patterns = await _load_language_patterns(lang_lower)
    if patterns:
        imports = _extract_with_patterns(content, patterns)
        _log.debug(
            "Pattern cache hit for %s: extracted %d imports from %s",
            language, len(imports), path,
        )
        await _save_file_cache(content_hash, lang_lower, imports)
        return imports

    _log.info(
        "No patterns for '%s' — calling LLM to derive import patterns (file: %s)",
        language, path,
    )
    imports, raw_patterns = await _extract_with_llm(lang_lower, content)

    if raw_patterns:
        await _save_language_patterns(lang_lower, raw_patterns)

    await _save_file_cache(content_hash, lang_lower, imports)

    return imports
