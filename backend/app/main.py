from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bookmycare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.auto_migrate:
        from app.db.migrate import upgrade_head

        upgrade_head()
    if s.seed_knowledge:
        from app.db.session import SessionLocal
        from app.services.retrieval import seed_curated

        with SessionLocal() as db:
            n = seed_curated(db)
            if n:
                log.info("Seeded %d curated WHO/CDC documents", n)
    from app.ai.registry import status

    st = status()
    log.info("AI provider: %s%s", st["active_provider"], " (MOCK MODE - no API keys configured)" if st["mock_mode"] else "")
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", []) if x not in ("body", "query", "path"))
            errors.append({"field": loc, "message": e.get("msg", "Invalid value").removeprefix("Value error, ")})
        msg = "; ".join(f"{e['field']}: {e['message']}" if e["field"] else e["message"] for e in errors)
        return JSONResponse(status_code=422, content={"detail": msg or "Invalid request", "errors": errors})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # pragma: no cover - safety net
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_router)
    return app


app = create_app()
