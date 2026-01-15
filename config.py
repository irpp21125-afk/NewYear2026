from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_token: str
    database_path: Path

    panel_api_key: str

    remanga_user_agent: str


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required. Put it in .env")

    db_path = Path(os.getenv("DATABASE_PATH", "./data/bot.sqlite")).resolve()

    panel_key = os.getenv("PANEL_API_KEY", "").strip()
    if not panel_key:
        raise RuntimeError("PANEL_API_KEY is required. Put it in .env")

    ua = os.getenv("REMANGA_USER_AGENT", "Mozilla/5.0").strip()

    return Settings(
        discord_token=token,
        database_path=db_path,
        panel_api_key=panel_key,
        remanga_user_agent=ua,
    )
