from __future__ import annotations

"""
sync_service.py — GitHub repo sync engine

Flow:
  1. Fetch latest commit SHA from GitHub API
  2. Compare against stored SHA — if same, return early (no changes)
  3. Download fresh ZIP
  4. Diff against stored files using content hashes:
       • Added   — path exists in new ZIP but not in DB
       • Modified — path exists in both but content hash differs
       • Deleted  — path exists in DB but not in new ZIP
  5. Apply diff to MongoDB:
       • Added/modified → upsert file doc, mark analysis_status=pending
       • Deleted        → remove file doc + all related analysis docs
  6. Trigger selective re-analysis:
       • Changed files + all files that import them (dependents)
  7. Update stored commit SHA + last_synced_at
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from database import get_db
from services.github_service import (
    download_and_extract,
    get_latest_commit_sha,
)
from services.analyzer_service import analyze_file
from services.smart_classifier import classify_file_async
from services.node_analyzer_service import _analyze_single_node
from models.repository import SyncResponse

logger = logging.getLogger(__name__)


def _content_hash(content: str) -> str:
    """MD5 hash of file content — fast, good enough for change detection."""
    return hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()


async def sync_repository(repo_id: str) -> SyncResponse:
    """
    Main entry point for manual sync. Called by the sync route.
    Returns a SyncResponse describing what changed.
    """
    db = get_db()

    # ── 1. Load repo doc ──────────────────────────────────────────────────
    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    if repo.get("status") not in ("ready",):
        raise ValueError(
            f"Repository is currently '{repo.get('status')}'. "
            "Only ready repositories can be synced."
        )

    github_url = repo["github_url"]
    branch     = repo["branch"]
    repo_name  = repo["name"]

    # ── 2. Check commit SHA — skip download if nothing changed ────────────
    stored_sha = repo.get("last_commit_sha")
    latest_sha = await get_latest_commit_sha(github_url, branch)

    if latest_sha and stored_sha and latest_sha == stored_sha:
        logger.info("Repo %s is already up to date (SHA %s)", repo_id, latest_sha[:8])
        return SyncResponse(
            repo_id=repo_id,
            name=repo_name,
            message="Repository is already up to date. No changes detected.",
            status="no_changes",
        )

    logger.info(
        "Syncing repo %s — stored SHA: %s → latest SHA: %s",
        repo_id,
        (stored_sha or "none")[:8],
        (latest_sha or "unknown")[:8],
    )

    # ── 3. Download fresh ZIP ─────────────────────────────────────────────
    try:
        fresh_files = await download_and_extract(github_url, branch)
    except Exception as e:
        raise ValueError(f"Failed to download repository: {e}")

    # Build a map of path → file dict for the fresh download
    fresh_map = {f["path"]: f for f in fresh_files}

    # ── 4. Load existing files from MongoDB ───────────────────────────────
    cursor = db.files.find(
        {"repo_id": repo_id},
        {"path": 1, "content_hash": 1, "content": 1},
    )
    existing_files = await cursor.to_list(length=None)

    # Build path → stored hash map
    # If content_hash wasn't stored (older import), compute it from content
    stored_map: dict[str, str] = {}
    for f in existing_files:
        stored_hash = f.get("content_hash") or _content_hash(f.get("content", ""))
        stored_map[f["path"]] = stored_hash

    fresh_paths   = set(fresh_map.keys())
    existing_paths = set(stored_map.keys())

    added_paths    = fresh_paths - existing_paths
    deleted_paths  = existing_paths - fresh_paths
    common_paths   = fresh_paths & existing_paths

    modified_paths = {
        p for p in common_paths
        if _content_hash(fresh_map[p]["content"]) != stored_map[p]
    }

    changed_paths = added_paths | modified_paths

    logger.info(
        "Repo %s diff — added: %d, modified: %d, deleted: %d",
        repo_id, len(added_paths), len(modified_paths), len(deleted_paths),
    )

    # ── 5a. Delete removed files ──────────────────────────────────────────
    if deleted_paths:
        await db.files.delete_many(
            {"repo_id": repo_id, "path": {"$in": list(deleted_paths)}}
        )
        await db.node_analysis.delete_many(
            {"repo_id": repo_id, "file_path": {"$in": list(deleted_paths)}}
        )
        await db.file_explanations.delete_many(
            {"repo_id": repo_id, "path": {"$in": list(deleted_paths)}}
        )
        logger.info("Deleted %d files from repo %s", len(deleted_paths), repo_id)

    # ── 5b. Upsert added + modified files ─────────────────────────────────
    for path in changed_paths:
        f = fresh_map[path]
        cat, sub = await classify_file_async(f["path"], f.get("content", ""), repo_id)
        imports, exports = await analyze_file(sub, f["content"], f["path"])

        file_doc = {
            "repo_id":         repo_id,
            "path":            f["path"],
            "name":            f["name"],
            "extension":       f["extension"],
            "content":         f["content"],
            "size":            f["size"],
            "language":        sub,
            "github_url":      f.get("github_url", ""),
            "imports":         imports,
            "exports":         exports,
            "content_hash":    _content_hash(f["content"]),
            "analysis_status": "pending",   # triggers ghosting in the graph
        }

        await db.files.update_one(
            {"repo_id": repo_id, "path": path},
            {"$set": file_doc},
            upsert=True,
        )

        # Clear stale analysis and explanation for this file
        await db.node_analysis.delete_one(
            {"repo_id": repo_id, "file_path": path}
        )
        await db.file_explanations.delete_one(
            {"repo_id": repo_id, "path": path}
        )

    # ── 5c. Backfill content_hash for unchanged files (first sync only) ───
    # Files imported before sync support existed have no content_hash stored.
    # Backfill now so future syncs can do fast hash comparisons.
    files_without_hash = await db.files.find(
        {"repo_id": repo_id, "content_hash": {"$exists": False}},
        {"path": 1, "content": 1},
    ).to_list(length=None)

    for f in files_without_hash:
        await db.files.update_one(
            {"repo_id": repo_id, "path": f["path"]},
            {"$set": {"content_hash": _content_hash(f.get("content", ""))}},
        )

    # ── 6. Determine which files need re-analysis ─────────────────────────
    # Changed files + all files that directly import any changed file
    # (dependents might need to update their dependency summaries)
    all_files_cursor = db.files.find({"repo_id": repo_id})
    all_files = await all_files_cursor.to_list(length=None)

    dependent_paths: set[str] = set()
    for f in all_files:
        file_imports = set(f.get("imports", []))
        if file_imports & changed_paths:
            # This file imports at least one changed file → re-analyze it
            dependent_paths.add(f["path"])

    # Don't double-count files already in changed_paths
    dependents_only = dependent_paths - changed_paths
    paths_to_reanalyze = changed_paths | dependents_only

    logger.info(
        "Repo %s — re-analyzing %d files (%d changed + %d dependents)",
        repo_id,
        len(paths_to_reanalyze),
        len(changed_paths),
        len(dependents_only),
    )

    # Mark dependents as pending too so they ghost in the graph
    if dependents_only:
        await db.files.update_many(
            {"repo_id": repo_id, "path": {"$in": list(dependents_only)}},
            {"$set": {"analysis_status": "pending"}},
        )
        await db.node_analysis.delete_many(
            {"repo_id": repo_id, "file_path": {"$in": list(dependents_only)}}
        )

    # ── 7. Update repo metadata ───────────────────────────────────────────
    new_file_count = len(fresh_paths) - len(deleted_paths) + len(added_paths)
    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {
            "file_count":      len(fresh_map),
            "last_commit_sha": latest_sha or stored_sha,
            "last_synced_at":  datetime.now(timezone.utc),
            "analysis_status": "analyzing" if paths_to_reanalyze else "understood",
        }},
    )

    # Invalidate repo-level cache so next chat/summary uses fresh data
    from controllers.repo_chat_controller import invalidate_repo_cache
    await invalidate_repo_cache(repo_id)

    # ── 8. Trigger selective re-analysis in background ────────────────────
    if paths_to_reanalyze:
        asyncio.create_task(
            _reanalyze_changed_nodes(repo_id, paths_to_reanalyze, all_files)
        )

    return SyncResponse(
        repo_id=repo_id,
        name=repo_name,
        added=len(added_paths),
        modified=len(modified_paths),
        deleted=len(deleted_paths),
        reanalyzed=len(paths_to_reanalyze),
        message=(
            f"Sync complete — {len(added_paths)} added, "
            f"{len(modified_paths)} modified, "
            f"{len(deleted_paths)} deleted, "
            f"{len(paths_to_reanalyze)} queued for re-analysis."
        ),
        status="synced",
    )


async def _reanalyze_changed_nodes(
    repo_id: str,
    paths_to_reanalyze: set[str],
    all_files: list[dict],
) -> None:
    """
    Background task: re-analyzes only the changed/dependent files one at a time.
    Uses the same sequential strategy as analyze_all_nodes() for hardware
    efficiency and accurate solidification animation.

    Runs a topological sort over just the affected subset so dependencies
    within the changed set are still processed in the right order.
    """
    db = get_db()

    # Refresh all_files from DB to pick up the newly upserted content
    cursor = db.files.find({"repo_id": repo_id})
    all_files_fresh = await cursor.to_list(length=None)
    file_map = {f["path"]: f for f in all_files_fresh}

    # Topological sort of just the affected files
    from services.node_analyzer_service import _sort_by_dependency_order
    affected_docs = [file_map[p] for p in paths_to_reanalyze if p in file_map]
    sorted_affected = _sort_by_dependency_order(affected_docs)

    logger.info(
        "Re-analysis background task started for repo %s — %d files",
        repo_id, len(sorted_affected),
    )

    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {"analysis_status": "analyzing"}},
    )

    for file_doc in sorted_affected:
        await _analyze_single_node(repo_id, file_doc, all_files_fresh)

    # Mark repo as done
    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {"analysis_status": "understood"}},
    )

    logger.info("Re-analysis complete for repo %s", repo_id)