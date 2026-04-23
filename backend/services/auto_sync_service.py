"""
Auto-sync background service.
Polls MongoDB every 60 seconds for repos with auto_sync=True and syncs them
when their sync_interval_minutes have elapsed since last_synced_at.
"""
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _polling_loop():
    from database import get_db
    from services.sync_service import sync_repository

    while True:
        try:
            db = get_db()
            now = datetime.utcnow()

            # Find repos due for auto-sync
            cursor = db.repositories.find({
                "auto_sync": True,
                "analysis_status": {"$nin": ["importing", "analyzing"]},
            })
            repos = await cursor.to_list(length=None)

            for repo in repos:
                repo_id = repo.get("repo_id")
                interval = repo.get("sync_interval_minutes", 30)
                last_synced = repo.get("last_synced_at")

                due = (
                    last_synced is None or
                    (now - last_synced) >= timedelta(minutes=interval)
                )

                if not due:
                    continue

                logger.info(f"[AutoSync] Triggering sync for {repo_id}")
                try:
                    result = await sync_repository(repo_id)
                    await db.repositories.update_one(
                        {"repo_id": repo_id},
                        {"$set": {
                            "last_synced_at": now,
                            "last_auto_sync_result": result.get("summary", "synced"),
                            "last_auto_sync_status": "ok",
                        }}
                    )
                    logger.info(f"[AutoSync] Sync completed for {repo_id}: {result.get('summary', '')}")
                except Exception as e:
                    logger.error(f"[AutoSync] Sync failed for {repo_id}: {e}")
                    await db.repositories.update_one(
                        {"repo_id": repo_id},
                        {"$set": {
                            "last_synced_at": now,
                            "last_auto_sync_status": "error",
                            "last_auto_sync_result": str(e),
                        }}
                    )

        except Exception as e:
            logger.error(f"[AutoSync] Polling error: {e}")

        await asyncio.sleep(60)  # Check every minute


def start_background_polling():
    """Start the auto-sync polling loop as a background task."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_polling_loop())
        logger.info("[AutoSync] Background polling started")


def stop_background_polling():
    """Cancel the background polling task (called on shutdown)."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        logger.info("[AutoSync] Background polling stopped")
