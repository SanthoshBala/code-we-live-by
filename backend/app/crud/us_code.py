"""CRUD operations for US Code tree navigation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.us_code import USCodeChapter, USCodeSection, USCodeSubchapter, USCodeTitle
from app.schemas.us_code import (
    ChapterTreeSchema,
    SectionSummarySchema,
    SubchapterTreeSchema,
    TitleStructureSchema,
    TitleSummarySchema,
)


async def get_all_titles(session: AsyncSession) -> list[TitleSummarySchema]:
    """Return all titles with chapter and section counts."""
    chapter_count = (
        select(func.count(USCodeChapter.chapter_id))
        .where(USCodeChapter.title_id == USCodeTitle.title_id)
        .correlate(USCodeTitle)
        .scalar_subquery()
        .label("chapter_count")
    )
    section_count = (
        select(func.count(USCodeSection.section_id))
        .where(USCodeSection.title_id == USCodeTitle.title_id)
        .correlate(USCodeTitle)
        .scalar_subquery()
        .label("section_count")
    )

    stmt = (
        select(USCodeTitle, chapter_count, section_count)
        .order_by(USCodeTitle.title_number)
    )
    result = await session.execute(stmt)

    titles: list[TitleSummarySchema] = []
    for row in result.all():
        title = row[0]
        titles.append(
            TitleSummarySchema(
                title_number=title.title_number,
                title_name=title.title_name,
                is_positive_law=title.is_positive_law,
                positive_law_date=title.positive_law_date,
                chapter_count=row[1],
                section_count=row[2],
            )
        )
    return titles


async def get_title_structure(
    session: AsyncSession, title_number: int
) -> TitleStructureSchema | None:
    """Return the chapter/subchapter/section tree for a title.

    Returns None if the title is not found.
    """
    stmt = (
        select(USCodeTitle)
        .where(USCodeTitle.title_number == title_number)
        .options(
            selectinload(USCodeTitle.chapters)
            .selectinload(USCodeChapter.subchapters)
            .selectinload(USCodeSubchapter.sections),
            selectinload(USCodeTitle.chapters).selectinload(USCodeChapter.sections),
        )
    )
    result = await session.execute(stmt)
    title = result.scalar_one_or_none()

    if title is None:
        return None

    chapters: list[ChapterTreeSchema] = []
    for ch in sorted(title.chapters, key=lambda c: c.sort_order):
        # Sections directly under this chapter (no subchapter)
        direct_sections = [
            SectionSummarySchema(
                section_number=s.section_number,
                heading=s.heading,
                sort_order=s.sort_order,
            )
            for s in sorted(ch.sections, key=lambda s: s.sort_order)
            if s.subchapter_id is None
        ]

        subchapters = [
            SubchapterTreeSchema(
                subchapter_number=sc.subchapter_number,
                subchapter_name=sc.subchapter_name,
                sort_order=sc.sort_order,
                sections=[
                    SectionSummarySchema(
                        section_number=s.section_number,
                        heading=s.heading,
                        sort_order=s.sort_order,
                    )
                    for s in sorted(sc.sections, key=lambda s: s.sort_order)
                ],
            )
            for sc in sorted(ch.subchapters, key=lambda sc: sc.sort_order)
        ]

        chapters.append(
            ChapterTreeSchema(
                chapter_number=ch.chapter_number,
                chapter_name=ch.chapter_name,
                sort_order=ch.sort_order,
                subchapters=subchapters,
                sections=direct_sections,
            )
        )

    return TitleStructureSchema(
        title_number=title.title_number,
        title_name=title.title_name,
        is_positive_law=title.is_positive_law,
        chapters=chapters,
    )
