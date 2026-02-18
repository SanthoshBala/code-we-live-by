"""Tests for the RP-to-RP diff engine (Task 1.20)."""

from __future__ import annotations

from pipeline.olrc.diff_engine import diff_section_maps
from pipeline.olrc.snapshot_service import SectionState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    title: int = 17,
    section: str = "101",
    text_hash: str = "abc123",
    notes_hash: str | None = None,
    revision_id: int = 1,
) -> SectionState:
    """Create a minimal SectionState for testing."""
    return SectionState(
        title_number=title,
        section_number=section,
        heading=f"Section {section}",
        text_content="text",
        text_hash=text_hash,
        normalized_provisions=None,
        notes=None,
        normalized_notes=None,
        notes_hash=notes_hash,
        full_citation=f"{title} U.S.C. § {section}",
        snapshot_id=1,
        revision_id=revision_id,
        is_deleted=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiffSectionMaps:
    """Tests for the pure diff_section_maps function."""

    def test_identical_revisions(self) -> None:
        """All sections unchanged -> empty diffs, correct unchanged count."""
        states = [
            _make_state(section="101", text_hash="aaa"),
            _make_state(section="102", text_hash="bbb"),
        ]
        result = diff_section_maps(
            states, states, before_revision_id=1, after_revision_id=2
        )

        assert result.sections_added == 0
        assert result.sections_modified == 0
        assert result.sections_deleted == 0
        assert result.sections_unchanged == 2
        assert result.diffs == []

    def test_section_added(self) -> None:
        """Section in after but not before -> ADDED."""
        before = [_make_state(section="101", text_hash="aaa")]
        after = [
            _make_state(section="101", text_hash="aaa"),
            _make_state(section="102", text_hash="bbb"),
        ]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_added == 1
        assert result.sections_unchanged == 1
        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert diff.change_type == "added"
        assert diff.section_number == "102"
        assert diff.before_state is None
        assert diff.after_state is not None
        assert diff.text_changed is True

    def test_section_deleted(self) -> None:
        """Section in before but not after -> DELETED."""
        before = [
            _make_state(section="101", text_hash="aaa"),
            _make_state(section="102", text_hash="bbb"),
        ]
        after = [_make_state(section="101", text_hash="aaa")]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_deleted == 1
        assert result.sections_unchanged == 1
        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert diff.change_type == "deleted"
        assert diff.section_number == "102"
        assert diff.before_state is not None
        assert diff.after_state is None

    def test_section_text_modified(self) -> None:
        """Different text_hash -> MODIFIED with text_changed=True."""
        before = [_make_state(section="101", text_hash="aaa", notes_hash="nnn")]
        after = [_make_state(section="101", text_hash="bbb", notes_hash="nnn")]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_modified == 1
        assert result.sections_unchanged == 0
        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert diff.change_type == "modified"
        assert diff.text_changed is True
        assert diff.notes_changed is False
        assert diff.before_state is not None
        assert diff.after_state is not None

    def test_section_notes_modified(self) -> None:
        """Same text_hash, different notes_hash -> MODIFIED with notes_changed=True."""
        before = [_make_state(section="101", text_hash="aaa", notes_hash="nnn")]
        after = [_make_state(section="101", text_hash="aaa", notes_hash="mmm")]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_modified == 1
        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert diff.change_type == "modified"
        assert diff.text_changed is False
        assert diff.notes_changed is True

    def test_mixed_changes(self) -> None:
        """Combination of added, modified, deleted, and unchanged."""
        before = [
            _make_state(section="101", text_hash="aaa"),  # unchanged
            _make_state(section="102", text_hash="bbb"),  # modified
            _make_state(section="103", text_hash="ccc"),  # deleted
        ]
        after = [
            _make_state(section="101", text_hash="aaa"),  # unchanged
            _make_state(section="102", text_hash="xxx"),  # modified
            _make_state(section="104", text_hash="ddd"),  # added
        ]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_added == 1
        assert result.sections_modified == 1
        assert result.sections_deleted == 1
        assert result.sections_unchanged == 1
        assert len(result.diffs) == 3

        by_type = {d.change_type: d for d in result.diffs}
        assert by_type["added"].section_number == "104"
        assert by_type["modified"].section_number == "102"
        assert by_type["deleted"].section_number == "103"

    def test_diffs_sorted_by_title_and_section(self) -> None:
        """Diffs should be sorted by (title_number, section_number)."""
        before: list[SectionState] = []
        after = [
            _make_state(title=18, section="201", text_hash="aaa"),
            _make_state(title=17, section="102", text_hash="bbb"),
            _make_state(title=17, section="101", text_hash="ccc"),
        ]
        result = diff_section_maps(before, after, 1, 2)

        assert len(result.diffs) == 3
        assert result.diffs[0].title_number == 17
        assert result.diffs[0].section_number == "101"
        assert result.diffs[1].title_number == 17
        assert result.diffs[1].section_number == "102"
        assert result.diffs[2].title_number == 18
        assert result.diffs[2].section_number == "201"

    def test_notes_hash_none_to_value(self) -> None:
        """notes_hash changing from None to a value -> MODIFIED."""
        before = [_make_state(section="101", text_hash="aaa", notes_hash=None)]
        after = [_make_state(section="101", text_hash="aaa", notes_hash="nnn")]
        result = diff_section_maps(before, after, 1, 2)

        assert result.sections_modified == 1
        diff = result.diffs[0]
        assert diff.notes_changed is True
        assert diff.text_changed is False

    def test_empty_revisions(self) -> None:
        """Both revisions empty -> all zeros."""
        result = diff_section_maps([], [], 1, 2)
        assert result.sections_added == 0
        assert result.sections_modified == 0
        assert result.sections_deleted == 0
        assert result.sections_unchanged == 0
        assert result.diffs == []

    def test_revision_ids_preserved(self) -> None:
        """Result should carry the correct revision IDs."""
        result = diff_section_maps([], [], before_revision_id=10, after_revision_id=20)
        assert result.before_revision_id == 10
        assert result.after_revision_id == 20
