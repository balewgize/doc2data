"""Runtime configuration for Doc2Data.

Values come from the environment (docker compose or a local shell). For native
runs we also look for a root ``.env`` and a ``backend/.env`` file so a plain
``uv run uvicorn`` behaves like the container.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

for candidate in (PROJECT_DIR / ".env", BACKEND_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


LLM_PROVIDER = _env("LLM_PROVIDER").lower()
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _env("OPENROUTER_MODEL", "openrouter/auto")
OPENROUTER_BASE_URL = _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OLLAMA_BASE_URL = _env("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "gemma3:1b")

_default_database = (
    Path("/tmp/doc2data.db")
    if os.getenv("VERCEL")
    else BACKEND_DIR / "data" / "doc2data.db"
)
DATABASE_PATH = Path(_env("DATABASE_PATH", str(_default_database)))
MAX_UPLOAD_MB = int(_env("MAX_UPLOAD_MB", "20"))
MAX_CHARS_PER_CHUNK = int(_env("MAX_CHARS_PER_CHUNK", "12000"))


def resolved_provider() -> str:
    """Explicit LLM_PROVIDER wins; otherwise use OpenRouter when a key exists."""
    if LLM_PROVIDER:
        return LLM_PROVIDER
    return "openrouter" if OPENROUTER_API_KEY else "mock"
