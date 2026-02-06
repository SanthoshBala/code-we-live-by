"""Title endpoints for browsing the US Code hierarchy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.us_code import get_all_titles, get_title_structure
from app.models.base import get_async_session
from app.schemas.us_code import TitleStructureSchema, TitleSummarySchema

router = APIRouter()


@router.get("/")
async def list_titles(
    session: AsyncSession = Depends(get_async_session),
) -> list[TitleSummarySchema]:
    """List all US Code titles with chapter and section counts."""
    return await get_all_titles(session)


@router.get("/{title_number}/structure")
async def get_structure(
    title_number: int,
    session: AsyncSession = Depends(get_async_session),
) -> TitleStructureSchema:
    """Get the chapter/subchapter/section tree for a title."""
    result = await get_title_structure(session, title_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Title {title_number} not found")
    return result
