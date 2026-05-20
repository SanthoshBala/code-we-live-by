"""CRUD operations for CODEOWNERS committee queries."""

from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.codeowners import CommitteeUSCodeMapping
from app.models.supporting import Committee
from app.schemas.committees import (
    CommitteeBaseSchema,
    CommitteeCongressInstanceSchema,
    CommitteeOwnershipSchema,
)

# Update this constant at the start of each new Congress.
CURRENT_CONGRESS = 119


def _congress_filter(congress: int):  # type: ignore[return]
    """SQLAlchemy WHERE clause for mappings valid at the given Congress."""
    return and_(
        CommitteeUSCodeMapping.congress_start <= congress,
        or_(
            CommitteeUSCodeMapping.congress_end.is_(None),
            CommitteeUSCodeMapping.congress_end >= congress,
        ),
    )


def _build_ownership(
    mapping: CommitteeUSCodeMapping,
    committee: Committee,
) -> CommitteeOwnershipSchema:
    return CommitteeOwnershipSchema(
        committee=CommitteeBaseSchema(
            committee_code=committee.committee_code,
            chamber=committee.chamber.value,
            name=committee.name,
            url=committee.url,
        ),
        jurisdiction_type=mapping.jurisdiction_type,
        display_order=mapping.display_order,
        title_number=mapping.title_number,
        chapter_number=mapping.chapter_number,
        notes=mapping.notes,
        congress_start=mapping.congress_start,
        congress_end=mapping.congress_end,
    )


async def get_owners_for_title(
    session: AsyncSession,
    title_number: int,
    congress: int = CURRENT_CONGRESS,
) -> list[CommitteeOwnershipSchema]:
    """Return committees that own the given US Code title (title-level only).

    Returns only title-level mappings (chapter_number IS NULL), ordered by display_order.
    """
    result = await session.execute(
        select(CommitteeUSCodeMapping, Committee)
        .join(Committee, CommitteeUSCodeMapping.committee_id == Committee.committee_id)
        .where(
            CommitteeUSCodeMapping.title_number == title_number,
            CommitteeUSCodeMapping.chapter_number.is_(None),
            _congress_filter(congress),
        )
        .order_by(CommitteeUSCodeMapping.display_order)
    )
    return [_build_ownership(m, c) for m, c in result]


async def get_owners_for_chapter(
    session: AsyncSession,
    title_number: int,
    chapter_number: str,
    congress: int = CURRENT_CONGRESS,
) -> list[CommitteeOwnershipSchema]:
    """Return committees that own the given chapter, falling back to title-level.

    Implements the CODEOWNERS specificity rule: chapter-level overrides take
    precedence; if none exist, title-level mappings are returned instead.
    """
    chapter_result = await session.execute(
        select(CommitteeUSCodeMapping, Committee)
        .join(Committee, CommitteeUSCodeMapping.committee_id == Committee.committee_id)
        .where(
            CommitteeUSCodeMapping.title_number == title_number,
            CommitteeUSCodeMapping.chapter_number == chapter_number,
            _congress_filter(congress),
        )
        .order_by(CommitteeUSCodeMapping.display_order)
    )
    rows = chapter_result.all()
    if rows:
        return [_build_ownership(m, c) for m, c in rows]

    # Fall back to title-level
    return await get_owners_for_title(session, title_number, congress)


async def get_all_mappings(
    session: AsyncSession,
    congress: int = CURRENT_CONGRESS,
) -> list[CommitteeOwnershipSchema]:
    """Return all committee→code mappings valid for the given Congress."""
    result = await session.execute(
        select(CommitteeUSCodeMapping, Committee)
        .join(Committee, CommitteeUSCodeMapping.committee_id == Committee.committee_id)
        .where(_congress_filter(congress))
        .order_by(
            CommitteeUSCodeMapping.title_number,
            CommitteeUSCodeMapping.chapter_number.nulls_first(),
            CommitteeUSCodeMapping.display_order,
        )
    )
    return [_build_ownership(m, c) for m, c in result]


async def get_congress_instances(
    session: AsyncSession,
    congress: int,
    chamber: str | None = None,
) -> list[CommitteeCongressInstanceSchema]:
    """Return CommitteeCongressInstance records for the given Congress.

    Args:
        session: Async DB session.
        congress: Congress number.
        chamber: Optional "House" or "Senate" filter.
    """
    from app.models.codeowners import CommitteeCongressInstance

    stmt = (
        select(CommitteeCongressInstance, Committee)
        .join(
            Committee,
            CommitteeCongressInstance.committee_id == Committee.committee_id,
        )
        .where(CommitteeCongressInstance.congress == congress)
        .order_by(Committee.chamber, Committee.name)
    )
    if chamber is not None:
        stmt = stmt.where(Committee.chamber == chamber)

    result = await session.execute(stmt)
    return [
        CommitteeCongressInstanceSchema(
            committee_code=committee.committee_code,
            chamber=committee.chamber.value,
            official_name=instance.official_name,
            congress=instance.congress,
            rule_citation=instance.rule_citation,
        )
        for instance, committee in result
    ]
