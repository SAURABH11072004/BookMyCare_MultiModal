"""Fetch WHO / CDC public pages and index their text for retrieval.

Usage (from the backend folder, with the virtualenv active):
    python -m scripts.ingest_who_cdc                # ingest the default page list
    python -m scripts.ingest_who_cdc URL [URL ...]  # ingest specific who.int / cdc.gov pages

Only https://www.who.int and https://www.cdc.gov URLs are accepted. Page text is
stored locally for search; the app shows short excerpts with a link to the source.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from app.db.migrate import upgrade_head
from app.db.session import SessionLocal
from app.models import HealthDocument
from app.services.retrieval import DATA, invalidate

ALLOWED_HOSTS = {"www.who.int", "who.int", "www.cdc.gov", "cdc.gov"}
MAX_CHARS = 30000


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "noscript", "svg", "form", "button"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        if tag == "title":
            self._in_title = True
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "br", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join(ln for ln in lines if len(ln) > 30)  # drop menus / short fragments
    return p.title.strip(), text[:MAX_CHARS]


def default_urls() -> list[dict]:
    with open(DATA / "health_corpus.json", encoding="utf-8") as f:
        docs = json.load(f)["documents"]
    return [{"url": d["url"], "source": d["source"], "topics": d["topics"]} for d in docs]


def ingest(items: list[dict]) -> tuple[int, list[str]]:
    errors: list[str] = []
    n = 0
    with SessionLocal() as db, httpx.Client(timeout=30, follow_redirects=True,
                                            headers={"User-Agent": "BookMyCare-student-project/0.1 (educational)"}) as client:
        for item in items:
            url = item["url"]
            host = urlparse(url).hostname or ""
            if urlparse(url).scheme != "https" or host not in ALLOWED_HOSTS:
                errors.append(f"skipped (not who.int/cdc.gov over https): {url}")
                continue
            try:
                r = client.get(url)
                r.raise_for_status()
            except httpx.HTTPError as exc:
                errors.append(f"{url}: {exc}")
                continue
            title, text = html_to_text(r.text)
            if len(text) < 200:
                errors.append(f"{url}: too little text extracted")
                continue
            source = item.get("source") or ("WHO" if "who.int" in host else "CDC")
            slug = "live-" + re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.lower()).strip("-")[:110]
            doc = db.scalar(select(HealthDocument).where(HealthDocument.slug == slug))
            if doc is None:
                doc = HealthDocument(slug=slug, url=url, source=source, origin="ingested")
                db.add(doc)
            doc.title = (title or url)[:300]
            doc.topics = item.get("topics", [])
            doc.content = text
            doc.retrieved_at = datetime.now(timezone.utc)
            n += 1
            print(f"  ✓ {source}: {doc.title[:80]} ({len(text)} chars)")
        db.commit()
    invalidate()
    return n, errors


def main(argv: list[str]) -> int:
    upgrade_head()
    items = [{"url": u} for u in argv] if argv else default_urls()
    print(f"Ingesting {len(items)} page(s)…")
    n, errors = ingest(items)
    print(f"Indexed {n} page(s).")
    for e in errors:
        print("  !", e)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
