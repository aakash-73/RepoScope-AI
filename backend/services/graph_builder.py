from __future__ import annotations
import logging
import os
import re
from collections import defaultdict
from typing import Optional

from .smart_classifier import (
    classify_file_async,
    category_color,
    edge_color,
    CATEGORY_COLORS,
)
from .language_registry import register_file_types
from .analyzer_service import (
    analyze_file as _analyze_file_dispatch,
    JS_SUBS,
    HTML_SUBS,
    JS_IMPORT_RE,  # noqa: F401
    _NO_IMPORTS_SUBS,
)

_log = logging.getLogger(__name__)

_SKIP_CATEGORIES = {"config", "docs", "data", "devops"}


async def _analyze_file(sub: str, content: str, path: str = "") -> tuple[list, list]:
    return await _analyze_file_dispatch(sub, content, path)

def _build_path_index(all_paths: set[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for p in all_paths:
        basename = os.path.basename(p)
        stem = basename.rsplit(".", 1)[0].lower()
        index[stem].append(p)
        index[p.lower()].append(p)
    return index

def _is_external_package(raw_imp: str, src_path: str = "") -> bool:
    """
    Language-aware external package detection.
    Returns True if raw_imp is an external dependency that should NOT
    be resolved to a file in the repo.
    """
    if raw_imp.startswith("http://") or raw_imp.startswith("https://"):
        return True
    if raw_imp.startswith(".") or raw_imp.startswith("/"):
        return False
    if raw_imp.startswith("~/") or raw_imp.startswith("#"):
        return False

    ext = os.path.splitext(src_path)[1].lower() if src_path else ""

    if ext in (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx"):
        if raw_imp.startswith("<") and raw_imp.endswith(">"):
            return True
        return False

    if ext in (".cs", ".csx"):
        external_namespaces = (
            "System.", "Microsoft.", "Newtonsoft.", "NUnit.",
            "Xunit.", "NLog.", "Serilog.", "AutoMapper.",
        )
        return any(raw_imp.startswith(ns) for ns in external_namespaces)

    if ext in (".swift",):
        apple_frameworks = {
            "Foundation", "UIKit", "SwiftUI", "AppKit", "CoreData",
            "CoreLocation", "MapKit", "AVFoundation", "ARKit",
            "Combine", "XCTest", "Swift", "Darwin",
        }
        if raw_imp in apple_frameworks:
            return True
        if "." in raw_imp:
            return True
        return False

    if ext in (".rb", ".rake"):
        ruby_stdlib = {
            "json", "yaml", "csv", "net/http", "uri", "date",
            "time", "fileutils", "pathname", "digest", "base64",
            "openssl", "logger", "rails", "sinatra", "rack",
        }
        if raw_imp in ruby_stdlib:
            return True
        if "/" in raw_imp:
            return False
        return True

    if ext in (".ex", ".exs"):
        return True

    if ext in (".go",):
        if "." not in raw_imp and "/" not in raw_imp:
            return True
        if raw_imp.startswith("github.com") or raw_imp.startswith("golang.org"):
            return True
        return False

    if ext in (".kt", ".kts", ".java"):
        external_prefixes = (
            "kotlin.", "java.", "javax.", "android.", "androidx.",
            "com.google.", "org.jetbrains.", "io.ktor.", "kotlinx.",
            "dagger.", "hilt.", "retrofit2.", "okhttp3.",
            "org.junit.", "junit.", "org.mockito.",
            "org.bson.", "org.mongodb.",
        )
        return any(raw_imp.startswith(p) for p in external_prefixes)

    if raw_imp.startswith("@"):
        return True
    if "/" in raw_imp:
        left = raw_imp.split("/")[0]
        if re.match(r'^[a-z@][a-z0-9\-]*$', left):
            return True
        return False
    if "-" in raw_imp and "." not in raw_imp:
        return True

    return False

def _resolve_import(
    raw_imp: str,
    src_path: str,
    all_paths: set[str],
    path_index: dict[str, list[str]],
) -> Optional[str]:
    if not raw_imp:
        return None

    if _is_external_package(raw_imp, src_path):
        _log.debug("  EXTERNAL (dropped): %s (from %s)", raw_imp, src_path)
        return None

    imp = raw_imp.strip("<>").split("?")[0]
    src_dir = os.path.dirname(src_path)
    src_ext = os.path.splitext(src_path)[1].lower()

    if imp.startswith("."):
        resolved = os.path.normpath(os.path.join(src_dir, imp))
        resolved = resolved.replace("\\", "/").lstrip("/")

        if resolved in all_paths:
            _log.debug("  RESOLVED (exact): %s → %s", raw_imp, resolved)
            return resolved

        resolved_lower = resolved.lower()
        candidates = path_index.get(resolved_lower, [])
        if len(candidates) == 1:
            _log.debug("  RESOLVED (ci-exact): %s → %s", raw_imp, candidates[0])
            return candidates[0]
        if len(candidates) > 1:
            best = _best_dir_match(resolved, candidates)
            _log.debug("  RESOLVED (ci-multi): %s → %s", raw_imp, best)
            return best

        for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
                    ".py", ".kt", ".java", ".go", ".rs", ".dart",
                    ".cpp", ".cc", ".c", ".h", ".hpp", ".swift",
                    ".rb", ".ex", ".exs", ".cs", ".fs"):
            candidate = resolved + ext
            if candidate in all_paths:
                _log.debug("  RESOLVED (ext %s): %s → %s", ext, raw_imp, candidate)
                return candidate
            ci_candidates = path_index.get((resolved + ext).lower(), [])
            if ci_candidates:
                _log.debug("  RESOLVED (ci-ext %s): %s → %s", ext, raw_imp, ci_candidates[0])
                return ci_candidates[0]

        for idx in ("index.js", "index.jsx", "index.ts", "index.tsx",
                    "__init__.py", "mod.rs"):
            candidate = resolved + "/" + idx
            if candidate in all_paths:
                _log.debug("  RESOLVED (barrel): %s → %s", raw_imp, candidate)
                return candidate
            ci_candidates = path_index.get((resolved + "/" + idx).lower(), [])
            if ci_candidates:
                _log.debug("  RESOLVED (ci-barrel): %s → %s", raw_imp, ci_candidates[0])
                return ci_candidates[0]

        _log.debug(
            "  UNRESOLVED (relative): %s (from %s) — tried '%s'",
            raw_imp, src_path, resolved,
        )
        return None

    for prefix in ("@/", "~/", "/src/", "@/src/"):
        if imp.startswith(prefix):
            imp = imp[len(prefix):]
            break

    if src_ext in (".kt", ".kts", ".java", ".cs") and "." in imp:
        path_form = imp.replace(".", "/")
        for ext in (".kt", ".java", ".cs", ".kts"):
            candidate = path_form + ext
            if candidate in all_paths:
                _log.debug("  RESOLVED (dotted-path): %s → %s", raw_imp, candidate)
                return candidate
            ci_candidates = path_index.get(candidate.lower(), [])
            if ci_candidates:
                _log.debug("  RESOLVED (ci-dotted): %s → %s", raw_imp, ci_candidates[0])
                return ci_candidates[0]

        for root in ("app/src/main/java", "app/src/main/kotlin", "src/main/java", "src/main/kotlin", "src"):
            rooted = root + "/" + path_form
            for ext in (".kt", ".java", ".cs", ".kts"):
                candidate = rooted + ext
                if candidate in all_paths:
                    _log.debug("  RESOLVED (dotted-rooted): %s → %s", raw_imp, candidate)
                    return candidate
                ci_candidates = path_index.get(candidate.lower(), [])
                if ci_candidates:
                    _log.debug("  RESOLVED (ci-dotted-rooted): %s → %s", raw_imp, ci_candidates[0])
                    return ci_candidates[0]

    if src_ext in (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx"):
        candidate = os.path.normpath(os.path.join(src_dir, imp))
        candidate = candidate.replace("\\", "/").lstrip("/")
        if candidate in all_paths:
            _log.debug("  RESOLVED (cpp-relative): %s → %s", raw_imp, candidate)
            return candidate
        ci_candidates = path_index.get(candidate.lower(), [])
        if ci_candidates:
            _log.debug("  RESOLVED (cpp-ci): %s → %s", raw_imp, ci_candidates[0])
            return ci_candidates[0]
        for root in ("src", "include", "lib", ""):
            rooted = (root + "/" + imp).lstrip("/")
            if rooted in all_paths:
                _log.debug("  RESOLVED (cpp-root): %s → %s", raw_imp, rooted)
                return rooted
            ci_candidates = path_index.get(rooted.lower(), [])
            if ci_candidates:
                _log.debug("  RESOLVED (cpp-ci-root): %s → %s", raw_imp, ci_candidates[0])
                return ci_candidates[0]

    if "." in imp and "/" not in imp:
        stem = imp.split(".")[-1].lower()
    else:
        stem = os.path.basename(imp).rsplit(".", 1)[0].lower()

    candidates = path_index.get(stem, [])

    if not candidates:
        _log.debug("  UNRESOLVED (stem): %s — stem '%s' not in index", raw_imp, stem)
        return None
    if len(candidates) == 1:
        _log.debug("  RESOLVED (stem): %s → %s", raw_imp, candidates[0])
        return candidates[0]

    best = _best_dir_match(src_path, candidates)
    _log.debug("  RESOLVED (stem-proximity): %s → %s", raw_imp, best)
    return best

def _best_dir_match(reference_path: str, candidates: list[str]) -> str:
    ref_parts = reference_path.lower().replace("\\", "/").split("/")

    def score(candidate: str) -> int:
        cand_parts = candidate.lower().replace("\\", "/").split("/")
        common = 0
        for a, b in zip(ref_parts, cand_parts):
            if a == b:
                common += 1
            else:
                break
        return common

    return max(candidates, key=score)

def _css_html_match(imp: str, all_paths: set, path_index: dict) -> Optional[str]:
    css_name = os.path.basename(imp.split("?")[0]).lower()
    candidates = path_index.get(css_name.rsplit(".", 1)[0], [])
    for p in candidates:
        if p.endswith((".css", ".scss", ".sass", ".less")):
            return p
    return None


def _norm(r: str) -> str:
    r = r.split("?")[0]
    r = re.sub(r"\{[^}]+\}", "", r)
    r = re.sub(r":[A-Za-z_]\w*", "", r)
    r = re.sub(r"//+", "/", r)
    return r.rstrip("/")


def _match_axios_to_backend(fe_call: str, backend_routes: dict) -> Optional[str]:
    norm_fe = _norm(fe_call)
    for route_path, backend_file in backend_routes.items():
        norm_be = _norm(route_path)
        if not norm_be:
            continue
        if norm_fe == norm_be or norm_fe.endswith(norm_be):
            return backend_file
    return None

def detect_cycles(adjacency: dict) -> list[list]:
    WHITE, GRAY, BLACK = 0, 1, 2

    all_nodes: set[str] = set(adjacency.keys())
    for targets in adjacency.values():
        all_nodes.update(targets)

    seen_normalized: set[tuple] = set()
    cycles: list[list] = []
    no_cycle_nodes: set[str] = set()

    for start in list(all_nodes):
        if start in no_cycle_nodes:
            continue

        color: dict[str, int] = {n: WHITE for n in all_nodes}
        color[start] = GRAY

        found_any = False
        stack: list[tuple[str, object, list[str]]] = [
            (start, iter(adjacency.get(start, set())), [start])
        ]

        while stack:
            node, neighbors, path = stack[-1]
            try:
                nb = next(neighbors)
                nb_color = color.get(nb, WHITE)

                if nb_color == GRAY:
                    cycle_start = path.index(nb)
                    cycle = path[cycle_start:] + [nb]
                    body = cycle[:-1]
                    min_idx = body.index(min(body))
                    normalized = body[min_idx:] + body[:min_idx] + [body[min_idx]]
                    norm_key = tuple(normalized)

                    if norm_key not in seen_normalized:
                        seen_normalized.add(norm_key)
                        cycles.append(normalized)
                        found_any = True
                        _log.debug("CYCLE FOUND: %s", " → ".join(normalized))

                elif nb_color == WHITE:
                    color[nb] = GRAY
                    stack.append((nb, iter(adjacency.get(nb, set())), path + [nb]))

            except StopIteration:
                color[node] = BLACK
                stack.pop()

        if not found_any:
            no_cycle_nodes.add(start)

    _log.debug("Total cycles found: %d", len(cycles))
    return cycles

async def build_dependency_graph(files: list[dict], repo_id: str = "unknown") -> dict:
    all_paths = {f["path"] for f in files}
    path_index = _build_path_index(all_paths)

    analysis: dict[str, dict] = {}
    file_meta: dict[str, dict] = {}

    for f in files:
        content = f.get("content", "")

        cat, sub = await classify_file_async(f["path"], content)
        file_meta[f["path"]] = {"category": cat, "sub_category": sub}

        ext = os.path.splitext(f["path"])[1].lower()
        if ext not in (".md", ".json", ".lock", ".yaml", ".yml", ".txt", ".env", ".png", ".jpg", ".svg", ".ico", ".gif", ".webp"):
            _log.debug("CLASSIFY: %s → cat=%s sub=%s", f["path"], cat, sub)

        if cat in _SKIP_CATEGORIES or sub in _NO_IMPORTS_SUBS:
            analysis[f["path"]] = {"imports": [], "exports": []}
        else:
            imp, exp = await _analyze_file(sub, content, f["path"])
            analysis[f["path"]] = {"imports": imp, "exports": exp}

    for f in files:
        p = f["path"]
        meta = file_meta[p]
        if meta["sub_category"] not in (
            "css", "html", "image", "config", "docs", "lock",
            "json", "yaml", "lockfile", "npm", "gradle", "sql",
        ):
            _log.debug(
                "FILE: %s | sub=%s | imports=%s",
                p, meta["sub_category"], analysis[p]["imports"],
            )

    discovered = [(m["category"], m["sub_category"]) for m in file_meta.values()]
    try:
        color_map = await register_file_types(discovered, repo_id)
    except Exception:
        color_map = {}

    backend_route_map: dict[str, str] = {}
    for f in files:
        if file_meta[f["path"]]["category"] == "backend":
            for route in analysis[f["path"]]["exports"]:
                if route.startswith("/"):
                    backend_route_map[route] = f["path"]

    adjacency: dict[str, set] = defaultdict(set)
    edge_types: dict[tuple, str] = {}

    def connect(src: str, tgt: str, color: str) -> None:
        if src != tgt:
            adjacency[src].add(tgt)
            edge_types[(src, tgt)] = color

    _log.debug("=== RESOLVING IMPORTS for repo %s ===", repo_id)

    for f in files:
        src     = f["path"]
        src_cat = file_meta[src]["category"]

        for imp in analysis[src]["imports"]:
            imp_clean_lower = imp.split("?")[0].lower()
            if any(imp_clean_lower.endswith(e) for e in (".css", ".scss", ".sass", ".less")):
                tgt = _css_html_match(imp, all_paths, path_index)
                if tgt:
                    connect(src, tgt, CATEGORY_COLORS["css"])
                continue

            tgt = _resolve_import(imp, src, all_paths, path_index)
            if tgt and tgt != src:
                tgt_cat = file_meta[tgt]["category"]
                connect(src, tgt, edge_color(src_cat, tgt_cat))
                continue

            if imp.startswith("/") or imp.startswith("http"):
                be_file = _match_axios_to_backend(imp, backend_route_map)
                if be_file and be_file != src:
                    connect(src, be_file, edge_color(src_cat, "backend"))
                    continue
                fe_norm = _norm(imp)
                for p, data in analysis.items():
                    if file_meta[p]["category"] != "backend":
                        continue
                    for r in data["exports"]:
                        if r.startswith("/") and (
                            fe_norm.endswith(_norm(r)) or _norm(r).endswith(fe_norm)
                        ):
                            connect(src, p, edge_color(src_cat, "backend"))

    _log.debug("=== ADJACENCY DUMP for repo %s ===", repo_id)
    for src, targets in adjacency.items():
        for tgt in targets:
            _log.debug("EDGE: %s → %s", src, tgt)
    _log.debug(
        "=== END ADJACENCY DUMP (%d edges total) ===",
        sum(len(t) for t in adjacency.values()),
    )

    cycles = detect_cycles(adjacency)

    # ── Dependency Depth (BFS from roots) ──────────────────────────────
    all_graph_nodes = {f["path"] for f in files}
    in_degree = {n: 0 for n in all_graph_nodes}
    for src, targets in adjacency.items():
        if src not in in_degree:
            in_degree[src] = 0
        for tgt in targets:
            if tgt in in_degree:
                in_degree[tgt] += 1
            else:
                in_degree[tgt] = 1

    roots = [n for n, deg in in_degree.items() if deg == 0]
    depths: dict[str, int] = {}
    queue = [(r, 0) for r in roots]
    for r in roots:
        depths[r] = 0

    while queue:
        curr, d = queue.pop(0)
        for tgt in adjacency.get(curr, []):
            if tgt not in depths or d + 1 < depths[tgt]:
                depths[tgt] = d + 1
                queue.append((tgt, d + 1))

    # ── Dead Code Detection ────────────────────────────────────────────
    _ENTRY_BASENAMES = {
        "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py", "server.py",
        "index.js", "index.ts", "index.jsx", "index.tsx",
        "main.js", "main.ts", "main.jsx", "main.tsx",
        "app.js", "app.ts", "app.jsx", "app.tsx",
        "server.js", "server.ts",
        "mod.rs", "lib.rs", "main.rs",
        "main.go", "main.java", "main.kt",
        "program.cs",
        "index.html",
        "vite.config.js", "vite.config.ts",
        "next.config.js", "next.config.ts", "next.config.mjs",
        "webpack.config.js", "rollup.config.js", "tailwind.config.js",
        "postcss.config.js", "babel.config.js", "jest.config.js",
        "tsconfig.json", "package.json",
        "setup.py", "setup.cfg", "pyproject.toml",
        "gemfile", "rakefile", "cargo.toml", "go.mod",
    }
    _ENTRY_PATTERNS = re.compile(
        r"(^|/)("
        r"__init__\.py|__main__\.py"
        r"|routes?\.(py|js|ts|jsx|tsx)"
        r"|urls\.py"
        r"|settings\.py"
        r"|conftest\.py"
        r"|dockerfile"
        r"|makefile"
        r"|cmakelists\.txt"
        r")$",
        re.IGNORECASE,
    )

    def _is_entry_point(path: str) -> bool:
        basename = os.path.basename(path).lower()
        if basename in _ENTRY_BASENAMES:
            return True
        if _ENTRY_PATTERNS.search(path.lower()):
            return True
        return False

    dead_code_ids: set[str] = set()
    for p in all_graph_nodes:
        if in_degree.get(p, 0) == 0 and not _is_entry_point(p):
            cat = file_meta[p]["category"]
            sub = file_meta[p]["sub_category"]
            # Skip config/docs/data — those are expected to have no importers
            if cat not in _SKIP_CATEGORIES and sub not in _NO_IMPORTS_SUBS:
                dead_code_ids.add(p)

    # ── Test Coverage Mapping ──────────────────────────────────────────
    _TEST_PATTERNS = re.compile(
        r"(^|/)(test_[^/]+|[^/]+[._]test\.[^/]+|[^/]+[._]spec\.[^/]+|__tests__/[^/]+|tests?/[^/]+)$",
        re.IGNORECASE,
    )

    test_files: set[str] = set()
    tested_files: set[str] = set()

    for p in all_graph_nodes:
        if _TEST_PATTERNS.search(p):
            test_files.add(p)

    # Trace what each test imports → those source files are "tested"
    for tf in test_files:
        for tgt in adjacency.get(tf, []):
            if tgt not in test_files:
                tested_files.add(tgt)

    # ── Coupling Score ─────────────────────────────────────────────────
    coupling_scores: dict[tuple, int] = {}
    for src, targets in adjacency.items():
        for tgt in targets:
            pair = tuple(sorted([src, tgt]))
            coupling_scores[pair] = coupling_scores.get(pair, 0) + 1
    # Pairs with score > 1 are bidirectionally coupled or share many imports

    # ── Build Nodes & Edges ────────────────────────────────────────────
    circular_nodes: set[str] = set()
    circular_edges: set[tuple] = set()
    for cycle in cycles:
        for i, node in enumerate(cycle[:-1]):
            circular_nodes.add(node)
            circular_edges.add((cycle[i], cycle[i + 1]))

    nodes, edges = [], []

    for f in files:
        node_id = f["path"].replace("/", "__").replace(".", "_")
        meta    = file_meta[f["path"]]
        cat, sub = meta["category"], meta["sub_category"]
        node_color = color_map.get(f"{cat}:{sub}") or category_color(cat)

        nodes.append({
            "id":   node_id,
            "type": "codeNode",
            "position": {"x": 0, "y": 0},
            "data": {
                "label":        f["name"],
                "file_path":    f["path"],
                "github_url":   f.get("github_url", ""),
                "language":     sub,
                "category":     cat,
                "sub_category": sub,
                "node_color":   node_color,
                "lines":        len(f.get("content", "").splitlines()),
                "dependency_depth": depths.get(f["path"], -1),
                "imports":      analysis[f["path"]]["imports"],
                "exports":      analysis[f["path"]]["exports"],
                "is_circular":  f["path"] in circular_nodes,
                "is_dead_code": f["path"] in dead_code_ids,
                "is_test_file": f["path"] in test_files,
                "is_tested":    f["path"] in tested_files,
                "folder":       os.path.dirname(f["path"]) or ".",
                "analysis_status": f.get("analysis_status", "pending"),
            },
        })

    for src, targets in adjacency.items():
        sid = src.replace("/", "__").replace(".", "_")
        for tgt in targets:
            tid   = tgt.replace("/", "__").replace(".", "_")
            is_ce = (src, tgt) in circular_edges
            color = "#FF4500" if is_ce else edge_types.get((src, tgt), "#B6FF3B")
            pair  = tuple(sorted([src, tgt]))
            c_score = coupling_scores.get(pair, 0)
            edges.append({
                "id":          f"e_{sid}_{tid}",
                "source":      sid,
                "target":      tid,
                "style":       {"stroke": color, "strokeWidth": 3 if is_ce else 1.5},
                "animated":    is_ce,
                "is_circular": is_ce,
                "coupling_score": c_score,
            })

    seen_cycles: set[tuple] = set()
    unique_cycles: list[list] = []
    for cycle in cycles:
        key = tuple(cycle)
        if key not in seen_cycles:
            seen_cycles.add(key)
            unique_cycles.append(cycle)

    _log.debug("=== FINAL CYCLES for repo %s: %d ===", repo_id, len(unique_cycles))
    for i, cycle in enumerate(unique_cycles):
        _log.debug("  Cycle %d: %s", i + 1, " → ".join(cycle))

    return {"nodes": nodes, "edges": edges, "circular_paths": unique_cycles}
