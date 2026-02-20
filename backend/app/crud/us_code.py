"""CRUD operations for US Code tree navigation.

Reads section content from SectionSnapshot at HEAD revision, with optional
revision parameter for time-travel queries. Group hierarchy comes from
SectionGroup (populated by both ingestion and bootstrap).
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.models.us_code import SectionGroup
from app.schemas.us_code import (
    CodeLineSchema,
    SectionGroupTreeSchema,
    SectionNotesSchema,
    SectionSummarySchema,
    SectionViewerSchema,
    TitleStructureSchema,
    TitleSummarySchema,
)
from pipeline.olrc.snapshot_service import SectionState, SnapshotService


def _extract_last_amendment(
    notes: dict[str, Any] | None,
) -> tuple[int | None, str | None]:
    """Extract the most recent amendment year and law from normalized_notes.

    The amendments list is stored newest-first per the parser convention.
    Returns (year, "PL {congress}-{law_number}") or (None, None).
    """
    if not notes:
        return None, None
    amendments = notes.get("amendments", [])
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


def _extract_note_categories(notes: dict[str, Any] | None) -> list[str]:
    """Return the distinct note categories present in normalized_notes."""
    if not notes:
        return []
    note_list = notes.get("notes", [])
    if not note_list:
        return []
    return sorted({n["category"] for n in note_list if "category" in n})


def _build_section_summary(state: SectionState) -> SectionSummarySchema:
    """Build a SectionSummarySchema from a SectionState."""
    year, law = _extract_last_amendment(state.normalized_notes)
    return SectionSummarySchema(
        section_number=state.section_number,
        heading=state.heading or "",
        sort_order=state.sort_order,
        is_repealed=state.is_deleted,
        last_amendment_year=year,
        last_amendment_law=law,
        note_categories=_extract_note_categories(state.normalized_notes),
    )


def _build_group_tree(
    group: SectionGroup,
    sections_by_group: dict[int, list[SectionState]],
) -> SectionGroupTreeSchema:
    """Recursively build a SectionGroupTreeSchema from ORM objects."""
    child_trees = [
        _build_group_tree(child, sections_by_group)
        for child in sorted(group.children, key=lambda g: g.sort_order)
    ]
    states = sections_by_group.get(group.group_id, [])
    section_summaries = [
        _build_section_summary(s) for s in sorted(states, key=lambda s: s.sort_order)
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


async def _resolve_head(session: AsyncSession, revision_id: int | None) -> int | None:
    """Resolve an explicit revision_id or fall back to HEAD."""
    if revision_id is not None:
        return revision_id
    svc = SnapshotService(session)
    return await svc.get_head_revision_id()


async def get_all_titles(
    session: AsyncSession, revision_id: int | None = None
) -> list[TitleSummarySchema]:
    """Return all titles with child group and section counts."""
    stmt = (
        select(SectionGroup)
        .where(SectionGroup.group_type == "title")
        .order_by(SectionGroup.number)
    )
    result = await session.execute(stmt)
    title_groups = result.scalars().all()

    # Resolve HEAD revision and load all sections once
    head_id = await _resolve_head(session, revision_id)

    sections_by_title: dict[int, int] = {}
    if head_id is not None:
        svc = SnapshotService(session)
        all_states = await svc.get_all_sections_at_revision(head_id)
        for s in all_states:
            sections_by_title[s.title_number] = (
                sections_by_title.get(s.title_number, 0) + 1
            )

    # Count child groups per title in one query
    child_counts_stmt = (
        select(SectionGroup.parent_id, func.count(SectionGroup.group_id))
        .where(SectionGroup.parent_id.in_([tg.group_id for tg in title_groups]))
        .group_by(SectionGroup.parent_id)
    )
    child_counts_result = await session.execute(child_counts_stmt)
    child_counts: dict[int | None, int] = {
        row[0]: row[1] for row in child_counts_result.all()
    }

    titles: list[TitleSummarySchema] = []
    for tg in title_groups:
        title_number = int(tg.number)
        titles.append(
            TitleSummarySchema(
                title_number=title_number,
                title_name=tg.name,
                is_positive_law=tg.is_positive_law,
                positive_law_date=tg.positive_law_date,
                chapter_count=child_counts.get(tg.group_id, 0),
                section_count=sections_by_title.get(title_number, 0),
            )
        )
    return titles


async def get_title_structure(
    session: AsyncSession, title_number: int, revision_id: int | None = None
) -> TitleStructureSchema | None:
    """Return the full group/section tree for a title.

    Sections come from SectionSnapshot at HEAD (or specified revision).
    Returns None if the title is not found.
    """
    # Load the title group
    stmt = select(SectionGroup).where(
        SectionGroup.group_type == "title",
        SectionGroup.number == str(title_number),
    )
    result = await session.execute(stmt)
    title_group = result.scalar_one_or_none()

    if title_group is None:
        return None

    # Load all groups that descend from this title using a recursive CTE
    base = (
        select(SectionGroup.group_id)
        .where(SectionGroup.parent_id == title_group.group_id)
        .cte(name="descendants", recursive=True)
    )
    descendants = base.union_all(
        select(SectionGroup.group_id).where(SectionGroup.parent_id == base.c.group_id)
    )

    all_ids = [title_group.group_id] + [
        row[0] for row in (await session.execute(select(descendants.c.group_id))).all()
    ]

    # Load all groups at once
    groups_stmt = select(SectionGroup).where(SectionGroup.group_id.in_(all_ids))
    groups_result = await session.execute(groups_stmt)
    all_groups = {g.group_id: g for g in groups_result.scalars().unique().all()}

    # Build parent->children mapping
    children_by_parent: dict[int, list[SectionGroup]] = {}
    for g in all_groups.values():
        if g.parent_id is not None and g.parent_id in all_groups:
            children_by_parent.setdefault(g.parent_id, []).append(g)

    for g in all_groups.values():
        children = children_by_parent.get(g.group_id, [])
        attributes.set_committed_value(g, "children", children)

    # Load sections from snapshots at HEAD
    head_id = await _resolve_head(session, revision_id)
    sections_by_group: dict[int, list[SectionState]] = {}

    if head_id is not None:
        svc = SnapshotService(session)
        all_states = await svc.get_all_sections_at_revision(head_id)
        for state in all_states:
            if state.title_number == title_number and state.group_id is not None:
                sections_by_group.setdefault(state.group_id, []).append(state)

    # Build the tree
    title_obj = all_groups[title_group.group_id]
    child_trees = [
        _build_group_tree(child, sections_by_group)
        for child in sorted(title_obj.children, key=lambda g: g.sort_order)
    ]

    # Sections directly under the title group
    title_sections = sections_by_group.get(title_group.group_id, [])
    section_summaries = [
        _build_section_summary(s)
        for s in sorted(title_sections, key=lambda s: s.sort_order)
    ]

    return TitleStructureSchema(
        title_number=int(title_obj.number),
        title_name=title_obj.name,
        is_positive_law=title_obj.is_positive_law,
        children=child_trees,
        sections=section_summaries,
    )


async def get_section(
    session: AsyncSession,
    title_number: int,
    section_number: str,
    revision_id: int | None = None,
) -> SectionViewerSchema | None:
    """Return full section content for the viewer page.

    Reads from SectionSnapshot at HEAD (or specified revision).
    Returns None if the section is not found.
    """
    head_id = await _resolve_head(session, revision_id)
    if head_id is None:
        return None

    svc = SnapshotService(session)
    state = await svc.get_section_at_revision(title_number, section_number, head_id)

    if state is None:
        return None

    notes = None
    if state.normalized_notes is not None:
        notes = SectionNotesSchema.model_validate(state.normalized_notes)

    provisions = None
    if state.normalized_provisions is not None:
        provisions = [
            CodeLineSchema.model_validate(line) for line in state.normalized_provisions
        ]

    # Derive is_positive_law and dates from notes when available
    enacted_date = None
    last_modified_date = None
    is_positive_law = False

    if state.normalized_notes:
        # Extract enacted_date from first citation
        citations = state.normalized_notes.get("citations", [])
        if citations:
            first = citations[0]
            law_data = first.get("law") or first.get("act")
            if law_data and law_data.get("date"):
                from pipeline.olrc.group_service import _parse_citation_date

                enacted_date = _parse_citation_date(law_data["date"])

        # Extract last_modified_date from amendments
        amendments = state.normalized_notes.get("amendments", [])
        if amendments:
            from datetime import date

            max_year = max(a["year"] for a in amendments if "year" in a)
            last_modified_date = date(max_year, 1, 1)

    return SectionViewerSchema(
        title_number=title_number,
        section_number=state.section_number,
        heading=state.heading or "",
        full_citation=state.full_citation or f"{title_number} USC {section_number}",
        text_content=state.text_content,
        provisions=provisions,
        enacted_date=enacted_date,
        last_modified_date=last_modified_date,
        is_positive_law=is_positive_law,
        is_repealed=state.is_deleted,
        notes=notes,
    )
