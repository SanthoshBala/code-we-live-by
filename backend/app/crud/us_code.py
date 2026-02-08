"""CRUD operations for US Code tree navigation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.us_code import (
    USCodeChapter,
    USCodeChapterGroup,
    USCodeSection,
    USCodeSubchapter,
    USCodeTitle,
)
from app.schemas.us_code import (
    ChapterGroupTreeSchema,
    ChapterTreeSchema,
    CodeLineSchema,
    SectionNotesSchema,
    SectionSummarySchema,
    SectionViewerSchema,
    SubchapterTreeSchema,
    TitleStructureSchema,
    TitleSummarySchema,
)


def _extract_last_amendment(
    section: USCodeSection,
) -> tuple[int | None, str | None]:
    """Extract the most recent amendment year and law from normalized_notes.

    The amendments list is stored newest-first per the parser convention.
    Returns (year, "PL {congress}-{law_number}") or (None, None).
    """
    if not section.normalized_notes:
        return None, None
    amendments = section.normalized_notes.get("amendments", [])
    if not amendments:
        return None, None
    latest = amendments[0]
    year = latest.get("year")
    law = latest.get("law", {})
    congress = law.get("congress")
    law_number = law.get("law_number")
    if congress is not None and law_number is not None:
        return year, f"PL {congress}-{law_number}"
    return year, None


def _extract_note_categories(section: USCodeSection) -> list[str]:
    """Return the distinct note categories present in normalized_notes."""
    if not section.normalized_notes:
        return []
    notes = section.normalized_notes.get("notes", [])
    if not notes:
        return []
    return sorted({n["category"] for n in notes if "category" in n})


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

    stmt = select(USCodeTitle, chapter_count, section_count).order_by(
        USCodeTitle.title_number
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


def _build_chapter_tree(ch: USCodeChapter) -> ChapterTreeSchema:
    """Build a ChapterTreeSchema from a USCodeChapter ORM object."""
    direct_sections = []
    for s in sorted(ch.sections, key=lambda s: s.sort_order):
        if s.subchapter_id is not None:
            continue
        year, law = _extract_last_amendment(s)
        direct_sections.append(
            SectionSummarySchema(
                section_number=s.section_number,
                heading=s.heading,
                sort_order=s.sort_order,
                last_amendment_year=year,
                last_amendment_law=law,
                note_categories=_extract_note_categories(s),
            )
        )

    subchapters = []
    for sc in sorted(ch.subchapters, key=lambda sc: sc.sort_order):
        sc_sections = []
        for s in sorted(sc.sections, key=lambda s: s.sort_order):
            year, law = _extract_last_amendment(s)
            sc_sections.append(
                SectionSummarySchema(
                    section_number=s.section_number,
                    heading=s.heading,
                    sort_order=s.sort_order,
                    last_amendment_year=year,
                    last_amendment_law=law,
                    note_categories=_extract_note_categories(s),
                )
            )
        subchapters.append(
            SubchapterTreeSchema(
                subchapter_number=sc.subchapter_number,
                subchapter_name=sc.subchapter_name,
                sort_order=sc.sort_order,
                sections=sc_sections,
            )
        )

    return ChapterTreeSchema(
        chapter_number=ch.chapter_number,
        chapter_name=ch.chapter_name,
        sort_order=ch.sort_order,
        subchapters=subchapters,
        sections=direct_sections,
    )


def _build_group_tree(
    group: USCodeChapterGroup,
    groups_by_parent: dict[int | None, list[USCodeChapterGroup]],
    chapters_by_group: dict[int | None, list[USCodeChapter]],
) -> ChapterGroupTreeSchema:
    """Recursively build a ChapterGroupTreeSchema from ORM objects."""
    child_groups = sorted(
        groups_by_parent.get(group.group_id, []),
        key=lambda g: g.sort_order,
    )
    group_chapters = sorted(
        chapters_by_group.get(group.group_id, []),
        key=lambda c: c.sort_order,
    )

    return ChapterGroupTreeSchema(
        group_type=group.group_type,
        group_number=group.group_number,
        group_name=group.group_name,
        sort_order=group.sort_order,
        child_groups=[
            _build_group_tree(cg, groups_by_parent, chapters_by_group)
            for cg in child_groups
        ],
        chapters=[_build_chapter_tree(ch) for ch in group_chapters],
    )


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
            selectinload(USCodeTitle.chapter_groups),
        )
    )
    result = await session.execute(stmt)
    title = result.scalar_one_or_none()

    if title is None:
        return None

    # Build group tree
    groups_by_parent: dict[int | None, list[USCodeChapterGroup]] = {}
    for g in title.chapter_groups:
        groups_by_parent.setdefault(g.parent_group_id, []).append(g)

    chapters_by_group: dict[int | None, list[USCodeChapter]] = {}
    for ch in title.chapters:
        chapters_by_group.setdefault(ch.group_id, []).append(ch)

    # Top-level groups (no parent)
    top_groups = sorted(
        groups_by_parent.get(None, []),
        key=lambda g: g.sort_order,
    )
    chapter_group_trees = [
        _build_group_tree(g, groups_by_parent, chapters_by_group) for g in top_groups
    ]

    # Ungrouped chapters (group_id is None)
    ungrouped_chapters = sorted(
        chapters_by_group.get(None, []),
        key=lambda c: c.sort_order,
    )
    chapter_trees = [_build_chapter_tree(ch) for ch in ungrouped_chapters]

    return TitleStructureSchema(
        title_number=title.title_number,
        title_name=title.title_name,
        is_positive_law=title.is_positive_law,
        chapter_groups=chapter_group_trees,
        chapters=chapter_trees,
    )


async def get_section(
    session: AsyncSession, title_number: int, section_number: str
) -> SectionViewerSchema | None:
    """Return full section content for the viewer page.

    Returns None if the section is not found.
    """
    stmt = (
        select(USCodeSection)
        .join(USCodeTitle, USCodeSection.title_id == USCodeTitle.title_id)
        .where(
            USCodeTitle.title_number == title_number,
            USCodeSection.section_number == section_number,
        )
    )
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if section is None:
        return None

    notes = None
    if section.normalized_notes is not None:
        notes = SectionNotesSchema.model_validate(section.normalized_notes)

    provisions = None
    if section.normalized_provisions is not None:
        provisions = [
            CodeLineSchema.model_validate(line)
            for line in section.normalized_provisions
        ]

    return SectionViewerSchema(
        title_number=title_number,
        section_number=section.section_number,
        heading=section.heading,
        full_citation=section.full_citation,
        text_content=section.text_content,
        provisions=provisions,
        enacted_date=section.enacted_date,
        last_modified_date=section.last_modified_date,
        is_positive_law=section.is_positive_law,
        is_repealed=section.is_repealed,
        notes=notes,
    )
