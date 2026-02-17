"""Tests for the snapshot query service."""

from unittest.mock import MagicMock

from pipeline.olrc.snapshot_service import SectionState, SnapshotService


class TestSectionState:
    """Tests for the SectionState dataclass."""

    def test_creation(self) -> None:
        state = SectionState(
            title_number=17,
            section_number="106",
            heading="Exclusive rights in copyrighted works",
            text_content="The owner of copyright...",
            text_hash="abc123",
            normalized_provisions={"type": "section"},
            full_citation="17 USC 106",
            snapshot_id=1,
            revision_id=1,
            is_deleted=False,
        )
        assert state.title_number == 17
        assert state.section_number == "106"
        assert not state.is_deleted

    def test_deleted_state(self) -> None:
        state = SectionState(
            title_number=17,
            section_number="106",
            heading=None,
            text_content=None,
            text_hash=None,
            normalized_provisions=None,
            full_citation="17 USC 106",
            snapshot_id=1,
            revision_id=1,
            is_deleted=True,
        )
        assert state.is_deleted


class TestSnapshotServiceHelpers:
    """Tests for SnapshotService static methods."""

    def test_snapshot_to_state(self) -> None:
        """Test converting a mock snapshot ORM object to SectionState."""
        mock_snap = MagicMock()
        mock_snap.title_number = 17
        mock_snap.section_number = "106"
        mock_snap.heading = "Test heading"
        mock_snap.text_content = "Test content"
        mock_snap.text_hash = "abc123"
        mock_snap.normalized_provisions = {"type": "section"}
        mock_snap.full_citation = "17 USC 106"
        mock_snap.snapshot_id = 42
        mock_snap.revision_id = 7
        mock_snap.is_deleted = False

        state = SnapshotService._snapshot_to_state(mock_snap)

        assert state.title_number == 17
        assert state.section_number == "106"
        assert state.heading == "Test heading"
        assert state.text_content == "Test content"
        assert state.text_hash == "abc123"
        assert state.snapshot_id == 42
        assert state.revision_id == 7
        assert not state.is_deleted
