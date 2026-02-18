"""Tests for the bootstrap service (Task 1.19)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import RevisionStatus, RevisionType
from pipeline.olrc.bootstrap import BootstrapResult, BootstrapService
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


def _make_mock_downloader(
    xml_path: Path | None = Path("/fake/title17.xml"),
) -> MagicMock:
    """Create a mock OLRCDownloader."""
    downloader = MagicMock()
    downloader.download_title_at_release_point = AsyncMock(return_value=xml_path)
    return downloader


def _make_mock_parser(parse_result: USLMParseResult | None = None) -> MagicMock:
    """Create a mock USLMParser."""
    parser = MagicMock()
    parser.parse_file.return_value = parse_result or _make_parse_result()
    return parser


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
        parser = _make_mock_parser()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        # revision_id is None with mock session (no DB to assign PK)
        assert result.rp_identifier == "113-21"
        assert result.titles_processed == 1
        assert result.total_sections == 1

        # Verify session.add was called with OLRCReleasePoint and CodeRevision
        add_calls = session.add.call_args_list
        # Should have at least: release_point, revision, snapshot(s)
        assert len(add_calls) >= 3

        # Check the revision object was added
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
        parser = _make_mock_parser(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        assert result.total_sections == 2

        # Check snapshot objects were added
        add_calls = session.add.call_args_list
        added_objects = [call.args[0] for call in add_calls]

        from app.models.snapshot import SectionSnapshot

        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 2
        assert snapshots[0].section_number == "101"
        assert snapshots[1].section_number == "102"
        assert snapshots[0].title_number == 17
        assert snapshots[1].title_number == 17

    @pytest.mark.asyncio
    async def test_skip_unavailable_titles(self) -> None:
        """Title download returns None -> skipped, no error."""
        session = _make_mock_session()
        downloader = _make_mock_downloader(xml_path=None)
        parser = _make_mock_parser()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            result = await service.create_initial_commit("113-21", titles=[99])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0
        assert result.total_sections == 0

    @pytest.mark.asyncio
    async def test_idempotent_completed(self) -> None:
        """If revision already ingested, returns early."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

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

        service = BootstrapService(session, downloader, parser)
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
        parser = _make_mock_parser()

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

        def fake_execute(_stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_rp
            elif call_count == 2:
                result.scalar_one_or_none.return_value = mock_rev
            else:
                # For _ingest_title idempotency check
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
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
        parser = _make_mock_parser(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            await service.create_initial_commit("113-21", titles=[17])

        # Find the snapshot that was added
        from app.models.snapshot import SectionSnapshot

        added = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], SectionSnapshot)
        ]
        assert len(added) == 1
        assert added[0].text_hash == expected_hash

    @pytest.mark.asyncio
    async def test_snapshot_notes_hash(self) -> None:
        """Verify notes hash is computed when notes are present."""
        notes = "(Pub. L. 94-553, title I, Oct. 19, 1976, 90 Stat. 2546)"
        expected_hash = hashlib.sha256(notes.encode("utf-8")).hexdigest()

        session = _make_mock_session()
        sections = [_make_parsed_section(notes=notes)]
        parser = _make_mock_parser(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            await service.create_initial_commit("113-21", titles=[17])

        from app.models.snapshot import SectionSnapshot

        added = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], SectionSnapshot)
        ]
        assert len(added) == 1
        assert added[0].notes_hash == expected_hash
        assert added[0].notes == notes

    @pytest.mark.asyncio
    async def test_snapshot_no_notes_hash_when_none(self) -> None:
        """Verify notes_hash is None when notes are absent."""
        session = _make_mock_session()
        sections = [_make_parsed_section(notes=None)]
        parser = _make_mock_parser(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            await service.create_initial_commit("113-21", titles=[17])

        from app.models.snapshot import SectionSnapshot

        added = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], SectionSnapshot)
        ]
        assert len(added) == 1
        assert added[0].notes_hash is None

    @pytest.mark.asyncio
    async def test_snapshot_full_citation(self) -> None:
        """Verify full_citation is preserved on snapshot."""
        session = _make_mock_session()
        sections = [_make_parsed_section(full_citation="17 U.S.C. § 101")]
        parser = _make_mock_parser(_make_parse_result(sections=sections))
        downloader = _make_mock_downloader()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            await service.create_initial_commit("113-21", titles=[17])

        from app.models.snapshot import SectionSnapshot

        added = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], SectionSnapshot)
        ]
        assert len(added) == 1
        assert added[0].full_citation == "17 U.S.C. § 101"
        assert added[0].is_deleted is False

    @pytest.mark.asyncio
    async def test_download_failure_skips_title(self) -> None:
        """Download raising an exception should skip the title, not fail."""
        session = _make_mock_session()
        downloader = MagicMock()
        downloader.download_title_at_release_point = AsyncMock(
            side_effect=Exception("Network error")
        )
        parser = _make_mock_parser()

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0

    @pytest.mark.asyncio
    async def test_parse_failure_skips_title(self) -> None:
        """Parser raising an exception should skip the title, not fail."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = MagicMock()
        parser.parse_file.side_effect = Exception("Parse error")

        service = BootstrapService(session, downloader, parser)

        with patch(
            "pipeline.olrc.bootstrap.normalize_parsed_section",
            side_effect=lambda s: s,
        ):
            result = await service.create_initial_commit("113-21", titles=[17])

        assert result.titles_skipped == 1
        assert result.titles_processed == 0
