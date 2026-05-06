"""Tests for structure upsert methods (unified SectionGroup model)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.olrc.group_service import upsert_group, upsert_groups_from_parse_result
from pipeline.olrc.parser import (
    ParsedGroup,
    ParsedSection,
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


class TestUpsertGroup:
    """Tests for upsert_group function."""

    @pytest.mark.asyncio
    async def test_new_title_insert(self, mock_session) -> None:
        """Test inserting a new title group when none exists."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            positive_law_date="July 30, 1947",
            key="title:17",
        )
        group, was_created = await upsert_group(mock_session, parsed, parent_id=None)

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.group_type == "title"
        assert added.number == "17"
        assert added.name == "Copyrights"
        assert added.is_positive_law is True

    @pytest.mark.asyncio
    async def test_new_chapter_insert(self, mock_session) -> None:
        """Test inserting a new chapter group."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="chapter",
            number="1",
            name="Subject Matter and Scope of Copyright",
            sort_order=1,
            parent_key="title:17",
            key="title:17/chapter:1",
        )
        group, was_created = await upsert_group(mock_session, parsed, parent_id=100)

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.group_type == "chapter"
        assert added.number == "1"
        assert added.name == "Subject Matter and Scope of Copyright"
        assert added.sort_order == 1
        assert added.parent_id == 100

    @pytest.mark.asyncio
    async def test_new_subchapter_insert(self, mock_session) -> None:
        """Test inserting a new subchapter group."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="subchapter",
            number="I",
            name="General Provisions",
            sort_order=1,
            parent_key="title:17/chapter:1",
            key="title:17/chapter:1/subchapter:I",
        )
        group, was_created = await upsert_group(mock_session, parsed, parent_id=200)

        assert was_created is True
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.group_type == "subchapter"
        assert added.number == "I"
        assert added.parent_id == 200

    @pytest.mark.asyncio
    async def test_update_with_force(self, mock_session) -> None:
        """Test updating an existing group with force=True."""
        existing = MagicMock()
        existing.name = "Old Name"
        existing.sort_order = 0
        mock_session.execute.return_value = _mock_found(existing)

        parsed = ParsedGroup(
            group_type="chapter",
            number="1",
            name="New Name",
            sort_order=5,
            parent_key="title:17",
            key="title:17/chapter:1",
        )
        group, was_created = await upsert_group(
            mock_session, parsed, parent_id=100, force=True
        )

        assert was_created is False
        assert group is existing
        assert existing.name == "New Name"
        assert existing.sort_order == 5
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_force(self, mock_session) -> None:
        """Test skipping update when force=False and record exists."""
        existing = MagicMock()
        existing.name = "Old Name"
        mock_session.execute.return_value = _mock_found(existing)

        parsed = ParsedGroup(
            group_type="chapter",
            number="1",
            name="New Name",
            parent_key="title:17",
            key="title:17/chapter:1",
        )
        group, was_created = await upsert_group(
            mock_session, parsed, parent_id=100, force=False
        )

        assert was_created is False
        assert group is existing
        assert existing.name == "Old Name"

    @pytest.mark.asyncio
    async def test_positive_law_with_parser_date(self, mock_session) -> None:
        """Test positive law title uses parser-provided date."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            positive_law_date="July 30, 1947",
            key="title:17",
        )
        group, _ = await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_positive_law_fallback_date(self, mock_session) -> None:
        """Test positive law title falls back to hardcoded date when parser provides none."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            positive_law_date=None,
            key="title:17",
        )
        group, _ = await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        # Title 17 fallback date is 1947-07-30
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_non_positive_law(self, mock_session) -> None:
        """Test non-positive law title has no positive_law_date."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="42",
            name="The Public Health and Welfare",
            is_positive_law=False,
            key="title:42",
        )
        group, _ = await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date is None
        assert added.is_positive_law is False


class TestIngestParseResult:
    """Tests for _ingest_parse_result orchestration via upsert_groups_from_parse_result."""

    @pytest.fixture
    def minimal_parse_result(self):
        """Create a minimal parse result with one of each entity."""
        title_group = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            key="title:17",
        )
        chapter_group = ParsedGroup(
            group_type="chapter",
            number="1",
            name="Subject Matter",
            sort_order=1,
            parent_key="title:17",
            key="title:17/chapter:1",
        )
        subchapter_group = ParsedGroup(
            group_type="subchapter",
            number="I",
            name="General Provisions",
            sort_order=1,
            parent_key="title:17/chapter:1",
            key="title:17/chapter:1/subchapter:I",
        )
        return USLMParseResult(
            title=title_group,
            groups=[title_group, chapter_group, subchapter_group],
            sections=[
                ParsedSection(
                    section_number="101",
                    heading="Definitions",
                    full_citation="17 U.S.C. § 101",
                    text_content="Definitions text...",
                    parent_group_key="title:17/chapter:1/subchapter:I",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(
        self, mock_session, minimal_parse_result
    ) -> None:
        """Test that all groups are upserted."""
        mock_session.execute.return_value = _mock_not_found()

        group_lookup = await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )

        # 3 groups (title + chapter + subchapter)
        assert len(group_lookup) == 3

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_session) -> None:
        """Test upsert with no groups."""
        group_lookup = await upsert_groups_from_parse_result(mock_session, [])

        assert len(group_lookup) == 0

    @pytest.mark.asyncio
    async def test_created_vs_updated_stats(self, mock_session) -> None:
        """Test that existing groups are returned without re-adding."""
        existing_title = MagicMock()
        existing_title.group_id = 1

        call_count = 0

        async def side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_found(existing_title)
            else:
                return _mock_not_found()

        mock_session.execute = AsyncMock(side_effect=side_effect)

        title_group = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            key="title:17",
        )
        chapter_group = ParsedGroup(
            group_type="chapter",
            number="1",
            name="Subject Matter",
            parent_key="title:17",
            key="title:17/chapter:1",
        )

        group_lookup = await upsert_groups_from_parse_result(
            mock_session, [title_group, chapter_group], force=True
        )

        assert len(group_lookup) == 2
        # Title was existing, chapter was new
        assert group_lookup["title:17"] is existing_title
