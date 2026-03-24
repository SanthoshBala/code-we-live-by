"""Title endpoints for browsing the US Code hierarchy."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.us_code import get_all_titles, get_title_structure
from app.models.base import get_async_session
from app.schemas.us_code import TitleStructureSchema, TitleSummarySchema

router = APIRouter()

# Title data changes only when new revisions are ingested (~monthly).
# Cache for 5 min at the edge, allow stale-while-revalidate for 1 hour.
_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=3600"


@router.get("")
async def list_titles(
    revision: int | None = Query(None, description="Revision ID (default: HEAD)"),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """List all US Code titles with chapter and section counts."""
    titles = await get_all_titles(session, revision)
    return JSONResponse(
        content=[t.model_dump(mode="json") for t in titles],
        headers={"Cache-Control": _CACHE_CONTROL},
    )


@router.get("/{title_number}/structure")
async def get_structure(
    title_number: int,
    revision: int | None = Query(None, description="Revision ID (default: HEAD)"),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """Get the group/section tree for a title."""
    result = await get_title_structure(session, title_number, revision)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Title {title_number} not found")
    return JSONResponse(
        content=result.model_dump(),
        headers={"Cache-Control": _CACHE_CONTROL},
    )
