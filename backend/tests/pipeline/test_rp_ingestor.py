"""Tests for the RP ingestor (Task 1.20)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import RevisionStatus, RevisionType
from pipeline.olrc.parser import ParsedGroup, ParsedSection, USLMParseResult
from pipeline.olrc.rp_ingestor import RPIngestor, RPIngestResult

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
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
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


def _make_mock_diff_result() -> MagicMock:
    """Create a mock RevisionDiffResult."""
    from pipeline.olrc.diff_engine import RevisionDiffResult

    return RevisionDiffResult(
        before_revision_id=1,
        after_revision_id=2,
        sections_added=1,
        sections_modified=0,
        sections_deleted=0,
        sections_unchanged=0,
        diffs=[],
        elapsed_seconds=0.1,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRPIngestResult:
    """Tests for the RPIngestResult dataclass."""

    def test_creation(self) -> None:
        result = RPIngestResult(
            revision_id=2,
            rp_identifier="113-37",
            parent_revision_id=1,
            titles_processed=3,
            titles_skipped=1,
            total_sections=100,
            diff_summary=None,
            elapsed_seconds=5.2,
        )
        assert result.revision_id == 2
        assert result.rp_identifier == "113-37"
        assert result.parent_revision_id == 1
        assert result.titles_processed == 3


class TestRPIngestor:
    """Tests for RPIngestor.ingest_release_point."""

    @pytest.mark.asyncio
    async def test_ingest_creates_revision_with_parent(self) -> None:
        """Verify CodeRevision is created with parent link and sequence_number."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

        ingestor = RPIngestor(session, downloader, parser)

        with (
            patch(
                "pipeline.olrc.rp_ingestor.ingest_title",
                new_callable=AsyncMock,
                return_value=5,
            ),
            patch(
                "pipeline.olrc.rp_ingestor.RevisionDiffEngine",
            ) as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            mock_engine.diff = AsyncMock(return_value=_make_mock_diff_result())
            mock_engine_cls.return_value = mock_engine

            result = await ingestor.ingest_release_point(
                "113-37",
                parent_revision_id=1,
                sequence_number=1,
                titles=[17],
            )

        assert result.rp_identifier == "113-37"
        assert result.parent_revision_id == 1
        assert result.titles_processed == 1

        # Verify revision was created with parent link
        from app.models.revision import CodeRevision

        added_objects = [call.args[0] for call in session.add.call_args_list]
        revisions = [o for o in added_objects if isinstance(o, CodeRevision)]
        assert len(revisions) == 1
        rev = revisions[0]
        assert rev.parent_revision_id == 1
        assert rev.sequence_number == 1
        assert rev.revision_type == RevisionType.RELEASE_POINT.value
        assert rev.is_ground_truth is True

    @pytest.mark.asyncio
    async def test_ingest_creates_snapshots(self) -> None:
        """Parsed sections become snapshots via ingest_title."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

        ingestor = RPIngestor(session, downloader, parser)

        with (
            patch(
                "pipeline.olrc.rp_ingestor.ingest_title",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_ingest,
            patch(
                "pipeline.olrc.rp_ingestor.RevisionDiffEngine",
            ) as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            mock_engine.diff = AsyncMock(return_value=_make_mock_diff_result())
            mock_engine_cls.return_value = mock_engine

            result = await ingestor.ingest_release_point(
                "113-37",
                parent_revision_id=1,
                sequence_number=1,
                titles=[17],
            )

        assert result.total_sections == 3
        mock_ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_runs_diff(self) -> None:
        """Diff engine should be called after ingestion."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

        ingestor = RPIngestor(session, downloader, parser)

        with (
            patch(
                "pipeline.olrc.rp_ingestor.ingest_title",
                new_callable=AsyncMock,
                return_value=1,
            ),
            patch(
                "pipeline.olrc.rp_ingestor.RevisionDiffEngine",
            ) as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            diff_result = _make_mock_diff_result()
            mock_engine.diff = AsyncMock(return_value=diff_result)
            mock_engine_cls.return_value = mock_engine

            result = await ingestor.ingest_release_point(
                "113-37",
                parent_revision_id=1,
                sequence_number=1,
                titles=[17],
            )

        assert result.diff_summary is not None
        assert result.diff_summary.sections_added == 1
        mock_engine.diff.assert_called_once()

    @pytest.mark.asyncio
    async def test_idempotent_completed(self) -> None:
        """Already-ingested RP returns early without re-processing."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 2
        mock_rp.full_identifier = "113-37"

        mock_rev = MagicMock(spec=CodeRevision)
        mock_rev.revision_id = 42
        mock_rev.status = RevisionStatus.INGESTED.value

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

        ingestor = RPIngestor(session, downloader, parser)
        result = await ingestor.ingest_release_point(
            "113-37",
            parent_revision_id=1,
            sequence_number=1,
            titles=[17],
        )

        assert result.revision_id == 42
        assert result.titles_processed == 0
        assert result.diff_summary is None
        downloader.download_title_at_release_point.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent_resume_failed(self) -> None:
        """Failed status resumes ingestion."""
        session = _make_mock_session()
        downloader = _make_mock_downloader()
        parser = _make_mock_parser()

        from app.models.release_point import OLRCReleasePoint
        from app.models.revision import CodeRevision

        mock_rp = MagicMock(spec=OLRCReleasePoint)
        mock_rp.release_point_id = 2
        mock_rp.full_identifier = "113-37"
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
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = AsyncMock(side_effect=fake_execute)

        ingestor = RPIngestor(session, downloader, parser)

        with (
            patch(
                "pipeline.olrc.rp_ingestor.ingest_title",
                new_callable=AsyncMock,
                return_value=5,
            ),
            patch(
                "pipeline.olrc.rp_ingestor.RevisionDiffEngine",
            ) as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            mock_engine.diff = AsyncMock(return_value=_make_mock_diff_result())
            mock_engine_cls.return_value = mock_engine

            result = await ingestor.ingest_release_point(
                "113-37",
                parent_revision_id=1,
                sequence_number=1,
                titles=[17],
            )

        # Should proceed with ingestion
        assert result.revision_id == 42
        assert result.titles_processed == 1
        assert result.diff_summary is not None
