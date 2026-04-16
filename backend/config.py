from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────────────────────────
    MONGODB_URI: str
    DB_NAME: str = "reposcope"

    # ─── Ollama (self-hosted LLM — no API key needed) ─────────────────────────
    # Point this at wherever Ollama is running.
    # Local dev  : http://localhost:11434/v1
    # Remote VPS : http://<your-server-ip>:11434/v1
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    # Heavy analysis: per-file explain, node analysis, repo synthesis
    # Best for 8GB VRAM: qwen2.5-coder:7b-instruct
    OLLAMA_ANALYSIS_MODEL: str = "qwen2.5-coder:7b-instruct"

    # Fast chat: user-facing Q&A (context already pre-built, just needs retrieval)
    # Same model keeps things simple on 8GB — swap to a 3b if you want faster chat
    OLLAMA_CHAT_MODEL: str = "qwen2.5-coder:7b-instruct"

    # ─── Groq (optional — kept so old .env files don't break on startup) ──────
    # These are no longer used by the application. Safe to remove from .env.
    GROQ_API_KEY: Optional[str] = None
    GROQ_REPO_ANALYSIS_KEY: Optional[str] = None
    GROQ_REPO_CHAT_KEY: Optional[str] = None

    # ─── GitHub ───────────────────────────────────────────────────────────────
    # Optional — increases rate limit from 60 to 5000 req/hr for repo downloads
    GITHUB_TOKEN: str = ""

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]

    # ─── File processing limits ───────────────────────────────────────────────
    FILE_PREVIEW_CHARS: int = 900
    MAX_CODE_CHARS: int = 12_000
    HEAD_CHARS: int = 5_500
    TAIL_CHARS: int = 5_500

    # ─── GitHub fallback branches ─────────────────────────────────────────────
    FALLBACK_BRANCHES: List[str] = ["main", "master", "develop", "dev"]

    class Config:
        env_file = ".env"


settings = Settings()