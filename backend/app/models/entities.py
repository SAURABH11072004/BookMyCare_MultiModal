"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[PatientProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    history: Mapped[list[MedicalHistoryEntry]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[list[MedicalReport]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analyses: Mapped[list[Analysis]] = relationship(back_populates="user", cascade="all, delete-orphan")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)  # female / male / other
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_pregnant: Mapped[bool] = mapped_column(Boolean, default=False)
    smoker: Mapped[bool] = mapped_column(Boolean, default=False)
    alcohol_use: Mapped[str | None] = mapped_column(String(20), nullable=True)  # none/occasional/regular
    activity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low/moderate/high
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    chronic_conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_medications: Mapped[list[str]] = mapped_column(JSON, default=list)
    emergency_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class MedicalHistoryEntry(Base):
    __tablename__ = "medical_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))  # condition/surgery/medication/allergy/vaccination/visit/other
    title: Mapped[str] = mapped_column(String(200))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="history")


class MedicalReport(Base):
    """An uploaded file: either a document report (lab/PDF/scan) or a medical image."""

    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="report")  # report / image
    title: Mapped[str] = mapped_column(String(200))
    report_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. blood_test, xray, skin_photo
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/done/partial/failed/skipped
    extraction_method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # pdf_text/ocr/plain_text/image_meta
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lab_values: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    image_features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="reports")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed / failed
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    urgency: Mapped[str] = mapped_column(String(20), default="routine")  # emergency/urgent/soon/routine
    provider: Mapped[str] = mapped_column(String(30), default="mock")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="analyses")


class HealthDocument(Base):
    """Public-health reference text (WHO/CDC) used for retrieval."""

    __tablename__ = "health_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(20))  # WHO / CDC
    url: Mapped[str] = mapped_column(String(500))
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    content: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(20), default="curated")  # curated / ingested
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
