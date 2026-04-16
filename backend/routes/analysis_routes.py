import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database import get_db

router = APIRouter()


@router.get("/{repo_id}/status")
async def get_analysis_status(repo_id: str):
    db = get_db()

    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    total_nodes = await db.files.count_documents({"repo_id": repo_id})
    completed_nodes = await db.node_analysis.count_documents(
        {"repo_id": repo_id, "status": "done"}
    )

    analyzing_doc = await db.node_analysis.find_one(
        {"repo_id": repo_id, "status": "analyzing"},
        {"file_path": 1},
    )
    current_file = analyzing_doc["file_path"] if analyzing_doc else None

    recently_completed_cursor = db.node_analysis.find(
        {"repo_id": repo_id, "status": "done"},
        {"file_path": 1, "analyzed_at": 1},
    ).sort("analyzed_at", -1).limit(3)
    recently_completed = [
        doc["file_path"] async for doc in recently_completed_cursor
    ]

    repo_status = repo.get("analysis_status", "pending")
    if repo_status == "pending":
        repo_ana = await db.repo_analysis.find_one({"repo_id": repo_id})
        if repo_ana:
            repo_status = repo_ana.get("status", "pending")

    return {
        "repo_id": repo_id,
        "repo_analysis_status": repo_status,
        "current_file": current_file,
        "recently_completed": recently_completed,
        "nodes": {
            "total": total_nodes,
            "completed": completed_nodes,
            "percentage": (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0,
        },
    }


@router.get("/{repo_id}/stream")
async def stream_analysis_status(repo_id: str):
    """
    SSE endpoint. Streams node status change events to the frontend as they happen.

    Each event is a JSON object in one of these shapes:

      Node transition (fires whenever a single node changes status):
        { "type": "node_update", "file_path": "src/foo.py", "analysis_status": "analyzing" | "done" | "failed" }

      Progress heartbeat (fires every ~1s so the progress bar stays accurate):
        { "type": "progress", "completed": 12, "total": 40, "percentage": 30.0,
          "current_file": "src/bar.py", "repo_analysis_status": "analyzing" }

      Terminal event (fires once when the whole repo is done or failed, then the stream closes):
        { "type": "done", "repo_analysis_status": "done" | "understood" | "failed" }

    The frontend should:
      1. On "node_update" — patch that single node's analysis_status in graphData state (no re-fetch).
      2. On "progress"    — update the progress bar / current-file toast.
      3. On "done"        — close the EventSource and do one final fetchGraph() to get clean state.
    """
    db = get_db()

    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    async def event_generator():
        # Track which statuses we have already reported so we only emit changes.
        # Seed with the current snapshot so we don't re-fire events for nodes
        # that were already done before the client connected.
        known: dict[str, str] = {}

        cursor = db.files.find({"repo_id": repo_id}, {"path": 1, "analysis_status": 1})
        async for doc in cursor:
            known[doc["path"]] = doc.get("analysis_status", "pending")

        # Emit the full initial snapshot so the frontend can ghost/solidify correctly
        # without waiting for the first change event.
        snapshot_nodes = [
            {"file_path": path, "analysis_status": status}
            for path, status in known.items()
        ]
        yield _sse({"type": "snapshot", "nodes": snapshot_nodes})

        terminal_statuses = {"done", "understood", "failed"}

        while True:
            # ── 1. Check for node-level status changes ──────────────────
            cursor = db.files.find(
                {"repo_id": repo_id},
                {"path": 1, "analysis_status": 1},
            )
            async for doc in cursor:
                path = doc["path"]
                new_status = doc.get("analysis_status", "pending")
                if known.get(path) != new_status:
                    known[path] = new_status
                    yield _sse({
                        "type": "node_update",
                        "file_path": path,
                        "analysis_status": new_status,
                    })

            # ── 2. Emit a progress heartbeat ────────────────────────────
            total = await db.files.count_documents({"repo_id": repo_id})
            completed = await db.node_analysis.count_documents(
                {"repo_id": repo_id, "status": "done"}
            )
            analyzing_doc = await db.node_analysis.find_one(
                {"repo_id": repo_id, "status": "analyzing"},
                {"file_path": 1},
            )
            current_file = analyzing_doc["file_path"] if analyzing_doc else None

            repo_doc = await db.repositories.find_one(
                {"repo_id": repo_id}, {"analysis_status": 1}
            )
            repo_status = repo_doc.get("analysis_status", "pending") if repo_doc else "pending"

            yield _sse({
                "type": "progress",
                "completed": completed,
                "total": total,
                "percentage": round((completed / total * 100) if total > 0 else 0, 1),
                "current_file": current_file,
                "repo_analysis_status": repo_status,
            })

            # ── 3. Check for terminal state ──────────────────────────────
            if repo_status in terminal_statuses:
                yield _sse({"type": "done", "repo_analysis_status": repo_status})
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Disable all buffering so events reach the browser immediately
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # tells nginx not to buffer
            "Connection": "keep-alive",
        },
    )


def _sse(payload: dict) -> str:
    """Format a dict as a single SSE data frame."""
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/{repo_id}/repo")
async def get_repo_analysis(repo_id: str):
    db = get_db()
    doc = await db.repo_analysis.find_one(
        {"repo_id": repo_id, "status": "done"}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found or still in progress",
        )
    return doc


@router.get("/{repo_id}/node")
async def get_node_analysis(repo_id: str, file_path: str):
    db = get_db()
    doc = await db.node_analysis.find_one(
        {"repo_id": repo_id, "file_path": file_path, "status": "done"},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Node analysis not found or still in progress",
        )
    return doc