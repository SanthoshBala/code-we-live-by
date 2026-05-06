"""SectionGroup upsert service — shared between ingestion and bootstrap.

Handles creating/updating the SectionGroup hierarchy (title → subtitle →
chapter → subchapter → …) from parsed USLM data.
"""

import logging
import re
from datetime import date

from sqlalchemy import select, tuple_
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
    positive_law_date = None
    if parsed.group_type == "title":
        if parsed.positive_law_date:
            positive_law_date = _parse_citation_date(parsed.positive_law_date)
        if parsed.is_positive_law and not positive_law_date:
            positive_law_date = _get_positive_law_date(int(parsed.number))

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


def _compute_positive_law_date(parsed: ParsedGroup) -> date | None:
    """Compute the positive law enactment date for a title group."""
    if parsed.group_type != "title":
        return None
    if parsed.positive_law_date:
        return _parse_citation_date(parsed.positive_law_date)
    if parsed.is_positive_law:
        try:
            return _get_positive_law_date(int(parsed.number))
        except (ValueError, TypeError):
            pass
    return None


async def upsert_groups_from_parse_result(
    session: AsyncSession,
    groups: list[ParsedGroup],
    force: bool = False,
) -> dict[str, SectionGroup]:
    """Upsert all groups from a parse result, resolving parent_key → parent_id.

    Processes groups level-by-level (one bulk SELECT + one flush per tree depth)
    instead of one round-trip per group, which is critical on cloud deployments
    where each DB round-trip adds ~10-20ms of latency.

    Args:
        session: Database session.
        groups: Parsed groups (parents-before-children order).
        force: If True, update existing records.

    Returns:
        Dict mapping group key → SectionGroup record.
    """
    if not groups:
        return {}

    group_lookup: dict[str, SectionGroup] = {}

    # Assign tree depth to each group.  Parents appear before children per contract,
    # so by the time we process group G its parent_key is already in key_to_depth.
    key_to_depth: dict[str, int] = {}
    for g in groups:
        key_to_depth[g.key] = (
            0 if not g.parent_key else key_to_depth.get(g.parent_key, -1) + 1
        )

    # Bucket groups by depth so we can batch SELECT + flush per level.
    depth_to_groups: dict[int, list[ParsedGroup]] = {}
    for g in groups:
        depth_to_groups.setdefault(key_to_depth[g.key], []).append(g)

    for depth in sorted(depth_to_groups.keys()):
        level_groups = depth_to_groups[depth]

        # Resolve parent_ids — all depth-(d-1) records are already flushed.
        resolved: list[tuple[int | None, ParsedGroup]] = []
        for pg in level_groups:
            parent_id: int | None = None
            if pg.parent_key:
                parent_rec = group_lookup.get(pg.parent_key)
                if parent_rec:
                    parent_id = parent_rec.group_id
            resolved.append((parent_id, pg))

        # ---- Bulk SELECT for this level ----------------------------------------
        # Split into null-parent groups (titles) and non-null-parent groups, because
        # PostgreSQL's tuple-IN syntax cannot match NULLs.

        null_pairs = [(pg.group_type, pg.number) for pid, pg in resolved if pid is None]
        non_null_triples = [
            (pid, pg.group_type, pg.number) for pid, pg in resolved if pid is not None
        ]

        existing_by_key: dict[tuple[int | None, str, str], SectionGroup] = {}

        if null_pairs:
            stmt = select(SectionGroup).where(
                SectionGroup.parent_id.is_(None),
                tuple_(SectionGroup.group_type, SectionGroup.number).in_(null_pairs),
            )
            result = await session.execute(stmt)
            for rec in result.scalars():
                existing_by_key[(None, rec.group_type, rec.number)] = rec

        if non_null_triples:
            stmt = select(SectionGroup).where(
                tuple_(
                    SectionGroup.parent_id,
                    SectionGroup.group_type,
                    SectionGroup.number,
                ).in_(non_null_triples)
            )
            result = await session.execute(stmt)
            for rec in result.scalars():
                existing_by_key[(rec.parent_id, rec.group_type, rec.number)] = rec

        # ---- Upsert each group at this level ------------------------------------
        for parent_id, pg in resolved:
            existing = existing_by_key.get((parent_id, pg.group_type, pg.number))

            if existing:
                if force:
                    existing.name = pg.name
                    existing.sort_order = pg.sort_order
                    existing.is_positive_law = pg.is_positive_law
                    existing.positive_law_date = _compute_positive_law_date(pg)
                    existing.positive_law_citation = pg.positive_law_citation
                group_lookup[pg.key] = existing
            else:
                new_group = SectionGroup(
                    parent_id=parent_id,
                    group_type=pg.group_type,
                    number=pg.number,
                    name=pg.name,
                    sort_order=pg.sort_order,
                    is_positive_law=pg.is_positive_law,
                    positive_law_date=_compute_positive_law_date(pg),
                    positive_law_citation=pg.positive_law_citation,
                )
                session.add(new_group)
                group_lookup[pg.key] = new_group

        # One flush per level assigns PKs that the next depth's parent_ids need.
        await session.flush()

    return group_lookup
