"""Tests for structure upsert methods (title, chapter, subchapter) (Task 1A.2)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.olrc.parser import (
    ParsedChapter,
    ParsedSection,
    ParsedSubchapter,
    ParsedTitle,
    USLMParseResult,
)


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _mock_not_found():
    """Return a mock result where scalar_one_or_none returns None."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    return mock_result


def _mock_found(record):
    """Return a mock result where scalar_one_or_none returns a record."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    return mock_result


class TestUpsertTitle:
    """Tests for _upsert_title method."""

    @pytest.mark.asyncio
    async def test_new_insert(self, mock_session) -> None:
        """Test inserting a new title when none exists."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=17,
            title_name="Copyrights",
            is_positive_law=True,
            positive_law_date="July 30, 1947",
        )
        title, was_created = await service._upsert_title(parsed)

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.title_number == 17
        assert added.title_name == "Copyrights"
        assert added.is_positive_law is True

    @pytest.mark.asyncio
    async def test_update_with_force(self, mock_session) -> None:
        """Test updating an existing title with force=True."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.title_name = "Old Name"
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=17,
            title_name="Copyrights",
            is_positive_law=True,
        )
        title, was_created = await service._upsert_title(parsed, force=True)

        assert was_created is False
        assert title is existing
        assert existing.title_name == "Copyrights"
        assert existing.is_positive_law is True
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_force(self, mock_session) -> None:
        """Test skipping update when force=False and record exists."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.title_name = "Old Name"
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=17,
            title_name="Copyrights",
        )
        title, was_created = await service._upsert_title(parsed, force=False)

        assert was_created is False
        assert title is existing
        assert existing.title_name == "Old Name"

    @pytest.mark.asyncio
    async def test_positive_law_with_parser_date(self, mock_session) -> None:
        """Test positive law title uses parser-provided date."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=17,
            title_name="Copyrights",
            is_positive_law=True,
            positive_law_date="July 30, 1947",
        )
        title, _ = await service._upsert_title(parsed)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_positive_law_fallback_date(self, mock_session) -> None:
        """Test positive law title falls back to hardcoded date when parser provides none."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=17,
            title_name="Copyrights",
            is_positive_law=True,
            positive_law_date=None,
        )
        title, _ = await service._upsert_title(parsed)

        added = mock_session.add.call_args[0][0]
        # Title 17 fallback date is 1947-07-30
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_non_positive_law(self, mock_session) -> None:
        """Test non-positive law title has no positive_law_date."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedTitle(
            title_number=42,
            title_name="The Public Health and Welfare",
            is_positive_law=False,
        )
        title, _ = await service._upsert_title(parsed)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date is None
        assert added.is_positive_law is False


class TestUpsertChapter:
    """Tests for _upsert_chapter method."""

    @pytest.mark.asyncio
    async def test_new_insert(self, mock_session) -> None:
        """Test inserting a new chapter."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedChapter(
            chapter_number="1",
            chapter_name="Subject Matter and Scope of Copyright",
            sort_order=1,
        )
        chapter, was_created = await service._upsert_chapter(parsed, title_id=1)

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.chapter_number == "1"
        assert added.chapter_name == "Subject Matter and Scope of Copyright"
        assert added.sort_order == 1
        assert added.title_id == 1

    @pytest.mark.asyncio
    async def test_update_with_force(self, mock_session) -> None:
        """Test updating an existing chapter with force=True."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.chapter_name = "Old Name"
        existing.sort_order = 0
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedChapter(
            chapter_number="1",
            chapter_name="New Name",
            sort_order=5,
        )
        chapter, was_created = await service._upsert_chapter(
            parsed, title_id=1, force=True
        )

        assert was_created is False
        assert chapter is existing
        assert existing.chapter_name == "New Name"
        assert existing.sort_order == 5
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_force(self, mock_session) -> None:
        """Test skipping update when force=False and record exists."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.chapter_name = "Old Name"
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedChapter(
            chapter_number="1",
            chapter_name="New Name",
        )
        chapter, was_created = await service._upsert_chapter(
            parsed, title_id=1, force=False
        )

        assert was_created is False
        assert chapter is existing
        assert existing.chapter_name == "Old Name"


