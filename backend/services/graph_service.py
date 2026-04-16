# app/services/graph_service.py

from bson import ObjectId
from pathlib import PurePosixPath
import json
import re
from database import get_database
from analysis.import_extractor import extract_imports, detect_language


async def build_dependency_graph(repo_id: str):
    """
    Build a dependency graph for a repository stored entirely in MongoDB.

    Nodes = files
    Edges = imports between files
    """

    db = get_database()

    files = await db.files.find({"repo_id": ObjectId(repo_id)}).to_list(length=None)
    if not files:
        return {"error": "No files found for this repository"}

    nodes = []
    edges = []

    # Normalize all stored paths once
    for f in files:
        f["file_path"] = f["file_path"].replace("\\", "/")

    # Lookup dictionary
    file_path_lookup = {f["file_path"]: f for f in files}

    # 1️⃣ Parse package.json for external dependencies
    external_pkgs = set()
    for f in files:
        if f["file_name"] == "package.json":
            try:
                pkg = json.loads(f.get("content", "{}"))
                external_pkgs.update(pkg.get("dependencies", {}).keys())
                external_pkgs.update(pkg.get("devDependencies", {}).keys())
            except Exception:
                pass

    # 2️⃣ Parse tsconfig.json for path aliases
    tsconfig_paths = {}
    for f in files:
        if f["file_name"] in ("tsconfig.json", "jsconfig.json"):
            try:
                content = re.sub(r'//.*', '', f.get("content", ""))
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                ts_cfg = json.loads(content)
                paths = ts_cfg.get("compilerOptions", {}).get("paths", {})
                for k, v in paths.items():
                    if k and v and isinstance(v, list) and len(v) > 0:
                        tsconfig_paths[k] = v[0]
            except Exception:
                pass

    for file in files:
        file_name = file["file_name"]
        file_path = file["file_path"]
        language = file.get("language") or detect_language(file_name)
        content = file.get("content", "")

        # --------------------
        # Add Node
        # --------------------
        nodes.append({
            "id": file_path,
            "label": file_name,
            "type": language
        })

        # --------------------
        # Extract Imports
        # --------------------
        imports = extract_imports(
            content,
            file_name=file_name,
            language=language
        )

        for imp in imports:
            resolved = resolve_import(
                source_path=file_path,
                import_name=imp,
                all_files=file_path_lookup,
                external_pkgs=external_pkgs,
                tsconfig_paths=tsconfig_paths
            )

            # Only create edge if resolved to real file
            if resolved:
                if not any(
                    e["source"] == file_path and e["target"] == resolved
                    for e in edges
                ):
                    edges.append({
                        "source": file_path,
                        "target": resolved,
                        "type": "import"
                    })

    graph_doc = {
        "repo_id": str(repo_id),
        "nodes": nodes,
        "edges": edges
    }

    result = await db.graphs.insert_one(graph_doc)
    graph_doc["_id"] = str(result.inserted_id)

    return graph_doc


# ---------------------------------------------------
# 🔥 IMPORT RESOLUTION ENGINE
# ---------------------------------------------------

def resolve_import(source_path: str, import_name: str, all_files: dict, external_pkgs: set = None, tsconfig_paths: dict = None):
    """
    Resolve an import to a real file path inside the repo.
    """

    source_path = source_path.replace("\\", "/")
    import_name = import_name.strip().replace("\\", "/")

    # 🚀 Pre-check: Skip explicit external packages
    if external_pkgs:
        base_pkg = import_name.split("/")[0]
        if import_name.startswith("@"):
            parts = import_name.split("/")
            if len(parts) >= 2:
                base_pkg = f"{parts[0]}/{parts[1]}"
        if base_pkg in external_pkgs:
            return None

    # 🚀 Pre-check: Resolve path aliases (e.g., @/* -> src/*)
    if tsconfig_paths:
        for alias, target in tsconfig_paths.items():
            alias_prefix = alias.replace("*", "")
            if import_name.startswith(alias_prefix):
                target_prefix = target.replace("*", "")
                mapped = import_name.replace(alias_prefix, target_prefix, 1)
                possible_paths = generate_possible_paths(mapped.lstrip("./"))
                for path in possible_paths:
                    if path in all_files:
                        return path

    source_dir = str(PurePosixPath(source_path).parent)

    # ------------------------------------
    # 1️⃣ Handle Relative Imports (./, ../)
    # ------------------------------------
    if import_name.startswith("."):
        level = len(import_name) - len(import_name.lstrip("."))
        remaining = import_name.lstrip(".")

        base = PurePosixPath(source_dir)

        for _ in range(level - 1):
            base = base.parent

        candidate = str(base / remaining)

        possible_paths = generate_possible_paths(candidate)

        for path in possible_paths:
            if path in all_files:
                return path

    # ------------------------------------
    # 2️⃣ Handle Python Absolute Imports
    # e.g. app.services.repo_service
    # ------------------------------------
    if "." in import_name and not import_name.startswith("."):
        candidate = import_name.replace(".", "/")
        possible_paths = generate_possible_paths(candidate)

        for path in possible_paths:
            if path in all_files:
                return path

    # ------------------------------------
    # 3️⃣ Handle JS-style relative without dots
    # e.g. "utils/helper"
    # ------------------------------------
    candidate = str(PurePosixPath(source_dir) / import_name)
    possible_paths = generate_possible_paths(candidate)

    for path in possible_paths:
        if path in all_files:
            return path

    # ------------------------------------
    # 4️⃣ Not found → External dependency
    # ------------------------------------
    return None


def generate_possible_paths(base_path: str):
    """
    Generate possible file matches for an import
    """
    return [
        base_path,
        base_path + ".py",
        base_path + ".js",
        base_path + ".ts",
        base_path + ".tsx",
        base_path + "/__init__.py",
        base_path + "/index.js",
        base_path + "/index.ts",
        base_path + "/index.tsx",
    ]

