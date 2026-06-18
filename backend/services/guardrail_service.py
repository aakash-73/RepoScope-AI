"""
guardrail_service.py
────────────────────
Layer-1 guardrail: a fast, deterministic filter that runs *before* any LLM call
and blocks queries that are clearly unrelated to the loaded repository.

Design goals
────────────
• Permissive by default — only block obviously off-topic requests.
  False positives (blocking valid repo questions) hurt usability more than
  false negatives (the LLM's own system-prompt guardrail is Layer 2).
• Zero external dependencies — pure Python regex + heuristics, instant.
• Context-aware rejection messages so the user understands why they were blocked.
"""

from __future__ import annotations

import re
from typing import Optional

# ─── Refusal message template ─────────────────────────────────────────────────

_REFUSAL_REPO = (
    "I'm RepoScope's repository assistant and can only answer questions about "
    "**this specific codebase** — its files, architecture, dependencies, and logic.\n\n"
    "Your question appears to be a general programming or unrelated question. "
    "Please ask something about the repository you have loaded, for example:\n"
    "- *\"What does `auth_service.py` do?\"*\n"
    "- *\"How does data flow from the frontend to the database?\"*\n"
    "- *\"Which files import `config.py`?\"*"
)

_REFUSAL_FILE = (
    "I'm RepoScope's file-level assistant and can only answer questions about "
    "**this specific file** — its logic, structure, patterns, and dependencies.\n\n"
    "Your question appears to be a general programming or unrelated question. "
    "Please ask something about the file currently open, for example:\n"
    "- *\"What does the `process_data` function do?\"*\n"
    "- *\"What are the dependencies of this file?\"*\n"
    "- *\"Are there any potential bugs or concerns here?\"*"
)

# ─── Prompt-injection patterns ─────────────────────────────────────────────────
# These must always be blocked regardless of context.

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"forget\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN|GPT|a\s+different)", re.I),
    re.compile(r"pretend\s+(you\s+are|to\s+be|that\s+you)", re.I),
    re.compile(r"act\s+as\s+(?:a|an|if\s+you\s+are)", re.I),
    re.compile(r"simulate\s+(?:a\s+terminal|a\s+shell|being)", re.I),
    re.compile(r"output\s+(your\s+)?(system\s+prompt|instructions?|context)", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|instructions?|context)", re.I),
    re.compile(r"print\s+(your\s+)?(system\s+prompt|instructions?)", re.I),
    re.compile(r"bypass\s+(?:your\s+)?(?:safety|filter|guardrail|restriction)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\s+mode", re.I),
]

# ─── Off-topic request patterns ───────────────────────────────────────────────
# These match clearly general/tutorial/unrelated requests.
# Patterns are intentionally NOT matched when followed by repo-contextual words
# (see _has_repo_context below).

