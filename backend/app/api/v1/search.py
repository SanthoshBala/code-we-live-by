"""Search endpoints for sections and public laws."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.search import search_laws, search_sections
from app.models.base import get_async_session
from app.schemas.search import LawSearchResponse, SectionSearchResponse

router = APIRouter()

_MAX_LIMIT = 100


@router.get("/sections")
async def search_sections_endpoint(
    q: str = Query(..., min_length=2, description="Search query"),
    title: int | None = Query(None, description="Filter by title number"),
    limit: int = Query(20, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> SectionSearchResponse:
    """Search US Code sections by heading or text content."""
    return await search_sections(session, q, title=title, limit=limit, offset=offset)


@router.get("/laws")
async def search_laws_endpoint(
    q: str = Query(..., min_length=2, description="Search query"),
    congress: int | None = Query(None, description="Filter by congress number"),
    limit: int = Query(20, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> LawSearchResponse:
    """Search public laws by name, title, or number."""
    return await search_laws(session, q, congress=congress, limit=limit, offset=offset)
