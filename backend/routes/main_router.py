import json
import logging
from fastapi import APIRouter, HTTPException, Response, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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

class ReanalyzeNodeRequest(BaseModel):
    file_path: str

@router.post("/analysis/{repo_id}/reanalyze")
async def force_reanalyze_repo(repo_id: str):
    try:
        return await reanalyze_repository(repo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/{repo_id}/node/reanalyze")
async def force_reanalyze_node(repo_id: str, req: ReanalyzeNodeRequest):
    try:
        return await reanalyze_node(repo_id, req.file_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

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
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/repos/{repo_id}/retry", response_model=ImportResponse)
async def retry_repo_import(repo_id: str):
    try:
        return await retry_import(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


# ── NEW: Manual sync endpoint ─────────────────────────────────────────────────
# Triggered when the user clicks the Sync button in the UI.
# Downloads fresh ZIP, diffs against stored files, re-analyzes changed nodes.
@router.post("/repos/{repo_id}/sync", response_model=SyncResponse)
async def sync_repo(repo_id: str):
    try:
        return await sync_repo_controller(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/graph/{repo_id}", response_model=GraphResponse)
async def get_repo_graph(repo_id: str, view_type: str = Query("structure")):
    try:
        return await get_graph(repo_id, view_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph generation failed: {str(e)}")


@router.post("/explain", response_model=ExplainResponse)
async def explain_component(request: ExplainRequest):
    try:
        return await explain_file(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.get("/repos", response_model=List[RepoSummary])
async def list_repos():
    try:
        return await list_repositories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/repos/{repo_id}", response_model=DeleteRepoResponse)
async def delete_repo(repo_id: str):
    try:
        return await delete_repository(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/component/chat", response_model=ChatResponse)
async def component_chat(req: ComponentChatRequest):
    try:
        return await chat_component(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/repo/{repo_id}/summary")
async def get_repo_overview(repo_id: str):
    try:
        return await get_repo_summary(repo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")


@router.post("/repo/{repo_id}/chat", response_model=ChatResponse)
async def repo_level_chat(repo_id: str, req: RepoChatRequest):
    try:
        result = await repo_chat(repo_id, req.query, [m.model_dump() for m in req.history])
        history_to_save = [m.model_dump() for m in req.history] + [
            {"role": "user", "content": req.query},
            {"role": "assistant", "content": result.get("reply", "")},
        ]
        await save_chat_history(repo_id, history_to_save)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repo chat failed: {str(e)}")


@router.get("/repo/{repo_id}/chat/history", response_model=ChatHistoryResponse)
async def get_repo_chat_history(repo_id: str):
    try:
        messages = await get_chat_history(repo_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/repo/{repo_id}/chat/history", response_model=ClearHistoryResponse)
async def clear_repo_chat_history(repo_id: str):
    try:
        await clear_chat_history(repo_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repo/{repo_id}/insights", response_model=InsightsResponse)
async def repo_insights(repo_id: str):
    try:
        return await get_proactive_insights(repo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages", response_model=LanguageListResponse)
async def list_languages(repo_id: Optional[str] = Query(default=None)):
    try:
        if repo_id:
            languages = await get_languages_for_repo(repo_id)
        else:
            languages = await get_all_languages()
        return {"languages": languages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages/{key:path}")
async def get_language_entry(key: str):
    lang = await get_language(key)
    if not lang:
        raise HTTPException(status_code=404, detail=f"Language '{key}' not found")
    return lang


@router.patch("/languages/{key:path}")
async def patch_language_color(
    key: str,
    body: PatchColorRequest,
    repo_id: Optional[str] = Query(default=None),
):
    try:
        if body.color is None:
            updated = await reset_language_color(key, repo_id)
        else:
            updated = await update_language_color(key, body.color, repo_id)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Language '{key}' not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Streaming Chat ─────────────────────────────────────────────────────────

@router.post("/repo/{repo_id}/chat/stream")
async def repo_level_chat_stream(repo_id: str, req: RepoChatRequest):
    """Streaming SSE endpoint for repo-level chat."""
    from controllers.repo_chat_controller import repo_chat_stream

    async def event_generator():
        try:
            async for token in repo_chat_stream(repo_id, req.query, [m.model_dump() for m in req.history]):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── File Content ───────────────────────────────────────────────────────────

@router.get("/repo/{repo_id}/file/content")
async def get_file_content(repo_id: str, file_path: str = Query(...)):
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
    sync_interval_minutes: int = 30


@router.patch("/repos/{repo_id}/sync-settings")
async def patch_sync_settings(repo_id: str, body: SyncSettingsRequest):
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