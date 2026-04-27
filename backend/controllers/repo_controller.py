import uuid
import hashlib

from typing import List

from database import get_db
from models.repository import (
    ImportRequest, ImportResponse,
    ExplainRequest, ExplainResponse,
    GraphResponse, RepoSummary, SyncResponse,
)
from pymongo.errors import DuplicateKeyError
from services.github_service import download_and_extract, _parse_github_url, get_latest_commit_sha
from services.graph_builder import build_dependency_graph
from services.analyzer_service import analyze_file
from services.smart_classifier import classify_file_async
from services.groq_service import explain_component, chat_with_component
from controllers.repo_chat_controller import invalidate_repo_cache
from models.repository import ComponentChatRequest
from services.node_analyzer_service import analyze_all_nodes, _analyze_single_node
from services.repo_chat_service import get_pre_analyzed_node_context
from services.sync_service import sync_repository
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _content_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()


async def import_repository(request: ImportRequest) -> ImportResponse:
    db = get_db()

    owner, repo_name = _parse_github_url(request.github_url)

    normalized_owner = owner.strip().lower()
    normalized_repo = repo_name.replace(".git", "").strip().lower()
    normalized_branch = request.branch.strip().lower()

    repo_identity = f"{normalized_owner}/{normalized_repo}:{normalized_branch}"
    unique_key = hashlib.sha256(repo_identity.encode()).hexdigest()

    existing_repo = await db.repositories.find_one({"unique_key": unique_key})

    if existing_repo:
        if existing_repo.get("status") == "failed":
            return await _run_import_pipeline(
                db, existing_repo["repo_id"], request,
                normalized_owner, normalized_repo, normalized_branch,
                unique_key, is_retry=True,
            )

        return ImportResponse(
            repo_id=existing_repo["repo_id"],
            name=existing_repo["name"],
            file_count=existing_repo["file_count"],
            status=existing_repo.get("status", "ready"),
            message="This repository already exists.",
        )

    repo_id = str(uuid.uuid4())
    return await _run_import_pipeline(
        db, repo_id, request,
        normalized_owner, normalized_repo, normalized_branch,
        unique_key, is_retry=False, client_id=request.client_id
    )


async def _run_import_pipeline(
    db, repo_id, request, owner, repo_name, branch, unique_key, is_retry: bool, client_id: str = None
) -> ImportResponse:
    pending_doc = {
        "repo_id":         repo_id,
        "name":            repo_name,
        "owner":           owner,
        "branch":          branch,
        "file_count":      0,
        "github_url":      request.github_url,
        "unique_key":      unique_key,
        "client_id":       client_id,
        "status":          "pending",
        "error_message":   None,
        "last_commit_sha": None,
        "last_synced_at":  None,
    }

    if is_retry:
        await db.files.delete_many({"repo_id": repo_id})
        await db.file_explanations.delete_many({"repo_id": repo_id})
        await invalidate_repo_cache(repo_id)
        await db.repositories.update_one(
            {"repo_id": repo_id},
            {"$set": {
                "status": "pending",
                "error_message": None,
                "file_count": 0,
                "last_commit_sha": None,
            }},
        )
        logger.info("Retrying import for repo %s", repo_id)
    else:
        try:
            await db.repositories.insert_one(pending_doc)
        except DuplicateKeyError:
            existing = await db.repositories.find_one({"unique_key": unique_key})
            return ImportResponse(
                repo_id=existing["repo_id"],
                name=existing["name"],
                file_count=existing["file_count"],
                status=existing.get("status", "ready"),
                message="This repository already exists.",
            )

    try:
        files = await download_and_extract(request.github_url, request.branch)
    except Exception as exc:
        error_msg = str(exc)
        await db.repositories.update_one(
            {"repo_id": repo_id},
            {"$set": {"status": "failed", "error_message": error_msg}},
        )
        logger.error("Download failed for repo %s: %s", repo_id, error_msg)
        raise ValueError(error_msg)

    if not files:
        error_msg = "No supported files found in repository."
        await db.repositories.update_one(
            {"repo_id": repo_id},
            {"$set": {"status": "failed", "error_message": error_msg}},
        )
        raise ValueError(error_msg)

    try:
        file_docs = []
        for f in files:
            _, sub = await classify_file_async(f["path"], f.get("content", ""), repo_id)
            imports, exports = await analyze_file(sub, f["content"], f["path"])
            file_docs.append({
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
                # ── NEW: store content hash at import time for future sync ──
                "content_hash":    _content_hash(f["content"]),
            })

        await db.files.insert_many(file_docs, ordered=False)

    except Exception as exc:
        error_msg = f"File analysis/storage failed: {exc}"
        await db.repositories.update_one(
            {"repo_id": repo_id},
            {"$set": {"status": "failed", "error_message": error_msg}},
        )
        logger.error("Analysis failed for repo %s: %s", repo_id, error_msg)
        raise ValueError(error_msg)

    # ── NEW: fetch and store commit SHA at import time ─────────────────────
    commit_sha = await get_latest_commit_sha(request.github_url, request.branch)

    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {
            "status":          "ready",
            "file_count":      len(files),
            "error_message":   None,
            "last_commit_sha": commit_sha,
        }},
    )
    logger.info(
        "Import complete for repo %s (%d files, SHA: %s)",
        repo_id, len(files), (commit_sha or "unknown")[:8],
    )

    # Trigger automated node analysis in the background
    asyncio.create_task(analyze_all_nodes(repo_id))

    return ImportResponse(
        repo_id=repo_id,
        name=repo_name,
        file_count=len(files),
        status="ready",
        message=f"Successfully imported {len(files)} files from {owner}/{repo_name}",
    )


