from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Optional

from database import get_db

_FALLBACK_PALETTE = [
    "#F472B6", "#34D399", "#FBBF24", "#60A5FA", "#A78BFA",
    "#F87171", "#2DD4BF", "#E879F9", "#4ADE80", "#FB923C",
    "#818CF8", "#6EE7B7", "#FDE68A", "#C4B5FD", "#93C5FD",
]


def _make_display_name(sub_category: str) -> str:
    special = {
        "flutter":        "Flutter",
        "dart":           "Dart",
        "pubspec":        "Pubspec (Flutter)",
        "firebase":       "Firebase (Flutter)",
        "flutter-test":   "Flutter Tests",
        "fastapi":        "FastAPI",
        "nextjs":         "Next.js",
        "nestjs":         "NestJS",
        "nodejs":         "Node.js",
        "graphql":        "GraphQL",
        "prisma":         "Prisma",
        "github-actions": "GitHub Actions",
        "docker-compose": "Docker Compose",
        "scss":           "SCSS",
        "sass":           "Sass",
        "html":           "HTML",
        "css":            "CSS",
        "sql":            "SQL",
        "php":            "PHP",
        "javascript":     "JavaScript",
        "typescript":     "TypeScript",
        "csharp":         "C#",
        "cpp":            "C++",
        "objc":           "Objective-C",
        "rst":            "RST",
        "jsx":            "JSX",
        "tsx":            "TSX",
        "glsl":           "GLSL",
        "hlsl":           "HLSL",
        "wgsl":           "WGSL",
        "csv":            "CSV",
        "xml":            "XML",
        "kotlin":         "Kotlin",
        "java":           "Java",
        "swift":          "Swift",
        "ruby":           "Ruby",
        "rust":           "Rust",
        "go":             "Go",
        "c":              "C",
        "cpp":            "C++",
        "python":         "Python",
    }
    if sub_category in special:
        return special[sub_category]
    return re.sub(r"[-_]+", " ", sub_category).title()


_KNOWN_HEX = {
    "javascript": "#F1E05A", "typescript": "#3178C6", "react": "#61DAFB",
    "python": "#3572A5", "ruby": "#701516", "java": "#B07219",
    "kotlin": "#A97BFF", "go": "#00ADD8", "rust": "#DEA584",
    "c": "#555555", "cpp": "#F34B7D", "csharp": "#178600",
    "swift": "#F05138", "dart": "#00B4AB", "flutter": "#42A5F5",
    "shell": "#89E051", "html": "#E34C26", "css": "#563D7C",
    "scss": "#C6538C", "sass": "#A53B70", "sql": "#E38C00",
    "dockerfile": "#384D54", "hcl": "#844FBA", "terraform": "#844FBA",
    "vue": "#41B883", "svelte": "#FF3E00", "markdown": "#083FA1",
    "json": "#292929", "yaml": "#CB171E", "toml": "#9C4221",
}