_OFFTOPIC_PATTERNS: list[re.Pattern] = [
    # General "give me / write / generate code for X" without any file/repo reference
    re.compile(r"\b(give\s+me|write\s+(me\s+)?|generate\s+|create\s+|make\s+)(a\s+)?(python|java(?:script)?|typescript|c\+\+|golang?|rust|ruby|php|swift|kotlin)?\s*(code|snippet|script|program|function|class|method|example)\s+(for|that|to|which)\b", re.I),
    # "How do I X in Python/Java/etc" — general language tutorial
    re.compile(r"\bhow\s+(do\s+i|can\s+i|to)\s+\w+(\s+\w+){0,4}\s+in\s+(python|java(?:script)?|typescript|c\+\+|golang?|rust|ruby|php|swift|kotlin)\b", re.I),
    # "Implement X algorithm/data structure"
    re.compile(r"\bimplement\s+(a\s+|an\s+)?(?!the\s+)(quick\s*sort|merge\s*sort|bubble\s*sort|binary\s*search|linked\s+list|binary\s+tree|hash\s+map|stack|queue|heap|trie)\b", re.I),
    # "Explain X concept" — general CS education
    re.compile(r"\bexplain\s+(what\s+is\s+|how\s+)?(recursion|polymorphism|inheritance|encapsulation|memoization|dynamic\s+programming|big\s+o|time\s+complexity|space\s+complexity|pointer|garbage\s+collection)\b", re.I),
    # "What is X" — fundamental concept questions with no repo context
    re.compile(r"\bwhat\s+is\s+(a\s+|an\s+)?(lambda|closure|decorator|generator|iterator|coroutine|mutex|semaphore|deadlock|race\s+condition)\b", re.I),
    # "Tell me a joke / poem / story"
    re.compile(r"\b(tell\s+me\s+(a\s+)?(joke|story|poem|riddle)|write\s+me\s+(a\s+)?(poem|story|song|haiku))\b", re.I),
    # Weather / news / general knowledge
    re.compile(r"\b(weather|forecast|news|today['']?s?\s+date|current\s+time|stock\s+price|exchange\s+rate|capital\s+of|population\s+of)\b", re.I),
    # "Debug this code" followed by raw code that has no repo context marker
    # (only fired if the query also has no repo-context signals)
    re.compile(r"^\s*(debug|fix)\s+this\s+(code|snippet|error|bug)\s*:?\s*```", re.I),
    # "How to reverse a string", "how to find substrings", etc. — pure language tutorials
    re.compile(r"\bhow\s+to\s+(reverse|sort|find|search|split|join|convert|parse|format|serialize|deserialize)\s+(a\s+|an\s+|the\s+)?(string|array|list|dict(?:ionary)?|tuple|set|integer|number|float)\b", re.I),
    # Substring/string manipulation tutorial trigger
    re.compile(r"\b(substrings?\s+of\s+(a\s+)?string|string\s+manipulation\s+in|reverse\s+a\s+string|palindrome\s+check)\b", re.I),
]

# ─── Repo-context signal words ────────────────────────────────────────────────
# If ANY of these appear in the query, we consider it potentially repo-relevant
# and pass it through (permissive design).

_REPO_CONTEXT_SIGNALS = re.compile(
    r"\b("
    r"this\s+(file|repo(?:sitory)?|codebase|project|module|class|function|service|component)|"
    r"in\s+(this|the)\s+(file|repo(?:sitory)?|codebase|project)|"
    r"here|"
    r"current\s+(file|repo(?:sitory)?|codebase)|"
    r"the\s+repo(?:sitory)?|"
    r"our\s+(codebase|project|repo(?:sitory)?)|"
    r"above\s+code|"
    r"this\s+code(?:base)?"
    r")\b",
    re.I,
)

# Short query threshold — very short queries (< 4 words) are almost never
# off-topic general questions worth blocking; pass them through.
_MIN_WORDS_FOR_FILTER = 4


def _is_injection(query: str) -> bool:
    """Returns True if the query contains a prompt-injection attempt."""
    return any(p.search(query) for p in _INJECTION_PATTERNS)


def _is_offtopic(query: str) -> bool:
    """
    Returns True if the query matches an off-topic pattern AND does not
    contain any repository-context signals.
    """
    words = query.split()
    if len(words) < _MIN_WORDS_FOR_FILTER:
        return False

    # If the query references "this file", "this repo", etc., let it through.
    if _REPO_CONTEXT_SIGNALS.search(query):
        return False

    return any(p.search(query) for p in _OFFTOPIC_PATTERNS)


def check_query_relevance(
    query: str,
    context: str = "repo",
) -> tuple[bool, Optional[str]]:
    """
    Layer-1 guardrail check.

    Parameters
    ──────────
    query   : The raw user query string.
    context : ``"repo"`` for repository-level chat,
              ``"file"`` for file-level (component) chat.

    Returns
    ───────
    (is_blocked, rejection_message)
        is_blocked         — True  → caller should return rejection_message immediately.
        rejection_message  — Human-readable explanation; None when not blocked.
    """
    refusal = _REFUSAL_FILE if context == "file" else _REFUSAL_REPO

    if _is_injection(query):
        return True, refusal

    if _is_offtopic(query):
        return True, refusal

    return False, None
