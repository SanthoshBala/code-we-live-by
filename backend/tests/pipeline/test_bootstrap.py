"""Tests for the bootstrap service (Task 1.19) and Cloud Run fan-out (issue #181)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import RevisionStatus, RevisionType
from pipeline.olrc.bootstrap import (
    ALL_TITLES,
    BootstrapResult,
    BootstrapService,
    partition_titles,
)
from pipeline.olrc.parser import ParsedGroup, ParsedSection, USLMParseResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed_section(
    section_number: str = "101",
    heading: str = "Test heading",
    text_content: str = "The owner of copyright shall have exclusive rights.",
    notes: str | None = None,
    full_citation: str = "17 U.S.C. § 101",
) -> ParsedSection:
    """Create a minimal ParsedSection for testing."""
    return ParsedSection(
        section_number=section_number,
        heading=heading,
        text_content=text_content,
        full_citation=full_citation,
        notes=notes,
    )


def _make_parse_result(
    title_number: int = 17,
    sections: list[ParsedSection] | None = None,
) -> USLMParseResult:
    """Create a minimal USLMParseResult for testing."""
    if sections is None:
        sections = [_make_parsed_section()]
    title_group = ParsedGroup(
        group_type="title",
        number=str(title_number),
        name=f"Title {title_number}",
        key=f"title:{title_number}",
    )
    return USLMParseResult(
        title=title_group,
        groups=[title_group],
        sections=sections,
    )


def _make_mock_session() -> AsyncMock:
    """Create a mock AsyncSession with execute returning no results."""
    session = AsyncMock()
    # Default: no existing records found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    # session.add is synchronous in SQLAlchemy
    session.add = MagicMock()
    return session


def _get_snapshot_dicts(session: AsyncMock) -> list[dict]:
    """Extract snapshot insert dicts from session.execute bulk-insert calls."""
    for call in session.execute.call_args_list:
        if len(call.args) == 2 and isinstance(call.args[1], list):
            return call.args[1]
    return []


def _make_mock_downloader(
    xml_path: Path | None = Path("/fake/title17.xml"),
) -> MagicMock:
    """Create a mock OLRCDownloader."""
    downloader = MagicMock()
    downloader.download_title_at_release_point = AsyncMock(return_value=xml_path)
    return downloader


def _make_parser_mock(parse_result: USLMParseResult | None = None) -> MagicMock:
    """Create a USLMParser instance mock with a configured parse_file return value.

    Patch bootstrap.USLMParser with return_value=this to control what ingest_title
    parses without going through the real XML pipeline.
    """
    instance = MagicMock()
    instance.parse_file.return_value = parse_result or _make_parse_result()
    return instance


# ---------------------------------------------------------------------------
# Tests: BootstrapResult dataclass
# ---------------------------------------------------------------------------


class TestBootstrapResult:
    """Tests for the BootstrapResult dataclass."""

    def test_creation(self) -> None:
        result = BootstrapResult(
            revision_id=1,
            rp_identifier="113-21",
            titles_processed=3,
            titles_skipped=1,
            total_sections=100,
            elapsed_seconds=5.2,
        )
        assert result.revision_id == 1
        assert result.rp_identifier == "113-21"
        assert result.titles_processed == 3
        assert result.titles_skipped == 1
        assert result.total_sections == 100
        assert result.elapsed_seconds == 5.2


# ---------------------------------------------------------------------------
# Tests: create_initial_commit
# ---------------------------------------------------------------------------


class TestCreateInitialCommit:
    """Tests for BootstrapService.create_initial_commit."""

    @pytest.mark.asyncio
    async def test_creates_revision(self) -> None:
        """Verify CodeRevision is created with correct fields."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        # revision_id is None with mock session (no DB to assign PK)
        assert result.rp_identifier == "113-21"
        assert result.titles_processed == 1
        assert result.total_sections == 1

        # Verify session.add was called with OLRCReleasePoint and CodeRevision.
        # Snapshots are bulk-inserted via session.execute(), not session.add().
        add_calls = session.add.call_args_list
        assert len(add_calls) >= 2

        added_objects = [call.args[0] for call in add_calls]
        from app.models.revision import CodeRevision

        revisions = [o for o in added_objects if isinstance(o, CodeRevision)]
        assert len(revisions) == 1
        rev = revisions[0]
        assert rev.revision_type == RevisionType.RELEASE_POINT.value
        assert rev.parent_revision_id is None
        assert rev.is_ground_truth is True
        assert rev.sequence_number == 0

    @pytest.mark.asyncio
    async def test_creates_snapshots(self) -> None:
        """Verify SectionSnapshots are created from parsed sections."""
        session = _make_mock_session()
        sections = [
            _make_parsed_section("101", "First section", "Content A"),
            _make_parsed_section("102", "Second section", "Content B"),
        ]
        mock_parser = _make_parser_mock(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        assert result.total_sections == 2

        # Snapshots are bulk-inserted via session.execute(insert(...), dicts).
        snapshots = _get_snapshot_dicts(session)
        assert len(snapshots) == 2
        section_numbers = {s["section_number"] for s in snapshots}
        assert section_numbers == {"101", "102"}
        assert all(s["title_number"] == 17 for s in snapshots)

    @pytest.mark.asyncio
    async def test_skip_unavailable_titles(self) -> None:
        """Title download returns None -> skipped, no error."""
        session = _make_mock_session()
        downloader = _make_mock_downloader(xml_path=None)

        service = BootstrapService(session, downloader)

        result = await service.create_initial_commit("113-21", titles=[99])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0
        assert result.total_sections == 0

    @pytest.mark.asyncio
    async def test_idempotent_completed(self) -> None:
        """If revision already ingested, returns early."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        # Mock: release point exists, revision exists and is Ingested
        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1
        mock_rp.full_identifier = "113-21"

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 42
        mock_rev.status = RevisionStatus.INGESTED.value

        # First call: find release point. Second: find revision.
        call_count = 0

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_rp
            elif call_count == 2:
                result.scalar_one_or_none.return_value = mock_rev
            else:
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)
        result = await service.create_initial_commit("113-21", titles=[17])

        assert result.revision_id == 42
        assert result.titles_processed == 0
        assert result.total_sections == 0
        # Download should NOT have been called
        downloader.download_title_at_release_point.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent_resume_failed(self) -> None:
        """If revision status is Failed, resumes ingestion."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1
        mock_rp.full_identifier = "113-21"
        mock_rp.publication_date = None

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 42
        mock_rev.status = RevisionStatus.FAILED.value

        call_count = 0

        def fake_execute(*args):
            nonlocal call_count
            # Bulk inserts (2 positional args) don't increment the select counter.
            if len(args) == 2 and isinstance(args[1], list):
                return MagicMock()
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_rp
            elif call_count == 2:
                result.scalar_one_or_none.return_value = mock_rev
            else:
                # For ingest_title idempotency check
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        # Should proceed with ingestion
        assert result.revision_id == 42
        assert result.titles_processed == 1
        downloader.download_title_at_release_point.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: snapshot field mapping
# ---------------------------------------------------------------------------


class TestSnapshotFieldMapping:
    """Tests verifying snapshot fields are correctly mapped from parsed sections."""

    @pytest.mark.asyncio
    async def test_snapshot_text_hash(self) -> None:
        """Verify SHA-256 hash is computed correctly for text_content."""
        text = "The owner of copyright shall have exclusive rights."
        expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        session = _make_mock_session()
        sections = [_make_parsed_section(text_content=text)]
        mock_parser = _make_parser_mock(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            await service.create_initial_commit("113-21", titles=[17])

        snapshots = _get_snapshot_dicts(session)
        assert len(snapshots) == 1
        assert snapshots[0]["text_hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_snapshot_notes_hash(self) -> None:
        """Verify notes hash is computed when notes are present."""
        notes = "(Pub. L. 94-553, title I, Oct. 19, 1976, 90 Stat. 2546)"
        expected_hash = hashlib.sha256(notes.encode("utf-8")).hexdigest()

        session = _make_mock_session()
        sections = [_make_parsed_section(notes=notes)]
        mock_parser = _make_parser_mock(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            await service.create_initial_commit("113-21", titles=[17])

        snapshots = _get_snapshot_dicts(session)
        assert len(snapshots) == 1
        assert snapshots[0]["notes_hash"] == expected_hash
        assert snapshots[0]["notes"] == notes

    @pytest.mark.asyncio
    async def test_snapshot_no_notes_hash_when_none(self) -> None:
        """Verify notes_hash is None when notes are absent."""
        session = _make_mock_session()
        sections = [_make_parsed_section(notes=None)]
        mock_parser = _make_parser_mock(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            await service.create_initial_commit("113-21", titles=[17])

        snapshots = _get_snapshot_dicts(session)
        assert len(snapshots) == 1
        assert snapshots[0]["notes_hash"] is None

    @pytest.mark.asyncio
    async def test_snapshot_full_citation(self) -> None:
        """Verify full_citation is preserved on snapshot."""
        session = _make_mock_session()
        sections = [_make_parsed_section(full_citation="17 U.S.C. § 101")]
        mock_parser = _make_parser_mock(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            await service.create_initial_commit("113-21", titles=[17])

        snapshots = _get_snapshot_dicts(session)
        assert len(snapshots) == 1
        assert snapshots[0]["full_citation"] == "17 U.S.C. § 101"
        assert snapshots[0]["is_deleted"] is False

    @pytest.mark.asyncio
    async def test_download_failure_skips_title(self) -> None:
        """Download raising an exception should skip the title, not fail."""
        session = _make_mock_session()
        downloader = MagicMock()
        downloader.download_title_at_release_point = AsyncMock(
            side_effect=Exception("Network error")
        )

        service = BootstrapService(session, downloader)

        result = await service.create_initial_commit("113-21", titles=[17])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0

    @pytest.mark.asyncio
    async def test_parse_failure_skips_title(self) -> None:
        """Parser raising an exception should skip the title, not fail."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        mock_parser = MagicMock()
        mock_parser.parse_file.side_effect = Exception("Parse error")

        service = BootstrapService(session, downloader)

        with patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser):
            result = await service.create_initial_commit("113-21", titles=[17])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0

    @pytest.mark.asyncio
    async def test_multiple_titles_parallel(self) -> None:
        """All titles in the list are ingested and aggregated correctly."""
        session = _make_mock_session()
        sections_17 = [_make_parsed_section("101", "First", "Content A")]
        sections_18 = [
            _make_parsed_section("1", "Crimes", "Content B"),
            _make_parsed_section("2", "Penalties", "Content C"),
        ]

        # Return title-specific paths so parse_file can key on them (thread-safe).
        def fake_download(title_num: int, _rp: str) -> Path:
            return Path(f"/fake/title{title_num}.xml")

        downloader = MagicMock()
        downloader.download_title_at_release_point = AsyncMock(
            side_effect=fake_download
        )

        mock_parser = MagicMock()

        def fake_parse_file(path: Path) -> USLMParseResult:
            if "17" in str(path):
                return _make_parse_result(title_number=17, sections=sections_17)
            return _make_parse_result(title_number=18, sections=sections_18)

        mock_parser.parse_file.side_effect = fake_parse_file

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            result = await service.create_initial_commit("113-21", titles=[17, 18])

        assert result.titles_processed == 2
        assert result.titles_skipped == 0
        assert result.total_sections == 3  # 1 + 2

    @pytest.mark.asyncio
    async def test_concurrency_cap_respected(self) -> None:
        """Semaphore limits concurrency; all titles still complete."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock()

        # concurrency=2 with 5 titles — all should still complete
        service = BootstrapService(session, downloader, concurrency=2)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            result = await service.create_initial_commit(
                "113-21", titles=[17, 18, 26, 42, 50]
            )

        assert result.titles_processed == 5
        assert result.titles_skipped == 0

    @pytest.mark.asyncio
    async def test_revision_committed_before_parallel_ingest(self) -> None:
        """Parent session must commit before worker sessions start, so the
        revision row is visible to worker transactions and section_snapshot
        FK inserts succeed."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock()

        # session_factory yields a separate worker session — record when it
        # is entered relative to commits on the parent session.
        worker_session = _make_mock_session()
        events: list[str] = []

        original_commit = session.commit

        async def tracked_commit() -> None:
            events.append("parent_commit")
            await original_commit()

        session.commit = tracked_commit

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def factory():
            events.append("worker_session_open")
            yield worker_session

        service = BootstrapService(
            session, downloader, session_factory=factory, concurrency=1
        )

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
        ):
            await service.create_initial_commit("113-21", titles=[17])

        # The first parent commit must precede the first worker session open.
        assert "parent_commit" in events
        assert "worker_session_open" in events
        assert events.index("parent_commit") < events.index("worker_session_open")


# ---------------------------------------------------------------------------
# Tests: partition_titles
# ---------------------------------------------------------------------------


class TestPartitionTitles:
    """Tests for the partition_titles helper used by Cloud Run fan-out."""

    def test_single_task_gets_all_titles(self) -> None:
        result = partition_titles(0, 1)
        assert result == ALL_TITLES

    def test_round_robin_two_tasks(self) -> None:
        titles = list(range(1, 7))  # [1, 2, 3, 4, 5, 6]
        task0 = partition_titles(0, 2, all_titles=titles)
        task1 = partition_titles(1, 2, all_titles=titles)
        assert task0 == [1, 3, 5]
        assert task1 == [2, 4, 6]
        assert sorted(task0 + task1) == titles

    def test_54_tasks_one_title_each(self) -> None:
        all_slices = [partition_titles(i, 54) for i in range(54)]
        assert all(len(s) == 1 for s in all_slices)
        combined = sorted(t for s in all_slices for t in s)
        assert combined == ALL_TITLES

    def test_uneven_split(self) -> None:
        titles = list(range(1, 6))  # 5 titles, 3 tasks
        task0 = partition_titles(0, 3, all_titles=titles)
        task1 = partition_titles(1, 3, all_titles=titles)
        task2 = partition_titles(2, 3, all_titles=titles)
        assert sorted(task0 + task1 + task2) == titles

    def test_invalid_task_count(self) -> None:
        with pytest.raises(ValueError, match="task_count"):
            partition_titles(0, 0)

    def test_invalid_task_index(self) -> None:
        with pytest.raises(ValueError, match="task_index"):
            partition_titles(5, 5)  # index 5 out of range [0, 5)

    def test_custom_all_titles(self) -> None:
        custom = [10, 17, 26]
        assert partition_titles(0, 3, all_titles=custom) == [10]
        assert partition_titles(1, 3, all_titles=custom) == [17]
        assert partition_titles(2, 3, all_titles=custom) == [26]


# ---------------------------------------------------------------------------
# Tests: ingest_titles_for_task
# ---------------------------------------------------------------------------


class TestIngestTitlesForTask:
    """Tests for the Cloud Run Job fan-out ingestion method."""

    @pytest.mark.asyncio
    async def test_task0_creates_revision_and_ingests(self) -> None:
        """Task 0 creates records and ingests its assigned title."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock()

        service = BootstrapService(session, downloader)

        with (
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
            patch("pipeline.olrc.bootstrap.partition_titles", return_value=[17]),
        ):
            result = await service.ingest_titles_for_task(
                "113-21", task_index=0, task_count=1
            )

        assert result.rp_identifier == "113-21"
        assert result.titles_processed == 1
        assert result.total_sections == 1
        # Task 0 must commit (to make revision visible)
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_task0_returns_early_when_already_ingested(self) -> None:
        """Task 0 returns early if revision is already INGESTED."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 42
        mock_rev.status = RevisionStatus.INGESTED.value

        call_count = 0

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = (
                mock_rp if call_count == 1 else mock_rev
            )
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)

        with patch("pipeline.olrc.bootstrap.partition_titles", return_value=[17]):
            result = await service.ingest_titles_for_task(
                "113-21", task_index=0, task_count=1
            )

        assert result.revision_id == 42
        assert result.titles_processed == 0
        downloader.download_title_at_release_point.assert_not_called()

    @pytest.mark.asyncio
    async def test_nonzero_task_waits_then_ingests(self) -> None:
        """Non-zero task polls for the revision record then ingests."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        mock_parser = _make_parser_mock(_make_parse_result(title_number=18))

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 7
        mock_rev.status = RevisionStatus.INGESTING.value

        worker_session = _make_mock_session()
        poll_call_count = 0

        def fake_worker_execute(_stmt):
            nonlocal poll_call_count
            poll_call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = (
                mock_rp if poll_call_count % 2 == 1 else mock_rev
            )
            return result

        worker_session.execute = AsyncMock(side_effect=fake_worker_execute)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def factory():
            yield worker_session

        service = BootstrapService(session, downloader, session_factory=factory)

        with (
            patch("pipeline.olrc.bootstrap.partition_titles", return_value=[18]),
            patch("pipeline.olrc.bootstrap.USLMParser", return_value=mock_parser),
            patch(
                "pipeline.olrc.bootstrap.normalize_parsed_section",
                side_effect=lambda s: s,
            ),
            patch("pipeline.olrc.bootstrap.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await service.ingest_titles_for_task(
                "113-21", task_index=1, task_count=2
            )

        assert result.titles_processed == 1
        assert result.revision_id == 7

    @pytest.mark.asyncio
    async def test_nonzero_task_raises_on_timeout(self) -> None:
        """Non-zero task raises TimeoutError if revision never appears."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        worker_session = _make_mock_session()
        never_found = MagicMock()
        never_found.scalar_one_or_none.return_value = None
        worker_session.execute = AsyncMock(return_value=never_found)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def factory():
            yield worker_session

        # poll_timeout=0.0 forces the while loop to exit immediately
        service = BootstrapService(
            session, downloader, session_factory=factory, poll_timeout=0.0
        )

        with (
            patch("pipeline.olrc.bootstrap.partition_titles", return_value=[18]),
            patch("pipeline.olrc.bootstrap.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError, match="113-21"),
        ):
            await service.ingest_titles_for_task("113-21", task_index=1, task_count=2)


# ---------------------------------------------------------------------------
# Tests: finalize_revision
# ---------------------------------------------------------------------------


class TestFinalizeRevision:
    """Tests for BootstrapService.finalize_revision."""

    @pytest.mark.asyncio
    async def test_marks_ingesting_as_ingested(self) -> None:
        """INGESTING revision is updated to INGESTED."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 99
        mock_rev.status = RevisionStatus.INGESTING.value

        call_count = 0

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = (
                mock_rp if call_count == 1 else mock_rev
            )
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)
        revision_id = await service.finalize_revision("113-21")

        assert revision_id == 99
        assert mock_rev.status == RevisionStatus.INGESTED.value
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_idempotent_when_already_ingested(self) -> None:
        """Already INGESTED revision does not error."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1
        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 99
        mock_rev.status = RevisionStatus.INGESTED.value

        call_count = 0

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = (
                mock_rp if call_count == 1 else mock_rev
            )
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)
        revision_id = await service.finalize_revision("113-21")

        assert revision_id == 99

    @pytest.mark.asyncio
    async def test_raises_when_no_revision(self) -> None:
        """ValueError raised if no revision exists."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader)
        with pytest.raises(ValueError, match="No revision found"):
            await service.finalize_revision("113-21")

    @pytest.mark.asyncio
    async def test_raises_when_failed(self) -> None:
        """ValueError raised if revision is in FAILED status."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 1
        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 5
        mock_rev.status = RevisionStatus.FAILED.value

        call_count = 0

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = (
                mock_rp if call_count == 1 else mock_rev
            )
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader)
        with pytest.raises(ValueError, match="FAILED"):
            await service.finalize_revision("113-21")


class TestFinalizeLatestIngesting:
    """Tests for BootstrapService.finalize_latest_ingesting (auto-detect)."""

    @pytest.mark.asyncio
    async def test_finds_and_marks_ingested(self) -> None:
        """Finds the INGESTING revision and marks it INGESTED."""
        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        session = _make_mock_session()
        downloader = _make_mock_downloader()

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.full_identifier = "113-21"
        mock_rp.release_point_id = 1

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 7
        mock_rev.status = RevisionStatus.INGESTING.value
        mock_rev.is_ground_truth = True

        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter([mock_rev, mock_rp]))

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row
        session.execute = AsyncMock(return_value=mock_result)

        service = BootstrapService(session, downloader)
        rp_id, rev_id = await service.finalize_latest_ingesting()

        assert rp_id == "113-21"
        assert rev_id == 7
        assert mock_rev.status == RevisionStatus.INGESTED.value
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_idempotent_when_already_ingested(self) -> None:
        """Returns without error when revision is already INGESTED (retry case)."""
        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        session = _make_mock_session()
        downloader = _make_mock_downloader()

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.full_identifier = "113-21"
        mock_rp.release_point_id = 1

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 7
        mock_rev.status = RevisionStatus.INGESTED.value
        mock_rev.is_ground_truth = True

        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter([mock_rev, mock_rp]))

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row
        session.execute = AsyncMock(return_value=mock_result)

        service = BootstrapService(session, downloader)
        rp_id, rev_id = await service.finalize_latest_ingesting()

        assert rp_id == "113-21"
        assert rev_id == 7
        # Status unchanged, no commit needed
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_none_found(self) -> None:
        """ValueError raised if no INGESTING revision exists."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = BootstrapService(session, downloader)
        with pytest.raises(ValueError, match="No bootstrap revision found"):
            await service.finalize_latest_ingesting()
