from __future__ import annotations

from fastapi import APIRouter

from app.ai import registry
from app.core.config import get_settings
from app.services.extraction import tesseract_available
from app.services.safety import DISCLAIMER

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/system/status")
def system_status():
    s = get_settings()
    return {
        "app": s.app_name,
        "environment": s.environment,
        "ai": registry.status(),
        "ocr": {"tesseract_available": tesseract_available()},
        "emergency_number": s.emergency_number,
        "crisis_line": s.crisis_line,
        "disclaimer": DISCLAIMER,
    }
