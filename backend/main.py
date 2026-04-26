import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import connect_db, close_db
from routes.main_router import router
from services import ollama_manager

_log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ollama_manager.start()
    await connect_db()
    try:
        from services.classifier_registry import get_rules
        from services.classifier_seed import seed as seed_classifier
        from database import get_db

        db = get_db()
        count = await db.classifier_extensions.count_documents({})
        if count == 0:
            _log.info("classifier_extensions is empty — running seed...")
            await seed_classifier()
        else:
            _log.info("Classifier rules found in MongoDB (%d extensions)", count)
        rules = await get_rules()
        _log.info(
            "Classifier cache pre-warmed — %d extensions, %d fingerprints, %d path patterns",
            len(rules.ext_map), len(rules.fingerprints), len(rules.path_patterns),
        )
    except Exception as e:
        _log.warning("Classifier pre-warm failed (will use defaults): %s", e)

    from services.auto_sync_service import start_background_polling
    start_background_polling()

    yield

    await close_db()
    ollama_manager.stop()
    from services.auto_sync_service import stop_background_polling
    stop_background_polling()



app = FastAPI(
    title="RepoScope AI",
    description="Code Architecture Intelligence — Visualise any GitHub repo as an interactive dependency graph.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )