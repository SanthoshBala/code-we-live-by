"""Revision endpoints for querying the commit timeline."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.revision import get_head_revision
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
