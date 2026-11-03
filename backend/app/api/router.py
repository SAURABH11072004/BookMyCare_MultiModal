from fastapi import APIRouter

from app.api.routes import analyses, auth, knowledge, profile, reports, staff, support, system, trends

api_router = APIRouter(prefix="/api")
for r in (system.router, auth.router, profile.router, reports.router, analyses.router, knowledge.router, trends.router, support.router, staff.router):
    api_router.include_router(r)
