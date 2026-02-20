"""CRUD operations for code revisions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RevisionStatus
from app.models.revision import CodeRevision
from app.schemas.revision import HeadRevisionSchema


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
