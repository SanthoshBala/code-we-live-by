"""Tests for pipeline.chrono.play_forward — PlayForwardEngine."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import RevisionStatus, RevisionType
from pipeline.chrono.play_forward import AdvanceResult, PlayForwardEngine
from pipeline.chrono.revision_builder import RevisionBuildResult
from pipeline.olrc.rp_ingestor import RPIngestResult
from pipeline.olrc.snapshot_service import SectionState
from pipeline.timeline import TimelineEvent, TimelineEventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_revision(
    revision_id: int = 1,
    sequence_number: int = 1,
    revision_type: str = RevisionType.RELEASE_POINT.value,
    law_id: int | None = None,
    release_point_id: int | None = None,
    is_ground_truth: bool = True,
    status: str = RevisionStatus.INGESTED.value,
) -> MagicMock:
    """Create a mock CodeRevision."""
    rev = MagicMock()
    rev.revision_id = revision_id
    rev.sequence_number = sequence_number
    rev.revision_type = revision_type
    rev.law_id = law_id
    rev.release_point_id = release_point_id
    rev.is_ground_truth = is_ground_truth
    rev.status = status
    rev.release_point = None
    if release_point_id is not None:
        rp_mock = MagicMock()
        rp_mock.full_identifier = "113-21"
        rev.release_point = rp_mock
    return rev


def _make_law_event(
    congress: int = 113,
    law_number: int = 22,
    law_id: int = 100,
    event_date: date | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        event_type=TimelineEventType.PUBLIC_LAW,
        identifier=f"PL {congress}-{law_number}",
        congress=congress,
        law_number=law_number,
        event_date=event_date or date(2014, 6, 1),
        law_id=law_id,
    )


def _make_rp_event(
    identifier: str = "113-37",
    congress: int = 113,
    law_number: int = 37,
    event_date: date | None = None,
    deferred_laws: list[int] | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        event_type=TimelineEventType.RELEASE_POINT,
        identifier=identifier,
        congress=congress,
        law_number=law_number,
        event_date=event_date or date(2014, 7, 1),
        deferred_laws=deferred_laws or [],
    )


def _make_build_result(
    revision_id: int = 2,
    law_id: int = 100,
    parent_revision_id: int = 1,
    sequence_number: int = 2,
) -> RevisionBuildResult:
    return RevisionBuildResult(
        revision_id=revision_id,
        law_id=law_id,
        parent_revision_id=parent_revision_id,
        sequence_number=sequence_number,
        sections_applied=3,
    )


def _make_rp_ingest_result(
    revision_id: int = 3,
    rp_identifier: str = "113-37",
    parent_revision_id: int = 2,
) -> RPIngestResult:
    return RPIngestResult(
        revision_id=revision_id,
        rp_identifier=rp_identifier,
        parent_revision_id=parent_revision_id,
        titles_processed=1,
        titles_skipped=0,
        total_sections=10,
        diff_summary=None,
        elapsed_seconds=1.0,
    )


def _make_section(
    title: int = 17,
    section: str = "101",
    text_hash: str = "h1",
    notes_hash: str = "n1",
) -> SectionState:
    return SectionState(
        title_number=title,
        section_number=section,
        heading="Test",
        text_content="text",
        text_hash=text_hash,
        normalized_provisions=None,
        notes="notes",
        normalized_notes=None,
        notes_hash=notes_hash,
        full_citation=None,
        snapshot_id=1,
        revision_id=1,
        is_deleted=False,
    )


def _make_engine(session: AsyncMock) -> PlayForwardEngine:
    """Create a PlayForwardEngine with mock dependencies."""
    downloader = MagicMock()
    parser = MagicMock()
    engine = PlayForwardEngine(session, downloader, parser)
    return engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdvanceResult:
    def test_creation(self) -> None:
        result = AdvanceResult()
        assert result.events_processed == 0
        assert result.revisions_created == []
        assert result.checkpoint_result is None


class TestAdvanceSingleLaw:
    @pytest.mark.asyncio
    async def test_advance_single_law(self) -> None:
        """Advance processes one law event, creates derived revision."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)

        # Timeline: [RP 113-21 (head), LAW 113-22, RP 113-37]
        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 22, law_id=100, event_date=date(2014, 6, 1)),
            _make_rp_event("113-37", 113, 37, date(2014, 7, 1)),
        ]
        build_result = _make_build_result(revision_id=2, law_id=100)

        law_mock = MagicMock()
        law_mock.law_id = 100

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
            patch.object(engine, "_find_law", return_value=law_mock),
            patch.object(
                engine.law_change_service, "process_law", return_value=MagicMock()
            ),
            patch.object(
                engine.revision_builder,
                "build_revision",
                return_value=build_result,
            ),
        ):
            result = await engine.advance(count=1)

        assert result.events_processed == 1
        assert result.laws_applied == 1
        assert result.revisions_created == [2]

    @pytest.mark.asyncio
    async def test_advance_single_rp(self) -> None:
        """Advance processes one RP event, creates ground-truth revision."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(
            revision_id=2,
            sequence_number=2,
            revision_type=RevisionType.PUBLIC_LAW.value,
            law_id=100,
            is_ground_truth=False,
        )

        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 22, law_id=100, event_date=date(2014, 6, 1)),
            _make_rp_event("113-37", 113, 37, date(2014, 7, 1)),
        ]
        rp_result = _make_rp_ingest_result(revision_id=3)

        # For checkpoint: no derived revision before RP
        rp_revision_mock = _make_revision(revision_id=3, sequence_number=3)

        # session.execute returns for: rp_revision lookup, derived revision lookup
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=rp_revision_mock)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # no derived
        ]
        session.execute = AsyncMock(side_effect=execute_results)

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
            patch.object(
                engine.rp_ingestor,
                "ingest_release_point",
                return_value=rp_result,
            ),
        ):
            result = await engine.advance(count=1)

        assert result.events_processed == 1
        assert result.rps_ingested == 1
        assert result.revisions_created == [3]
        # No checkpoint because no derived revision before RP
        assert result.checkpoint_result is None


class TestAdvanceToRP:
    @pytest.mark.asyncio
    async def test_advance_to_rp(self) -> None:
        """advance_to processes multiple events up to target RP."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)

        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 22, law_id=100, event_date=date(2014, 3, 1)),
            _make_law_event(113, 23, law_id=101, event_date=date(2014, 5, 1)),
            _make_rp_event("113-37", 113, 37, date(2014, 7, 1)),
        ]

        law_mock = MagicMock()
        build_results = [
            _make_build_result(revision_id=2, law_id=100, sequence_number=2),
            _make_build_result(revision_id=3, law_id=101, sequence_number=3),
        ]
        rp_result = _make_rp_ingest_result(revision_id=4)

        # For checkpoint after RP
        rp_revision_mock = _make_revision(revision_id=4, sequence_number=4)
        derived_revision_mock = _make_revision(
            revision_id=3, sequence_number=3, is_ground_truth=False
        )
        sections = [_make_section()]

        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=rp_revision_mock)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=derived_revision_mock)),
        ]
        session.execute = AsyncMock(side_effect=execute_results)

        call_count = 0

        async def mock_build(*_args, **_kwargs):
            nonlocal call_count
            result = build_results[call_count]
            call_count += 1
            return result

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
            patch.object(engine, "_find_law", return_value=law_mock),
            patch.object(
                engine.law_change_service, "process_law", return_value=MagicMock()
            ),
            patch.object(
                engine.revision_builder, "build_revision", side_effect=mock_build
            ),
            patch.object(
                engine.rp_ingestor,
                "ingest_release_point",
                return_value=rp_result,
            ),
            patch.object(
                engine.snapshot_service,
                "get_all_sections_at_revision",
                return_value=sections,
            ),
        ):
            result = await engine.advance_to("113-37")

        assert result.events_processed == 3  # 2 laws + 1 RP
        assert result.laws_applied == 2
        assert result.rps_ingested == 1
        assert result.revisions_created == [2, 3, 4]
        assert result.checkpoint_result is not None
        assert result.checkpoint_result.is_clean is True


