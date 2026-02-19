"""Tests for pipeline.chrono.checkpoint — pure checkpoint validation logic."""

from pipeline.chrono.checkpoint import (
    CheckpointResult,
    validate_checkpoint,
)
from pipeline.olrc.snapshot_service import SectionState


def _make_section(
    title: int = 17,
    section: str = "101",
    text_hash: str | None = "abc123",
    notes_hash: str | None = "notes123",
    is_deleted: bool = False,
) -> SectionState:
    """Create a minimal SectionState for testing."""
    return SectionState(
        title_number=title,
        section_number=section,
        heading="Test Section",
        text_content="some text",
        text_hash=text_hash,
        normalized_provisions=None,
        notes="some notes",
        normalized_notes=None,
        notes_hash=notes_hash,
        full_citation=None,
        snapshot_id=1,
        revision_id=1,
        is_deleted=is_deleted,
    )


class TestCheckpointResult:
    def test_is_clean_when_all_match(self) -> None:
        result = CheckpointResult(
            rp_identifier="113-37",
            rp_revision_id=2,
            derived_revision_id=1,
            sections_match=5,
        )
        assert result.is_clean is True

    def test_is_not_clean_with_mismatch(self) -> None:
        result = CheckpointResult(
            rp_identifier="113-37",
            rp_revision_id=2,
            derived_revision_id=1,
            sections_match=4,
            sections_mismatch=1,
        )
        assert result.is_clean is False

    def test_is_not_clean_with_only_in_derived(self) -> None:
        result = CheckpointResult(
            rp_identifier="113-37",
            rp_revision_id=2,
            derived_revision_id=1,
            sections_only_in_derived=1,
        )
        assert result.is_clean is False


class TestValidateCheckpoint:
    def test_all_match(self) -> None:
        """Identical sections produce 0 mismatches."""
        derived = [
            _make_section(section="101", text_hash="h1", notes_hash="n1"),
            _make_section(section="102", text_hash="h2", notes_hash="n2"),
        ]
        rp = [
            _make_section(section="101", text_hash="h1", notes_hash="n1"),
            _make_section(section="102", text_hash="h2", notes_hash="n2"),
        ]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_match == 2
        assert result.sections_mismatch == 0
        assert result.sections_only_in_derived == 0
        assert result.sections_only_in_rp == 0
        assert result.mismatches == []
        assert result.is_clean is True

    def test_text_mismatch(self) -> None:
        """Different text_hash is reported as 'text' mismatch."""
        derived = [_make_section(section="101", text_hash="h1", notes_hash="n1")]
        rp = [_make_section(section="101", text_hash="h2", notes_hash="n1")]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_mismatch == 1
        assert len(result.mismatches) == 1
        assert result.mismatches[0].mismatch_type == "text"
        assert result.mismatches[0].derived_hash == "h1"
        assert result.mismatches[0].rp_hash == "h2"

    def test_notes_mismatch(self) -> None:
        """Different notes_hash is reported as 'notes' mismatch."""
        derived = [_make_section(section="101", text_hash="h1", notes_hash="n1")]
        rp = [_make_section(section="101", text_hash="h1", notes_hash="n2")]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_mismatch == 1
        assert result.mismatches[0].mismatch_type == "notes"

    def test_both_mismatch(self) -> None:
        """Different text AND notes hashes reported as 'both'."""
        derived = [_make_section(section="101", text_hash="h1", notes_hash="n1")]
        rp = [_make_section(section="101", text_hash="h2", notes_hash="n2")]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_mismatch == 1
        assert result.mismatches[0].mismatch_type == "both"

    def test_section_only_in_derived(self) -> None:
        """Section exists in derived but not RP."""
        derived = [
            _make_section(section="101", text_hash="h1"),
            _make_section(section="102", text_hash="h2"),
        ]
        rp = [_make_section(section="101", text_hash="h1")]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_match == 1
        assert result.sections_only_in_derived == 1
        assert result.mismatches[0].mismatch_type == "only_in_derived"
        assert result.mismatches[0].section_number == "102"

    def test_section_only_in_rp(self) -> None:
        """Section exists in RP but not derived."""
        derived = [_make_section(section="101", text_hash="h1")]
        rp = [
            _make_section(section="101", text_hash="h1"),
            _make_section(section="102", text_hash="h2"),
        ]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_match == 1
        assert result.sections_only_in_rp == 1
        assert result.mismatches[0].mismatch_type == "only_in_rp"
        assert result.mismatches[0].section_number == "102"

    def test_deleted_mismatch(self) -> None:
        """Derived says deleted, RP says alive (or vice versa)."""
        derived = [_make_section(section="101", is_deleted=True)]
        rp = [_make_section(section="101", is_deleted=False)]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_mismatch == 1
        assert result.mismatches[0].mismatch_type == "deleted_mismatch"

    def test_both_deleted_match(self) -> None:
        """Both deleted with same hashes → match."""
        derived = [
            _make_section(
                section="101", is_deleted=True, text_hash="h1", notes_hash="n1"
            )
        ]
        rp = [
            _make_section(
                section="101", is_deleted=True, text_hash="h1", notes_hash="n1"
            )
        ]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_match == 1
        assert result.sections_mismatch == 0

    def test_empty_sections(self) -> None:
        """Empty lists produce all-zero result."""
        result = validate_checkpoint([], [], "113-37", 2, 1)
        assert result.sections_match == 0
        assert result.sections_mismatch == 0
        assert result.is_clean is True

    def test_multiple_titles(self) -> None:
        """Sections from different titles are compared independently."""
        derived = [
            _make_section(title=17, section="101", text_hash="h1", notes_hash="n1"),
            _make_section(title=18, section="101", text_hash="h2", notes_hash="n2"),
        ]
        rp = [
            _make_section(title=17, section="101", text_hash="h1", notes_hash="n1"),
            _make_section(title=18, section="101", text_hash="h3", notes_hash="n2"),
        ]
        result = validate_checkpoint(derived, rp, "113-37", 2, 1)

        assert result.sections_match == 1
        assert result.sections_mismatch == 1
        assert result.mismatches[0].title_number == 18
