"""SectionGroup upsert service — shared between ingestion and bootstrap.

Handles creating/updating the SectionGroup hierarchy (title → subtitle →
chapter → subchapter → …) from parsed USLM data.
"""

import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.us_code import SectionGroup
from pipeline.olrc.parser import ParsedGroup

logger = logging.getLogger(__name__)

# Fallback positive law enactment dates for titles where XML doesn't provide the date.
# Source: https://uscode.house.gov/codification/legislation.shtml
POSITIVE_LAW_DATES: dict[int, date] = {
    1: date(1947, 7, 30),
    3: date(1948, 6, 25),
    4: date(1947, 7, 30),
    5: date(1966, 9, 6),
    9: date(1947, 7, 30),
    10: date(1956, 8, 10),
    11: date(1978, 11, 6),
    13: date(1954, 8, 31),
    14: date(1949, 8, 4),
    17: date(1947, 7, 30),
    18: date(1948, 6, 25),
    23: date(1958, 7, 7),
    28: date(1948, 6, 25),
    31: date(1982, 9, 13),
    32: date(1956, 8, 10),
    35: date(1952, 7, 19),
    36: date(1998, 8, 12),
    37: date(1962, 9, 7),
    38: date(1958, 9, 2),
    39: date(1970, 8, 12),
    40: date(2002, 8, 21),
    41: date(2011, 1, 4),
    44: date(1968, 6, 19),
    46: date(2006, 10, 6),
    49: date(1983, 7, 5),
    51: date(2010, 10, 11),
    54: date(2014, 12, 19),
}


def _parse_citation_date(date_str: str | None) -> date | None:
    """Parse a date string from a citation into a Python date object.

    Handles two formats:
    - ISO format from Act hrefs: "1935-08-14" -> date(1935, 8, 14)
    - Prose format from source credits: "Oct. 19, 1976" -> date(1976, 10, 19)
    """
    if not date_str:
        return None

    iso_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if iso_match:
        try:
            return date(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
            )
        except ValueError:
            pass

    month_map = {
        "Jan": 1,
        "January": 1,
        "Feb": 2,
        "February": 2,
        "Mar": 3,
        "March": 3,
        "Apr": 4,
        "April": 4,
        "May": 5,
        "Jun": 6,
        "June": 6,
        "Jul": 7,
        "July": 7,
        "Aug": 8,
        "August": 8,
        "Sep": 9,
        "Sept": 9,
        "September": 9,
        "Oct": 10,
        "October": 10,
        "Nov": 11,
        "November": 11,
        "Dec": 12,
        "December": 12,
    }

    match = re.match(r"([A-Z][a-z]+)\.?\s+(\d{1,2})\s*,\s+(\d{4})", date_str)
    if match:
        month_str = match.group(1)
        month = month_map.get(month_str)
        if month:
            try:
                return date(int(match.group(3)), month, int(match.group(2)))
            except ValueError:
                pass

    return None


def _get_positive_law_date(title_number: int) -> date | None:
    """Get the positive law enactment date for a title."""
    return POSITIVE_LAW_DATES.get(title_number)


def _compute_positive_law_date(parsed: ParsedGroup) -> date | None:
    """Compute the positive_law_date value for a ParsedGroup."""
    if parsed.group_type != "title":
        return None
    positive_law_date = None
    if parsed.positive_law_date:
        positive_law_date = _parse_citation_date(parsed.positive_law_date)
    if parsed.is_positive_law and not positive_law_date:
        positive_law_date = _get_positive_law_date(int(parsed.number))
    return positive_law_date


