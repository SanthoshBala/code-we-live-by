"""Tests for pipeline.chrono.revision_builder — mocked DB tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ChangeType
from app.models.public_law import LawChange
from app.models.revision import CodeRevision
from app.models.snapshot import SectionSnapshot
from pipeline.chrono.revision_builder import RevisionBuilder
from pipeline.olrc.snapshot_service import SectionState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_law(
    law_id: int = 1,
    congress: int = 115,
    law_number: str = "97",
    enacted_date: date | None = None,
) -> MagicMock:
    """Create a minimal mock PublicLaw."""
    law = MagicMock()
    law.law_id = law_id
    law.congress = congress
    law.law_number = law_number
    law.enacted_date = enacted_date or date(2017, 12, 22)
    law.official_title = None
    law.short_title = "Tax Cuts and Jobs Act"
    return law


def _make_change(
    change_id: int = 1,
    law_id: int = 1,
    change_type: ChangeType = ChangeType.MODIFY,
    old_text: str | None = "5 percent",
    new_text: str | None = "10 percent",
    title_number: int = 26,
    section_number: str = "401",
    description: str | None = "substituted '10 percent' for '5 percent'",
) -> MagicMock:
    """Create a minimal mock LawChange with natural keys."""
    change = MagicMock(spec=LawChange)
    change.change_id = change_id
    change.law_id = law_id
    change.change_type = change_type
    change.old_text = old_text
    change.new_text = new_text
    change.description = description
    change.title_number = title_number
    change.section_number = section_number
    return change


def _make_parent_state(
    title_number: int = 26,
    section_number: str = "401",
    text_content: str = "The rate shall be 5 percent of the amount.",
    heading: str = "Test heading",
) -> SectionState:
    """Create a SectionState representing parent revision state."""
    return SectionState(
        title_number=title_number,
        section_number=section_number,
        heading=heading,
        text_content=text_content,
        text_hash="abc123",
        normalized_provisions=None,
        notes=None,
        normalized_notes=None,
        notes_hash=None,
        full_citation=f"{title_number} USC {section_number}",
        snapshot_id=1,
        revision_id=1,
        is_deleted=False,
    )


def _make_mock_session(
    existing_revision: CodeRevision | None = None,
    changes: list | None = None,
) -> AsyncMock:
    """Create a mock AsyncSession.

    Args:
        existing_revision: If set, the first execute returns this (idempotency).
        changes: LawChange mocks to return from the second execute.
    """
    session = AsyncMock()
    added_objects: list = []

    def track_add(obj: object) -> None:
        added_objects.append(obj)
        # Simulate DB assigning an ID on add
        if isinstance(obj, CodeRevision) and obj.revision_id is None:
            obj.revision_id = 100

    session.add = MagicMock(side_effect=track_add)

    call_count = 0

    def fake_execute(_stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Idempotency check
            result.scalar_one_or_none.return_value = existing_revision
        elif call_count == 2:
            # LawChange fetch
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = changes or []
            result.scalars.return_value = scalars_mock
        else:
            result.scalar_one_or_none.return_value = None
        return result

    session.execute = AsyncMock(side_effect=fake_execute)
    session.flush = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRevisionBuilder:
    """Tests for RevisionBuilder.build_revision."""

    @pytest.mark.asyncio
    async def test_build_single_modify(self) -> None:
        """One MODIFY change produces snapshot with updated text."""
        change = _make_change()
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.law_id == 1
        assert result.sections_applied == 1
        assert result.sections_failed == 0

        # Check a snapshot was added
        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        assert "10 percent" in snapshots[0].text_content
        assert snapshots[0].is_deleted is False

    @pytest.mark.asyncio
    async def test_build_multiple_changes_same_section(self) -> None:
        """Sequential application: each change operates on result of previous."""
        change1 = _make_change(
            change_id=1,
            old_text="5 percent",
            new_text="10 percent",
        )
        change2 = _make_change(
            change_id=2,
            old_text="the amount",
            new_text="the total",
            description="substituted 'the total' for 'the amount'",
        )
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change1, change2])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.sections_applied == 2

        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        assert "10 percent" in snapshots[0].text_content
        assert "the total" in snapshots[0].text_content

    @pytest.mark.asyncio
    async def test_build_add_new_section(self) -> None:
        """ADD for a missing section creates snapshot with new text."""
        change = _make_change(
            change_type=ChangeType.ADD,
            old_text=None,
            new_text="(a) New section text.",
            section_number="401A",
        )
        session = _make_mock_session(changes=[change])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=None,  # No parent state — new section
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.sections_added == 1

        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        assert snapshots[0].text_content == "(a) New section text."

    @pytest.mark.asyncio
    async def test_build_repeal(self) -> None:
        """REPEAL creates snapshot with is_deleted=True."""
        change = _make_change(
            change_type=ChangeType.REPEAL,
            old_text=None,
            new_text=None,
        )
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.sections_repealed == 1

        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        assert snapshots[0].is_deleted is True

    @pytest.mark.asyncio
    async def test_build_redesignate_skipped(self) -> None:
        """REDESIGNATE produces no snapshot, counted as skipped."""
        change = _make_change(
            change_type=ChangeType.REDESIGNATE,
            old_text=None,
            new_text=None,
        )
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.sections_skipped == 1

        # No snapshots created (only the revision itself is added)
        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_build_idempotent(self) -> None:
        """Existing law revision returns early without creating new objects."""
        existing_rev = MagicMock(spec=CodeRevision)
        existing_rev.revision_id = 99
        existing_rev.sequence_number = 5

        session = _make_mock_session(existing_revision=existing_rev)
        law = _make_law()

        builder = RevisionBuilder(session)
        result = await builder.build_revision(
            law, parent_revision_id=1, sequence_number=2
        )

        assert result.revision_id == 99
        # No new objects added
        assert session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_build_failed_change_continues(self) -> None:
        """Failed application doesn't abort — continues to next change."""
        change1 = _make_change(
            change_id=1,
            old_text="nonexistent phrase",
            new_text="replacement",
        )
        change2 = _make_change(
            change_id=2,
            old_text="5 percent",
            new_text="10 percent",
        )
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change1, change2])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            result = await builder.build_revision(
                law, parent_revision_id=1, sequence_number=2
            )

        assert result.sections_failed == 1
        assert result.sections_applied == 1

        # Snapshot should still be created (partial application)
        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        assert "10 percent" in snapshots[0].text_content

    @pytest.mark.asyncio
    async def test_hashes_recomputed(self) -> None:
        """text_hash and notes_hash are updated on the new snapshot."""
        change = _make_change()
        parent_state = _make_parent_state()
        session = _make_mock_session(changes=[change])
        law = _make_law()

        builder = RevisionBuilder(session)

        with patch.object(
            builder.snapshot_service,
            "get_section_at_revision",
            new_callable=AsyncMock,
            return_value=parent_state,
        ):
            await builder.build_revision(law, parent_revision_id=1, sequence_number=2)

        added_objects = [call.args[0] for call in session.add.call_args_list]
        snapshots = [o for o in added_objects if isinstance(o, SectionSnapshot)]
        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Hashes should be non-None and different from parent
        assert snapshot.text_hash is not None
        assert snapshot.text_hash != "abc123"  # Different from parent
        assert snapshot.notes_hash is not None
