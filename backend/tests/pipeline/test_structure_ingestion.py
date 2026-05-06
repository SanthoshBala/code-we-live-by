"""Tests for structure upsert methods (unified SectionGroup model)."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.us_code import SectionGroup
from pipeline.olrc.group_service import (
    _GROUP_NS,
    group_id_from_key,
    upsert_group,
    upsert_groups_from_parse_result,
)
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


def _mock_not_found() -> MagicMock:
    """Return a mock execute result with no matching row."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value = []
    return mock_result


def _mock_found(record: object) -> MagicMock:
    """Return a mock execute result containing one matching record."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = record
    mock_result.scalars.return_value = [record]
    return mock_result


# ---------------------------------------------------------------------------
# group_id_from_key
# ---------------------------------------------------------------------------


class TestGroupIdFromKey:
    """Tests for the deterministic UUID helper."""

    def test_same_key_same_uuid(self) -> None:
        assert group_id_from_key("title:17") == group_id_from_key("title:17")

    def test_different_keys_different_uuids(self) -> None:
        assert group_id_from_key("title:17") != group_id_from_key("title:18")

    def test_child_differs_from_parent(self) -> None:
        assert group_id_from_key("title:17") != group_id_from_key("title:17/chapter:1")

    def test_uses_project_namespace(self) -> None:
        expected = uuid.uuid5(_GROUP_NS, "title:17")
        assert group_id_from_key("title:17") == expected


# ---------------------------------------------------------------------------
# upsert_group
# ---------------------------------------------------------------------------


class TestUpsertGroup:
    """Tests for upsert_group function."""

    @pytest.mark.asyncio
    async def test_new_title_insert(self, mock_session: AsyncMock) -> None:
        """New title: session.add is called, was_created=True, group_id is a UUID."""
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
        assert added.group_id == group_id_from_key("title:17")

    @pytest.mark.asyncio
    async def test_new_group_does_not_flush(self, mock_session: AsyncMock) -> None:
        """UUID is pre-computed — no flush needed after insert."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            key="title:17",
        )
        await upsert_group(mock_session, parsed, parent_id=None)

        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_chapter_insert(self, mock_session: AsyncMock) -> None:
        """New chapter: parent_id is propagated as a UUID."""
        mock_session.execute.return_value = _mock_not_found()

        parent_uuid = group_id_from_key("title:17")
        parsed = ParsedGroup(
            group_type="chapter",
            number="1",
            name="Subject Matter and Scope of Copyright",
            sort_order=1,
            parent_key="title:17",
            key="title:17/chapter:1",
        )
        group, was_created = await upsert_group(mock_session, parsed, parent_id=parent_uuid)

        assert was_created is True
        added = mock_session.add.call_args[0][0]
        assert added.group_type == "chapter"
        assert added.number == "1"
        assert added.parent_id == parent_uuid
        assert added.group_id == group_id_from_key("title:17/chapter:1")

    @pytest.mark.asyncio
    async def test_new_subchapter_insert(self, mock_session: AsyncMock) -> None:
        """New subchapter: correct UUID and parent propagation."""
        mock_session.execute.return_value = _mock_not_found()

        parent_uuid = group_id_from_key("title:17/chapter:1")
        parsed = ParsedGroup(
            group_type="subchapter",
            number="I",
            name="General Provisions",
            sort_order=1,
            parent_key="title:17/chapter:1",
            key="title:17/chapter:1/subchapter:I",
        )
        group, was_created = await upsert_group(mock_session, parsed, parent_id=parent_uuid)

        assert was_created is True
        added = mock_session.add.call_args[0][0]
        assert added.group_type == "subchapter"
        assert added.number == "I"
        assert added.parent_id == parent_uuid

    @pytest.mark.asyncio
    async def test_update_with_force(self, mock_session: AsyncMock) -> None:
        """Existing group with force=True: record is updated in place."""
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
            mock_session, parsed, parent_id=group_id_from_key("title:17"), force=True
        )

        assert was_created is False
        assert group is existing
        assert existing.name == "New Name"
        assert existing.sort_order == 5
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_without_force(self, mock_session: AsyncMock) -> None:
        """Existing group with force=False: record is returned unchanged."""
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
            mock_session, parsed, parent_id=group_id_from_key("title:17"), force=False
        )

        assert was_created is False
        assert group is existing
        assert existing.name == "Old Name"

    @pytest.mark.asyncio
    async def test_positive_law_with_parser_date(self, mock_session: AsyncMock) -> None:
        """Positive-law title uses the date from the XML."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            positive_law_date="July 30, 1947",
            key="title:17",
        )
        await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_positive_law_fallback_date(self, mock_session: AsyncMock) -> None:
        """Positive-law title falls back to hardcoded date when XML omits it."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="17",
            name="Copyrights",
            is_positive_law=True,
            positive_law_date=None,
            key="title:17",
        )
        await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date == date(1947, 7, 30)

    @pytest.mark.asyncio
    async def test_non_positive_law(self, mock_session: AsyncMock) -> None:
        """Non-positive-law title has no positive_law_date."""
        mock_session.execute.return_value = _mock_not_found()

        parsed = ParsedGroup(
            group_type="title",
            number="42",
            name="The Public Health and Welfare",
            is_positive_law=False,
            key="title:42",
        )
        await upsert_group(mock_session, parsed, parent_id=None)

        added = mock_session.add.call_args[0][0]
        assert added.positive_law_date is None
        assert added.is_positive_law is False


