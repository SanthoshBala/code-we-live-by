"""CRUD operations for full-text search across sections and laws."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_law import PublicLaw
from app.models.us_code import USCodeSection
from app.schemas.search import (
    LawSearchResponse,
    LawSearchResult,
    SectionSearchResponse,
    SectionSearchResult,
)

_SNIPPET_MAX_LEN = 200


def _make_snippet(text: str | None, query: str) -> str | None:
    """Return a short excerpt around the first match of query in text."""
    if not text:
        return None
    lower_text = text.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)
    if pos == -1:
        return text[:_SNIPPET_MAX_LEN].rstrip() + (
            "…" if len(text) > _SNIPPET_MAX_LEN else ""
        )
    start = max(0, pos - 80)
    end = min(len(text), pos + len(query) + 120)
    snippet = (
        ("…" if start > 0 else "")
        + text[start:end].strip()
        + ("…" if end < len(text) else "")
    )
    return snippet


async def search_sections(
    session: AsyncSession,
    q: str,
    title: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> SectionSearchResponse:
    pattern = f"%{q}%"
    conditions = [
        or_(
            USCodeSection.heading.ilike(pattern),
            USCodeSection.text_content.ilike(pattern),
        )
    ]
    if title is not None:
        conditions.append(USCodeSection.title_number == title)

    count_stmt = select(func.count()).select_from(USCodeSection).where(*conditions)
    total = (await session.scalar(count_stmt)) or 0

    stmt = (
        select(
            USCodeSection.title_number,
            USCodeSection.section_number,
            USCodeSection.heading,
            USCodeSection.full_citation,
            USCodeSection.text_content,
            USCodeSection.is_repealed,
            USCodeSection.last_modified_date,
        )
        .where(*conditions)
        .order_by(USCodeSection.title_number, USCodeSection.sort_order)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    results = [
        SectionSearchResult(
            title_number=r.title_number,
            section_number=r.section_number,
            heading=r.heading,
            full_citation=r.full_citation,
            snippet=_make_snippet(r.text_content, q),
            is_repealed=r.is_repealed,
            last_modified_date=r.last_modified_date,
        )
        for r in rows
    ]
    return SectionSearchResponse(
        results=results, total=total, limit=limit, offset=offset
    )


async def search_laws(
    session: AsyncSession,
    q: str,
    congress: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> LawSearchResponse:
    pattern = f"%{q}%"
    conditions = [
        or_(
            PublicLaw.popular_name.ilike(pattern),
            PublicLaw.short_title.ilike(pattern),
            PublicLaw.law_number.ilike(pattern),
        )
    ]
    if congress is not None:
        conditions.append(PublicLaw.congress == congress)

    count_stmt = select(func.count()).select_from(PublicLaw).where(*conditions)
    total = (await session.scalar(count_stmt)) or 0

    stmt = (
        select(
            PublicLaw.congress,
            PublicLaw.law_number,
            PublicLaw.short_title,
            PublicLaw.popular_name,
            PublicLaw.enacted_date,
        )
        .where(*conditions)
        .order_by(PublicLaw.enacted_date.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    results = [
        LawSearchResult(
            congress=r.congress,
            law_number=r.law_number,
            short_title=r.short_title,
            popular_name=r.popular_name,
            enacted_date=r.enacted_date,
        )
        for r in rows
    ]
    return LawSearchResponse(results=results, total=total, limit=limit, offset=offset)
