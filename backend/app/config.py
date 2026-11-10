"""Runtime settings, read from the environment (backend/.env, see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")  # real environment variables win over .env


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, default: str) -> Path:
    p = Path(os.environ.get(name) or default)
    return p if p.is_absolute() else BACKEND / p


@dataclass(frozen=True)
class Settings:
    llm_provider: str  # anthropic | openai | deepseek | offline
    llm_model: str
    llm_api_key: str
    llm_timeout_s: int
    planner: str  # "llm" = the model picks the next tool; "rules" = deterministic policy only
    db_path: Path
    upload_dir: Path
    max_upload_mb: int
    max_pages: int
    max_attempts: int  # questions per concept before the agent stops re-testing it
    max_agent_steps: int  # tool calls per answer before the loop is forced to finish
    enable_short_answer: bool


def get_settings() -> Settings:
    """Built on every call so tests can change the environment."""
    return Settings(
        llm_provider=os.environ.get("LLM_PROVIDER", "anthropic").strip().lower(),
        llm_model=os.environ.get("LLM_MODEL", "").strip(),
        llm_api_key=os.environ.get("LLM_API_KEY", "").strip(),
        llm_timeout_s=_int("LLM_TIMEOUT_S", 60),
        planner=os.environ.get("AGENT_PLANNER", "llm").strip().lower(),
        db_path=_path("DB_PATH", "data/lectureloop.sqlite3"),
        upload_dir=_path("UPLOAD_DIR", "uploads"),
        max_upload_mb=_int("MAX_UPLOAD_MB", 25),
        max_pages=_int("MAX_PAGES", 150),
        max_attempts=_int("MAX_ATTEMPTS_PER_CONCEPT", 4),
        max_agent_steps=_int("MAX_AGENT_STEPS", 8),
        enable_short_answer=_bool("ENABLE_SHORT_ANSWER", True),
    )
