"""Section endpoints for viewing US Code section content."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.us_code import get_section
from app.models.base import get_async_session
from app.schemas.us_code import SectionViewerSchema

router = APIRouter()


@router.get("/{title_number}/{section_number}")
async def read_section(
    title_number: int,
    section_number: str,
    session: AsyncSession = Depends(get_async_session),
) -> SectionViewerSchema:
    """Get the full content of a US Code section."""
    result = await get_section(session, title_number, section_number)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {title_number} USC § {section_number} not found",
        )
    return result


@router.get("/{title_number}/{section_number}/blame")
async def get_section_blame(title_number: int, section_number: str) -> dict[str, str]:
    """Get blame view for a section."""
    return {
        "message": f"Blame for {title_number} USC § {section_number} - not yet implemented"
    }
