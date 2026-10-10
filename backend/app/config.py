"""Reads settings from backend/.env (or real environment variables)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    lastfm_api_key: str
    mb_user_agent: str
    cache_path: Path
    frontend_origins: list[str]  # sites allowed to call the API from a browser (CORS)


def parse_origins(value: str) -> list[str]:
    """ "https://a.vercel.app/, http://localhost:5173" -> ["https://a.vercel.app", "http://localhost:5173"]

    Browsers send the origin with no trailing slash, and CORS needs an exact
    match, so a pasted "https://site.vercel.app/" would never match.
    """
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


def load_settings() -> Settings:
    load_dotenv(BACKEND_DIR / ".env")

    missing = [name for name in ("LASTFM_API_KEY", "MB_USER_AGENT") if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing {', '.join(missing)}. Set them in backend/.env (see .env.example).")

    # A relative CACHE_PATH means "relative to backend/", not to whatever
    # directory you happened to run the command from.
    cache_path = Path(os.environ.get("CACHE_PATH", "cache.db"))
    if not cache_path.is_absolute():
        cache_path = BACKEND_DIR / cache_path

    return Settings(
        lastfm_api_key=os.environ["LASTFM_API_KEY"],
        mb_user_agent=os.environ["MB_USER_AGENT"],
        cache_path=cache_path,
        frontend_origins=parse_origins(os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")),
    )
