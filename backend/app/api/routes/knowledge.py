from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import HealthDocument, User
from app.services import retrieval

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=200), k: int = Query(5, ge=1, le=20),
           _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"query": q, "results": retrieval.search(db, q, k=k)}


@router.get("/stats")
def stats(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(HealthDocument.source, HealthDocument.origin, func.count()).group_by(HealthDocument.source, HealthDocument.origin)).all()
    return {"documents": [{"source": s, "origin": o, "count": c} for s, o, c in rows]}
