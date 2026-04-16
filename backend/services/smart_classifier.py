from __future__ import annotations

import logging
import os
import subprocess
import json
from typing import Optional

_log = logging.getLogger(__name__)
_enry_available: Optional[bool] = None


def _check_enry() -> bool:
    global _enry_available
    if _enry_available is not None:
        return _enry_available
    try:
        result = subprocess.run(
            ["enry", "--version"],
            capture_output=True, timeout=2,
        )
        _enry_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _enry_available = False
    if _enry_available:
        _log.info("enry binary detected — using as primary language signal")
    else:
        _log.info("enry not found — using extension + fingerprint classification only")
    return _enry_available


def _enry_classify(path: str, content: str) -> Optional[tuple[str, str]]:
    """
    Call enry binary to detect language for a file.
    Returns (category, sub) or None if enry is unavailable or fails.
    """
    if not _check_enry():
        return None
    try:
        basename = os.path.basename(path)
        sample = content[:2000].encode("utf-8", errors="replace")
        result = subprocess.run(
            ["enry", "--filename", basename, "--json"],
            input=sample,
            capture_output=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout.decode("utf-8", errors="replace").strip())
        language  = data.get("language", "").lower()
        lang_type = data.get("type", "")
        if not language or lang_type in ("vendor", "generated"):
            return None
        return _enry_language_to_cat_sub(language, lang_type)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        _log.debug("enry classification failed for %s: %s", path, e)
        return None


_ENRY_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "python":           ("backend",  "python"),
    "javascript":       ("frontend", "javascript"),
    "typescript":       ("frontend", "typescript"),
    "jsx":              ("frontend", "react"),
    "tsx":              ("frontend", "react"),
    "ruby":             ("backend",  "ruby"),
    "java":             ("backend",  "java"),
    "kotlin":           ("backend",  "kotlin"),
    "go":               ("backend",  "go"),
    "rust":             ("backend",  "rust"),
    "c":                ("backend",  "c"),
    "c++":              ("backend",  "cpp"),
    "c#":               ("backend",  "csharp"),
    "swift":            ("mobile",   "swift"),
    "dart":             ("mobile",   "dart"),
    "shell":            ("backend",  "shell"),
    "bash":             ("backend",  "shell"),
    "powershell":       ("backend",  "powershell"),
    "html":             ("html",     "html"),
    "css":              ("css",      "css"),
    "scss":             ("css",      "scss"),
    "sass":             ("css",      "sass"),
    "less":             ("css",      "less"),
    "sql":              ("database", "sql"),
    "plsql":            ("database", "sql"),
    "graphql":          ("database", "graphql"),
    "dockerfile":       ("devops",   "dockerfile"),
    "hcl":              ("devops",   "hcl"),
    "terraform":        ("devops",   "terraform"),
    "yaml":             ("config",   "yaml"),
    "json":             ("config",   "json"),
    "toml":             ("config",   "toml"),
    "markdown":         ("docs",     "markdown"),
    "restructuredtext": ("docs",     "rst"),
    "tex":              ("docs",     "latex"),
    "glsl":             ("shader",   "glsl"),
    "hlsl":             ("shader",   "hlsl"),
    "vue":              ("frontend", "vue"),
    "svelte":           ("frontend", "svelte"),
    "elixir":           ("backend",  "elixir"),
    "erlang":           ("backend",  "erlang"),
    "haskell":          ("backend",  "haskell"),
    "scala":            ("backend",  "scala"),
    "clojure":          ("backend",  "clojure"),
    "groovy":           ("backend",  "groovy"),
    "perl":             ("backend",  "perl"),
    "lua":              ("backend",  "lua"),
    "r":                ("backend",  "r"),
    "matlab":           ("backend",  "matlab"),
    "julia":            ("backend",  "julia"),
    "nim":              ("backend",  "nim"),
    "zig":              ("backend",  "zig"),
    "crystal":          ("backend",  "crystal"),
    "d":                ("backend",  "d"),
    "fortran":          ("backend",  "fortran"),
    "cobol":            ("backend",  "cobol"),
    "assembly":         ("backend",  "assembly"),
    "objective-c":      ("mobile",   "objc"),
    "objective-c++":    ("mobile",   "objc"),
    "proto":            ("data",     "protobuf"),
    "protocol buffer":  ("data",     "protobuf"),
    "csv":              ("data",     "csv"),
    "xml":              ("data",     "xml"),
}


