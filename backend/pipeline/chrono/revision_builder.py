"""Orchestrator for building derived CodeRevisions from law changes.

Creates a CodeRevision (type=PUBLIC_LAW) by applying all LawChange records
for a given PublicLaw to the parent revision's section state.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ChangeType, RevisionStatus, RevisionType
from app.models.public_law import LawChange, PublicLaw
from app.models.revision import CodeRevision
from app.models.snapshot import SectionSnapshot
from pipeline.chrono.amendment_applicator import (
    ApplicationResult,
    ApplicationStatus,
    apply_text_change,
)
from pipeline.chrono.notes_updater import update_notes_for_applied_law
from pipeline.olrc.parser import compute_text_hash
from pipeline.olrc.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


@dataclass
class RevisionBuildResult:
    """Summary of a revision build operation."""

    revision_id: int
    law_id: int
    parent_revision_id: int
    sequence_number: int
    sections_applied: int = 0
    sections_skipped: int = 0
    sections_failed: int = 0
    sections_added: int = 0
    sections_repealed: int = 0
    application_results: list[ApplicationResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0


class RevisionBuilder:
    """Builds derived revisions by applying law changes."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.snapshot_service = SnapshotService(session)

    async def build_revision(
        self,
        law: PublicLaw,
        parent_revision_id: int,
        sequence_number: int,
    ) -> RevisionBuildResult:
        """Build a CodeRevision by applying all LawChange records for a law.

        Args:
            law: The PublicLaw whose changes to apply.
            parent_revision_id: ID of the parent revision.
            sequence_number: Global ordering position for the new revision.

        Returns:
            RevisionBuildResult with counts and details.
        """
        start = time.monotonic()

        # 1. Idempotency: check if revision already exists for this law
        existing_stmt = select(CodeRevision).where(
            CodeRevision.law_id == law.law_id,
            CodeRevision.status == RevisionStatus.INGESTED.value,
        )
        existing_result = await self.session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            logger.info(
                "Revision already exists for PL %s-%s (revision_id=%d)",
                law.congress,
                law.law_number,
                existing.revision_id,
            )
            return RevisionBuildResult(
                revision_id=existing.revision_id,
                law_id=law.law_id,
                parent_revision_id=parent_revision_id,
                sequence_number=existing.sequence_number,
                elapsed_seconds=time.monotonic() - start,
            )

        # 2. Fetch LawChange records, eagerly loading section relationship
        changes_stmt = (
            select(LawChange)
            .where(LawChange.law_id == law.law_id)
            .options(selectinload(LawChange.section))
            .order_by(LawChange.change_id)
        )
        changes_result = await self.session.execute(changes_stmt)
        changes = list(changes_result.scalars().all())

        if not changes:
            logger.warning(
                "No LawChange records for PL %s-%s", law.congress, law.law_number
            )

        # 3. Create CodeRevision
        revision = CodeRevision(
            revision_type=RevisionType.PUBLIC_LAW.value,
            law_id=law.law_id,
            parent_revision_id=parent_revision_id,
            effective_date=law.enacted_date,
            is_ground_truth=False,
            status=RevisionStatus.INGESTING.value,
            sequence_number=sequence_number,
            summary=f"PL {law.congress}-{law.law_number}",
        )
        self.session.add(revision)
        await self.session.flush()  # Get revision_id

        result = RevisionBuildResult(
            revision_id=revision.revision_id,
            law_id=law.law_id,
            parent_revision_id=parent_revision_id,
            sequence_number=sequence_number,
        )

        # 4. Group changes by (title_number, section_number)
        section_groups: dict[tuple[int, str], list[LawChange]] = {}
        for change in changes:
            section = change.section
            key = (section.title_number, section.section_number)
            section_groups.setdefault(key, []).append(change)

        # 5. Process each section group
        for (title_num, section_num), section_changes in section_groups.items():
            await self._apply_section_changes(
                revision=revision,
                title_number=title_num,
                section_number=section_num,
                section_changes=section_changes,
                parent_revision_id=parent_revision_id,
                law=law,
                result=result,
            )

        # 6. Mark revision as INGESTED
        revision.status = RevisionStatus.INGESTED.value
        await self.session.flush()

        result.elapsed_seconds = time.monotonic() - start
        logger.info(
            "Built revision %d for PL %s-%s: "
            "%d applied, %d skipped, %d failed, %d added, %d repealed",
            revision.revision_id,
            law.congress,
            law.law_number,
            result.sections_applied,
            result.sections_skipped,
            result.sections_failed,
            result.sections_added,
            result.sections_repealed,
        )
        return result

    async def _apply_section_changes(
        self,
        revision: CodeRevision,
        title_number: int,
        section_number: str,
        section_changes: list[LawChange],
        parent_revision_id: int,
        law: PublicLaw,
        result: RevisionBuildResult,
    ) -> None:
        """Apply all changes for a single section and create a snapshot."""
        # Fetch parent state
        parent_state = await self.snapshot_service.get_section_at_revision(
            title_number, section_number, parent_revision_id
        )

        current_text = parent_state.text_content if parent_state else None
        is_deleted = False
        is_new_section = parent_state is None
        any_applied = False
        descriptions: list[str] = []

        for change in section_changes:
            app_result = apply_text_change(
                text_content=current_text,
                change_type=change.change_type,
                old_text=change.old_text,
                new_text=change.new_text,
                title_number=title_number,
                section_number=section_number,
            )
            result.application_results.append(app_result)

            if app_result.status == ApplicationStatus.APPLIED:
                any_applied = True
                current_text = app_result.new_text
                desc = change.description or app_result.description
                descriptions.append(desc)

                if change.change_type == ChangeType.REPEAL:
                    is_deleted = True
                    result.sections_repealed += 1
                    break  # No further changes after repeal
                elif change.change_type == ChangeType.ADD and is_new_section:
                    result.sections_added += 1
                    is_new_section = False  # Only count once
                else:
                    result.sections_applied += 1

            elif app_result.status == ApplicationStatus.SKIPPED:
                result.sections_skipped += 1

            elif app_result.status == ApplicationStatus.FAILED:
                result.sections_failed += 1
                logger.warning(
                    "Failed to apply %s change to %d USC %s: %s",
                    change.change_type.value,
                    title_number,
                    section_number,
                    app_result.description,
                )

        # Only create a snapshot if something changed
        if not any_applied:
            return

        # Update notes
        existing_notes = parent_state.normalized_notes if parent_state else None
        existing_raw_notes = parent_state.notes if parent_state else None
        combined_description = "; ".join(descriptions)
        updated_notes_dict, updated_raw_notes = update_notes_for_applied_law(
            existing_notes=existing_notes,
            raw_notes=existing_raw_notes,
            law=law,
            change_type=section_changes[0].change_type,
            description=combined_description,
        )

        # Compute hashes
        text_hash = compute_text_hash(current_text) if current_text else None
        notes_hash = compute_text_hash(updated_raw_notes) if updated_raw_notes else None

        # Create snapshot
        snapshot = SectionSnapshot(
            revision_id=revision.revision_id,
            title_number=title_number,
            section_number=section_number,
            heading=parent_state.heading if parent_state else None,
            text_content=current_text,
            normalized_provisions=(
                parent_state.normalized_provisions if parent_state else None
            ),
            notes=updated_raw_notes,
            normalized_notes=updated_notes_dict,
            text_hash=text_hash,
            notes_hash=notes_hash,
            full_citation=(
                parent_state.full_citation
                if parent_state
                else f"{title_number} USC {section_number}"
            ),
            is_deleted=is_deleted,
        )
        self.session.add(snapshot)