class TestDeferredLaws:
    @pytest.mark.asyncio
    async def test_deferred_law_skipped(self) -> None:
        """Law in deferred list is skipped."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)

        # RP 113-37 defers law 25
        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 25, law_id=200, event_date=date(2014, 4, 1)),
            _make_rp_event("113-37", 113, 37, date(2014, 7, 1), deferred_laws=[25]),
        ]

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
        ):
            result = await engine.advance(count=1)

        assert result.events_processed == 1
        assert result.laws_skipped == 1
        assert result.laws_applied == 0


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_advance_from_empty(self) -> None:
        """Error when no revisions exist."""
        session = AsyncMock()
        engine = _make_engine(session)

        with (
            patch.object(engine, "_get_current_head", return_value=None),
            pytest.raises(RuntimeError, match="No ingested revisions"),
        ):
            await engine.advance()

    @pytest.mark.asyncio
    async def test_advance_nothing_to_process(self) -> None:
        """Returns early when timeline is current (no events after head)."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)
        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
        ]

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
        ):
            result = await engine.advance()

        assert result.events_processed == 0

    @pytest.mark.asyncio
    async def test_advance_law_not_in_db(self) -> None:
        """Law not found in DB is counted as failed."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)

        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 22, law_id=100),
        ]

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
            patch.object(engine, "_find_law", return_value=None),
        ):
            result = await engine.advance(count=1)

        assert result.events_processed == 1
        assert result.laws_failed == 1
        assert result.laws_applied == 0


class TestValidateAtRP:
    @pytest.mark.asyncio
    async def test_validate_at_rp(self) -> None:
        """Standalone validation compares derived vs RP ground truth."""
        session = AsyncMock()
        engine = _make_engine(session)

        rp_revision = _make_revision(
            revision_id=3, sequence_number=3, release_point_id=20
        )
        derived_revision = _make_revision(
            revision_id=2,
            sequence_number=2,
            is_ground_truth=False,
            revision_type=RevisionType.PUBLIC_LAW.value,
        )

        sections = [_make_section()]

        # _find_rp_revision returns the rp revision
        # Then _run_checkpoint queries for the derived revision
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=derived_revision)),
        ]
        session.execute = AsyncMock(side_effect=execute_results)

        with (
            patch.object(engine, "_find_rp_revision", return_value=rp_revision),
            patch.object(
                engine.snapshot_service,
                "get_all_sections_at_revision",
                return_value=sections,
            ),
        ):
            checkpoint = await engine.validate_at_rp("113-37")

        assert checkpoint is not None
        assert checkpoint.rp_identifier == "113-37"
        assert checkpoint.is_clean is True

    @pytest.mark.asyncio
    async def test_validate_at_rp_not_found(self) -> None:
        """Raises ValueError when RP revision doesn't exist."""
        session = AsyncMock()
        engine = _make_engine(session)

        with (
            patch.object(engine, "_find_rp_revision", return_value=None),
            pytest.raises(ValueError, match="No ingested revision"),
        ):
            await engine.validate_at_rp("113-99")

    @pytest.mark.asyncio
    async def test_validate_at_rp_no_derived(self) -> None:
        """Returns None when no derived revisions exist before RP."""
        session = AsyncMock()
        engine = _make_engine(session)

        rp_revision = _make_revision(
            revision_id=1, sequence_number=1, release_point_id=10
        )

        # No derived revision found
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch.object(engine, "_find_rp_revision", return_value=rp_revision):
            checkpoint = await engine.validate_at_rp("113-21")

        assert checkpoint is None


