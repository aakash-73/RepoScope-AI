"""
Manages the Ollama server process lifecycle.

Behaviour:
- If Ollama is already running when the backend starts, we leave it alone
  and will NOT stop it on shutdown (we didn't own it).
- If Ollama is NOT running, we start it via `ollama serve`, wait for it to
  be ready, pull any missing models, and stop it cleanly on backend shutdown.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from urllib.parse import urlparse

import httpx

from config import settings

_log = logging.getLogger(__name__)

# Set only if WE started Ollama — used to decide whether to stop it later.
_ollama_proc: subprocess.Popen | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ollama_host() -> str:
    """Strip the /v1 suffix from OLLAMA_BASE_URL to get the bare Ollama host."""
    parsed = urlparse(settings.OLLAMA_BASE_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


async def _is_running() -> bool:
    host = _ollama_host()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{host}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _wait_until_ready(timeout_s: int = 30) -> bool:
    for _ in range(timeout_s):
        if await _is_running():
            return True
        await asyncio.sleep(1)
    return False


async def _pull_model_if_missing(model: str) -> None:
    host = _ollama_host()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{host}/api/tags")
            if r.status_code == 200:
                present = [m["name"] for m in r.json().get("models", [])]
                # Match loosely — "qwen2.5-coder:7b-instruct" is in "qwen2.5-coder:7b-instruct"
                if any(model in name for name in present):
                    _log.info("Ollama model '%s' already present — skipping pull.", model)
                    return

        _log.info("Pulling Ollama model '%s' — this may take a while on first run…", model)
        proc = await asyncio.create_subprocess_exec(
            "ollama", "pull", model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            _log.info("Model '%s' pulled successfully.", model)
        else:
            _log.warning(
                "ollama pull '%s' exited with code %d: %s",
                model, proc.returncode, stdout.decode(errors="replace"),
            )
    except FileNotFoundError:
        _log.warning("ollama CLI not found — cannot pull model '%s'.", model)
    except Exception as e:
        _log.warning("Could not pull model '%s': %s", model, e)


# ── Public API ─────────────────────────────────────────────────────────────────

async def start() -> None:
    """
    Start Ollama if it isn't already running, then ensure required models are present.
    Called from the FastAPI lifespan on startup.
    """
    global _ollama_proc

    if await _is_running():
        _log.info("Ollama already running at %s — not starting a new instance.", _ollama_host())
    else:
        _log.info("Ollama not detected — starting 'ollama serve'…")
        try:
            kwargs: dict = dict(
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # On Windows, suppress the extra console window that Popen would open.
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            _ollama_proc = subprocess.Popen(["ollama", "serve"], **kwargs)
        except FileNotFoundError:
            _log.error(
                "ollama executable not found. "
                "Install Ollama from https://ollama.com and ensure it is on your PATH."
            )
            return

        _log.info("Waiting for Ollama to become ready (pid=%d)…", _ollama_proc.pid)
        ready = await _wait_until_ready(timeout_s=30)
        if not ready:
            _log.warning(
                "Ollama server did not respond within 30 s. "
                "Analysis requests will fail until it is reachable."
            )
            return
        _log.info("Ollama server ready at %s.", _ollama_host())

    # Ensure all required models are present (deduplicated in case analysis == chat model).
    models_needed = {settings.OLLAMA_ANALYSIS_MODEL, settings.OLLAMA_CHAT_MODEL}
    for model in models_needed:
        await _pull_model_if_missing(model)


def stop() -> None:
    """
    Stop the Ollama process only if WE started it.
    Called from the FastAPI lifespan on shutdown.
    """
    global _ollama_proc
    if _ollama_proc is None:
        return  # Either already running before us, or we never started it.

    _log.info("Stopping Ollama server (pid=%d)…", _ollama_proc.pid)
    _ollama_proc.terminate()
    try:
        _ollama_proc.wait(timeout=10)
        _log.info("Ollama server stopped cleanly.")
    except subprocess.TimeoutExpired:
        _log.warning("Ollama did not exit in 10 s — force-killing.")
        _ollama_proc.kill()
    _ollama_proc = None