def _enry_language_to_cat_sub(
    language: str,
    lang_type: str,
) -> Optional[tuple[str, str]]:
    if language in _ENRY_LANGUAGE_MAP:
        return _ENRY_LANGUAGE_MAP[language]
    type_fallback = {
        "programming": ("backend",  language),
        "markup":      ("html",     language),
        "data":        ("data",     language),
        "prose":       ("docs",     language),
    }
    if lang_type in type_fallback:
        cat, sub = type_fallback[lang_type]
        _log.debug("enry: unknown language '%s' → (%s, %s) via type", language, cat, sub)
        return cat, sub
    return None


# ── Pygments integration ──────────────────────────────────────────────────────
# Tier 6 — only called when ALL hardcoded rules (tiers 1-5) fail to match.
# Covers 500+ languages not explicitly mapped in this classifier.
# When a new language is identified, its color is automatically seeded into
# MongoDB via language_registry so it appears in the legend with a unique color.

# Maps Pygments lexer names (lowercased) → (category, sub_category)
_PYGMENTS_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "abap":                 ("backend",  "abap"),
    "ada":                  ("backend",  "ada"),
    "algol":                ("backend",  "algol"),
    "apex":                 ("backend",  "apex"),
    "awk":                  ("backend",  "awk"),
    "basic":                ("backend",  "basic"),
    "chapel":               ("backend",  "chapel"),
    "clean":                ("backend",  "clean"),
    "clips":                ("backend",  "clips"),
    "cmake":                ("devops",   "cmake"),
    "coffeescript":         ("frontend", "coffeescript"),
    "common lisp":          ("backend",  "lisp"),
    "lisp":                 ("backend",  "lisp"),
    "scheme":               ("backend",  "scheme"),
    "racket":               ("backend",  "racket"),
    "cython":               ("backend",  "cython"),
    "delphi":               ("backend",  "delphi"),
    "pascal":               ("backend",  "pascal"),
    "dylan":                ("backend",  "dylan"),
    "eiffel":               ("backend",  "eiffel"),
    "elm":                  ("frontend", "elm"),
    "emacs lisp":           ("backend",  "elisp"),
    "factor":               ("backend",  "factor"),
    "fennel":               ("backend",  "fennel"),
    "fish":                 ("backend",  "shell"),
    "fsharp":               ("backend",  "fsharp"),
    "f#":                   ("backend",  "fsharp"),
    "forth":                ("backend",  "forth"),
    "gherkin":              ("docs",     "gherkin"),
    "gnuplot":              ("data",     "gnuplot"),
    "hack":                 ("backend",  "hack"),
    "haml":                 ("html",     "haml"),
    "handlebars":           ("html",     "handlebars"),
    "haxe":                 ("backend",  "haxe"),
    "idl":                  ("backend",  "idl"),
    "ini":                  ("config",   "ini"),
    "io":                   ("backend",  "io"),
    "j":                    ("backend",  "j"),
    "janet":                ("backend",  "janet"),
    "jinja":                ("html",     "jinja"),
    "jinja2":               ("html",     "jinja"),
    "jsonnet":              ("config",   "jsonnet"),
    "lean":                 ("backend",  "lean"),
    "liquid":               ("html",     "liquid"),
    "livescript":           ("frontend", "livescript"),
    "llvm":                 ("backend",  "llvm"),
    "logo":                 ("backend",  "logo"),
    "makefile":             ("devops",   "makefile"),
    "mako":                 ("html",     "mako"),
    "mathematica":          ("backend",  "mathematica"),
    "mercury":              ("backend",  "mercury"),
    "meson":                ("devops",   "meson"),
    "mint":                 ("frontend", "mint"),
    "ml":                   ("backend",  "ml"),
    "ocaml":                ("backend",  "ocaml"),
    "modelica":             ("backend",  "modelica"),
    "moonscript":           ("backend",  "moonscript"),
    "mustache":             ("html",     "mustache"),
    "nginx":                ("devops",   "nginx"),
    "nix":                  ("devops",   "nix"),
    "nunjucks":             ("html",     "nunjucks"),
    "odin":                 ("backend",  "odin"),
    "openscad":             ("backend",  "openscad"),
    "php":                  ("backend",  "php"),
    "phtml":                ("html",     "php"),
    "pig":                  ("data",     "pig"),
    "pike":                 ("backend",  "pike"),
    "plpgsql":              ("database", "sql"),
    "prisma":               ("database", "prisma"),
    "prolog":               ("backend",  "prolog"),
    "promql":               ("devops",   "promql"),
    "puppet":               ("devops",   "puppet"),
    "purescript":           ("frontend", "purescript"),
    "qml":                  ("frontend", "qml"),
    "raku":                 ("backend",  "raku"),
    "reason":               ("frontend", "reason"),
    "rebol":                ("backend",  "rebol"),
    "red":                  ("backend",  "red"),
    "rescript":             ("frontend", "rescript"),
    "restructuredtext":     ("docs",     "rst"),
    "solidity":             ("backend",  "solidity"),
    "sparql":               ("database", "sparql"),
    "stylus":               ("css",      "stylus"),
    "supercollider":        ("backend",  "supercollider"),
    "swig":                 ("backend",  "swig"),
    "systemverilog":        ("backend",  "verilog"),
    "tcl":                  ("backend",  "tcl"),
    "twig":                 ("html",     "twig"),
    "vala":                 ("backend",  "vala"),
    "velocity":             ("html",     "velocity"),
    "verilog":              ("backend",  "verilog"),
    "vhdl":                 ("backend",  "vhdl"),
    "viml":                 ("backend",  "viml"),
    "vim script":           ("backend",  "viml"),
    "wasm":                 ("backend",  "wasm"),
    "webassembly":          ("backend",  "wasm"),
    "wgsl":                 ("shader",   "wgsl"),
    "xquery":               ("database", "xquery"),
    "xslt":                 ("data",     "xslt"),
    "yacc":                 ("backend",  "yacc"),
    "bison":                ("backend",  "yacc"),
    "zsh":                  ("backend",  "shell"),
}


