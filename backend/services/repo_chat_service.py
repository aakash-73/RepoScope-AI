from __future__ import annotations

import re
from typing import List, Optional
import openai
from openai import AsyncOpenAI
from config import settings
from database import get_db

# ─── Ollama clients (OpenAI-compatible API) ───────────────────────────────────
# Two clients mirror the original two-key Groq setup so the rest of the
# codebase (repo_chat_controller.py) doesn't need to change.
# Both point at the same Ollama server — the split is kept so you can
# trivially point them at different hosts later if needed.
_analysis_client = AsyncOpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)
_chat_client = AsyncOpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)


def get_analysis_client() -> AsyncOpenAI:
    return _analysis_client


def get_chat_client() -> AsyncOpenAI:
    return _chat_client


# ─── Thinking block stripper ──────────────────────────────────────────────────
def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ─── Context builders (unchanged from original) ───────────────────────────────

def build_communication_map(nodes: list[dict], edges: list[dict]) -> str:
    """Creates a textual representation of the dependency graph (imports)."""
    id_to_path = {n["id"]: n["data"]["file_path"] for n in nodes}

    lines = ["## COMMUNICATION MAP (File Dependencies)"]
    for edge in edges:
        src = id_to_path.get(edge["source"])
        tgt = id_to_path.get(edge["target"])
        if src and tgt:
            lines.append(f"- `{src}` -> depends on -> `{tgt}`")

    if len(lines) == 1:
        lines.append("No internal dependencies detected.")

    return "\n".join(lines)


def build_repo_context(files: list[dict], file_explanations: Optional[dict[str, str]] = None) -> str:
    lines = [f"This repository contains {len(files)} files.\n", "=" * 60]

    for f in files:
        path = f['path']
        lines.append(f"\n## {path}")
        lines.append(
            f"Language: {f.get('language', 'unknown')}  |  "
            f"Lines: {len(f.get('content', '').splitlines())}"
        )

        imports = f.get("imports", [])
        if imports:
            lines.append(f"Imports: {', '.join(imports[:15])}")

        exports = f.get("exports", [])
        if exports:
            lines.append(f"Exports: {', '.join(exports[:15])}")

        if file_explanations and path in file_explanations:
            lines.append(f"\n**Analysis:**\n{file_explanations[path]}")
        else:
            preview = f.get("content", "")[:settings.FILE_PREVIEW_CHARS].strip()
            if preview:
                lang = f.get("language", "")
                lines.append(f"``` {lang}\n{preview}\n```")

        lines.append("-" * 40)

    return "\n".join(lines)


# ─── Prompts (unchanged from original) ───────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert software architect. You will be given a structured dump of every \
file in a repository (paths, languages, imports, exports, and a short code preview).

Your task is to produce a comprehensive REPOSITORY UNDERSTANDING DOCUMENT with these sections:

1. **Project Overview** — What this project does in 2-3 sentences.
2. **Tech Stack** — Languages, frameworks, key libraries detected.
3. **Architecture** — How the codebase is structured (layers, services, modules).
4. **Entry Points** — Main files where execution or routing begins.
5. **Data Flow** — How data moves through the system at a high level.
6. **Key Components** — The 5-10 most important files and what each does.
7. **Notable Patterns** — Design patterns, conventions, or architectural decisions observed.

Be precise and technical. Reference actual file paths. Use markdown.
This document will be used as the sole knowledge base for answering user questions.
"""

CHAT_SYSTEM_PROMPT = """\
You are a helpful engineering assistant. You have been given a detailed \
Repository Understanding Document produced by a senior software architect.

