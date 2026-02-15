"""Law Viewer API endpoints for QC of parsed law text and amendments."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.public_law import get_law_text, get_laws_list, parse_law_amendments
from app.models.base import get_async_session
from app.schemas.law_viewer import (
    LawSummarySchema,
    LawTextSchema,
    ParsedAmendmentSchema,
)

router = APIRouter()


@router.get("/")
async def list_laws(
    session: AsyncSession = Depends(get_async_session),
) -> list[LawSummarySchema]:
    """List all public laws in the database."""
    return await get_laws_list(session)


@router.get("/{congress}/{law_number}/text")
async def read_law_text(
    congress: int,
    law_number: int,
) -> LawTextSchema:
    """Get raw HTM and XML text for a public law."""
    result = await get_law_text(congress, law_number)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Text not found for PL {congress}-{law_number}",
        )
    return result


@router.get("/{congress}/{law_number}/amendments")
async def read_law_amendments(
    congress: int,
    law_number: int,
) -> list[ParsedAmendmentSchema]:
    """Parse amendments from a law's text on-the-fly for QC."""
    return await parse_law_amendments(congress, law_number)
