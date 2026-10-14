from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sex = Literal["female", "male", "other"]
HistoryCategory = Literal["condition", "surgery", "medication", "allergy", "vaccination", "visit", "other"]


def _clean_list(v: list[str] | None) -> list[str]:
    if not v:
        return []
    seen, out = set(), []
    for item in v:
        item = (item or "").strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item[:100])
    return out[:50]


class ProfileBase(BaseModel):
    date_of_birth: date | None = None
    sex: Sex | None = None
    height_cm: float | None = Field(default=None, gt=30, lt=260)
    weight_kg: float | None = Field(default=None, gt=1, lt=400)
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] | None = None
    is_pregnant: bool = False
    smoker: bool = False
    alcohol_use: Literal["none", "occasional", "regular"] | None = None
    activity_level: Literal["low", "moderate", "high"] | None = None
    allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    emergency_contact: str | None = Field(default=None, max_length=200)

    @field_validator("allergies", "chronic_conditions", "current_medications", mode="before")
    @classmethod
    def clean_lists(cls, v):
        return _clean_list(v)

    @field_validator("date_of_birth")
    @classmethod
    def dob_in_past(cls, v: date | None) -> date | None:
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v and v.year < 1900:
            raise ValueError("Date of birth is not plausible")
        return v


class ProfileUpdate(ProfileBase):
    pass


class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    age: int | None = None
    bmi: float | None = None
    updated_at: datetime | None = None


class HistoryCreate(BaseModel):
    category: HistoryCategory
    title: str = Field(min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)
    event_date: date | None = None
    is_ongoing: bool = False


class HistoryUpdate(BaseModel):
    category: HistoryCategory | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)
    event_date: date | None = None
    is_ongoing: bool | None = None


class HistoryOut(HistoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