Rules:
- Answer questions using ONLY the information in the understanding document.
- Reference specific file paths when relevant (e.g. `services/github_service.py`).
- If the answer cannot be determined from the document, say so honestly.
- Keep answers concise and developer-friendly. Use markdown.
- Never fabricate file names, function names, or behaviors not mentioned in the document.
"""


# ─── Core LLM functions ───────────────────────────────────────────────────────

async def build_repo_understanding(
    files: list[dict],
    file_explanations: Optional[dict[str, str]] = None,
    communication_map: str = "",
) -> str:
    client = get_analysis_client()
    raw_context = build_repo_context(files, file_explanations)

    full_system_prompt = ANALYSIS_SYSTEM_PROMPT
    if communication_map:
        full_system_prompt += f"\n\n---\n{communication_map}"

    try:
        response = await client.chat.completions.create(
            model=settings.OLLAMA_ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Here is the full repository file summary (including granular analyses where available):\n\n"
                        + raw_context
                        + "\n\nPlease produce the Repository Understanding Document."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return _strip_thinking(response.choices[0].message.content or "Analysis unavailable.")

    except openai.RateLimitError:
        raise ValueError("Ollama rate limit reached. This is unexpected — check server logs.")
    except openai.APIConnectionError as e:
        raise ValueError(
            f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
            f"Is Ollama running? Try: ollama serve\nDetails: {e}"
        )
    except openai.APIStatusError as e:
        raise ValueError(f"Ollama API error {e.status_code}: {e.message}")
    except Exception as e:
        raise ValueError(f"Unexpected analysis error: {e}")


async def summarize_repo(
    files: list[dict],
    file_explanations: Optional[dict[str, str]] = None,
    communication_map: str = "",
) -> tuple[str, str]:
    understanding = await build_repo_understanding(files, file_explanations, communication_map)
    chat_client = get_chat_client()

    try:
        response = await chat_client.chat.completions.create(
            model=settings.OLLAMA_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        CHAT_SYSTEM_PROMPT
                        + "\n\n---\nREPOSITORY UNDERSTANDING DOCUMENT:\n"
                        + understanding
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Please give me a concise, friendly overview of this project "
                        "in 150-200 words — what it does, the tech stack, and the overall architecture."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=600,
        )
        summary = _strip_thinking(response.choices[0].message.content or "Could not generate summary.")

    except openai.RateLimitError:
        raise ValueError("Ollama rate limit reached.")
    except openai.APIConnectionError as e:
        raise ValueError(
            f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
            f"Is Ollama running? Try: ollama serve\nDetails: {e}"
        )
    except openai.APIStatusError as e:
        raise ValueError(f"Ollama API error {e.status_code}: {e.message}")
    except Exception as e:
        raise ValueError(f"Unexpected chat error: {e}")

    return understanding, summary


async def chat_with_repo(
    understanding: str,
    user_query: str,
    history: list[dict],
) -> str:
    client = get_chat_client()

    system = (
        CHAT_SYSTEM_PROMPT
        + "\n\n---\nREPOSITORY UNDERSTANDING DOCUMENT:\n"
        + understanding
    )

    try:
        response = await client.chat.completions.create(
            model=settings.OLLAMA_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                *history,
                {"role": "user", "content": user_query},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return _strip_thinking(response.choices[0].message.content or "No response.")

    except openai.RateLimitError:
        raise ValueError("Ollama rate limit reached.")
    except openai.APIConnectionError as e:
        raise ValueError(
            f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
            f"Is Ollama running? Try: ollama serve\nDetails: {e}"
        )
    except openai.APIStatusError as e:
        raise ValueError(f"Ollama API error {e.status_code}: {e.message}")
    except Exception as e:
        raise ValueError(f"Unexpected chat error: {e}")


# ─── Pre-analysis context fetchers (unchanged from original) ──────────────────

async def get_pre_analyzed_repo_context(repo_id: str) -> Optional[str]:
    """Fetches the synthesized repository-level understanding from pre-analysis."""
    db = get_db()
    doc = await db.repo_analysis.find_one({"repo_id": repo_id, "status": "done"})
    if not doc:
        return None

    context = [
        f"OVERALL SUMMARY:\n{doc.get('overall_summary', '')}\n",
        f"ARCHITECTURE PATTERNS: {', '.join(doc.get('architectural_patterns', []))}\n",
        f"DATA FLOW:\n{doc.get('data_flow', '')}\n",
        "LAYER SUMMARIES:",
        f"- Frontend: {doc.get('layer_summaries', {}).get('frontend', 'N/A')}",
        f"- Backend: {doc.get('layer_summaries', {}).get('backend', 'N/A')}",
        f"- Database: {doc.get('layer_summaries', {}).get('database', 'N/A')}",
        f"- DevOps: {doc.get('layer_summaries', {}).get('devops', 'N/A')}",
    ]
    return "\n".join(context)


async def get_pre_analyzed_node_context(repo_id: str, file_path: str) -> Optional[dict]:
    """Fetches the granular node analysis for a specific file."""
    db = get_db()
    doc = await db.node_analysis.find_one(
        {"repo_id": repo_id, "file_path": file_path, "status": "done"}
    )
    return doc.get("analysis") if doc else None