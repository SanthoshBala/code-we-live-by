"""RP-to-RP diff engine for the chronological pipeline.

Compares two revisions by materializing their section state and classifying
every section as ADDED, MODIFIED, DELETED, or UNCHANGED based on text_hash
and notes_hash comparisons.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.olrc.snapshot_service import SectionState, SnapshotService

logger = logging.getLogger(__name__)


@dataclass
class SectionDiff:
    """One section's change between two revisions."""

    title_number: int
    section_number: str
    change_type: str  # "added", "modified", "deleted"
    text_changed: bool
    notes_changed: bool
    before_state: SectionState | None  # None for added
    after_state: SectionState | None  # None for deleted


@dataclass
class RevisionDiffResult:
    """Full diff between two revisions."""

    before_revision_id: int
    after_revision_id: int
    sections_added: int
    sections_modified: int
    sections_deleted: int
    sections_unchanged: int
    diffs: list[SectionDiff]  # Only changed sections
    elapsed_seconds: float


class RevisionDiffEngine:
    """Compares two revisions and produces a section-level diff."""

    def __init__(self, session: AsyncSession) -> None:
        self.snapshot_service = SnapshotService(session)

    async def diff(
        self, before_revision_id: int, after_revision_id: int
    ) -> RevisionDiffResult:
        """Diff two revisions by comparing section hashes.

        Args:
            before_revision_id: The earlier revision ID.
            after_revision_id: The later revision ID.

        Returns:
            RevisionDiffResult with counts and changed-section diffs.
        """
        start = time.monotonic()

        before_states = await self.snapshot_service.get_all_sections_at_revision(
            before_revision_id
        )
        after_states = await self.snapshot_service.get_all_sections_at_revision(
            after_revision_id
        )

        result = diff_section_maps(
            before_states, after_states, before_revision_id, after_revision_id
        )

        elapsed = time.monotonic() - start
        result.elapsed_seconds = elapsed

        logger.info(
            f"Diff {before_revision_id} -> {after_revision_id}: "
            f"+{result.sections_added} ~{result.sections_modified} "
            f"-{result.sections_deleted} ={result.sections_unchanged} "
            f"({elapsed:.1f}s)"
        )

        return result


def diff_section_maps(
    before_states: list[SectionState],
    after_states: list[SectionState],
    before_revision_id: int,
    after_revision_id: int,
) -> RevisionDiffResult:
    """Pure-function diff logic operating on SectionState lists.

    Separated from the engine class so it can be tested without DB mocks.

    Args:
        before_states: Sections at the earlier revision.
        after_states: Sections at the later revision.
        before_revision_id: ID of the earlier revision.
        after_revision_id: ID of the later revision.

    Returns:
        RevisionDiffResult (elapsed_seconds set to 0.0; caller may override).
    """
    before_map: dict[tuple[int, str], SectionState] = {
        (s.title_number, s.section_number): s for s in before_states
    }
    after_map: dict[tuple[int, str], SectionState] = {
        (s.title_number, s.section_number): s for s in after_states
    }

    diffs: list[SectionDiff] = []
    added = 0
    modified = 0
    deleted = 0
    unchanged = 0

    # Check after_map against before_map
    for key, after_state in after_map.items():
        before_state = before_map.get(key)
        if before_state is None:
            # ADDED
            diffs.append(
                SectionDiff(
                    title_number=key[0],
                    section_number=key[1],
                    change_type="added",
                    text_changed=True,
                    notes_changed=after_state.notes_hash is not None,
                    before_state=None,
                    after_state=after_state,
                )
            )
            added += 1
        else:
            text_changed = before_state.text_hash != after_state.text_hash
            notes_changed = before_state.notes_hash != after_state.notes_hash
            if text_changed or notes_changed:
                # MODIFIED
                diffs.append(
                    SectionDiff(
                        title_number=key[0],
                        section_number=key[1],
                        change_type="modified",
                        text_changed=text_changed,
                        notes_changed=notes_changed,
                        before_state=before_state,
                        after_state=after_state,
                    )
                )
                modified += 1
            else:
                unchanged += 1

    # Check for deletions (in before but not in after)
    for key, before_state in before_map.items():
        if key not in after_map:
            diffs.append(
                SectionDiff(
                    title_number=key[0],
                    section_number=key[1],
                    change_type="deleted",
                    text_changed=True,
                    notes_changed=before_state.notes_hash is not None,
                    before_state=before_state,
                    after_state=None,
                )
            )
            deleted += 1

    # Sort diffs by title and section for consistent output
    diffs.sort(key=lambda d: (d.title_number, d.section_number))

    return RevisionDiffResult(
        before_revision_id=before_revision_id,
        after_revision_id=after_revision_id,
        sections_added=added,
        sections_modified=modified,
        sections_deleted=deleted,
        sections_unchanged=unchanged,
        diffs=diffs,
        elapsed_seconds=0.0,
    )