async def sync_repo_controller(repo_id: str) -> SyncResponse:
    """
    Controller wrapper for the manual sync endpoint.
    Delegates to sync_service.sync_repository().
    """
    return await sync_repository(repo_id)


async def get_graph(repo_id: str, view_type: str = "structure") -> GraphResponse:
    db = get_db()

    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    if repo.get("status") == "pending":
        raise ValueError("Repository import is still in progress. Please wait.")
    if repo.get("status") == "failed":
        raise ValueError(
            f"Repository import failed: {repo.get('error_message', 'unknown error')}. "
            "Please retry the import."
        )

    # If semantic view is requested, use the aggregator
    if view_type == "semantic":
        from services.graph_aggregator_service import get_dual_view_graph
        kg_data = await get_dual_view_graph(repo_id, "semantic")
        return GraphResponse(
            repo_id=repo_id,
            nodes=kg_data["nodes"],
            edges=kg_data["edges"],
            circular_paths=[], # Not relevant for semantic view
            is_semantic=True
        )

    # Baseline: structural view
    # Legacy support: ensure all nodes have analysis_status
    await db.files.update_many(
        {"repo_id": repo_id, "analysis_status": {"$exists": False}},
        {"$set": {"analysis_status": "pending"}}
    )

    cursor = db.files.find(
        {"repo_id": repo_id},
        {"_id": 0, "path": 1, "name": 1, "extension": 1,
         "content": 1, "size": 1, "language": 1, "github_url": 1,
         "analysis_status": 1, "imports": 1, "exports": 1},
    )
    files = await cursor.to_list(length=None)

    graph_data = await build_dependency_graph(files, repo_id=repo_id)

    return GraphResponse(
        repo_id=repo_id,
        nodes=graph_data["nodes"],
        edges=graph_data["edges"],
        circular_paths=graph_data["circular_paths"],
    )


async def explain_file(request: ExplainRequest) -> ExplainResponse:
    db = get_db()

    batch_node = await db.node_analysis.find_one(
        {"repo_id": request.repo_id, "file_path": request.file_path, "status": "done"}
    )
    if batch_node and "analysis" in batch_node:
        ana = batch_node["analysis"]
        explanation_md = f"### Purpose\n{ana.get('purpose', 'N/A')}\n\n"
        explanation_md += f"### Architectural Role\n**{ana.get('architectural_role', 'N/A')}**\n\n"
        if ana.get("key_patterns"):
            explanation_md += "### Key Patterns\n- " + "\n- ".join(ana["key_patterns"]) + "\n\n"
        if ana.get("concerns"):
            explanation_md += "### Responsibilities & Concerns\n- " + "\n- ".join(ana["concerns"]) + "\n\n"
        return ExplainResponse(
            file_path=request.file_path,
            explanation=explanation_md,
            dependencies=batch_node.get("exports", []),
            cached=True,
        )

    file_doc = await db.files.find_one(
        {"repo_id": request.repo_id, "path": request.file_path},
        {"_id": 0},
    )
    if not file_doc:
        raise ValueError(f"File {request.file_path} not found in repo {request.repo_id}")

    cached = await db.file_explanations.find_one(
        {"repo_id": request.repo_id, "path": request.file_path},
        {"_id": 0},
    )
    if cached:
        logger.info("Explanation cache hit for %s", request.file_path)
        return ExplainResponse(
            file_path=request.file_path,
            explanation=cached["explanation"],
            dependencies=cached["dependencies"],
            cached=True,
        )

    logger.info("Explanation cache miss for %s — calling LLM", request.file_path)

    _, sub_for_explain = await classify_file_async(
        file_doc["path"], file_doc.get("content", "")
    )
    imports, _ = await analyze_file(
        sub_for_explain, file_doc["content"], file_doc["path"]
    )

    explanation = await explain_component(
        file_path=file_doc["path"],
        content=file_doc["content"],
        language=file_doc["language"],
        imports=imports,
    )

    dependencies = imports[:30]

    await db.file_explanations.update_one(
        {"repo_id": request.repo_id, "path": request.file_path},
        {"$set": {
            "repo_id":      request.repo_id,
            "path":         request.file_path,
            "explanation":  explanation,
            "dependencies": dependencies,
        }},
        upsert=True,
    )

    return ExplainResponse(
        file_path=request.file_path,
        explanation=explanation,
        dependencies=dependencies,
        cached=False,
    )


