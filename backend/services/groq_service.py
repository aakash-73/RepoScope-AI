from __future__ import annotations

import asyncio
import random
import re
from typing import List, Optional
import httpx
import openai
from openai import AsyncOpenAI
from config import settings

# ─── Ollama client (OpenAI-compatible API) ────────────────────────────────────
# api_key="ollama" is just a placeholder — Ollama doesn't require authentication
_client = AsyncOpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)

API_TIMEOUT = 120           # Ollama on first token can be slower than Groq — give it headroom
CHUNK_SIZE = 6000
# Limit concurrent Ollama calls to 1 — local model can't parallelise like a cloud API
_ollama_semaphore = asyncio.Semaphore(1)


def get_client() -> AsyncOpenAI:
    return _client


# ─── Thinking block stripper ──────────────────────────────────────────────────
# qwen2.5-coder (and other reasoning models) sometimes emit <think>...</think>
# blocks before their actual answer. Strip them before storing or returning.
def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _chunk_content(content: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    if len(content) <= chunk_size:
        return [content]

    chunks = []
    overlap = 300
    start = 0

    while start < len(content):
        end = start + chunk_size
        if end < len(content):
            newline_pos = content.rfind("\n", start + chunk_size - 200, end)
            if newline_pos != -1:
                end = newline_pos
        chunks.append(content[start:end])
        start = end - overlap

    return chunks


def _smart_truncate(content: str) -> tuple[str, bool]:
    if len(content) <= settings.MAX_CODE_CHARS:
        return content, False

    head = content[:settings.HEAD_CHARS]
    tail = content[-settings.TAIL_CHARS:]
    omitted_lines = content[settings.HEAD_CHARS:-settings.TAIL_CHARS].count("\n")
    marker = (
        f"\n\n# ─── {omitted_lines} lines omitted for brevity "
        f"({len(content) - settings.HEAD_CHARS - settings.TAIL_CHARS:,} chars) ───\n\n"
    )
    return head + marker + tail, True


SYSTEM_PROMPT = """You are an expert software architect. Analyze the provided source code file and return a concise, structured explanation. Focus on:
1. The primary purpose / responsibility of this module
2. Key classes, functions, or components exported
3. Notable patterns, frameworks, or libraries used
4. Potential concerns (complexity, coupling, tech debt)

Keep the response under 300 words. Use markdown formatting."""

CHUNK_ANALYSIS_PROMPT = """You are an expert software architect analyzing a CHUNK of a larger file.
Briefly summarize only what's in this chunk:
- Functions/classes defined
- Key logic or patterns
- Any concerns

Be concise (under 150 words). This will be merged with other chunk summaries."""

MERGE_PROMPT = """You are an expert software architect. Below are partial analyses of consecutive chunks of a single source file.
Synthesize them into ONE cohesive analysis covering:
1. Primary purpose / responsibility of the module
2. Key classes, functions, or components exported
3. Notable patterns, frameworks, or libraries used
4. Potential concerns (complexity, coupling, tech debt)

Keep the final response under 300 words. Use markdown formatting."""


async def _analyse_chunk(chunk: str, language: str, index: int, total: int) -> str:
    """Analyse a single chunk — waits for semaphore so only 1 runs at a time."""
    prompt = (
        f"{CHUNK_ANALYSIS_PROMPT}\n\n"
        f"Chunk {index + 1}/{total}:\n"
        f"```{language}\n{chunk}\n```"
    )
    print(f"  🔍 Analysing chunk {index + 1}/{total}...")
    async with _ollama_semaphore:
        result = await call_ollama_with_retry(prompt, max_tokens=600)
        await asyncio.sleep(1.5)
        return result


async def explain_component(
    file_path: str,
    content: str,
    language: str,
    imports: List[str],
) -> str:
    chunks = _chunk_content(content)

    if len(chunks) == 1:
        user_message = (
            f"**File:** `{file_path}`\n"
            f"**Language:** {language}\n"
            f"**Imports:** {', '.join(imports[:20]) if imports else 'none'}\n\n"
            f"```{language}\n{content}\n```"
        )
        prompt = f"{SYSTEM_PROMPT}\n\n{user_message}"
        return await call_ollama_with_retry(prompt)

    print(f"📦 Large file ({len(content):,} chars) → {len(chunks)} chunks (sequential)")

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        summary = await _analyse_chunk(chunk, language, i, len(chunks))
        chunk_summaries.append(summary)

    combined = "\n\n---\n\n".join(
        f"**Chunk {i + 1}/{len(chunks)}:**\n{summary}"
        for i, summary in enumerate(chunk_summaries)
    )
    merge_prompt = (
        f"{MERGE_PROMPT}\n\n"
        f"**File:** `{file_path}` | **Language:** {language}\n"
        f"**Imports:** {', '.join(imports[:20]) if imports else 'none'}\n\n"
        f"{combined}"
    )
    return await call_ollama_with_retry(merge_prompt)


async def chat_with_component(
    file_path: str,
    content: str,
    language: str,
    imports: List[str],
    user_query: str,
    history: List[dict] = [],
    context_override: Optional[str] = None,
) -> str:
    client = get_client()
    truncated_content, was_truncated = _smart_truncate(content)

    truncation_note = (
        f"\nNote: This file is large ({len(content):,} chars). "
        "The middle section has been omitted; head and tail are shown.\n"
        if was_truncated else ""
    )

    if context_override:
        context = (
            f"You are helping a developer understand this component.\n\n"
            f"PRE-ANALYZED CONTEXT:\n{context_override}\n\n"
            f"FILE: {file_path}\n"
            f"CODE SNIPPET:\n```{language}\n{truncated_content}\n```"
        )
    else:
        context = (
            f"You are helping a developer understand this component.\n\n"
            f"File: {file_path}\n"
            f"Language: {language}\n"
            f"Imports: {', '.join(imports[:20]) if imports else 'none'}\n"
            f"{truncation_note}\n"
            f"Code:\n```{language}\n{truncated_content}\n```"
        )

    try:
        async with _ollama_semaphore:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.OLLAMA_ANALYSIS_MODEL,
                    messages=[
                        {"role": "system", "content": context},
                        *history,
                        {"role": "user", "content": user_query},
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                ),
                timeout=API_TIMEOUT,
            )
        return _strip_thinking(response.choices[0].message.content or "")

    except asyncio.TimeoutError:
        raise ValueError(f"Chat timed out after {API_TIMEOUT}s for: {file_path}")
    except Exception as e:
        raise ValueError(f"Component chat failed: {e}")


