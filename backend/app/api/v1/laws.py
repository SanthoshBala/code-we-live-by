"""Law Viewer API endpoints for QC of parsed law text and amendments."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.public_law import (
    compute_law_diffs,
    get_law_text,
    get_laws_list,
    parse_law_amendments,
)
from app.models.base import get_async_session
from app.schemas.law_viewer import (
    LawSummarySchema,
    LawTextSchema,
    ParsedAmendmentSchema,
    SectionDiffSchema,
)

router = APIRouter()

_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=3600"


@router.get("")
async def list_laws(
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """List all public laws in the database."""
    laws = await get_laws_list(session)
    return JSONResponse(
        content=[law.model_dump(mode="json") for law in laws],
        headers={"Cache-Control": _CACHE_CONTROL},
    )


@router.get("/{congress}/{law_number}/text")
async def read_law_text(
    congress: int,
    law_number: int,
    session: AsyncSession = Depends(get_async_session),
) -> LawTextSchema:
    """Get raw HTM and XML text for a public law."""
    result = await get_law_text(session, congress, law_number)
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
    session: AsyncSession = Depends(get_async_session),
) -> list[ParsedAmendmentSchema]:
    """Parse amendments from a law's text on-the-fly for QC."""
    return await parse_law_amendments(session, congress, law_number)


@router.get("/{congress}/{law_number}/diffs")
async def read_law_diffs(
    congress: int,
    law_number: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[SectionDiffSchema]:
    """Compute per-section unified diffs for a law's amendments."""
    return await compute_law_diffs(session, congress, law_number)