async def list_repositories(client_id: str = None) -> List[RepoSummary]:
    db = get_db()
    query = {"client_id": client_id} if client_id else {}
    cursor = db.repositories.find(query, {"_id": 0})
    repos = await cursor.to_list(length=100)

    result = []
    for r in repos:
        try:
            result.append(RepoSummary(**r))
        except Exception:
            pass
    return result


async def delete_repository(repo_id: str, client_id: str = None) -> dict:
    db = get_db()
    query = {"repo_id": repo_id}
    if client_id:
        query["client_id"] = client_id
    r1 = await db.repositories.delete_one(query)
    r2 = await db.files.delete_many({"repo_id": repo_id})

    await db.file_explanations.delete_many({"repo_id": repo_id})
    await db.node_analysis.delete_many({"repo_id": repo_id})
    await db.repo_analysis.delete_many({"repo_id": repo_id})
    await invalidate_repo_cache(repo_id)

    if r1.deleted_count == 0:
        raise ValueError(f"Repository {repo_id} not found")

    return {"deleted_files": r2.deleted_count}


async def retry_import(repo_id: str) -> ImportResponse:
    db = get_db()

    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    if repo.get("status") == "ready":
        return ImportResponse(
            repo_id=repo_id,
            name=repo["name"],
            file_count=repo["file_count"],
            status="ready",
            message="Repository was already imported successfully.",
        )

    request = ImportRequest(github_url=repo["github_url"], branch=repo["branch"])
    return await _run_import_pipeline(
        db, repo_id, request,
        repo["owner"], repo["name"], repo["branch"],
        repo["unique_key"], is_retry=True,
    )


async def reanalyze_repository(repo_id: str) -> dict:
    db = get_db()
    await db.node_analysis.delete_many({"repo_id": repo_id})
    await db.repo_analysis.delete_many({"repo_id": repo_id})
    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$unset": {"analysis_status": ""}},
    )
    asyncio.create_task(analyze_all_nodes(repo_id))
    return {"message": "Re-analysis triggered successfully"}


async def reanalyze_node(repo_id: str, file_path: str) -> dict:
    db = get_db()
    cursor = db.files.find({"repo_id": repo_id})
    all_files = await cursor.to_list(length=None)
    file_doc = next((f for f in all_files if f["path"] == file_path), None)
    if not file_doc:
        raise ValueError(f"File {file_path} not found in repository {repo_id}")

    await db.node_analysis.update_one(
        {"repo_id": repo_id, "file_path": file_path},
        {"$set": {"status": "analyzing"}},
        upsert=True,
    )
    asyncio.create_task(_analyze_single_node(repo_id, file_doc, all_files))
    return {"message": f"Re-analysis triggered for {file_path}"}


async def chat_component(request: ComponentChatRequest):
    logger.info("Chat request received for %s", request.file_path)

    db = get_db()

    file_doc = await db.files.find_one({
        "repo_id": request.repo_id,
        "path":    request.file_path,
    })

    if not file_doc:
        raise ValueError(
            f"File {request.file_path} not found in repo {request.repo_id}"
        )

    pre_analyzed = await get_pre_analyzed_node_context(request.repo_id, request.file_path)
    if pre_analyzed:
        logger.info("Using pre-analyzed node context for chat: %s", request.file_path)
        context = (
            f"Purpose: {pre_analyzed.get('purpose')}\n"
            f"Role: {pre_analyzed.get('architectural_role')}\n"
            f"Patterns: {', '.join(pre_analyzed.get('key_patterns', []))}\n"
            f"Exports: {', '.join(pre_analyzed.get('exports', []))}\n"
            f"Concerns: {', '.join(pre_analyzed.get('concerns', []))}\n"
        )
        reply = await chat_with_component(
            file_path=file_doc["path"],
            content=file_doc["content"],
            language=file_doc.get("language", "text"),
            imports=file_doc.get("imports", []),
            user_query=request.query,
            history=[m.model_dump() for m in request.history],
            context_override=context,
        )
        return {"reply": reply}

    reply = await chat_with_component(
        file_path=file_doc["path"],
        content=file_doc["content"],
        language=file_doc.get("language", "text"),
        imports=file_doc.get("imports", []),
        user_query=request.query,
        history=[m.model_dump() for m in request.history],
    )
    return {"reply": reply}