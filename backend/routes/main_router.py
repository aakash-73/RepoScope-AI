import json
import logging
from fastapi import APIRouter, HTTPException, Response, status, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from models.repository import (
    ImportRequest, ImportResponse,
    ExplainRequest, ExplainResponse,
    GraphResponse, RepoSummary, ComponentChatRequest, ChatMessage,
    RepoChatRequest, SyncResponse,
)
from controllers.repo_controller import (
    import_repository,
    get_graph,
    explain_file,
    list_repositories,
    delete_repository,
    chat_component,
    retry_import,
    reanalyze_repository,
    reanalyze_node,
    sync_repo_controller,
)
from controllers.repo_chat_controller import (
    get_repo_summary, repo_chat,
    get_chat_history, save_chat_history, clear_chat_history,
    get_proactive_insights,
)
from services.language_registry import (
    get_all_languages, get_languages_for_repo,
    get_language,
    update_language_color, reset_language_color,
)
from routes import analysis_routes

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(analysis_routes.router, prefix="/analysis", tags=["Analysis"])


async def get_repo_and_check_ownership(repo_id: str, x_client_id: Optional[str] = None):
    from database import get_db
    db = get_db()
    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db_client_id = repo.get("client_id")
    if db_client_id and db_client_id != x_client_id:
        # Return 404 to avoid disclosing existence of repository to unauthorized clients
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


class ReanalyzeNodeRequest(BaseModel):
    file_path: str


