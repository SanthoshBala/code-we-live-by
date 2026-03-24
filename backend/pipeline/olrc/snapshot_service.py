"""Snapshot query helpers for the chronological pipeline.

Core read primitives for retrieving section state at any revision.
These are used by the diff engine, API, and frontend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
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
    normalized_provisions: dict[str, Any] | None
    notes: str | None
    normalized_notes: dict[str, Any] | None
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
        *,
        chain: list[int] | None = None,
    ) -> SectionState | None:
        """Get a section's state at a specific revision.

        Uses the revision chain CTE + DISTINCT ON to find the most recent
        snapshot in a single query instead of walking the parent chain
        sequentially.

        Args:
            title_number: US Code title number.
            section_number: Section number (e.g., "106", "80a-3a").
            revision_id: The revision to query at.
            chain: Pre-built revision chain (newest-first). If not provided,
                built internally via ``_get_revision_chain()``.

        Returns:
            SectionState or None if the section doesn't exist at this revision.
        """
        if chain is None:
            chain = await self._get_revision_chain(revision_id)
        if not chain:
            return None

        result = await self.session.execute(
            text("""
                SELECT DISTINCT ON (title_number, section_number)
                    snapshot_id, revision_id, title_number, section_number,
                    heading, text_content, text_hash,
                    normalized_provisions, notes, normalized_notes,
                    notes_hash, full_citation, is_deleted, group_id, sort_order
                FROM section_snapshot
                WHERE revision_id = ANY(:chain)
                  AND title_number = :title
                  AND section_number = :section
                ORDER BY title_number, section_number,
                    array_position(:chain, revision_id)
            """),
            {"chain": chain, "title": title_number, "section": section_number},
        )
        row = result.one_or_none()
        if row is None or row.is_deleted:
            return None
        return SectionState(
            title_number=row.title_number,
            section_number=row.section_number,
            heading=row.heading,
            text_content=row.text_content,
            text_hash=row.text_hash,
            normalized_provisions=row.normalized_provisions,
            notes=row.notes,
            normalized_notes=row.normalized_notes,
            notes_hash=row.notes_hash,
            full_citation=row.full_citation,
            snapshot_id=row.snapshot_id,
            revision_id=row.revision_id,
            is_deleted=row.is_deleted,
            group_id=row.group_id,
            sort_order=row.sort_order,
        )

    async def get_all_sections_at_revision(
        self,
        revision_id: int,
    ) -> list[SectionState]:
        """Materialize the full section state at a revision.

        Uses DISTINCT ON + array_position to find the latest snapshot per
        section across the revision chain in a single query.

        Args:
            revision_id: The revision to materialize.

        Returns:
            List of SectionState for all live sections at this revision.
        """
        chain = await self._get_revision_chain(revision_id)
        if not chain:
            return []

        result = await self.session.execute(
            text("""
                SELECT DISTINCT ON (title_number, section_number)
                    snapshot_id, revision_id, title_number, section_number,
                    heading, text_content, text_hash,
                    normalized_provisions, notes, normalized_notes,
                    notes_hash, full_citation, is_deleted, group_id, sort_order
                FROM section_snapshot
                WHERE revision_id = ANY(:chain)
                ORDER BY title_number, section_number,
                    array_position(:chain, revision_id)
            """),
            {"chain": chain},
        )

        states = []
        for row in result:
            if row.is_deleted:
                continue
            states.append(
                SectionState(
                    title_number=row.title_number,
                    section_number=row.section_number,
                    heading=row.heading,
                    text_content=row.text_content,
                    text_hash=row.text_hash,
                    normalized_provisions=row.normalized_provisions,
                    notes=row.notes,
                    normalized_notes=row.normalized_notes,
                    notes_hash=row.notes_hash,
                    full_citation=row.full_citation,
                    snapshot_id=row.snapshot_id,
                    revision_id=row.revision_id,
                    is_deleted=row.is_deleted,
                    group_id=row.group_id,
                    sort_order=row.sort_order,
                )
            )

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

    async def get_sections_at_revision(
        self,
        keys: list[tuple[int, str]],
        revision_id: int,
        *,
        chain: list[int] | None = None,
    ) -> dict[tuple[int, str], SectionState]:
        """Batch-fetch multiple sections' state at a specific revision.

        Uses a single DISTINCT ON query with an IN clause to look up all
        requested (title_number, section_number) pairs at once.

        Args:
            keys: List of (title_number, section_number) pairs to fetch.
            revision_id: The revision to query at.
            chain: Pre-built revision chain (newest-first). If not provided,
                built internally via ``_get_revision_chain()``.

        Returns:
            Dict mapping (title_number, section_number) to SectionState.
            Deleted or missing sections are omitted.
        """
        if not keys:
            return {}
        if chain is None:
            chain = await self._get_revision_chain(revision_id)
        if not chain:
            return {}

        # Use parallel arrays for parameterized filtering. The arrays
        # are zipped on index: titles[i] pairs with sections[i].
        titles = [k[0] for k in keys]
        sections = [k[1] for k in keys]

        result = await self.session.execute(
            text("""
                SELECT DISTINCT ON (ss.title_number, ss.section_number)
                    ss.snapshot_id, ss.revision_id, ss.title_number,
                    ss.section_number, ss.heading, ss.text_content,
                    ss.text_hash, ss.normalized_provisions, ss.notes,
                    ss.normalized_notes, ss.notes_hash, ss.full_citation,
                    ss.is_deleted, ss.group_id, ss.sort_order
                FROM section_snapshot ss
                JOIN unnest(:titles::int[], :sections::text[])
                     AS keys(title, section)
                  ON ss.title_number = keys.title
                 AND ss.section_number = keys.section
                WHERE ss.revision_id = ANY(:chain)
                ORDER BY ss.title_number, ss.section_number,
                    array_position(:chain, ss.revision_id)
            """),
            {"chain": chain, "titles": titles, "sections": sections},
        )

        states: dict[tuple[int, str], SectionState] = {}
        for row in result:
            if row.is_deleted:
                continue
            state = SectionState(
                title_number=row.title_number,
                section_number=row.section_number,
                heading=row.heading,
                text_content=row.text_content,
                text_hash=row.text_hash,
                normalized_provisions=row.normalized_provisions,
                notes=row.notes,
                normalized_notes=row.normalized_notes,
                notes_hash=row.notes_hash,
                full_citation=row.full_citation,
                snapshot_id=row.snapshot_id,
                revision_id=row.revision_id,
                is_deleted=row.is_deleted,
                group_id=row.group_id,
                sort_order=row.sort_order,
            )
            states[(row.title_number, row.section_number)] = state
        return states

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

        Uses a recursive CTE to fetch the entire chain in a single query
        instead of N sequential round-trips to the database.

        Returns list ordered from newest to oldest (target first).
        """
        result = await self.session.execute(
            text("""
                WITH RECURSIVE chain AS (
                    SELECT revision_id, parent_revision_id, 1 AS depth
                    FROM code_revision
                    WHERE revision_id = :start_id
                    UNION ALL
                    SELECT cr.revision_id, cr.parent_revision_id, c.depth + 1
                    FROM code_revision cr
                    JOIN chain c ON cr.revision_id = c.parent_revision_id
                )
                SELECT revision_id FROM chain ORDER BY depth
            """),
            {"start_id": revision_id},
        )
        return [row[0] for row in result]

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
