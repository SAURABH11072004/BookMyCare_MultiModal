"""Application configuration loaded from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "BookMyCare API"
    environment: str = "development"

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'bookmycare.db').as_posix()}"
    auto_migrate: bool = True  # run Alembic migrations on startup
    seed_knowledge: bool = True  # load curated WHO/CDC summaries on startup
    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: int = 15

    # Security. A random default is generated per process if unset; set a real
    # value in .env so tokens survive restarts.
    jwt_secret: str = Field(default="")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI providers. Order of preference; the first one with a key is used and
    # the rest are fallbacks. "mock" is always appended as the final fallback.
    ai_provider_order: str = "gemini,groq,openrouter"
    ai_force_mock: bool = False
    ai_timeout_seconds: float = 30.0

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Safety messaging (defaults are for India; change for your region)
    emergency_number: str = "112"
    crisis_line: str = "Tele-MANAS 14416 (India, 24x7 mental health helpline)"

    # OCR
    tesseract_cmd: str = ""  # e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def provider_order(self) -> list[str]:
        return [p.strip().lower() for p in self.ai_provider_order.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret or s.jwt_secret.startswith("change-me"):
        import logging
        import secrets

        logging.getLogger("bookmycare").warning(
            "JWT_SECRET is not set; using a random secret (logins will reset when the server restarts)."
        )
        s.jwt_secret = secrets.token_urlsafe(48)
    s.upload_dir.mkdir(parents=True, exist_ok=True)
    return s
