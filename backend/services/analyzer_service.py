import ast
import logging
import re
import os

_log = logging.getLogger(__name__)


def file_type(path: str, content: str = "") -> str:
    from .smart_classifier import classify_file
    cat, _ = classify_file(path, content)
    return cat

JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)

def _analyze_python(content):
    imports, exports = [], []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                exports.append(node.name)
    except Exception:
        pass
    return imports, exports

def _analyze_js(content):
    imports = []
    for m in JS_IMPORT_RE.finditer(content):
        imp = m.group(1) or m.group(2)
        if imp:
            imports.append(imp)
    return imports, []

_HTML_SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_HTML_CSS_RE    = re.compile(r'<link[^>]+href=["\']([^"\']+\.css)["\']', re.IGNORECASE)

def _analyze_html(content):
    imports = []
    for m in _HTML_SCRIPT_RE.finditer(content):
        imports.append(m.group(1))
    for m in _HTML_CSS_RE.finditer(content):
        imports.append(m.group(1))
    return imports, []

_KOTLIN_IMPORT_RE = re.compile(r'^import\s+([\w.]+(?:\.\*)?)', re.MULTILINE)
_KOTLIN_CLASS_RE  = re.compile(r'^(?:class|object|interface|fun)\s+(\w+)', re.MULTILINE)

def _analyze_kotlin(content):
    imports = []
    for m in _KOTLIN_IMPORT_RE.finditer(content):
        raw = m.group(1)
        if raw.endswith(".*"):
            raw = raw[:-2]
        imports.append(raw)
    exports = [m.group(1) for m in _KOTLIN_CLASS_RE.finditer(content)]
    return imports, exports

_JAVA_IMPORT_RE = re.compile(r'^import\s+(?:static\s+)?([\w.]+(?:\.\*)?);', re.MULTILINE)
_JAVA_CLASS_RE  = re.compile(r'^(?:public\s+)?(?:class|interface|enum)\s+(\w+)', re.MULTILINE)

def _analyze_java(content):
    imports = []
    for m in _JAVA_IMPORT_RE.finditer(content):
        raw = m.group(1)
        if raw.endswith(".*"):
            raw = raw[:-2]
        imports.append(raw)
    exports = [m.group(1) for m in _JAVA_CLASS_RE.finditer(content)]
    return imports, exports

_GO_IMPORT_RE = re.compile(r'["\'](\S+)["\'](\s*//.*)?$', re.MULTILINE)

def _analyze_go(content):
    return [m.group(1) for m in _GO_IMPORT_RE.finditer(content)], []

_RUST_USE_RE = re.compile(r'^use\s+([\w:]+)', re.MULTILINE)
_RUST_FN_RE  = re.compile(r'^pub\s+fn\s+(\w+)', re.MULTILINE)

def _analyze_rust(content):
    return (
        [m.group(1) for m in _RUST_USE_RE.finditer(content)],
        [m.group(1) for m in _RUST_FN_RE.finditer(content)],
    )

_DART_IMPORT_RE = re.compile(r"""^import\s+['"]([^'"]+)['"]""", re.MULTILINE)
_DART_CLASS_RE  = re.compile(r"^(?:class|mixin|extension)\s+(\w+)", re.MULTILINE)

def _analyze_dart(content):
    return (
        [m.group(1) for m in _DART_IMPORT_RE.finditer(content)],
        [m.group(1) for m in _DART_CLASS_RE.finditer(content)],
    )

