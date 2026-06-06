import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import connect_db, close_db
from routes.main_router import router
from services import ollama_manager

_log = logging.getLogger(__name__)

# ── API Key Authentication Middleware ─────────────────────────────────────────
# When API_KEY is set in .env, every request must carry:
#   Authorization: Bearer <API_KEY>
# OR
#   X-API-Key: <API_KEY>
#
# When API_KEY is blank (default), auth is disabled — safe for local dev.
# Bypass list: health check and CORS preflight never require a key.

_AUTH_BYPASS_PATHS = {"/api/v1/health"}

async def _api_key_middleware(request: Request, call_next):
    if settings.API_KEY:
        # Allow CORS preflight without auth
        if request.method == "OPTIONS":
            return await call_next(request)
        # Allow whitelisted paths (health check)
        if request.url.path in _AUTH_BYPASS_PATHS:
            return await call_next(request)

        # Check Authorization: Bearer <key>
        auth_header = request.headers.get("Authorization", "")
        bearer_key = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

        # Check X-API-Key header as fallback
        api_key_header = request.headers.get("X-API-Key", "")

        if bearer_key != settings.API_KEY and api_key_header != settings.API_KEY:
            _log.warning("Rejected unauthenticated request to %s", request.url.path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized. Provide a valid API key via 'Authorization: Bearer <key>' or 'X-API-Key' header."},
            )

    return await call_next(request)


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

# ── CORS — restrict to specific safe methods and headers (H4 fix) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Client-ID", "X-API-Key"],
)

# ── API Key auth middleware (H1 fix) ──────────────────────────────────────────
# Must be added AFTER CORS so preflight OPTIONS requests are handled correctly.
app.middleware("http")(_api_key_middleware)

app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,        # H3: configurable — defaults to 127.0.0.1
        port=8000,
        reload=settings.DEBUG,     # H3: reload only in DEBUG mode
    )