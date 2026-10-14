from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import MedicalHistoryEntry, PatientProfile, User
from app.schemas.patient import HistoryCreate, HistoryOut, HistoryUpdate, ProfileOut, ProfileUpdate
from app.services.analysis_engine import compute_age, compute_bmi

router = APIRouter(tags=["patient"])


def _profile_out(p: PatientProfile) -> ProfileOut:
    out = ProfileOut.model_validate(p)
    out.age = compute_age(p.date_of_birth)
    out.bmi = compute_bmi(p.height_cm, p.weight_kg)
    return out


def _ensure_profile(user: User, db: Session) -> PatientProfile:
    if user.profile is None:
        user.profile = PatientProfile()
        db.commit()
        db.refresh(user)
    return user.profile


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _profile_out(_ensure_profile(user, db))


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _ensure_profile(user, db)
    data = body.model_dump()
    if data.get("sex") != "female":
        data["is_pregnant"] = False
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _profile_out(p)


@router.get("/history", response_model=list[HistoryOut])
def list_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(MedicalHistoryEntry).where(MedicalHistoryEntry.user_id == user.id)
        .order_by(MedicalHistoryEntry.event_date.desc().nulls_last(), MedicalHistoryEntry.id.desc())
    ).all()
    return rows


@router.post("/history", response_model=HistoryOut, status_code=status.HTTP_201_CREATED)
def create_history(body: HistoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = MedicalHistoryEntry(user_id=user.id, **body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _get_entry(entry_id: int, user: User, db: Session) -> MedicalHistoryEntry:
    entry = db.get(MedicalHistoryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "History entry not found")
    return entry


@router.patch("/history/{entry_id}", response_model=HistoryOut)
def update_history(entry_id: int, body: HistoryUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = _get_entry(entry_id, user, db)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k in ("category", "title") and v is None:
            continue
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/history/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get_entry(entry_id, user, db))
    db.commit()