def _pygments_detect(path: str, content: str) -> Optional[tuple[str, str, str]]:
    """
    Use Pygments to detect language. Returns (category, sub_category, lexer_name)
    or None. Separated from color registration so it can be called from both
    sync and async contexts.

    Returns the raw lexer_name alongside the cat/sub so the async wrapper can
    use it for color registration without re-running Pygments.
    """
    try:
        from pygments.lexers import get_lexer_for_filename, guess_lexer
        from pygments.util import ClassNotFound

        lexer = None

        # Try filename-based detection first (most reliable)
        try:
            lexer = get_lexer_for_filename(path, code=content[:2000])
        except ClassNotFound:
            pass

        # Fall back to content-based detection
        if lexer is None:
            try:
                lexer = guess_lexer(content[:2000])
            except ClassNotFound:
                return None

        # Reject generic non-useful lexers
        lexer_name = lexer.name.lower()
        if lexer_name in ("text", "binary", "plain text", ""):
            return None

        # Check map by primary name
        if lexer_name in _PYGMENTS_LANGUAGE_MAP:
            cat, sub = _PYGMENTS_LANGUAGE_MAP[lexer_name]
            return cat, sub, lexer_name

        # Check map by aliases (Pygments lexers have multiple names)
        for alias in lexer.aliases:
            alias_lower = alias.lower()
            if alias_lower in _PYGMENTS_LANGUAGE_MAP:
                cat, sub = _PYGMENTS_LANGUAGE_MAP[alias_lower]
                return cat, sub, lexer_name

        # Language not in map — infer category from token types
        # Markup tokens → html, everything else → backend
        try:
            from pygments.token import Token
            sample_tokens = list(lexer.get_tokens(content[:500]))
            has_markup = any(t[0] in Token.Name.Tag for t in sample_tokens)
            cat = "html" if has_markup else "backend"
        except Exception:
            cat = "backend"

        sub = lexer_name
        _log.debug(
            "pygments classified %s → (%s, %s) — inferred from tokens",
            path, cat, sub
        )
        return cat, sub, lexer_name

    except ImportError:
        _log.warning(
            "pygments not installed — tier 6 unavailable. Run: pip install pygments"
        )
        return None
    except Exception as e:
        _log.debug("pygments classification failed for %s: %s", path, e)
        return None