# ---------------------------------------------------------------------------
# upsert_groups_from_parse_result
# ---------------------------------------------------------------------------


class TestIngestParseResult:
    """Tests for upsert_groups_from_parse_result bulk behaviour."""

    @pytest.fixture
    def minimal_parse_result(self) -> USLMParseResult:
        """Three-level hierarchy: title → chapter → subchapter."""
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
    async def test_bulk_insert_single_round_trip(
        self, mock_session: AsyncMock, minimal_parse_result: USLMParseResult
    ) -> None:
        """All groups are inserted in exactly one session.execute call."""
        await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_all_groups(
        self, mock_session: AsyncMock, minimal_parse_result: USLMParseResult
    ) -> None:
        """Lookup dict contains an entry for every group."""
        group_lookup = await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )
        assert len(group_lookup) == 3

    @pytest.mark.asyncio
    async def test_group_ids_are_deterministic_uuids(
        self, mock_session: AsyncMock, minimal_parse_result: USLMParseResult
    ) -> None:
        """Returned group_ids match what group_id_from_key() would compute."""
        group_lookup = await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )
        assert group_lookup["title:17"].group_id == group_id_from_key("title:17")
        assert group_lookup["title:17/chapter:1"].group_id == group_id_from_key(
            "title:17/chapter:1"
        )

    @pytest.mark.asyncio
    async def test_parent_ids_resolved_from_keys(
        self, mock_session: AsyncMock, minimal_parse_result: USLMParseResult
    ) -> None:
        """Child groups carry the parent's UUID as parent_id."""
        group_lookup = await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )
        chapter = group_lookup["title:17/chapter:1"]
        assert chapter.parent_id == group_id_from_key("title:17")

        subchapter = group_lookup["title:17/chapter:1/subchapter:I"]
        assert subchapter.parent_id == group_id_from_key("title:17/chapter:1")

    @pytest.mark.asyncio
    async def test_no_flush_called(
        self, mock_session: AsyncMock, minimal_parse_result: USLMParseResult
    ) -> None:
        """No flush is ever needed — UUIDs are pre-computed."""
        await upsert_groups_from_parse_result(
            mock_session, minimal_parse_result.groups
        )
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_session: AsyncMock) -> None:
        """Empty input returns an empty dict without touching the DB."""
        group_lookup = await upsert_groups_from_parse_result(mock_session, [])
        assert group_lookup == {}
        mock_session.execute.assert_not_called()
