"""CRUD operations for US Code tree navigation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes, selectinload

from app.models.us_code import (
    SectionGroup,
    USCodeSection,
)
from app.schemas.us_code import (
    CodeLineSchema,
    SectionGroupTreeSchema,
    SectionNotesSchema,
    SectionSummarySchema,
    SectionViewerSchema,
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


def _build_section_summary(section: USCodeSection) -> SectionSummarySchema:
    """Build a SectionSummarySchema from a USCodeSection ORM object."""
    year, law = _extract_last_amendment(section)
    return SectionSummarySchema(
        section_number=section.section_number,
        heading=section.heading,
        sort_order=section.sort_order,
        last_amendment_year=year,
        last_amendment_law=law,
        note_categories=_extract_note_categories(section),
    )


def _build_group_tree(group: SectionGroup) -> SectionGroupTreeSchema:
    """Recursively build a SectionGroupTreeSchema from ORM objects."""
    child_trees = [
        _build_group_tree(child)
        for child in sorted(group.children, key=lambda g: g.sort_order)
    ]
    section_summaries = [
        _build_section_summary(s)
        for s in sorted(group.sections, key=lambda s: s.sort_order)
    ]
    return SectionGroupTreeSchema(
        group_type=group.group_type,
        number=group.number,
        name=group.name,
        sort_order=group.sort_order,
        is_positive_law=group.is_positive_law,
        children=child_trees,
        sections=section_summaries,
    )


async def get_all_titles(session: AsyncSession) -> list[TitleSummarySchema]:
    """Return all titles with child group and section counts."""
    stmt = (
        select(SectionGroup)
        .where(SectionGroup.group_type == "title")
        .order_by(SectionGroup.number)
    )
    result = await session.execute(stmt)
    title_groups = result.scalars().all()

    titles: list[TitleSummarySchema] = []
    for tg in title_groups:
        title_number = int(tg.number)

        # Count sections for this title
        sec_count_result = await session.execute(
            select(func.count(USCodeSection.section_id)).where(
                USCodeSection.title_number == title_number
            )
        )
        sec_count = sec_count_result.scalar() or 0

        # Count direct child groups (chapters or top-level groups)
        ch_count_result = await session.execute(
            select(func.count(SectionGroup.group_id)).where(
                SectionGroup.parent_id == tg.group_id
            )
        )
        ch_count = ch_count_result.scalar() or 0

        titles.append(
            TitleSummarySchema(
                title_number=title_number,
                title_name=tg.name,
                is_positive_law=tg.is_positive_law,
                positive_law_date=tg.positive_law_date,
                chapter_count=ch_count,
                section_count=sec_count,
            )
        )
    return titles


async def get_title_structure(
    session: AsyncSession, title_number: int
) -> TitleStructureSchema | None:
    """Return the full group/section tree for a title.

    Returns None if the title is not found.
    """
    # Load the title group with all descendants eagerly loaded.
    # We use a CTE approach: load the title, then load ALL SectionGroup
    # records for this title and build the tree in Python.
    stmt = select(SectionGroup).where(
        SectionGroup.group_type == "title",
        SectionGroup.number == str(title_number),
    )
    result = await session.execute(stmt)
    title_group = result.scalar_one_or_none()

    if title_group is None:
        return None

    # Load all groups that descend from this title using a recursive CTE
    # (sqlalchemy CTE used below for recursive loading)

    # Base case: direct children of the title
    base = (
        select(SectionGroup.group_id)
        .where(SectionGroup.parent_id == title_group.group_id)
        .cte(name="descendants", recursive=True)
    )
    # Recursive case: children of children
    descendants = base.union_all(
        select(SectionGroup.group_id).where(SectionGroup.parent_id == base.c.group_id)
    )

    # Load all descendant groups with their sections
    all_ids = [title_group.group_id] + [
        row[0] for row in (await session.execute(select(descendants.c.group_id))).all()
    ]

    # Load all groups at once with their sections
    groups_stmt = (
        select(SectionGroup)
        .where(SectionGroup.group_id.in_(all_ids))
        .options(selectinload(SectionGroup.sections))
    )
    groups_result = await session.execute(groups_stmt)
    all_groups = {g.group_id: g for g in groups_result.scalars().unique().all()}

    # Build parent->children mapping
    children_by_parent: dict[int, list[SectionGroup]] = {}
    for g in all_groups.values():
        if g.parent_id is not None and g.parent_id in all_groups:
            children_by_parent.setdefault(g.parent_id, []).append(g)

    # Attach children lists to each group for _build_group_tree
    for g in all_groups.values():
        # Use set_committed_value to bypass lazy-load trigger on assignment
        children = children_by_parent.get(g.group_id, [])
        attributes.set_committed_value(g, "children", children)

    # Build the tree from title's direct children
    title_obj = all_groups[title_group.group_id]
    child_trees = [
        _build_group_tree(child)
        for child in sorted(title_obj.children, key=lambda g: g.sort_order)
    ]
    section_summaries = [
        _build_section_summary(s)
        for s in sorted(title_obj.sections, key=lambda s: s.sort_order)
    ]

    return TitleStructureSchema(
        title_number=int(title_obj.number),
        title_name=title_obj.name,
        is_positive_law=title_obj.is_positive_law,
        children=child_trees,
        sections=section_summaries,
    )


async def get_section(
    session: AsyncSession, title_number: int, section_number: str
) -> SectionViewerSchema | None:
    """Return full section content for the viewer page.

    Returns None if the section is not found.
    """
    stmt = select(USCodeSection).where(
        USCodeSection.title_number == title_number,
        USCodeSection.section_number == section_number,
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
