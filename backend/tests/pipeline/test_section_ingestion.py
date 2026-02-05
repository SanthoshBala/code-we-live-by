"""Tests for section ingestion with normalized data (Task 1A.1)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.olrc.ingestion import _parse_citation_date


class TestParseCitationDate:
    """Tests for the _parse_citation_date helper function."""

    def test_parse_citation_date_iso_format(self) -> None:
        """Test parsing ISO format dates (YYYY-MM-DD)."""
        assert _parse_citation_date("1935-08-14") == date(1935, 8, 14)
        assert _parse_citation_date("1976-10-19") == date(1976, 10, 19)
        assert _parse_citation_date("2023-01-01") == date(2023, 1, 1)

    def test_parse_citation_date_prose_format(self) -> None:
        """Test parsing prose format dates (e.g., 'Oct. 19, 1976')."""
        assert _parse_citation_date("Oct. 19, 1976") == date(1976, 10, 19)
        assert _parse_citation_date("July 3, 1990") == date(1990, 7, 3)
        assert _parse_citation_date("Jan 1, 2023") == date(2023, 1, 1)
        assert _parse_citation_date("December 25, 2000") == date(2000, 12, 25)

    def test_parse_citation_date_abbreviated_months(self) -> None:
        """Test parsing dates with abbreviated month names."""
        assert _parse_citation_date("Jan. 15, 2020") == date(2020, 1, 15)
        assert _parse_citation_date("Feb. 28, 2021") == date(2021, 2, 28)
        assert _parse_citation_date("Sept. 11, 2001") == date(2001, 9, 11)
        assert _parse_citation_date("Aug. 14, 1935") == date(1935, 8, 14)

    def test_parse_citation_date_none_input(self) -> None:
        """Test that None input returns None."""
        assert _parse_citation_date(None) is None

    def test_parse_citation_date_empty_string(self) -> None:
        """Test that empty string returns None."""
        assert _parse_citation_date("") is None

    def test_parse_citation_date_invalid_format(self) -> None:
        """Test that invalid formats return None."""
        assert _parse_citation_date("not a date") is None
        assert _parse_citation_date("19-10-1976") is None  # Wrong ISO format
        assert _parse_citation_date("1976") is None  # Year only

    def test_parse_citation_date_invalid_date_values(self) -> None:
        """Test that invalid date values return None."""
        # Invalid month
        assert _parse_citation_date("2021-13-01") is None
        # Invalid day
        assert _parse_citation_date("2021-02-30") is None


class TestUpsertSectionNormalization:
    """Tests for _upsert_section storing normalized data.

    These tests verify that the section ingestion correctly:
    1. Stores normalized_text in text_content
    2. Stores section_notes as JSON in normalized_notes
    3. Extracts enacted_date from first citation
    4. Extracts statutes_at_large_citation from first citation
    """

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def sample_parsed_section(self):
        """Create a sample ParsedSection with subsections and citations."""
        from pipeline.olrc.parser import (
            ParsedSection,
            ParsedSubsection,
            SourceCreditRef,
        )

        return ParsedSection(
            section_number="106",
            heading="Exclusive rights in copyrighted works",
            full_citation="17 U.S.C. § 106",
            text_content="Subject to sections 107 through 122...",
            subsections=[
                ParsedSubsection(
                    marker="(1)",
                    heading=None,
                    content="to reproduce the copyrighted work in copies",
                    children=[],
                ),
                ParsedSubsection(
                    marker="(2)",
                    heading=None,
                    content="to prepare derivative works based upon the copyrighted work",
                    children=[],
                ),
            ],
            source_credit_refs=[
                SourceCreditRef(
                    congress=94,
                    law_number=553,
                    division=None,
                    title="I",
                    section="106",
                    date="Oct. 19, 1976",
                    stat_volume=90,
                    stat_page=2546,
                    raw_text="Pub. L. 94–553, title I, § 106, Oct. 19, 1976, 90 Stat. 2546",
                ),
            ],
            notes="(Pub. L. 94–553, title I, § 106, Oct. 19, 1976, 90 Stat. 2546)",
        )

    @pytest.mark.asyncio
    async def test_upsert_section_stores_normalized_text(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that normalized_text is stored in text_content."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify the section was added
        mock_session.add.assert_called_once()
        added_section = mock_session.add.call_args[0][0]

        # Verify text_content contains normalized output (with indentation)
        assert added_section.text_content is not None
        # The normalized text should have markers like "(1)" and "(2)"
        assert "(1)" in added_section.text_content
        assert "(2)" in added_section.text_content

    @pytest.mark.asyncio
    async def test_upsert_section_stores_normalized_notes_json(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that section_notes is stored as JSON in normalized_notes."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify the section was added with normalized_notes
        added_section = mock_session.add.call_args[0][0]
        assert added_section.normalized_notes is not None
        assert isinstance(added_section.normalized_notes, dict)

        # Verify citations are in the JSON
        assert "citations" in added_section.normalized_notes
        citations = added_section.normalized_notes["citations"]
        assert len(citations) > 0

        # Verify first citation has expected structure
        first_citation = citations[0]
        assert "law" in first_citation
        assert first_citation["law"]["congress"] == 94
        assert first_citation["law"]["law_number"] == 553

    @pytest.mark.asyncio
    async def test_upsert_section_extracts_enacted_date(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that enacted_date is extracted from first citation."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify enacted_date is set
        added_section = mock_session.add.call_args[0][0]
        assert added_section.enacted_date is not None
        assert added_section.enacted_date == date(1976, 10, 19)

    @pytest.mark.asyncio
    async def test_upsert_section_extracts_statutes_citation(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that statutes_at_large_citation is extracted from first citation."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify statutes_at_large_citation is set
        added_section = mock_session.add.call_args[0][0]
        assert added_section.statutes_at_large_citation is not None
        assert added_section.statutes_at_large_citation == "90 Stat. 2546"

    @pytest.mark.asyncio
    async def test_upsert_section_updates_existing_with_force(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that existing section is updated when force=True."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock an existing section
        existing_section = MagicMock()
        existing_section.heading = "Old heading"
        existing_section.text_content = "Old content"
        existing_section.normalized_notes = None
        existing_section.enacted_date = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_section
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        result = await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=True,
        )

        # Verify the existing section was updated
        assert result is existing_section
        assert existing_section.heading == sample_parsed_section.heading
        assert existing_section.normalized_notes is not None
        assert existing_section.enacted_date == date(1976, 10, 19)

    @pytest.mark.asyncio
    async def test_upsert_section_skips_update_without_force(
        self, mock_session, sample_parsed_section
    ) -> None:
        """Test that existing section is not updated when force=False."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock an existing section
        existing_section = MagicMock()
        existing_section.heading = "Old heading"
        existing_section.text_content = "Old content"
        existing_section.normalized_notes = None
        existing_section.enacted_date = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_section
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        result = await service._upsert_section(
            sample_parsed_section,
            title_id=1,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify the existing section was returned unchanged
        assert result is existing_section
        assert existing_section.heading == "Old heading"
        assert existing_section.normalized_notes is None


class TestUpsertSectionWithActRefs:
    """Tests for _upsert_section with Act references (pre-1957 laws)."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def parsed_section_with_act(self):
        """Create a ParsedSection with Act references (pre-1957)."""
        from pipeline.olrc.parser import ActRef, ParsedSection

        return ParsedSection(
            section_number="80a-3a",
            heading="Definitions",
            full_citation="15 U.S.C. § 80a-3a",
            text_content="Definitions for investment companies...",
            subsections=[],
            act_refs=[
                ActRef(
                    date="1935-08-14",
                    chapter=687,
                    title="I",
                    section="3(a)",
                    stat_volume=49,
                    stat_page=477,
                    raw_text="Aug. 14, 1935, ch. 687, title I, § 3(a), 49 Stat. 477",
                ),
            ],
            notes="(Aug. 14, 1935, ch. 687, title I, § 3(a), 49 Stat. 477)",
        )

    @pytest.mark.asyncio
    async def test_upsert_section_with_act_extracts_date(
        self, mock_session, parsed_section_with_act
    ) -> None:
        """Test that enacted_date is extracted from Act reference."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            parsed_section_with_act,
            title_id=15,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify enacted_date is set from the Act
        added_section = mock_session.add.call_args[0][0]
        assert added_section.enacted_date == date(1935, 8, 14)

    @pytest.mark.asyncio
    async def test_upsert_section_with_act_extracts_statutes_citation(
        self, mock_session, parsed_section_with_act
    ) -> None:
        """Test that statutes_at_large_citation is extracted from Act reference."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Mock that no existing section is found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = USCodeIngestionService(mock_session)
        await service._upsert_section(
            parsed_section_with_act,
            title_id=15,
            chapter_id=1,
            subchapter_id=None,
            force=False,
        )

        # Verify statutes_at_large_citation is set
        added_section = mock_session.add.call_args[0][0]
        assert added_section.statutes_at_large_citation == "49 Stat. 477"
