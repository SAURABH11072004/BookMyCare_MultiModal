from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisCreate(BaseModel):
    symptoms: list[str] = Field(default_factory=list, max_length=40)
    symptom_text: str | None = Field(default=None, max_length=4000)
    duration_days: int | None = Field(default=None, ge=0, le=3650)
    severity: Literal["mild", "moderate", "severe"] | None = None
    report_ids: list[int] = Field(default_factory=list, max_length=20)
    image_ids: list[int] = Field(default_factory=list, max_length=10)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("symptoms", mode="before")
    @classmethod
    def clean(cls, v):
        return [s.strip()[:80] for s in (v or []) if isinstance(s, str) and s.strip()]


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    urgency: str
    provider: str
    is_mock: bool
    created_at: datetime
    top_condition: str | None = None
    symptom_preview: list[str] = []


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    urgency: str
    provider: str
    is_mock: bool
    created_at: datetime
    inputs: dict[str, Any]
    result: dict[str, Any]
