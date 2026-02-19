"""Play-forward engine — walks the timeline forward event-by-event.

Coordinates TimelineBuilder, RPIngestor, and RevisionBuilder to advance
the US Code state through chronological events. At each RP checkpoint,
validates derived state against ground truth.

Phase 5 of the chrono pipeline:
    1.18 foundation -> 1.19 bootstrap -> 1.20 RP diffing ->
    1.20b amendment application -> 1.20c play-forward.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import RevisionStatus, RevisionType
from app.models.public_law import PublicLaw
from app.models.revision import CodeRevision
from pipeline.chrono.checkpoint import CheckpointResult, validate_checkpoint
from pipeline.chrono.revision_builder import RevisionBuilder
from pipeline.legal_parser.law_change_service import LawChangeService
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.parser import USLMParser
from pipeline.olrc.rp_ingestor import RPIngestor
from pipeline.olrc.snapshot_service import SnapshotService
from pipeline.timeline import TimelineBuilder, TimelineEvent, TimelineEventType

logger = logging.getLogger(__name__)


@dataclass
class AdvanceResult:
    """Result of advancing the timeline by one or more events."""

    events_processed: int = 0
    revisions_created: list[int] = field(default_factory=list)
    laws_applied: int = 0
    rps_ingested: int = 0
    laws_skipped: int = 0
    laws_failed: int = 0
    checkpoint_result: CheckpointResult | None = None
    elapsed_seconds: float = 0.0


class PlayForwardEngine:
    """Walks the timeline forward, dispatching events to the appropriate handler.

    Uses TimelineBuilder for event ordering, RevisionBuilder for law events,
    and RPIngestor for release point events. Validates derived state against
    RP ground truth at each checkpoint.
    """

    def __init__(
        self,
        session: AsyncSession,
        downloader: OLRCDownloader,
        parser: USLMParser,
    ):
        self.session = session
        self.timeline_builder = TimelineBuilder(session)
        self.rp_ingestor = RPIngestor(session, downloader, parser)
        self.revision_builder = RevisionBuilder(session)
        self.snapshot_service = SnapshotService(session)
        self.law_change_service = LawChangeService(session)

    async def advance(self, count: int = 1) -> AdvanceResult:
        """Advance the timeline by processing the next `count` events.

        Args:
            count: Number of events to process (default: 1).

        Returns:
            AdvanceResult with processing summary.

        Raises:
            RuntimeError: If no ingested revisions exist (must bootstrap first).
        """
        start = time.monotonic()
        result = AdvanceResult()

        # Get current head and timeline
        head = await self._get_current_head()
        if head is None:
            raise RuntimeError(
                "No ingested revisions found. Run 'chrono-bootstrap' first."
            )

        events = await self.timeline_builder.build()
        position = self._find_position(events, head)

        if position is None:
            logger.warning(
                f"Current head (revision {head.revision_id}) not found in timeline. "
                "Advancing from end of known events."
            )
            position = len(events) - 1

        # Get next events
        remaining = events[position + 1 :]
        to_process = remaining[:count]

        if not to_process:
            logger.info("No more events to process — timeline is current.")
            result.elapsed_seconds = time.monotonic() - start
            return result

        # Build set of deferred laws from upcoming RPs
        deferred = self._collect_deferred_laws(remaining)

        parent_revision_id = head.revision_id
        sequence_number = head.sequence_number + 1

        for event in to_process:
            parent_revision_id, sequence_number = await self._process_event(
                event, parent_revision_id, sequence_number, deferred, result
            )

        result.elapsed_seconds = time.monotonic() - start
        return result

    async def advance_to(self, rp_identifier: str) -> AdvanceResult:
        """Advance through all events up to and including the target RP.

        Args:
            rp_identifier: Target release point (e.g., "113-37").

        Returns:
            AdvanceResult with checkpoint_result populated.

        Raises:
            RuntimeError: If no ingested revisions exist.
            ValueError: If the target RP is not found in the timeline.
        """
        start = time.monotonic()
        result = AdvanceResult()

        head = await self._get_current_head()
        if head is None:
            raise RuntimeError(
                "No ingested revisions found. Run 'chrono-bootstrap' first."
            )

        events = await self.timeline_builder.build()
        position = self._find_position(events, head)

        if position is None:
            logger.warning(
                f"Current head (revision {head.revision_id}) not found in timeline."
            )
            position = len(events) - 1

        # Find the target RP
        target_idx = None
        for i, event in enumerate(events):
            if (
                event.event_type == TimelineEventType.RELEASE_POINT
                and event.identifier == rp_identifier
            ):
                target_idx = i
                break

        if target_idx is None:
            raise ValueError(f"Release point '{rp_identifier}' not found in timeline.")

        if target_idx <= position:
            logger.info(
                f"Target RP '{rp_identifier}' is at or before current position. "
                "Nothing to process."
            )
            result.elapsed_seconds = time.monotonic() - start
            return result

        to_process = events[position + 1 : target_idx + 1]
        deferred = self._collect_deferred_laws(to_process)

        parent_revision_id = head.revision_id
        sequence_number = head.sequence_number + 1

        for event in to_process:
            parent_revision_id, sequence_number = await self._process_event(
                event, parent_revision_id, sequence_number, deferred, result
            )

        result.elapsed_seconds = time.monotonic() - start
        return result

    async def validate_at_rp(self, rp_identifier: str) -> CheckpointResult | None:
        """Standalone validation: compare derived state against RP ground truth.

        Does NOT ingest anything — read-only.

        Args:
            rp_identifier: Release point to validate against.

        Returns:
            CheckpointResult, or None if no derived revisions exist before the RP.

        Raises:
            ValueError: If the RP revision is not found.
        """
        # Find the RP revision
        rp_revision = await self._find_rp_revision(rp_identifier)
        if rp_revision is None:
            raise ValueError(
                f"No ingested revision found for RP '{rp_identifier}'. "
                "Ingest the RP first."
            )

        return await self._run_checkpoint(rp_revision, rp_identifier)

    async def _get_current_head(self) -> CodeRevision | None:
        """Get the latest ingested CodeRevision (with release_point eager-loaded)."""
        stmt = (
            select(CodeRevision)
            .options(selectinload(CodeRevision.release_point))
            .where(CodeRevision.status == RevisionStatus.INGESTED.value)
            .order_by(CodeRevision.sequence_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _find_position(
        self, events: list[TimelineEvent], head: CodeRevision
    ) -> int | None:
        """Find the current head's position in the timeline.

        Matches by law_id (for PUBLIC_LAW revisions) or release_point_id
        identifier (for RELEASE_POINT revisions).
        """
        for i, event in enumerate(events):
            if (
                head.revision_type == RevisionType.PUBLIC_LAW.value
                and event.event_type == TimelineEventType.PUBLIC_LAW
                and event.law_id == head.law_id
            ):
                return i
            if (
                head.revision_type == RevisionType.RELEASE_POINT.value
                and event.event_type == TimelineEventType.RELEASE_POINT
            ):
                # Match by RP identifier — need to check if the revision's
                # release_point has the same identifier
                rp = head.release_point
                if rp is not None and event.identifier == rp.full_identifier:
                    return i
        return None

    def _collect_deferred_laws(
        self, events: list[TimelineEvent]
    ) -> set[tuple[int, int]]:
        """Collect (congress, law_number) pairs deferred by upcoming RPs."""
        deferred: set[tuple[int, int]] = set()
        for event in events:
            if event.event_type == TimelineEventType.RELEASE_POINT:
                for law_num in event.deferred_laws:
                    deferred.add((event.congress, law_num))
        return deferred

    async def _process_event(
        self,
        event: TimelineEvent,
        parent_revision_id: int,
        sequence_number: int,
        deferred: set[tuple[int, int]],
        result: AdvanceResult,
    ) -> tuple[int, int]:
        """Process a single timeline event. Returns (new_parent_id, new_seq)."""
        if event.event_type == TimelineEventType.PUBLIC_LAW:
            return await self._process_law(
                event, parent_revision_id, sequence_number, deferred, result
            )
        else:
            return await self._process_rp(
                event, parent_revision_id, sequence_number, result
            )

    async def _process_law(
        self,
        event: TimelineEvent,
        parent_revision_id: int,
        sequence_number: int,
        deferred: set[tuple[int, int]],
        result: AdvanceResult,
    ) -> tuple[int, int]:
        """Process a PUBLIC_LAW event.

        Auto-processes the law (fetch text, parse amendments, generate diffs)
        if no LawChange records exist yet.
        """
        assert event.law_number is not None

        # Check if deferred
        if (event.congress, event.law_number) in deferred:
            logger.info(f"Skipping deferred law PL {event.congress}-{event.law_number}")
            result.laws_skipped += 1
            result.events_processed += 1
            return parent_revision_id, sequence_number

        # Look up the PublicLaw record
        law = await self._find_law(event.congress, event.law_number)
        if law is None:
            logger.warning(
                f"PublicLaw {event.congress}-{event.law_number} not found in DB. "
                "Skipping."
            )
            result.laws_failed += 1
            result.events_processed += 1
            return parent_revision_id, sequence_number

        # Auto-process: generate LawChange records if none exist (idempotent)
        try:
            await self.law_change_service.process_law(
                congress=law.congress,
                law_number=int(law.law_number),
            )
        except Exception:
            logger.exception(
                f"Failed to auto-process PL {event.congress}-{event.law_number}"
            )
            await self.session.rollback()

        try:
            build_result = await self.revision_builder.build_revision(
                law=law,
                parent_revision_id=parent_revision_id,
                sequence_number=sequence_number,
            )
            await self.session.commit()
        except Exception:
            logger.exception(
                f"Failed to apply law PL {event.congress}-{event.law_number}"
            )
            await self.session.rollback()
            result.laws_failed += 1
            result.events_processed += 1
            return parent_revision_id, sequence_number

        logger.info(
            f"Applied PL {event.congress}-{event.law_number} -> "
            f"revision {build_result.revision_id} "
            f"(applied={build_result.sections_applied}, "
            f"failed={build_result.sections_failed})"
        )
        result.laws_applied += 1
        result.events_processed += 1
        result.revisions_created.append(build_result.revision_id)
        return build_result.revision_id, sequence_number + 1

    async def _process_rp(
        self,
        event: TimelineEvent,
        parent_revision_id: int,
        sequence_number: int,
        result: AdvanceResult,
    ) -> tuple[int, int]:
        """Process a RELEASE_POINT event."""
        try:
            rp_result = await self.rp_ingestor.ingest_release_point(
                rp_identifier=event.identifier,
                parent_revision_id=parent_revision_id,
                sequence_number=sequence_number,
            )
            await self.session.commit()
        except Exception:
            logger.exception(f"Failed to ingest RP {event.identifier}")
            await self.session.rollback()
            result.events_processed += 1
            return parent_revision_id, sequence_number

        logger.info(
            f"Ingested RP {event.identifier} -> revision {rp_result.revision_id} "
            f"({rp_result.total_sections} sections)"
        )
        result.rps_ingested += 1
        result.events_processed += 1
        result.revisions_created.append(rp_result.revision_id)

        # Run checkpoint validation
        rp_revision_stmt = select(CodeRevision).where(
            CodeRevision.revision_id == rp_result.revision_id
        )
        rp_rev_result = await self.session.execute(rp_revision_stmt)
        rp_revision = rp_rev_result.scalar_one_or_none()
        if rp_revision is not None:
            checkpoint = await self._run_checkpoint(rp_revision, event.identifier)
            if checkpoint is not None:
                result.checkpoint_result = checkpoint

        return rp_result.revision_id, sequence_number + 1

    async def _run_checkpoint(
        self, rp_revision: CodeRevision, rp_identifier: str
    ) -> CheckpointResult | None:
        """Run checkpoint validation between the last derived revision and an RP.

        Returns None if no derived revisions exist before the RP.
        """
        # Find the last derived (non-ground-truth) revision before this RP
        derived_stmt = (
            select(CodeRevision)
            .where(
                CodeRevision.sequence_number < rp_revision.sequence_number,
                CodeRevision.is_ground_truth == False,  # noqa: E712
                CodeRevision.status == RevisionStatus.INGESTED.value,
            )
            .order_by(CodeRevision.sequence_number.desc())
            .limit(1)
        )
        derived_result = await self.session.execute(derived_stmt)
        derived_revision = derived_result.scalar_one_or_none()

        if derived_revision is None:
            logger.info(
                f"No derived revisions before RP {rp_identifier}. "
                "Skipping checkpoint validation."
            )
            return None

        # Materialize both states
        derived_sections = await self.snapshot_service.get_all_sections_at_revision(
            derived_revision.revision_id
        )
        rp_sections = await self.snapshot_service.get_all_sections_at_revision(
            rp_revision.revision_id
        )

        checkpoint = validate_checkpoint(
            derived_sections=derived_sections,
            rp_sections=rp_sections,
            rp_identifier=rp_identifier,
            rp_revision_id=rp_revision.revision_id,
            derived_revision_id=derived_revision.revision_id,
        )

        if checkpoint.is_clean:
            logger.info(
                f"Checkpoint {rp_identifier}: CLEAN "
                f"({checkpoint.sections_match} sections match)"
            )
        else:
            logger.warning(
                f"Checkpoint {rp_identifier}: DIVERGED "
                f"(match={checkpoint.sections_match}, "
                f"mismatch={checkpoint.sections_mismatch}, "
                f"only_derived={checkpoint.sections_only_in_derived}, "
                f"only_rp={checkpoint.sections_only_in_rp})"
            )

        return checkpoint

    async def _find_rp_revision(self, rp_identifier: str) -> CodeRevision | None:
        """Find the ingested CodeRevision for a release point identifier."""
        from app.models.release_point import OLRCReleasePoint

        stmt = (
            select(CodeRevision)
            .join(
                OLRCReleasePoint,
                CodeRevision.release_point_id == OLRCReleasePoint.release_point_id,
            )
            .where(
                OLRCReleasePoint.full_identifier == rp_identifier,
                CodeRevision.status == RevisionStatus.INGESTED.value,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_law(self, congress: int, law_number: int) -> PublicLaw | None:
        """Look up a PublicLaw by congress and law number."""
        stmt = select(PublicLaw).where(
            PublicLaw.congress == congress,
            PublicLaw.law_number == str(law_number),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
