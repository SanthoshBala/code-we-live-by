"""Revision endpoints for querying the commit timeline."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.revision import (
    get_head_revision,
    get_latest_revision_for_title,
    get_revision_by_id,
)
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


@router.get("/{revision_id}")
async def get_revision(
    revision_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> HeadRevisionSchema:
    """Return metadata for a specific revision by ID."""
    result = await get_revision_by_id(session, revision_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Revision {revision_id} not found")
    return result