@router.post("/analysis/{repo_id}/reanalyze")
async def force_reanalyze_repo(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await reanalyze_repository(repo_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reanalysis failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during reanalysis")


@router.post("/analysis/{repo_id}/node/reanalyze")
async def force_reanalyze_node(repo_id: str, req: ReanalyzeNodeRequest, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await reanalyze_node(repo_id, req.file_path)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Node reanalysis failed for %s path %s", repo_id, req.file_path)
        raise HTTPException(status_code=500, detail="Internal server error during node reanalysis")


class ChatResponse(BaseModel):
    reply: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]


class InsightItem(BaseModel):
    type: str
    title: str
    body: str


class InsightsResponse(BaseModel):
    insights: List[InsightItem]


class DeleteRepoResponse(BaseModel):
    deleted_files: int


class HealthResponse(BaseModel):
    status: str
    service: str


class LanguageListResponse(BaseModel):
    languages: List[dict]


class ClearHistoryResponse(BaseModel):
    ok: bool


class PatchColorRequest(BaseModel):
    color: Optional[str] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok", "service": "reposcope-ai"}


@router.post("/import", response_model=ImportResponse)
async def import_repo(request: ImportRequest, response: Response):
    try:
        result = await import_repository(request)
        if result.message == "This repository already exists.":
            response.status_code = status.HTTP_409_CONFLICT
        else:
            response.status_code = status.HTTP_201_CREATED
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Import failed for %s", request.github_url)
        raise HTTPException(status_code=500, detail="Internal server error during import")


@router.post("/repos/{repo_id}/retry", response_model=ImportResponse)
async def retry_repo_import(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await retry_import(repo_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Retry failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during retry")


# ── Manual sync endpoint ──────────────────────────────────────────────────────
# Triggered when the user clicks the Sync button in the UI.
# Downloads fresh ZIP, diffs against stored files, re-analyzes changed nodes.
@router.post("/repos/{repo_id}/sync", response_model=SyncResponse)
async def sync_repo(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await sync_repo_controller(repo_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Sync failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during sync")


@router.get("/graph/{repo_id}", response_model=GraphResponse)
async def get_repo_graph(repo_id: str, view_type: str = Query("structure"), x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await get_graph(repo_id, view_type)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Graph generation failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error generating graph")


@router.post("/explain", response_model=ExplainResponse)
async def explain_component(request: ExplainRequest, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(request.repo_id, x_client_id)
        return await explain_file(request)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Explanation failed for %s", request.repo_id)
        raise HTTPException(status_code=500, detail="Internal server error generating explanation")


@router.get("/repos", response_model=List[RepoSummary])
async def list_repos(x_client_id: Optional[str] = Header(None)):
    try:
        return await list_repositories(x_client_id)
    except Exception as e:
        logger.exception("Failed to list repositories")
        raise HTTPException(status_code=500, detail="Internal server error listing repositories")


@router.delete("/repos/{repo_id}", response_model=DeleteRepoResponse)
async def delete_repo(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await delete_repository(repo_id, x_client_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Delete failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during deletion")


@router.post("/component/chat", response_model=ChatResponse)
async def component_chat(req: ComponentChatRequest, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(req.repo_id, x_client_id)
        return await chat_component(req)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Component chat failed for %s", req.repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during component chat")


@router.get("/repo/{repo_id}/summary")
async def get_repo_overview(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await get_repo_summary(repo_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Summary failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error generating repository summary")


@router.post("/repo/{repo_id}/chat", response_model=ChatResponse)
async def repo_level_chat(repo_id: str, req: RepoChatRequest, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        result = await repo_chat(repo_id, req.query, [m.model_dump() for m in req.history])
        history_to_save = [m.model_dump() for m in req.history] + [
            {"role": "user", "content": req.query},
            {"role": "assistant", "content": result.get("reply", "")},
        ]
        await save_chat_history(repo_id, history_to_save)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Repo chat failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error during repo chat")


@router.get("/repo/{repo_id}/chat/history", response_model=ChatHistoryResponse)
async def get_repo_chat_history(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        messages = await get_chat_history(repo_id)
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat history retrieval failed for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error retrieving chat history")


@router.delete("/repo/{repo_id}/chat/history", response_model=ClearHistoryResponse)
async def clear_repo_chat_history(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        await clear_chat_history(repo_id)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to clear chat history for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error clearing chat history")


@router.get("/repo/{repo_id}/insights", response_model=InsightsResponse)
async def repo_insights(repo_id: str, x_client_id: Optional[str] = Header(None)):
    try:
        await get_repo_and_check_ownership(repo_id, x_client_id)
        return await get_proactive_insights(repo_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get insights for %s", repo_id)
        raise HTTPException(status_code=500, detail="Internal server error generating insights")


@router.get("/languages", response_model=LanguageListResponse)
async def list_languages(repo_id: Optional[str] = Query(default=None), x_client_id: Optional[str] = Header(None)):
    try:
        if repo_id:
            await get_repo_and_check_ownership(repo_id, x_client_id)
            languages = await get_languages_for_repo(repo_id)
        else:
            languages = await get_all_languages()
        return {"languages": languages}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list languages")
        raise HTTPException(status_code=500, detail="Internal server error listing languages")


@router.get("/languages/{key:path}")
async def get_language_entry(key: str):
    try:
        lang = await get_language(key)
        if not lang:
            raise HTTPException(status_code=404, detail=f"Language '{key}' not found")
        return lang
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get language entry")
        raise HTTPException(status_code=500, detail="Internal server error retrieving language details")


@router.patch("/languages/{key:path}")
async def patch_language_color(
    key: str,
    body: PatchColorRequest,
    repo_id: Optional[str] = Query(default=None),
    x_client_id: Optional[str] = Header(None),
):
    try:
        if repo_id:
            await get_repo_and_check_ownership(repo_id, x_client_id)
        if body.color is None:
            updated = await reset_language_color(key, repo_id)
        else:
            updated = await update_language_color(key, body.color, repo_id)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Language '{key}' not found")
        return updated
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Failed to patch language color")
        raise HTTPException(status_code=500, detail="Internal server error updating language color")


# ─── Streaming Chat ─────────────────────────────────────────────────────────

@router.post("/repo/{repo_id}/chat/stream")
async def repo_level_chat_stream(repo_id: str, req: RepoChatRequest, x_client_id: Optional[str] = Header(None)):
    """Streaming SSE endpoint for repo-level chat."""
    from controllers.repo_chat_controller import repo_chat_stream

    await get_repo_and_check_ownership(repo_id, x_client_id)

    async def event_generator():
        try:
            async for token in repo_chat_stream(repo_id, req.query, [m.model_dump() for m in req.history]):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            logger.exception("Repo level chat stream failed for %s", repo_id)
            yield f"data: {json.dumps({'error': 'Internal server error during chat streaming'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── File Content ───────────────────────────────────────────────────────────

@router.get("/repo/{repo_id}/file/content")
async def get_file_content(repo_id: str, file_path: str = Query(...), x_client_id: Optional[str] = Header(None)):
    await get_repo_and_check_ownership(repo_id, x_client_id)
    from database import get_db
    db = get_db()
    doc = await db.files.find_one(
        {"repo_id": repo_id, "path": file_path},
        {"_id": 0, "path": 1, "content": 1, "language": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    return doc


# ─── Auto-sync Settings ──────────────────────────────────────────────────────

class SyncSettingsRequest(BaseModel):
    auto_sync: bool
    sync_interval_minutes: int = Field(default=30, ge=5, le=10080)


@router.patch("/repos/{repo_id}/sync-settings")
async def patch_sync_settings(repo_id: str, body: SyncSettingsRequest, x_client_id: Optional[str] = Header(None)):
    await get_repo_and_check_ownership(repo_id, x_client_id)
    from database import get_db
    db = get_db()
    result = await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {
            "auto_sync": body.auto_sync,
            "sync_interval_minutes": body.sync_interval_minutes,
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"ok": True, "auto_sync": body.auto_sync, "sync_interval_minutes": body.sync_interval_minutes}