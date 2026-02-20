"""Revision endpoints for querying the commit timeline."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.revision import get_head_revision, get_latest_revision_for_title
from app.models.base import get_async_session
from app.schemas.revision import HeadRevisionSchema

router = APIRouter()


@router.get("/head")
async def head_revision(
    session: AsyncSession = Depends(get_async_session),
) -> HeadRevisionSchema:
    """Return the latest ingested revision (HEAD)."""
    result = await get_head_revision(session)
    if result is None:
        raise HTTPException(status_code=404, detail="No ingested revisions found")
    return result


@router.get("/latest")
async def latest_revision_for_title(
    title: int = Query(..., description="Title number"),
    session: AsyncSession = Depends(get_async_session),
) -> HeadRevisionSchema:
    """Return the most recent revision that affected any section in a title."""
    result = await get_latest_revision_for_title(session, title)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"No revisions found for title {title}"
        )
    return result
