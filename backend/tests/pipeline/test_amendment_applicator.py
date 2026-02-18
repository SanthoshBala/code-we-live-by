"""Tests for pipeline.chrono.amendment_applicator — pure unit tests, no DB."""

from app.models.enums import ChangeType
from pipeline.chrono.amendment_applicator import (
    ApplicationStatus,
    apply_text_change,
)


class TestApplyTextChange:
    """Tests for apply_text_change dispatch and matching."""

    def test_modify_exact_match(self) -> None:
        """MODIFY replaces old_text with new_text (exact match)."""
        result = apply_text_change(
            text_content="The rate shall be 5 percent of the amount.",
            change_type=ChangeType.MODIFY,
            old_text="5 percent",
            new_text="10 percent",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text == "The rate shall be 10 percent of the amount."
        assert result.old_text_matched is True

    def test_modify_whitespace_normalized(self) -> None:
        """MODIFY matches despite whitespace differences."""
        result = apply_text_change(
            text_content="The  rate  shall  be  5  percent.",
            change_type=ChangeType.MODIFY,
            old_text="rate shall be 5 percent",
            new_text="rate shall be 10 percent",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert "10 percent" in result.new_text  # type: ignore[operator]
        assert result.old_text_matched is True

    def test_modify_case_insensitive_fallback(self) -> None:
        """MODIFY falls back to case-insensitive when exact/ws fails."""
        result = apply_text_change(
            text_content="the Secretary of the Treasury shall certify.",
            change_type=ChangeType.MODIFY,
            old_text="The Secretary Of The Treasury",
            new_text="The Secretary of Labor",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert "The Secretary of Labor" in result.new_text  # type: ignore[operator]

    def test_modify_not_found(self) -> None:
        """MODIFY returns FAILED when old_text is absent."""
        result = apply_text_change(
            text_content="The rate shall be 5 percent.",
            change_type=ChangeType.MODIFY,
            old_text="nonexistent phrase",
            new_text="replacement",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.FAILED
        assert result.old_text_matched is False
        assert result.new_text == "The rate shall be 5 percent."

    def test_delete_removes_text(self) -> None:
        """DELETE removes old_text from content."""
        result = apply_text_change(
            text_content="(a) General rule. (b) Exception for small plans.",
            change_type=ChangeType.DELETE,
            old_text=" (b) Exception for small plans.",
            new_text=None,
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text == "(a) General rule."

    def test_add_to_existing(self) -> None:
        """ADD appends new_text to existing content."""
        result = apply_text_change(
            text_content="(a) General rule.",
            change_type=ChangeType.ADD,
            old_text=None,
            new_text=" (b) Special rule.",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text == "(a) General rule. (b) Special rule."

    def test_add_new_section(self) -> None:
        """ADD with None content creates section from new_text."""
        result = apply_text_change(
            text_content=None,
            change_type=ChangeType.ADD,
            old_text=None,
            new_text="(a) New section text.",
            title_number=26,
            section_number="401A",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text == "(a) New section text."

    def test_repeal(self) -> None:
        """REPEAL returns APPLIED with None text."""
        result = apply_text_change(
            text_content="(a) This section is about to be repealed.",
            change_type=ChangeType.REPEAL,
            old_text=None,
            new_text=None,
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text is None
        assert result.change_type == ChangeType.REPEAL

    def test_redesignate_skipped(self) -> None:
        """REDESIGNATE returns SKIPPED (structural, out of scope)."""
        result = apply_text_change(
            text_content="Some content.",
            change_type=ChangeType.REDESIGNATE,
            old_text=None,
            new_text=None,
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.SKIPPED
        assert result.new_text == "Some content."

    def test_transfer_skipped(self) -> None:
        """TRANSFER returns SKIPPED (structural, out of scope)."""
        result = apply_text_change(
            text_content="Some content.",
            change_type=ChangeType.TRANSFER,
            old_text=None,
            new_text=None,
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.SKIPPED

    def test_modify_first_occurrence_only(self) -> None:
        """MODIFY replaces only the first occurrence when text appears twice."""
        result = apply_text_change(
            text_content="5 percent of the first amount and 5 percent of the second.",
            change_type=ChangeType.MODIFY,
            old_text="5 percent",
            new_text="10 percent",
            title_number=26,
            section_number="401",
        )
        assert result.status == ApplicationStatus.APPLIED
        assert result.new_text == (
            "10 percent of the first amount and 5 percent of the second."
        )