_C_INCLUDE_RE = re.compile(r'^#include\s+["<]([^">]+)[">]', re.MULTILINE)
_C_FUNC_RE    = re.compile(r'^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)

def _analyze_c(content):
    return (
        [m.group(1) for m in _C_INCLUDE_RE.finditer(content)],
        [m.group(1) for m in _C_FUNC_RE.finditer(content)][:20],
    )

_CSHARP_USING_RE = re.compile(r'^using\s+([\w.]+);', re.MULTILINE)
_CSHARP_CLASS_RE = re.compile(r'^(?:public\s+)?(?:class|interface|struct|enum)\s+(\w+)', re.MULTILINE)

def _analyze_csharp(content):
    return (
        [m.group(1) for m in _CSHARP_USING_RE.finditer(content)],
        [m.group(1) for m in _CSHARP_CLASS_RE.finditer(content)],
    )

_SWIFT_IMPORT_RE = re.compile(r'^import\s+(\w+)', re.MULTILINE)
_SWIFT_CLASS_RE  = re.compile(r'^(?:public\s+)?(?:class|struct|enum|protocol)\s+(\w+)', re.MULTILINE)

def _analyze_swift(content):
    return (
        [m.group(1) for m in _SWIFT_IMPORT_RE.finditer(content)],
        [m.group(1) for m in _SWIFT_CLASS_RE.finditer(content)],
    )
    
_RUBY_REQUIRE_RE = re.compile(r"^require(?:_relative)?\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_RUBY_CLASS_RE   = re.compile(r'^(?:class|module)\s+(\w+)', re.MULTILINE)

def _analyze_ruby(content):
    return (
        [m.group(1) for m in _RUBY_REQUIRE_RE.finditer(content)],
        [m.group(1) for m in _RUBY_CLASS_RE.finditer(content)],
    )

_CSS_IMPORT_RE = re.compile(r'@import\s+["\']([^"\']+)["\']')

def _analyze_css(content):
    return [m.group(1) for m in _CSS_IMPORT_RE.finditer(content)], []

_FETCH_RE        = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']')
_AXIOS_METHOD_RE = re.compile(r'axios\s*\.\s*(?:get|post|put|delete|patch|head|options)\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE)
_AXIOS_OBJECT_RE = re.compile(r'axios\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\']', re.IGNORECASE)
_API_INSTANCE_RE = re.compile(r'\bapi\s*\.\s*(?:get|post|put|delete|patch|head|options)\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE)

def _api_calls(content):
    calls = []
    for pat in (_FETCH_RE, _AXIOS_METHOD_RE, _AXIOS_OBJECT_RE, _API_INSTANCE_RE):
        for m in pat.finditer(content):
            calls.append(m.group(1))
    return calls

_FASTAPI = re.compile(r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
_FLASK   = re.compile(r'@app\.route\(["\']([^"\']+)["\']')
_EXPRESS = re.compile(r'router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')

def _routes(content, sub):
    routes = []
    python_subs = {"python", "fastapi", "django", "flask", "backend"}
    js_subs     = {"express", "nestjs", "nodejs", "javascript", "typescript"}
    if sub in python_subs:
        for m in _FASTAPI.finditer(content): routes.append(m.group(2))
        for m in _FLASK.finditer(content):   routes.append(m.group(1))
    if sub in js_subs:
        for m in _EXPRESS.finditer(content): routes.append(m.group(2))
    return routes

PYTHON_SUBS = {"python", "fastapi", "django", "flask"}

JS_SUBS = {
    "javascript", "typescript", "coffeescript",
    "react", "vue", "svelte", "astro", "nextjs", "angular",
    "nodejs", "express", "nestjs",
    "component", "page", "hook", "store", "middleware", "routes",
    "test", "jest", "cypress", "vitest", "storybook",
    "server", "ci", "frontend", "script",
}

HTML_SUBS   = {"html", "jinja", "nunjucks", "handlebars", "mustache", "ejs", "pug", "haml", "erb", "php"}
CSS_SUBS    = {"css", "scss", "sass", "less", "stylus", "postcss"}
KOTLIN_SUBS = {"kotlin", "kt", "kts"}
JAVA_SUBS   = {"java", "groovy", "scala"}
GO_SUBS     = {"go"}
RUST_SUBS   = {"rust"}
DART_SUBS   = {"dart", "flutter"}
C_SUBS      = {"c", "cpp", "cc", "cxx", "c++"}
CSHARP_SUBS = {"csharp", "cs"}
SWIFT_SUBS  = {"swift"}
RUBY_SUBS   = {"ruby", "rb", "rails"}

_ALL_KNOWN_SUBS = (
    PYTHON_SUBS | JS_SUBS | HTML_SUBS | CSS_SUBS |
    KOTLIN_SUBS | JAVA_SUBS | GO_SUBS | RUST_SUBS | DART_SUBS |
    C_SUBS | CSHARP_SUBS | SWIFT_SUBS | RUBY_SUBS
)

_NO_IMPORTS_SUBS = {
    "lockfile", "npm", "gradle", "json", "yaml", "toml", "env",
    "markdown", "text", "rst", "csv", "xml", "image", "binary",
    "gitignore", "editorconfig", "prettier", "eslint", "babel",
    "properties", "ini", "conf", "docs", "config", "data",
    "maven", "python-deps", "ruby-deps", "rust-deps", "go-deps",
    "dart-deps", "sql", "graphql", "prisma", "protobuf",
    "dockerfile", "docker-compose", "terraform", "hcl", "nix",
    "github-actions", "ci", "shell", "powershell",
    "lockfile", "editorconfig", "vite", "webpack", "tailwind",
    "tsconfig",
}

_EXT_FALLBACK: dict[str, str] = {
    ".js":    "javascript", ".mjs":  "javascript", ".cjs":  "javascript",
    ".jsx":   "react",      ".ts":   "typescript",  ".tsx":  "react",
    ".py":    "python",     ".html": "html",         ".htm":  "html",
    ".css":   "css",        ".scss": "css",           ".sass": "css",
    ".less":  "css",        ".java": "java",
    ".go":    "go",         ".rs":   "rust",
    ".kt":    "kotlin",     ".kts":  "kotlin",
    ".dart":  "dart",
    ".c":     "c",          ".h":    "c",
    ".cpp":   "cpp",        ".cc":   "cpp",          ".cxx":  "cpp",
    ".hpp":   "cpp",        ".hxx":  "cpp",
    ".cs":    "csharp",
    ".swift": "swift",
    ".rb":    "ruby",       ".rake": "ruby",
}

async def analyze_file(sub: str, content: str, path: str = "") -> tuple[list, list]:
    _log.debug("analyze_file: sub=%s path=%s", sub, path)

    effective_sub = sub

    if effective_sub not in _ALL_KNOWN_SUBS:
        ext = os.path.splitext(path)[1].lower() if path else ""
        if ext in _EXT_FALLBACK:
            corrected = _EXT_FALLBACK[ext]
            _log.debug(
                "analyze_file: correcting sub '%s' → '%s' via extension %s",
                sub, corrected, ext,
            )
            effective_sub = corrected

    if effective_sub in _NO_IMPORTS_SUBS:
        _log.debug("analyze_file: skipping non-code sub '%s' path=%s", effective_sub, path)
        return [], []
    
    if effective_sub in PYTHON_SUBS:
        imp, exp = _analyze_python(content)

    elif effective_sub in JS_SUBS:
        imp, exp = _analyze_js(content)

    elif effective_sub in HTML_SUBS:
        imp, exp = _analyze_html(content)

    elif effective_sub in CSS_SUBS:
        imp, exp = _analyze_css(content)

    elif effective_sub in KOTLIN_SUBS:
        imp, exp = _analyze_kotlin(content)

    elif effective_sub in JAVA_SUBS:
        imp, exp = _analyze_java(content)

    elif effective_sub in GO_SUBS:
        imp, exp = _analyze_go(content)

    elif effective_sub in RUST_SUBS:
        imp, exp = _analyze_rust(content)

    elif effective_sub in DART_SUBS:
        imp, exp = _analyze_dart(content)

    elif effective_sub in C_SUBS:
        imp, exp = _analyze_c(content)

    elif effective_sub in CSHARP_SUBS:
        imp, exp = _analyze_csharp(content)

    elif effective_sub in SWIFT_SUBS:
        imp, exp = _analyze_swift(content)

    elif effective_sub in RUBY_SUBS:
        imp, exp = _analyze_ruby(content)

    else:
        _log.info(
            "analyze_file: sub '%s' unknown — delegating to LLM extractor (path=%s)",
            effective_sub, path,
        )
        from .llm_import_extractor import extract_imports_llm
        imp = await extract_imports_llm(effective_sub, content, path)
        exp = []
        
    if effective_sub in JS_SUBS | HTML_SUBS:
        imp.extend(_api_calls(content))

    if effective_sub in PYTHON_SUBS | {"express", "nestjs", "nodejs"}:
        exp.extend(_routes(content, effective_sub))

    _log.debug(
        "analyze_file result: sub=%s imports=%d exports=%d path=%s",
        effective_sub, len(imp), len(exp), path,
    )

    return imp, exp
