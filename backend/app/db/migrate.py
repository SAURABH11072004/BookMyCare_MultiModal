"""Run Alembic migrations programmatically."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


def upgrade_head(database_url: str | None = None) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url or get_settings().database_url)
    command.upgrade(cfg, "head")