async def call_ollama_with_retry(
    prompt: str,
    max_retries: int = 5,
    max_tokens: int = 5000,
) -> str:
    client = get_client()

    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.OLLAMA_ANALYSIS_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=max_tokens,
                ),
                timeout=API_TIMEOUT,
            )
            return _strip_thinking(response.choices[0].message.content or "")

        except asyncio.TimeoutError:
            print(f"⏱️ Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt == max_retries - 1:
                raise ValueError(f"Ollama call timed out after {max_retries} attempts")
            await asyncio.sleep(2)

        except openai.RateLimitError:
            base_wait = (2 ** attempt) + 1
            jitter = random.uniform(0, 2)
            wait_time = base_wait + jitter
            print(f"⚠️ Rate limit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)

        except (openai.APIConnectionError, openai.APIStatusError) as e:
            if attempt == max_retries - 1:
                raise ValueError(f"Ollama API error after {max_retries} attempts: {e}")
            await asyncio.sleep(2 ** attempt)

        except (httpx.ConnectError, httpx.RemoteProtocolError) as e:
            if attempt == max_retries - 1:
                raise ValueError(
                    f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
                    "Is Ollama running? Try: ollama serve"
                )
            print(f"🔌 Ollama connection error (attempt {attempt + 1}): {e}. Retrying in {2 ** attempt}s...")
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            if attempt == max_retries - 1:
                raise ValueError(f"Ollama call failed after {max_retries} attempts: {e}")
            await asyncio.sleep(1)

    return ""


# ─── Backwards-compatible aliases ─────────────────────────────────────────────
# node_analyzer_service.py, repo_controller.py and others import these names.
# Keeping them here means zero changes needed in any other file.
async def call_groq(prompt: str) -> str:
    return await call_ollama_with_retry(prompt)


call_groq_with_retry = call_ollama_with_retry