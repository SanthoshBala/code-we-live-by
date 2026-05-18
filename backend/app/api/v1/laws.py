"""Law Viewer API endpoints for QC of parsed law text and amendments."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.public_law import (
    compute_law_diffs,
    get_law_history,
    get_law_metadata,
    get_law_standalone_provisions,
    get_law_text,
    get_laws_list,
    parse_law_amendments,
)
from app.models.base import get_async_session
from app.schemas.law_history import LegislativeHistorySchema
from app.schemas.law_viewer import (
    LawSummarySchema,
    LawTextSchema,
    ParsedAmendmentSchema,
    SectionDiffSchema,
    StandaloneProvisionSchema,
)

router = APIRouter()


@router.get("")
async def list_laws(
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[LawSummarySchema]:
    """List public laws in the database (paginated)."""
    return await get_laws_list(session, limit=limit, offset=offset)


@router.get("/{congress}/{law_number}/text")
async def read_law_text(
    congress: int,
    law_number: int,
    format: Literal["all", "metadata", "htm", "xml"] = Query(
        "all",
        description="What to include: 'metadata' (no content), 'htm', 'xml', or 'all'",
    ),
    session: AsyncSession = Depends(get_async_session),
) -> LawTextSchema:
    """Get text for a public law.

    Use format=metadata for just titles/dates (fast, no file I/O).
    Use format=htm or format=xml to fetch only the needed content.
    """
    if format == "metadata":
        result = await get_law_metadata(session, congress, law_number)
    else:
        include_htm = format in ("all", "htm")
        include_xml = format in ("all", "xml")
        result = await get_law_text(
            session,
            congress,
            law_number,
            include_htm=include_htm,
            include_xml=include_xml,
        )
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


@router.get("/{congress}/{law_number}/standalone-provisions")
async def read_standalone_provisions(
    congress: int,
    law_number: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[StandaloneProvisionSchema]:
    """Return freestanding provisions from a law that don't amend the US Code.

    These are sections like naming acts, sunset clauses, standalone
    appropriations, and definitions scoped to the act itself. They are not
    included in the codified amendments diff view.
    """
    return await get_law_standalone_provisions(session, congress, law_number)


@router.get("/{congress}/{law_number}/history")
async def read_law_history(
    congress: int,
    law_number: int,
    session: AsyncSession = Depends(get_async_session),
) -> LegislativeHistorySchema:
    """Return the legislative history timeline for a public law.

    Aggregates bill actions, sponsors, and vote data from the Congress.gov API
    and maps them to a PR-conversation-style timeline. Requires CONGRESS_API_KEY
    to be configured; returns 503 if the API is unavailable.
    """
    result = await get_law_history(session, congress, law_number)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Law PL {congress}-{law_number} not found",
        )
    return result
