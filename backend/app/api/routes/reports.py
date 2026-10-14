from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import MedicalReport, User
from app.schemas.report import ReportDetail, ReportSummary
from app.services import extraction
from app.services.lab_parser import parse_lab_values

router = APIRouter(prefix="/reports", tags=["reports"])

EXT_FOR_TYPE = {v: k for k, v in extraction.EXT_TO_TYPE.items() if k not in (".jpeg", ".tif")}


def _summary(r: MedicalReport) -> ReportSummary:
    s = ReportSummary.model_validate(r)
    s.lab_count = len(r.lab_values or [])
    return s


def _detail(r: MedicalReport) -> ReportDetail:
    d = ReportDetail.model_validate(r)
    d.lab_count = len(r.lab_values or [])
    return d


def _run_extraction(r: MedicalReport, data: bytes, sex: str | None) -> None:
    res = extraction.extract(data, r.content_type, r.kind)
    r.extraction_status = res.status
    r.extraction_method = res.method
    r.extracted_text = res.text or None
    r.extraction_error = res.error
    r.image_features = res.image_features
    r.lab_values = parse_lab_values(res.text, sex) if res.text else []


@router.post("", response_model=ReportDetail, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile = File(...),
    kind: Literal["report", "image"] = Form("report"),
    title: str | None = Form(None),
    report_type: str | None = Form(None),
    report_date: date | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = get_settings()
    limit = s.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File is larger than {s.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    filename = Path(file.filename or "upload").name[:200]
    ctype = extraction.detect_content_type(filename, file.content_type, data[:16])
    if ctype is None or ctype not in extraction.ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported file type. Upload PDF, PNG, JPG, WEBP, BMP, TIFF, TXT or CSV.")
    if kind == "image" and ctype not in extraction.IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Medical images must be PNG, JPG, WEBP, BMP or TIFF.")
    if report_date and report_date > date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Report date cannot be in the future")

    stored = f"{uuid.uuid4().hex}{EXT_FOR_TYPE.get(ctype, '')}"
    (s.upload_dir / stored).write_bytes(data)

    r = MedicalReport(
        user_id=user.id, kind=kind, title=(title or filename).strip()[:200] or filename,
        report_type=(report_type or None), original_filename=filename, stored_filename=stored,
        content_type=ctype, size_bytes=len(data), report_date=report_date,
    )
    _run_extraction(r, data, user.profile.sex if user.profile else None)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _detail(r)


@router.get("", response_model=list[ReportSummary])
def list_reports(kind: Literal["report", "image"] | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(MedicalReport).where(MedicalReport.user_id == user.id)
    if kind:
        q = q.where(MedicalReport.kind == kind)
    rows = db.scalars(q.order_by(MedicalReport.created_at.desc(), MedicalReport.id.desc())).all()
    return [_summary(r) for r in rows]


def _get(report_id: int, user: User, db: Session) -> MedicalReport:
    r = db.get(MedicalReport, report_id)
    if not r or r.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return r


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(_get(report_id, user, db))


@router.get("/{report_id}/file")
def download_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _get(report_id, user, db)
    path = get_settings().upload_dir / r.stored_filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    return FileResponse(path, media_type=r.content_type, filename=r.original_filename)


@router.post("/{report_id}/reprocess", response_model=ReportDetail)
def reprocess_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _get(report_id, user, db)
    path = get_settings().upload_dir / r.stored_filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file is missing")
    _run_extraction(r, path.read_bytes(), user.profile.sex if user.profile else None)
    db.commit()
    db.refresh(r)
    return _detail(r)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _get(report_id, user, db)
    path = get_settings().upload_dir / r.stored_filename
    db.delete(r)
    db.commit()
    path.unlink(missing_ok=True)