async def _pygments_classify_and_register(
    path: str,
    content: str,
    repo_id: Optional[str] = None,
) -> Optional[tuple[str, str]]:
    """
    Async wrapper around _pygments_detect that additionally registers the
    detected language in the language registry (MongoDB) so it gets a unique
    color that appears in the graph legend — exactly like hardcoded languages.

    Color assignment logic (handled by language_registry.register_file_types):
      - If this (category, sub) already exists in MongoDB → use existing color
        (preserves any user customization via the color picker)
      - If it's brand new → _auto_color() generates a deterministic unique
        color from the sub_category name using MD5 hashing, guaranteed not to
        clash with previously registered colors
    """
    result = _pygments_detect(path, content)
    if result is None:
        return None

    cat, sub, lexer_name = result

    # Register the language so it gets a color in MongoDB.
    # register_file_types handles the "already exists" check internally —
    # safe to call every time, it's idempotent for existing entries.
    try:
        from services.language_registry import register_file_types
        await register_file_types(
            discovered=[(cat, sub)],
            repo_id=repo_id or "pygments_auto",
        )
        _log.debug(
            "pygments registered new language: %s → (%s, %s)", lexer_name, cat, sub
        )
    except Exception as e:
        # Color registration failing should never block classification
        _log.debug("pygments color registration failed for %s: %s", path, e)

    return cat, sub


def _pygments_classify_sync(path: str, content: str) -> Optional[tuple[str, str]]:
    """
    Sync version — used by the sync classify_file() path.
    Skips color registration (can't call async from sync context) but still
    returns the correct (category, sub) for classification purposes.
    Color will be seeded on the next async call for the same language.
    """
    result = _pygments_detect(path, content)
    if result is None:
        return None
    cat, sub, _ = result
    return cat, sub


# ── Rules proxy helpers ───────────────────────────────────────────────────────

def _get_rules_sync():
    from services.classifier_registry import _cached_rules, _load_defaults
    return _cached_rules if _cached_rules is not None else _load_defaults()


class _ColorProxy(dict):
    def __getitem__(self, key: str) -> str:
        return _get_rules_sync().category_colors.get(key, "#6B7280")

    def get(self, key: str, default=None):
        return _get_rules_sync().category_colors.get(key, default)

    def __contains__(self, key) -> bool:
        return key in _get_rules_sync().category_colors

    def items(self):
        return _get_rules_sync().category_colors.items()

    def keys(self):
        return _get_rules_sync().category_colors.keys()

    def values(self):
        return _get_rules_sync().category_colors.values()


CATEGORY_COLORS = _ColorProxy()