class TestUpsertSubchapter:
    """Tests for _upsert_subchapter method."""

    @pytest.mark.asyncio
    async def test_new_insert(self, mock_session) -> None:
        """Test inserting a new subchapter."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        parsed = ParsedSubchapter(
            subchapter_number="I",
            subchapter_name="General Provisions",
            chapter_number="1",
            sort_order=1,
        )
        subchapter, was_created = await service._upsert_subchapter(
            parsed, chapter_id=10
        )

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.subchapter_number == "I"
        assert added.subchapter_name == "General Provisions"
        assert added.sort_order == 1
        assert added.chapter_id == 10

    @pytest.mark.asyncio
    async def test_update_with_force(self, mock_session) -> None:
        """Test updating an existing subchapter with force=True."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.subchapter_name = "Old Name"
        existing.sort_order = 0
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedSubchapter(
            subchapter_number="I",
            subchapter_name="New Name",
            chapter_number="1",
            sort_order=3,
        )
        subchapter, was_created = await service._upsert_subchapter(
            parsed, chapter_id=10, force=True
        )

        assert was_created is False
        assert subchapter is existing
        assert existing.subchapter_name == "New Name"
        assert existing.sort_order == 3
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_force(self, mock_session) -> None:
        """Test skipping update when force=False and record exists."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        existing = MagicMock()
        existing.subchapter_name = "Old Name"
        mock_session.execute.return_value = _mock_found(existing)

        service = USCodeIngestionService(mock_session)
        parsed = ParsedSubchapter(
            subchapter_number="I",
            subchapter_name="New Name",
            chapter_number="1",
        )
        subchapter, was_created = await service._upsert_subchapter(
            parsed, chapter_id=10, force=False
        )

        assert was_created is False
        assert subchapter is existing
        assert existing.subchapter_name == "Old Name"


class TestIngestParseResult:
    """Tests for _ingest_parse_result orchestration method."""

    @pytest.fixture
    def minimal_parse_result(self):
        """Create a minimal parse result with one of each entity."""
        return USLMParseResult(
            title=ParsedTitle(
                title_number=17,
                title_name="Copyrights",
                is_positive_law=True,
            ),
            chapters=[
                ParsedChapter(
                    chapter_number="1",
                    chapter_name="Subject Matter",
                    sort_order=1,
                ),
            ],
            subchapters=[
                ParsedSubchapter(
                    subchapter_number="I",
                    subchapter_name="General Provisions",
                    chapter_number="1",
                    sort_order=1,
                ),
            ],
            sections=[
                ParsedSection(
                    section_number="101",
                    heading="Definitions",
                    full_citation="17 U.S.C. § 101",
                    text_content="Definitions text...",
                    chapter_number="1",
                    subchapter_number="I",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(
        self, mock_session, minimal_parse_result
    ) -> None:
        """Test that all entities are ingested and stats are returned."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Each call to execute returns "not found" -> new inserts
        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        stats = await service._ingest_parse_result(minimal_parse_result)

        assert stats["chapters"] == 1
        assert stats["subchapters"] == 1
        assert stats["sections"] == 1
        # Title + chapter + subchapter + section = 4 created (section doesn't track)
        # Title (1 created) + chapter (1 created) + subchapter (1 created)
        assert stats["created"] >= 3

    @pytest.mark.asyncio
    async def test_missing_parent_chapter(self, mock_session) -> None:
        """Test that subchapters with missing parent chapters are skipped."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        parse_result = USLMParseResult(
            title=ParsedTitle(
                title_number=17,
                title_name="Copyrights",
            ),
            chapters=[],  # No chapters
            subchapters=[
                ParsedSubchapter(
                    subchapter_number="I",
                    subchapter_name="General Provisions",
                    chapter_number="99",  # Non-existent chapter
                ),
            ],
            sections=[],
        )

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        stats = await service._ingest_parse_result(parse_result)

        # Subchapter should be skipped because parent chapter doesn't exist
        assert stats["subchapters"] == 0

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_session) -> None:
        """Test ingestion with no chapters, subchapters, or sections."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        parse_result = USLMParseResult(
            title=ParsedTitle(
                title_number=17,
                title_name="Copyrights",
            ),
            chapters=[],
            subchapters=[],
            sections=[],
        )

        mock_session.execute.return_value = _mock_not_found()

        service = USCodeIngestionService(mock_session)
        stats = await service._ingest_parse_result(parse_result)

        assert stats["chapters"] == 0
        assert stats["subchapters"] == 0
        assert stats["sections"] == 0
        # Only the title was created
        assert stats["created"] == 1
        assert stats["updated"] == 0

    @pytest.mark.asyncio
    async def test_created_vs_updated_stats(self, mock_session) -> None:
        """Test that created/updated stats are tracked correctly."""
        from pipeline.olrc.ingestion import USCodeIngestionService

        # Title: existing (updated), Chapter: new (created)
        existing_title = MagicMock()
        existing_title.title_id = 1

        call_count = 0

        async def side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Title lookup -> found
                return _mock_found(existing_title)
            else:
                # Chapter, subchapter, section lookups -> not found
                return _mock_not_found()

        mock_session.execute = AsyncMock(side_effect=side_effect)

        parse_result = USLMParseResult(
            title=ParsedTitle(
                title_number=17,
                title_name="Copyrights",
            ),
            chapters=[
                ParsedChapter(
                    chapter_number="1",
                    chapter_name="Subject Matter",
                ),
            ],
            subchapters=[],
            sections=[],
        )

        service = USCodeIngestionService(mock_session)
        stats = await service._ingest_parse_result(parse_result, force=True)

        # Title existed -> updated, Chapter new -> created
        assert stats["updated"] == 1
        assert stats["created"] == 1
