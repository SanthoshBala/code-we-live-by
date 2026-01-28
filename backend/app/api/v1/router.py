"""API v1 router combining all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import titles, sections

api_router = APIRouter()

api_router.include_router(titles.router, prefix="/titles", tags=["titles"])
api_router.include_router(sections.router, prefix="/sections", tags=["sections"])