def _classify(path: str, content: str, rules) -> tuple[str, str]:
    """
    Sync classification — used during repo ingestion where async isn't available.

    Priority:
      1. Named files            — exact basename match (e.g. Dockerfile, Makefile)
      2. enry                   — GitHub's language detector (if installed)
      3. Unambiguous extensions — .py, .go, .rs etc.
      4. Content fingerprints   — regex patterns in file content
      5. Extension fallback     — ambiguous extensions resolved by map
      6. Pygments (sync)        — 500+ language coverage, no color registration
      7. Path heuristics        — directory/path pattern matching
      8. other/unknown          — last resort
    """
    ext      = os.path.splitext(path)[1].lower()
    basename = os.path.basename(path).lower()
    head     = content[:4000]

    # ── Tier 1: Named files ───────────────────────────────────────────────
    if basename in rules.named_map:
        return rules.named_map[basename]

    # ── Tier 2: enry (skipped for unambiguous extensions) ────────────────
    if ext not in rules.unambiguous_exts:
        enry_result = _enry_classify(path, content)
        if enry_result:
            _log.debug("enry classified %s → %s", path, enry_result)
            return enry_result

    # ── Tier 3: Unambiguous extensions ───────────────────────────────────
    if ext in rules.unambiguous_exts:
        return rules.ext_map[ext]

    # ── Tier 4: Content fingerprints ─────────────────────────────────────
    for pattern, cat, sub in rules.fingerprints:
        if pattern.search(head):
            return cat, sub

    # ── Tier 5: Extension fallback map ───────────────────────────────────
    if ext in rules.ext_map:
        return rules.ext_map[ext]

    # ── Tier 6: Pygments sync — no color registration in sync context ─────
    # Color will be registered on the next async classify_file_async() call
    # for the same file (e.g. during graph rebuild or re-analysis).
    pygments_result = _pygments_classify_sync(path, content)
    if pygments_result:
        return pygments_result

    # ── Tier 7: Path heuristics ───────────────────────────────────────────
    for pattern, cat, sub in rules.path_patterns:
        if pattern.search(path):
            return cat, sub

    # ── Tier 8: Give up ───────────────────────────────────────────────────
    return "other", "unknown"


async def classify_file_async(
    path: str,
    content: str = "",
    repo_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Async classification — used by graph builder and node analyzer.
    Runs all 8 tiers including Pygments with full color registration.
    Pass repo_id so newly detected languages are associated with the repo.
    """
    from services.classifier_registry import get_rules
    rules = await get_rules()

    ext      = os.path.splitext(path)[1].lower()
    basename = os.path.basename(path).lower()
    head     = content[:4000]

    # ── Tier 1: Named files ───────────────────────────────────────────────
    if basename in rules.named_map:
        return rules.named_map[basename]

    # ── Tier 2: enry ─────────────────────────────────────────────────────
    if ext not in rules.unambiguous_exts:
        enry_result = _enry_classify(path, content)
        if enry_result:
            return enry_result

    # ── Tier 3: Unambiguous extensions ───────────────────────────────────
    if ext in rules.unambiguous_exts:
        return rules.ext_map[ext]

    # ── Tier 4: Content fingerprints ─────────────────────────────────────
    for pattern, cat, sub in rules.fingerprints:
        if pattern.search(head):
            return cat, sub

    # ── Tier 5: Extension fallback map ───────────────────────────────────
    if ext in rules.ext_map:
        return rules.ext_map[ext]

    # ── Tier 6: Pygments async — with full color registration ────────────
    # Newly detected languages get a unique deterministic color seeded into
    # MongoDB so they appear in the graph legend like hardcoded languages.
    # Previously detected languages reuse their existing color from MongoDB
    # (including any user customizations from the color picker).
    pygments_result = await _pygments_classify_and_register(path, content, repo_id)
    if pygments_result:
        return pygments_result

    # ── Tier 7: Path heuristics ───────────────────────────────────────────
    for pattern, cat, sub in rules.path_patterns:
        if pattern.search(path):
            return cat, sub

    # ── Tier 8: Give up ───────────────────────────────────────────────────
    return "other", "unknown"


def classify_file(path: str, content: str = "") -> tuple[str, str]:
    """Sync classify — used during initial ingestion pipeline."""
    rules = _get_rules_sync()
    return _classify(path, content, rules)


def category_color(category: str) -> str:
    return _get_rules_sync().category_colors.get(category, "#6B7280")


def edge_color(src_cat: str, tgt_cat: str) -> str:
    rules = _get_rules_sync()
    return rules.edge_colors.get(
        (src_cat, tgt_cat),
        rules.category_colors.get(src_cat, "#6B7280"),
    )