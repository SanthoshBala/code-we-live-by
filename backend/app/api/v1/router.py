"""API v1 router combining all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import laws, revisions, sections, titles

api_router = APIRouter()

api_router.include_router(titles.router, prefix="/titles", tags=["titles"])
api_router.include_router(sections.router, prefix="/sections", tags=["sections"])
api_router.include_router(laws.router, prefix="/laws", tags=["laws"])
api_router.include_router(revisions.router, prefix="/revisions", tags=["revisions"])
