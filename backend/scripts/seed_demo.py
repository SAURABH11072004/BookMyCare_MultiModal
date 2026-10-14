"""Create a demo account populated with SYNTHETIC data.

    python -m scripts.seed_demo
Login: demo@bookmycare.dev / DemoPass123  (development only)
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.migrate import upgrade_head
from app.db.session import SessionLocal
from app.models import MedicalHistoryEntry, MedicalReport, PatientProfile, User
from app.services import extraction
from app.services.lab_parser import parse_lab_values
from app.services.retrieval import seed_curated

SAMPLES = Path(__file__).resolve().parents[1] / "sample_data"
DEMO_EMAIL = "demo@bookmycare.dev"
DEMO_PASSWORD = "DemoPass123"


def _add_file(db, user: User, filename: str, kind: str, title: str, report_type: str, report_date: date):
    data = (SAMPLES / filename).read_bytes()
    ctype = extraction.detect_content_type(filename, None, data[:16])
    stored = f"{uuid.uuid4().hex}{Path(filename).suffix}"
    (get_settings().upload_dir / stored).write_bytes(data)
    res = extraction.extract(data, ctype, kind)
    db.add(MedicalReport(
        user_id=user.id, kind=kind, title=title, report_type=report_type, original_filename=filename,
        stored_filename=stored, content_type=ctype, size_bytes=len(data), report_date=report_date,
        extraction_status=res.status, extraction_method=res.method, extracted_text=res.text or None,
        extraction_error=res.error, image_features=res.image_features,
        lab_values=parse_lab_values(res.text, "female") if res.text else [],
    ))


def main() -> None:
    upgrade_head()
    with SessionLocal() as db:
        seed_curated(db)
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return
        user = User(email=DEMO_EMAIL, full_name="Demo Patient (synthetic)", hashed_password=hash_password(DEMO_PASSWORD))
        user.profile = PatientProfile(
            date_of_birth=date(1974, 3, 15), sex="female", height_cm=158, weight_kg=74, blood_group="B+",
            activity_level="low", alcohol_use="none", allergies=["Penicillin"],
            chronic_conditions=[], current_medications=[], emergency_contact="Synthetic contact",
        )
        db.add(user)
        db.flush()
        db.add_all([
            MedicalHistoryEntry(user_id=user.id, category="condition", title="Family history of diabetes",
                                details="Mother has type 2 diabetes (synthetic example)."),
            MedicalHistoryEntry(user_id=user.id, category="allergy", title="Penicillin", details="Rash (synthetic example)."),
            MedicalHistoryEntry(user_id=user.id, category="vaccination", title="Influenza vaccine", event_date=date(2025, 10, 1)),
            MedicalHistoryEntry(user_id=user.id, category="visit", title="Annual check-up", event_date=date(2026, 9, 20),
                                details="Advised blood tests (synthetic example)."),
        ])
        _add_file(db, user, "synthetic_metabolic_panel.pdf", "report", "Metabolic panel (synthetic)", "blood_test", date(2026, 9, 22))
        _add_file(db, user, "synthetic_grayscale_image.png", "image", "Synthetic test image", "other", date(2026, 9, 22))
        db.commit()
        print(f"Created demo user {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
