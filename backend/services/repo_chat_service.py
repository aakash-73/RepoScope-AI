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
        
        preview = f.get("content", "")[:settings.FILE_PREVIEW_CHARS].strip()
        if preview:
            lang = f.get("language", "")
            lines.append(f"\n**Code Preview:**\n``` {lang}\n{preview}\n```")

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
You are a helpful engineering assistant for a code intelligence tool. \
You have been given a detailed Repository Understanding Document along with \
granular per-file analyses produced by automated AI analysis of the codebase.

Rules:
- Use ALL the provided context — the high-level understanding AND the per-file analyses.
- Prioritize facts from per-file analysis (purpose, architectural_role, key_patterns, functional_categories) over general summaries when answering specific questions.
- When asked about the tech stack, frameworks, or libraries: scan the key_patterns and language fields across all analyzed files and produce an accurate, complete answer.
- Reference specific file paths when relevant (e.g. `services/github_service.py`).
- If the answer truly cannot be found in the context, say so — do NOT fabricate.
- Keep answers concise and developer-friendly. Use markdown.
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
            max_tokens=1000,
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
            max_tokens=1000,
        )
        return _strip_thinking(response.choices[0].message.content or "No response.")

    except openai.RateLimitError:
        raise ValueError("Ollama rate limit reached.")
    except openai.APIConnectionError as e:
        raise ValueError(
            f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
            f"Is Ollama running? Try: ollama serve\nDetails: {e}"
        )


async def stream_chat_with_repo(
    understanding: str,
    user_query: str,
    history: list[dict],
):
    """
    Async generator that yields raw token strings one at a time.
    Strips <think> blocks incrementally.
    """
    client = get_chat_client()

    system = (
        CHAT_SYSTEM_PROMPT
        + "\n\n---\nREPOSITORY UNDERSTANDING DOCUMENT:\n"
        + understanding
    )

    in_think = False
    think_buf = ""

    try:
        stream = await client.chat.completions.create(
            model=settings.OLLAMA_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                *history,
                {"role": "user", "content": user_query},
            ],
            temperature=0.3,
            max_tokens=1000,
            stream=True,
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if not token:
                continue

            # Strip <think>...</think> blocks on-the-fly
            if not in_think:
                if "<think>" in token:
                    parts = token.split("<think>", 1)
                    if parts[0]:
                        yield parts[0]
                    in_think = True
                    think_buf = parts[1] if len(parts) > 1 else ""
                    # Check if the block closes in same token
                    if "</think>" in think_buf:
                        after = think_buf.split("</think>", 1)[1]
                        in_think = False
                        think_buf = ""
                        if after:
                            yield after
                else:
                    yield token
            else:
                think_buf += token
                if "</think>" in think_buf:
                    after = think_buf.split("</think>", 1)[1]
                    in_think = False
                    think_buf = ""
                    if after:
                        yield after

    except openai.APIConnectionError as e:
        yield f"\n\n[Error: Cannot connect to Ollama. Is it running?]"
    except Exception as e:
        yield f"\n\n[Error: {e}]"



# ─── Pre-analysis context fetchers (unchanged from original) ──────────────────

async def get_pre_analyzed_repo_context(repo_id: str) -> Optional[str]:
    """Fetches synthesized repo-level understanding + all granular per-file analyses."""
    db = get_db()
    doc = await db.repo_analysis.find_one({"repo_id": repo_id, "status": "done"})

    # Always try to build a rich context from per-file analyses even if top-level doc is missing
    node_cursor = db.node_analysis.find(
        {"repo_id": repo_id, "status": "done"},
        {"_id": 0, "file_path": 1, "analysis": 1}
    )
    node_docs = await node_cursor.to_list(length=None)

    # If we have neither, return None
    if not doc and not node_docs:
        return None

    # Sort by richness (files with more analysis content first), cap to avoid LLM token overflow
    node_docs.sort(key=lambda d: len(str(d.get("analysis") or {})), reverse=True)
    node_docs = node_docs[:60]  # Top 60 most detailed analyses

    context = []

    # High-level summary section (if available)
    if doc:
        context += [
            "## HIGH-LEVEL REPOSITORY SUMMARY",
            f"{doc.get('overall_summary', '')}",
            "",
            f"**Architecture Patterns:** {', '.join(doc.get('architectural_patterns', []) or ['N/A'])}",
            f"**Data Flow:** {doc.get('data_flow', 'N/A')}",
            "",
            "**Layer Summaries:**",
            f"- Frontend: {doc.get('layer_summaries', {}).get('frontend', 'N/A')}",
            f"- Backend: {doc.get('layer_summaries', {}).get('backend', 'N/A')}",
            f"- Database: {doc.get('layer_summaries', {}).get('database', 'N/A')}",
            f"- DevOps: {doc.get('layer_summaries', {}).get('devops', 'N/A')}",
            "",
        ]

    # Rich per-file granular analysis section
    if node_docs:
        context.append("## PER-FILE ANALYSIS (granular AI analysis of every file)")
        context.append("")
        for ndoc in node_docs:
            path = ndoc.get("file_path", "unknown")
            a = ndoc.get("analysis") or {}
            purpose = a.get("purpose", "").strip()
            role = a.get("architectural_role", "")
            patterns = ", ".join(a.get("key_patterns", []))
            categories = ", ".join(a.get("functional_categories", []))
            concerns = "; ".join(a.get("concerns", []))
            summary = a.get("summary_for_dependents", "")

            lines = [f"### `{path}`"]
            if role:
                lines.append(f"**Role:** {role}")
            if categories:
                lines.append(f"**Functional Areas:** {categories}")
            if patterns:
                lines.append(f"**Tech/Patterns:** {patterns}")
            if purpose:
                lines.append(f"**Purpose:** {purpose}")
            if summary:
                lines.append(f"**One-liner:** {summary}")
            if concerns:
                lines.append(f"**Concerns:** {concerns}")
            lines.append("")
            context.extend(lines)

    return "\n".join(context)


async def get_pre_analyzed_node_context(repo_id: str, file_path: str) -> Optional[dict]:
    """Fetches the granular node analysis for a specific file."""
    db = get_db()
    doc = await db.node_analysis.find_one(
        {"repo_id": repo_id, "file_path": file_path, "status": "done"}
    )
    return doc.get("analysis") if doc else None