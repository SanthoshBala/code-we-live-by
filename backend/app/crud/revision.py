"""CRUD operations for code revisions."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RevisionStatus
from app.models.revision import CodeRevision
from app.schemas.revision import HeadRevisionSchema
from pipeline.olrc.snapshot_service import SnapshotService


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


async def get_latest_revision_for_title(
    session: AsyncSession, title_number: int
) -> HeadRevisionSchema | None:
    """Return the most recent revision that touched any section in a title.

    Finds the latest snapshot per section (DISTINCT ON) across the revision
    chain, then picks the revision with the highest sequence_number.
    """
    svc = SnapshotService(session)
    head_id = await svc.get_head_revision_id()
    if head_id is None:
        return None

    chain = await svc._get_revision_chain(head_id)
    if not chain:
        return None

    # Find the revision_id with the highest sequence_number among the
    # latest snapshots for each section in this title.
    result = await session.execute(
        text("""
            SELECT cr.revision_id, cr.revision_type, cr.effective_date,
                   cr.summary, cr.sequence_number
            FROM code_revision cr
            WHERE cr.revision_id = (
                SELECT latest.revision_id
                FROM (
                    SELECT DISTINCT ON (section_number)
                        revision_id
                    FROM section_snapshot
                    WHERE revision_id = ANY(:chain)
                      AND title_number = :title
                    ORDER BY section_number,
                        array_position(:chain, revision_id)
                ) latest
                JOIN code_revision r ON r.revision_id = latest.revision_id
                ORDER BY r.sequence_number DESC
                LIMIT 1
            )
        """),
        {"chain": chain, "title": title_number},
    )
    row = result.one_or_none()
    if row is None:
        return None

    return HeadRevisionSchema(
        revision_id=row.revision_id,
        revision_type=row.revision_type,
        effective_date=row.effective_date,
        summary=row.summary,
        sequence_number=row.sequence_number,
    )