async def upsert_group(
    session: AsyncSession,
    parsed: ParsedGroup,
    parent_id: int | None,
    force: bool = False,
) -> tuple[SectionGroup, bool]:
    """Insert or update a single SectionGroup record.

    Returns:
        Tuple of (group record, was_created).
    """
    positive_law_date = _compute_positive_law_date(parsed)

    if parent_id is not None:
        stmt = select(SectionGroup).where(
            SectionGroup.parent_id == parent_id,
            SectionGroup.group_type == parsed.group_type,
            SectionGroup.number == parsed.number,
        )
    else:
        stmt = select(SectionGroup).where(
            SectionGroup.parent_id.is_(None),
            SectionGroup.group_type == parsed.group_type,
            SectionGroup.number == parsed.number,
        )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if force:
            existing.name = parsed.name
            existing.sort_order = parsed.sort_order
            existing.is_positive_law = parsed.is_positive_law
            existing.positive_law_date = positive_law_date
            existing.positive_law_citation = parsed.positive_law_citation
        return existing, False

    group = SectionGroup(
        parent_id=parent_id,
        group_type=parsed.group_type,
        number=parsed.number,
        name=parsed.name,
        sort_order=parsed.sort_order,
        is_positive_law=parsed.is_positive_law,
        positive_law_date=positive_law_date,
        positive_law_citation=parsed.positive_law_citation,
    )
    session.add(group)
    await session.flush()
    return group, True


async def upsert_groups_from_parse_result(
    session: AsyncSession,
    groups: list[ParsedGroup],
    force: bool = False,
) -> dict[str, SectionGroup]:
    """Upsert all groups from a parse result, resolving parent_key → parent_id.

    Pre-loads all existing groups for the title hierarchy in a single recursive
    CTE query to eliminate per-group SELECTs on re-runs. On fresh seeds the CTE
    returns nothing and new groups are inserted one at a time (flush required to
    obtain DB-generated group_id for child foreign keys).

    Args:
        session: Database session.
        groups: Parsed groups (parents-before-children order).
        force: If True, update existing records.

    Returns:
        Dict mapping group key → SectionGroup record.
    """
    if not groups:
        return {}

    # Pre-load the full group hierarchy for this title in one round-trip.
    # Key: (parent_id, group_type, number) → SectionGroup
    preloaded: dict[tuple[int | None, str, str], SectionGroup] = {}
    root = next((g for g in groups if g.parent_key is None), None)
    if root is not None:
        sg_cte = (
            select(SectionGroup.group_id)
            .where(
                SectionGroup.parent_id.is_(None),
                SectionGroup.group_type == root.group_type,
                SectionGroup.number == root.number,
            )
            .cte(name="sg_hierarchy", recursive=True)
        )
        sg_cte = sg_cte.union_all(
            select(SectionGroup.group_id).where(
                SectionGroup.parent_id == sg_cte.c.group_id
            )
        )
        result = await session.execute(
            select(SectionGroup).where(
                SectionGroup.group_id.in_(select(sg_cte.c.group_id))
            )
        )
        for sg in result.scalars():
            preloaded[(sg.parent_id, sg.group_type, sg.number)] = sg

    group_lookup: dict[str, SectionGroup] = {}

    for parsed_group in groups:
        parent_id: int | None = None
        if parsed_group.parent_key:
            parent_record = group_lookup.get(parsed_group.parent_key)
            if parent_record:
                parent_id = parent_record.group_id

        cached = preloaded.get((parent_id, parsed_group.group_type, parsed_group.number))
        if cached is not None:
            if force:
                cached.name = parsed_group.name
                cached.sort_order = parsed_group.sort_order
                cached.is_positive_law = parsed_group.is_positive_law
                cached.positive_law_date = _compute_positive_law_date(parsed_group)
                cached.positive_law_citation = parsed_group.positive_law_citation
            group_record = cached
        else:
            # Group not yet in DB — insert and flush to materialise group_id
            # so child groups can reference it as parent_id.
            group_record, _ = await upsert_group(session, parsed_group, parent_id, force)
            preloaded[(parent_id, parsed_group.group_type, parsed_group.number)] = group_record

        group_lookup[parsed_group.key] = group_record

    return group_lookup
