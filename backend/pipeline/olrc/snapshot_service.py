"""Snapshot query helpers for the chronological pipeline.

Core read primitives for retrieving section state at any revision.
These are used by the diff engine, API, and frontend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.revision import CodeRevision
from app.models.snapshot import SectionSnapshot

logger = logging.getLogger(__name__)


@dataclass
class SectionState:
    """The state of a section at a particular revision."""

    title_number: int
    section_number: str
    heading: str | None
    text_content: str | None
    text_hash: str | None
    normalized_provisions: dict | None
    notes: str | None
    normalized_notes: dict | None
    notes_hash: str | None
    full_citation: str | None
    snapshot_id: int
    revision_id: int
    is_deleted: bool
    group_id: int | None = None
    sort_order: int = 0


class SnapshotService:
    """Service for querying section snapshots across revisions.

    Implements parent-chain traversal: only changed sections get new
    snapshots, so finding a section's state at a revision may require
    walking back through parent revisions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_head_revision_id(self) -> int | None:
        """Return the latest INGESTED revision's ID.

        Returns None if no revisions have been ingested yet.
        """
        from app.models.enums import RevisionStatus

        stmt = (
            select(CodeRevision.revision_id)
            .where(CodeRevision.status == RevisionStatus.INGESTED.value)
            .order_by(CodeRevision.sequence_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_section_at_revision(
        self,
        title_number: int,
        section_number: str,
        revision_id: int,
    ) -> SectionState | None:
        """Get a section's state at a specific revision.

        Walks the parent chain from the given revision backwards to find
        the most recent snapshot for the requested section.

        Args:
            title_number: US Code title number.
            section_number: Section number (e.g., "106", "80a-3a").
            revision_id: The revision to query at.

        Returns:
            SectionState or None if the section doesn't exist at this revision.
        """
        current_rev_id: int | None = revision_id

        while current_rev_id is not None:
            # Look for a snapshot at this revision
            stmt = select(SectionSnapshot).where(
                SectionSnapshot.revision_id == current_rev_id,
                SectionSnapshot.title_number == title_number,
                SectionSnapshot.section_number == section_number,
            )
            result = await self.session.execute(stmt)
            snapshot = result.scalar_one_or_none()

            if snapshot is not None:
                if snapshot.is_deleted:
                    return None
                return self._snapshot_to_state(snapshot)

            # Walk to parent revision
            rev_stmt = select(CodeRevision.parent_revision_id).where(
                CodeRevision.revision_id == current_rev_id
            )
            rev_result = await self.session.execute(rev_stmt)
            parent_id = rev_result.scalar_one_or_none()
            current_rev_id = parent_id

        return None

    async def get_all_sections_at_revision(
        self,
        revision_id: int,
    ) -> list[SectionState]:
        """Materialize the full section state at a revision.

        Accumulates snapshots from the initial commit through the target
        revision, applying the most recent snapshot for each section.

        Args:
            revision_id: The revision to materialize.

        Returns:
            List of SectionState for all live sections at this revision.
        """
        # Build the revision chain from target back to initial
        revision_chain = await self._get_revision_chain(revision_id)

        if not revision_chain:
            return []

        # Accumulate snapshots: most recent wins
        # key: (title_number, section_number) -> SectionSnapshot
        section_map: dict[tuple[int, str], SectionSnapshot] = {}

        # Process from oldest to newest so latest snapshots override
        for rev_id in reversed(revision_chain):
            stmt = select(SectionSnapshot).where(SectionSnapshot.revision_id == rev_id)
            result = await self.session.execute(stmt)
            snapshots = result.scalars().all()

            for snap in snapshots:
                key = (snap.title_number, snap.section_number)
                section_map[key] = snap

        # Filter out deleted sections and convert to SectionState
        states = []
        for snap in section_map.values():
            if not snap.is_deleted:
                states.append(self._snapshot_to_state(snap))

        # Sort by title and section for consistent ordering
        states.sort(key=lambda s: (s.title_number, s.section_number))
        return states

    async def get_section_history(
        self,
        title_number: int,
        section_number: str,
    ) -> list[SectionState]:
        """Return all snapshots of a section across revisions, chronologically.

        Args:
            title_number: US Code title number.
            section_number: Section number.

        Returns:
            List of SectionState ordered by revision sequence_number.
        """
        stmt = (
            select(SectionSnapshot)
            .join(
                CodeRevision,
                SectionSnapshot.revision_id == CodeRevision.revision_id,
            )
            .where(
                SectionSnapshot.title_number == title_number,
                SectionSnapshot.section_number == section_number,
            )
            .order_by(CodeRevision.sequence_number)
        )
        result = await self.session.execute(stmt)
        snapshots = result.scalars().all()

        return [self._snapshot_to_state(snap) for snap in snapshots]

    async def get_changed_sections_at_revision(
        self,
        revision_id: int,
    ) -> list[SectionState]:
        """Get only the sections that changed at a specific revision.

        Args:
            revision_id: The revision to query.

        Returns:
            List of SectionState for sections with snapshots at this revision.
        """
        stmt = select(SectionSnapshot).where(SectionSnapshot.revision_id == revision_id)
        result = await self.session.execute(stmt)
        snapshots = result.scalars().all()

        return [self._snapshot_to_state(snap) for snap in snapshots]

    async def _get_revision_chain(self, revision_id: int) -> list[int]:
        """Build the chain of revision IDs from target back to initial.

        Returns list ordered from newest to oldest (target first).
        """
        chain: list[int] = []
        current_id: int | None = revision_id

        while current_id is not None:
            chain.append(current_id)
            stmt = select(CodeRevision.parent_revision_id).where(
                CodeRevision.revision_id == current_id
            )
            result = await self.session.execute(stmt)
            current_id = result.scalar_one_or_none()

        return chain

    @staticmethod
    def _snapshot_to_state(snapshot: SectionSnapshot) -> SectionState:
        """Convert a SectionSnapshot ORM object to a SectionState dataclass."""
        return SectionState(
            title_number=snapshot.title_number,
            section_number=snapshot.section_number,
            heading=snapshot.heading,
            text_content=snapshot.text_content,
            text_hash=snapshot.text_hash,
            normalized_provisions=snapshot.normalized_provisions,
            notes=snapshot.notes,
            normalized_notes=snapshot.normalized_notes,
            notes_hash=snapshot.notes_hash,
            full_citation=snapshot.full_citation,
            snapshot_id=snapshot.snapshot_id,
            revision_id=snapshot.revision_id,
            is_deleted=snapshot.is_deleted,
            group_id=snapshot.group_id,
            sort_order=snapshot.sort_order,
        )