class TestAutoProcessLaw:
    @pytest.mark.asyncio
    async def test_process_law_error_does_not_block_advance(self) -> None:
        """Auto-processing failure logs error but advance continues."""
        session = AsyncMock()
        engine = _make_engine(session)

        head = _make_revision(revision_id=1, sequence_number=1, release_point_id=10)
        events = [
            _make_rp_event("113-21", 113, 21, date(2014, 1, 1)),
            _make_law_event(113, 22, law_id=100, event_date=date(2014, 6, 1)),
        ]

        law_mock = MagicMock()
        law_mock.law_id = 100
        law_mock.congress = 113
        law_mock.law_number = "22"

        build_result = _make_build_result(revision_id=2, law_id=100)

        with (
            patch.object(engine, "_get_current_head", return_value=head),
            patch.object(engine.timeline_builder, "build", return_value=events),
            patch.object(engine, "_find_law", return_value=law_mock),
            patch.object(
                engine.law_change_service,
                "process_law",
                side_effect=RuntimeError("GovInfo unavailable"),
            ),
            patch.object(
                engine.revision_builder,
                "build_revision",
                return_value=build_result,
            ),
        ):
            result = await engine.advance(count=1)

        # Advance still succeeds (build_revision runs with whatever state exists)
        assert result.events_processed == 1
        assert result.laws_applied == 1