def _hsl_to_hex(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60: r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else: r, g, b = c, 0, x
    return f"#{int((r+m)*255):02X}{int((g+m)*255):02X}{int((b+m)*255):02X}"

def _auto_color(category: str, sub_category: str, used_colors: set[str]) -> str:
    import hashlib
    if sub_category in _KNOWN_HEX:
        return _KNOWN_HEX[sub_category]
    
    # Generate deterministic unique pastel hex from the sub_category string
    hash_val = int(hashlib.md5(sub_category.encode()).hexdigest(), 16)
    h = hash_val % 360
    return _hsl_to_hex(h, 0.70, 0.65)


async def register_file_types(
    discovered: list[tuple[str, str]],
    repo_id: str,
) -> dict[str, str]:
    db = get_db()
    collection = db.language_registry
    now = datetime.now(timezone.utc).isoformat()

    existing = await collection.find({}, {"auto_color": 1}).to_list(length=None)
    used_colors = {doc["auto_color"] for doc in existing if "auto_color" in doc}

    result_map: dict[str, str] = {}
    unique_pairs = list({(c, s) for c, s in discovered})

    for category, sub_category in unique_pairs:
        key = f"{category}:{sub_category}"
        auto_color = _auto_color(category, sub_category, used_colors)
        used_colors.add(auto_color)
        display_name = _make_display_name(sub_category)

        existing_doc = await collection.find_one({"key": key})

        if existing_doc is None:
            await collection.insert_one({
                "key":          key,
                "category":     category,
                "sub_category": sub_category,
                "color":        auto_color,
                "auto_color":   auto_color,
                "custom_color": None,
                "repo_colors":  {},
                "display_name": display_name,
                "first_seen":   now,
                "last_seen":    now,
                "file_count":   1,
                "repos":        [repo_id],
            })
            result_map[key] = auto_color
        else:
            effective = existing_doc.get("repo_colors", {}).get(repo_id) or existing_doc.get("custom_color") or auto_color
            repos = existing_doc.get("repos", [])
            if repo_id not in repos:
                repos.append(repo_id)

            await collection.update_one(
                {"key": key},
                {"$set": {
                    "last_seen":  now,
                    "color":      effective,
                    "auto_color": auto_color,
                    "repos":      repos,
                }, "$inc": {"file_count": 1}},
            )
            result_map[key] = effective

    return result_map


async def get_all_languages() -> list[dict]:
    db = get_db()
    docs = await db.language_registry.find(
        {}, {"_id": 0}
    ).sort([("category", 1), ("sub_category", 1)]).to_list(length=None)
    return docs


async def get_languages_for_repo(repo_id: str) -> list[dict]:
    """Return only languages detected in a specific repo."""
    db = get_db()
    query = {"repos": repo_id} if repo_id else {}
    docs = await db.language_registry.find(
        query, {"_id": 0}
    ).sort([("category", 1), ("sub_category", 1)]).to_list(length=None)
    for d in docs:
        repo_colors = d.get("repo_colors", {})
        if repo_id and repo_id in repo_colors:
            d["color"] = repo_colors[repo_id]
            d["custom_color"] = repo_colors[repo_id]
        else:
            d["color"] = d.get("custom_color") or d.get("auto_color", "#6B7280")
            d["custom_color"] = d.get("custom_color")
    return docs


async def get_language(key: str) -> Optional[dict]:
    db = get_db()
    return await db.language_registry.find_one({"key": key}, {"_id": 0})


async def update_language_color(key: str, custom_color: Optional[str], repo_id: Optional[str] = None) -> Optional[dict]:
    # None means reset to auto color
    if custom_color is None:
        return await reset_language_color(key, repo_id)

    if not re.match(r"^#[0-9A-Fa-f]{3,8}$", custom_color):
        raise ValueError(f"Invalid hex color: {custom_color}")

    db = get_db()
    if repo_id:
        result = await db.language_registry.find_one_and_update(
            {"key": key},
            {"$set": {
                f"repo_colors.{repo_id}": custom_color,
            }},
            return_document=True,
        )
    else:
        result = await db.language_registry.find_one_and_update(
            {"key": key},
            {"$set": {
                "custom_color": custom_color,
                "color":        custom_color,
            }},
            return_document=True,
        )
        
    if result:
        result["color"] = custom_color
        result["custom_color"] = custom_color
        result.pop("_id", None)
    return result


async def reset_language_color(key: str, repo_id: Optional[str] = None) -> Optional[dict]:
    db = get_db()
    doc = await db.language_registry.find_one({"key": key})
    if not doc:
        return None
        
    if repo_id:
        result = await db.language_registry.find_one_and_update(
            {"key": key},
            {"$unset": {f"repo_colors.{repo_id}": ""}},
            return_document=True,
        )
        if result:
            resolved_color = result.get("custom_color") or result.get("auto_color", "#6B7280")
            result["color"] = resolved_color
            result["custom_color"] = result.get("custom_color")
    else:
        auto = doc.get("auto_color", "#6B7280")
        result = await db.language_registry.find_one_and_update(
            {"key": key},
            {"$set": {
                "custom_color": None,
                "color":        auto,
            }},
            return_document=True,
        )
        if result:
            result["color"] = auto
            result["custom_color"] = None
            
    if result:
        result.pop("_id", None)
    return result


async def get_color_map() -> dict[str, str]:
    docs = await get_all_languages()
    return {d["key"]: d["color"] for d in docs}
