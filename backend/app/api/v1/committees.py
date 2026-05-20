"""CODEOWNERS API: committee jurisdiction for US Code titles and chapters."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.committees import (
    CURRENT_CONGRESS,
    get_all_mappings,
    get_congress_instances,
    get_owners_for_chapter,
    get_owners_for_title,
)
from app.models.base import get_async_session
from app.schemas.committees import (
    CodeOwnersForPathSchema,
    CommitteeCongressInstanceSchema,
    CommitteeOwnershipSchema,
)

router = APIRouter()


@router.get("/owners/title/{title_number}")
async def owners_for_title(
    title_number: int,
    congress: int = Query(CURRENT_CONGRESS, description="Congress number"),
    session: AsyncSession = Depends(get_async_session),
) -> CodeOwnersForPathSchema:
    """Return committees that own the given US Code title."""
    owners = await get_owners_for_title(session, title_number, congress)
    return CodeOwnersForPathSchema(
        title_number=title_number,
        chapter_number=None,
        congress=congress,
        owners=owners,
    )


@router.get("/owners/title/{title_number}/chapter/{chapter_number}")
async def owners_for_chapter(
    title_number: int,
    chapter_number: str,
    congress: int = Query(CURRENT_CONGRESS, description="Congress number"),
    session: AsyncSession = Depends(get_async_session),
) -> CodeOwnersForPathSchema:
    """Return committees that own the given chapter, with title-level fallback."""
    owners = await get_owners_for_chapter(
        session, title_number, chapter_number, congress
    )
    return CodeOwnersForPathSchema(
        title_number=title_number,
        chapter_number=chapter_number,
        congress=congress,
        owners=owners,
    )


@router.get("/congress/{congress}/owners")
async def all_owners_for_congress(
    congress: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[CommitteeOwnershipSchema]:
    """Return all CODEOWNERS mappings valid for the given Congress."""
    return await get_all_mappings(session, congress)


@router.get("/congress/{congress}/instances")
async def committee_instances(
    congress: int,
    chamber: str | None = Query(
        None, description="Filter by chamber: 'House' or 'Senate'"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> list[CommitteeCongressInstanceSchema]:
    """Return committee congress instances (Rule X data) for the given Congress."""
    return await get_congress_instances(session, congress, chamber)
