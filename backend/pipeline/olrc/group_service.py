"""SectionGroup upsert service — shared between ingestion and bootstrap.

Handles creating/updating the SectionGroup hierarchy (title → subtitle →
chapter → subchapter → …) from parsed USLM data.
"""

import logging
import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.us_code import SectionGroup
from pipeline.olrc.parser import ParsedGroup

logger = logging.getLogger(__name__)

# Fixed project namespace for deterministic group UUIDs.  Must never change
# after first deployment — altering it would invalidate all stored group_ids.
_GROUP_NS = uuid.UUID("6f3a4b5c-2d1e-4f0a-9c8d-7e6f5d4c3b2a")


def group_id_from_key(key: str) -> uuid.UUID:
    """Compute a stable UUID for a SectionGroup from its hierarchy key.

    The key format (e.g. "title:17/chapter:1/subchapter:I") is derived
    entirely from the US Code's XML structure and is stable across release
    points for the same structural node.  UUID5 over a fixed project namespace
    guarantees uniqueness and reproducibility without any DB round-trip.
    """
    return uuid.uuid5(_GROUP_NS, key)


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
    parent_id: uuid.UUID | None,
    force: bool = False,
) -> tuple[SectionGroup, bool]:
    """Insert or update a single SectionGroup record.

    The group_id is computed deterministically from ``parsed.key`` via
    UUID5 so no DB flush is needed to obtain it before inserting children.

    Returns:
        Tuple of (group record, was_created).
    """
    gid = group_id_from_key(parsed.key)
    positive_law_date = _compute_positive_law_date(parsed)

    result = await session.execute(
        select(SectionGroup).where(SectionGroup.group_id == gid)
    )
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
        group_id=gid,
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
    # No flush needed — group_id is pre-computed, not DB-generated.
    return group, True


async def upsert_groups_from_parse_result(
    session: AsyncSession,
    groups: list[ParsedGroup],
    force: bool = False,
) -> dict[str, SectionGroup]:
    """Upsert all groups from a parse result in a single bulk statement.

    Because group IDs are computed deterministically from the hierarchy key
    (UUID5 over ``_GROUP_NS``), all parent_ids are known before any DB write.
    The entire hierarchy is inserted in one ``INSERT … ON CONFLICT`` round-trip
    with no intermediate flushes.

    Args:
        session: Database session.
        groups: Parsed groups (parents-before-children order).
        force: If True, update name/sort_order/positive-law fields on conflict.

    Returns:
        Dict mapping group key → SectionGroup instance (transient — callers
        should only read .group_id from these objects).
    """
    if not groups:
        return {}

    rows = [
        {
            "group_id": group_id_from_key(g.key),
            "parent_id": group_id_from_key(g.parent_key) if g.parent_key else None,
            "group_type": g.group_type,
            "number": g.number,
            "name": g.name,
            "sort_order": g.sort_order,
            "is_positive_law": g.is_positive_law,
            "positive_law_date": _compute_positive_law_date(g),
            "positive_law_citation": g.positive_law_citation,
        }
        for g in groups
    ]

    stmt = pg_insert(SectionGroup).values(rows)
    if force:
        stmt = stmt.on_conflict_do_update(
            index_elements=["group_id"],
            set_={
                col: stmt.excluded[col]
                for col in (
                    "name",
                    "sort_order",
                    "is_positive_law",
                    "positive_law_date",
                    "positive_law_citation",
                )
            },
        )
    else:
        stmt = stmt.on_conflict_do_nothing()

    await session.execute(stmt)

    # Build the lookup from computed data — no DB fetch needed because all
    # group_ids are known from the UUID5 computation above.
    return {
        g.key: SectionGroup(
            group_id=row["group_id"],
            parent_id=row["parent_id"],
            group_type=g.group_type,
            number=g.number,
            name=g.name,
            sort_order=g.sort_order,
            is_positive_law=g.is_positive_law,
            positive_law_date=row["positive_law_date"],
            positive_law_citation=g.positive_law_citation,
        )
        for g, row in zip(groups, rows)
    }
