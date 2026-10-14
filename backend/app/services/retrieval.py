"""Lightweight BM25 retrieval over WHO/CDC reference documents stored in the DB."""
from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HealthDocument

DATA = Path(__file__).resolve().parents[1] / "data"

_STOP = set(
    "a an and are as at be by can for from has have if in into is it its of on or such that the their then there these they this to was were will with you your may not no more most other some than very who which also about after before over under".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(t: str) -> str:
    for suf in ("ations", "ation", "ings", "ing", "ness", "ies", "es", "ed", "ly", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)] + ("y" if suf == "ies" else "")
    return t


def tokenize(text: str) -> list[str]:
    text = text.lower().replace("anaemia", "anemia").replace("haemo", "hemo").replace("diarrhoea", "diarrhea")
    return [_stem(t) for t in _TOKEN.findall(text) if t not in _STOP and len(t) > 1]


class BM25Index:
    def __init__(self, docs: list[dict], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d["title"] + " " + d["title"] + " " + d["content"] + " " + " ".join(d["topics"]))) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lens) / len(self.lens)) if docs else 0
        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 5, topics: list[str] | None = None) -> list[tuple[dict, float]]:
        q = tokenize(query)
        if not q and not topics:
            return []
        scores = []
        for i, tf in enumerate(self.tfs):
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                f = tf[t]
                s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / (self.avgdl or 1)))
            if topics and set(topics) & set(self.docs[i]["topics"]):
                s += 3.0
            if s > 0:
                scores.append((self.docs[i], s))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]


_lock = threading.Lock()
_index: BM25Index | None = None


def invalidate() -> None:
    global _index
    with _lock:
        _index = None


def get_index(db: Session) -> BM25Index:
    global _index
    with _lock:
        if _index is None:
            rows = db.scalars(select(HealthDocument)).all()
            _index = BM25Index([
                {"id": r.id, "slug": r.slug, "title": r.title, "source": r.source, "url": r.url,
                 "topics": r.topics or [], "content": r.content, "origin": r.origin}
                for r in rows
            ])
        return _index


def snippet(content: str, query: str, length: int = 320) -> str:
    """Return a short excerpt around the first query term occurrence."""
    terms = [t for t in re.findall(r"[a-zA-Z]{4,}", query.lower())]
    low = content.lower()
    pos = min((low.find(t) for t in terms if low.find(t) != -1), default=0)
    start = max(0, pos - 80)
    start = content.rfind(". ", 0, start) + 2 if content.rfind(". ", 0, start) != -1 else start
    text = content[start : start + length].strip()
    return text + ("…" if start + length < len(content) else "")


def search(db: Session, query: str, k: int = 5, topics: list[str] | None = None) -> list[dict]:
    out = []
    for doc, score in get_index(db).search(query, k=k, topics=topics):
        out.append({
            "slug": doc["slug"], "title": doc["title"], "source": doc["source"], "url": doc["url"],
            "topics": doc["topics"], "origin": doc["origin"], "score": round(score, 3),
            "snippet": snippet(doc["content"], query),
        })
    return out


def seed_curated(db: Session) -> int:
    """Insert curated WHO/CDC summaries if missing. Returns number inserted."""
    with open(DATA / "health_corpus.json", encoding="utf-8") as f:
        docs = json.load(f)["documents"]
    existing = set(db.scalars(select(HealthDocument.slug)).all())
    n = 0
    for d in docs:
        if d["slug"] in existing:
            continue
        db.add(HealthDocument(slug=d["slug"], title=d["title"], source=d["source"], url=d["url"],
                              topics=d["topics"], content=d["content"], origin="curated"))
        n += 1
    if n:
        db.commit()
        invalidate()
    return n
