import httpx
import zipfile
import io
import re
from typing import List, Dict, Optional
from config import settings


SUPPORTED_EXTENSIONS = {
    # Frontend
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".vue", ".svelte", ".astro", ".elm", ".coffee",
    # HTML / Templates
    ".html", ".htm", ".jinja", ".jinja2", ".j2", ".njk",
    ".hbs", ".mustache", ".ejs", ".pug", ".haml", ".erb",
    # CSS
    ".css", ".scss", ".sass", ".less", ".styl", ".pcss",
    # Backend
    ".py", ".pyi", ".rb", ".rake",
    ".java", ".kt", ".kts", ".groovy", ".scala",
    ".go", ".rs",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
    ".cs", ".pl", ".pm",
    ".ex", ".exs", ".erl",
    ".lua", ".hs",
    ".sh", ".bash", ".zsh", ".fish", ".ps1",
    # Database
    ".sql", ".prisma", ".graphql", ".gql",
    # Mobile
    ".swift", ".m", ".mm", ".dart",
    # DevOps / Config
    ".tf", ".tfvars", ".hcl", ".gradle",
    ".json", ".json5", ".toml", ".yaml", ".yml",
    ".ini", ".cfg", ".conf", ".env",
    # Docs
    ".md", ".mdx", ".rst", ".txt",
    # Shader
    ".glsl", ".vert", ".frag", ".hlsl", ".wgsl",
    # Data
    ".csv", ".xml", ".proto",
    # PHP
    ".php",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    "egg-info", ".tox",
}

LANGUAGE_MAP = {
    ".py": "python",      ".pyi": "python",     ".pyw": "python",
    ".js": "javascript",  ".mjs": "javascript",  ".cjs": "javascript",
    ".jsx": "react",      ".ts": "typescript",   ".tsx": "react",
    ".vue": "vue",        ".svelte": "svelte",   ".astro": "astro",
    ".elm": "elm",        ".coffee": "coffeescript",
    ".html": "html",      ".htm": "html",        ".jinja": "jinja",
    ".jinja2": "jinja",   ".j2": "jinja",        ".njk": "nunjucks",
    ".hbs": "handlebars", ".mustache": "mustache", ".ejs": "ejs",
    ".pug": "pug",        ".haml": "haml",       ".erb": "erb",
    ".php": "php",
    ".css": "css",        ".scss": "scss",       ".sass": "sass",
    ".less": "less",      ".styl": "stylus",     ".pcss": "postcss",
    ".java": "java",      ".kt": "kotlin",       ".kts": "kotlin",
    ".groovy": "groovy",  ".scala": "scala",
    ".go": "go",          ".rs": "rust",
    ".c": "c",            ".h": "c",             ".cpp": "cpp",
    ".cc": "cpp",         ".cxx": "cpp",         ".hpp": "cpp",
    ".cs": "csharp",      ".rb": "ruby",         ".rake": "ruby",
    ".pl": "perl",        ".pm": "perl",
    ".ex": "elixir",      ".exs": "elixir",      ".erl": "erlang",
    ".lua": "lua",        ".hs": "haskell",
    ".sh": "shell",       ".bash": "shell",      ".zsh": "shell",
    ".fish": "shell",     ".ps1": "powershell",
    ".swift": "swift",    ".m": "objc",          ".mm": "objc",
    ".dart": "dart",
    ".sql": "sql",        ".prisma": "prisma",   ".graphql": "graphql",
    ".gql": "graphql",    ".tf": "terraform",    ".tfvars": "terraform",
    ".json": "json",      ".json5": "json",      ".toml": "toml",
    ".yaml": "yaml",      ".yml": "yaml",        ".ini": "ini",
    ".cfg": "ini",        ".conf": "conf",       ".env": "env",
    ".md": "markdown",    ".mdx": "markdown",    ".rst": "rst",
    ".txt": "text",       ".glsl": "glsl",       ".vert": "glsl",
    ".frag": "glsl",      ".hlsl": "hlsl",       ".wgsl": "wgsl",
    ".csv": "csv",        ".xml": "xml",         ".proto": "protobuf",
    ".gradle": "gradle",
}

FALLBACK_BRANCHES = ["main", "master", "develop", "dev"]


def _parse_github_url(url: str):
    """Return (owner, repo) from various github URL forms."""
    url = url.strip().rstrip("/")
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if match:
        return match.group(1), match.group(2)
    match = re.match(r"^([^/]+)/([^/]+)$", url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"Cannot parse GitHub URL: {url}")


def _build_headers() -> dict:
    headers = {"User-Agent": "reposcope-ai/1.0"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def _fetch_zip(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    headers: dict,
) -> Optional[httpx.Response]:
    """Try to download the ZIP for a specific branch. Returns response or None if 404."""
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    response = await client.get(zip_url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response


# ── NEW: commit SHA fetcher ────────────────────────────────────────────────────
async def get_latest_commit_sha(github_url: str, branch: str) -> Optional[str]:
    """
    Fetch the HEAD commit SHA for a branch using the GitHub API.
    Returns the SHA string or None if it can't be determined
    (e.g. no token, private repo, API rate limit hit).

    Used by sync_service to check whether the repo has changed since last
    import without downloading the full ZIP.
    """
    try:
        owner, repo = _parse_github_url(github_url)
        headers = _build_headers()
        headers["Accept"] = "application/vnd.github.v3+json"

        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data.get("sha")

        # 403 = rate limited, 404 = not found, 401 = bad token
        return None

    except Exception:
        return None


async def download_and_extract(github_url: str, branch: str = "main") -> List[Dict]:
    owner, repo = _parse_github_url(github_url)
    headers = _build_headers()

    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        response = await _fetch_zip(client, owner, repo, branch, headers)
        resolved_branch = branch

        if response is None:
            tried = [branch]
            for fallback in FALLBACK_BRANCHES:
                if fallback in tried:
                    continue
                tried.append(fallback)
                response = await _fetch_zip(client, owner, repo, fallback, headers)
                if response is not None:
                    resolved_branch = fallback
                    break

        if response is None:
            tried_str = ", ".join(f"'{b}'" for b in tried)
            raise ValueError(
                f"Repository '{owner}/{repo}' not found or branch not accessible. "
                f"Tried branches: {tried_str}. "
                f"Please check the URL and that the repository is public."
            )

    if resolved_branch != branch:
        import logging
        logging.getLogger(__name__).warning(
            "Branch '%s' not found for %s/%s — fell back to '%s'",
            branch, owner, repo, resolved_branch,
        )

    return _extract_zip(response.content, owner, repo, resolved_branch)


def _extract_zip(
    zip_bytes: bytes,
    owner: str,
    repo: str,
    branch: str = "main",
) -> List[Dict]:
    files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue

            parts = member.filename.split("/")
            if len(parts) < 2:
                continue

            relative_path = "/".join(parts[1:])

            if any(skip in parts for skip in SKIP_DIRS):
                continue

            ext = "." + relative_path.rsplit(".", 1)[-1] if "." in relative_path else ""
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            try:
                content_bytes = zf.read(member.filename)
                content = content_bytes.decode("utf-8", errors="replace")
            except Exception:
                continue

            if len(content) > 500_000:
                continue

            filename = parts[-1]
            files.append({
                "path":       relative_path,
                "name":       filename,
                "extension":  ext,
                "content":    content,
                "size":       len(content),
                "language":   LANGUAGE_MAP.get(ext, "unknown"),
                "github_url": f"https://github.com/{owner}/{repo}/blob/{branch}/{relative_path}",
            })

    return files