"""CRUD operations for code revisions."""

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RevisionStatus
from app.models.revision import CodeRevision
from app.schemas.revision import HeadRevisionSchema
from pipeline.olrc.snapshot_service import SnapshotService


async def get_revision_by_id(
    session: AsyncSession, revision_id: int
) -> HeadRevisionSchema | None:
    """Return a specific revision by ID."""
    stmt = select(CodeRevision).where(CodeRevision.revision_id == revision_id)
    result = await session.execute(stmt)
    revision = result.scalar_one_or_none()

    if revision is None:
        return None

    return HeadRevisionSchema.model_validate(revision)


async def get_head_revision(session: AsyncSession) -> HeadRevisionSchema | None:
    """Return the latest INGESTED revision with full metadata.

    Uses the same logic as SnapshotService.get_head_revision_id() but
    loads the full row to populate the schema.
    """
    stmt = (
        select(CodeRevision)
        .where(CodeRevision.status == RevisionStatus.INGESTED.value)
        .order_by(CodeRevision.sequence_number.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    revision = result.scalar_one_or_none()

    if revision is None:
        return None

    return HeadRevisionSchema.model_validate(revision)


async def _get_chain(session: AsyncSession) -> list[int] | None:
    """Return the HEAD revision chain (newest-first) or None."""
    svc = SnapshotService(session)
    head_id = await svc.get_head_revision_id()
    if head_id is None:
        return None
    chain = await svc._get_revision_chain(head_id)
    return chain if chain else None


def _row_to_schema(row: Any) -> HeadRevisionSchema:
    return HeadRevisionSchema(
        revision_id=row.revision_id,
        revision_type=row.revision_type,
        effective_date=row.effective_date,
        summary=row.summary,
        sequence_number=row.sequence_number,
    )


# SQL fragment: for each section, compare consecutive snapshots via LEAD()
# to find the most recent revision where content actually changed (hashes
# differ from the predecessor). LEAD() looks at the next row in chain
# order (= the chronologically older revision).
_LAST_CHANGED_CTE = """
    WITH windowed AS (
        SELECT revision_id, title_number, section_number,
               text_hash, notes_hash,
               LEAD(text_hash) OVER (
                   PARTITION BY title_number, section_number
                   ORDER BY array_position(:chain, revision_id)
               ) AS prev_text_hash,
               LEAD(notes_hash) OVER (
                   PARTITION BY title_number, section_number
                   ORDER BY array_position(:chain, revision_id)
               ) AS prev_notes_hash
        FROM section_snapshot
        WHERE revision_id = ANY(:chain)
          {filter}
    ),
    changed AS (
        SELECT revision_id, title_number, section_number
        FROM windowed
        WHERE prev_text_hash IS NULL
           OR text_hash IS DISTINCT FROM prev_text_hash
           OR notes_hash IS DISTINCT FROM prev_notes_hash
    ),
    per_section AS (
        SELECT DISTINCT ON (title_number, section_number)
            revision_id
        FROM changed
        ORDER BY title_number, section_number,
            array_position(:chain, revision_id)
    )
"""


async def get_latest_revision_for_title(
    session: AsyncSession, title_number: int
) -> HeadRevisionSchema | None:
    """Return the most recent revision that actually changed any section in a title.

    Compares content hashes between consecutive snapshots to find real
    changes (not just re-snapshots at a new release point).
    """
    chain = await _get_chain(session)
    if not chain:
        return None

    sql = (
        _LAST_CHANGED_CTE.format(filter="AND title_number = :title")
        + """
        SELECT cr.revision_id, cr.revision_type, cr.effective_date,
               cr.summary, cr.sequence_number
        FROM per_section ps
        JOIN code_revision cr ON cr.revision_id = ps.revision_id
        ORDER BY cr.sequence_number DESC
        LIMIT 1
    """
    )
    result = await session.execute(text(sql), {"chain": chain, "title": title_number})
    row = result.one_or_none()
    if row is None:
        return None
    return _row_to_schema(row)


async def get_last_changed_revision_for_section(
    session: AsyncSession, title_number: int, section_number: str
) -> HeadRevisionSchema | None:
    """Return the most recent revision that actually changed a specific section.

    Compares content hashes between consecutive snapshots so that a
    release point that re-snapshots unchanged content is skipped.
    """
    chain = await _get_chain(session)
    if not chain:
        return None

    sql = (
        _LAST_CHANGED_CTE.format(
            filter="AND title_number = :title AND section_number = :section"
        )
        + """
        SELECT cr.revision_id, cr.revision_type, cr.effective_date,
               cr.summary, cr.sequence_number
        FROM per_section ps
        JOIN code_revision cr ON cr.revision_id = ps.revision_id
        ORDER BY cr.sequence_number DESC
        LIMIT 1
    """
    )
    result = await session.execute(
        text(sql),
        {"chain": chain, "title": title_number, "section": section_number},
    )
    row = result.one_or_none()
    if row is None:
        return None
    return _row_to_schema(row)
