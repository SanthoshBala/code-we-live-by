"""Tests for diff generator."""

import pytest

from app.models.enums import ChangeType
from pipeline.legal_parser.amendment_parser import ParsedAmendment, SectionReference
from pipeline.legal_parser.diff_generator import DiffReport, DiffResult, _truncate
from pipeline.legal_parser.patterns import PatternType
from pipeline.legal_parser.section_resolver import ResolutionResult


class TestTruncate:
    """Tests for _truncate helper."""

    def test_short_text(self) -> None:
        assert _truncate("hello") == "hello"

    def test_long_text(self) -> None:
        long_text = "a" * 100
        result = _truncate(long_text, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length(self) -> None:
        text = "a" * 50
        assert _truncate(text, max_len=50) == text


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def _make_result(
        self,
        change_type: ChangeType = ChangeType.MODIFY,
        old_text: str | None = None,
        new_text: str | None = None,
    ) -> DiffResult:
        ref = SectionReference(title=17, section="106")
        amendment = ParsedAmendment(
            pattern_name="test",
            pattern_type=PatternType.STRIKE_INSERT,
            change_type=change_type,
            section_ref=ref,
            old_text=old_text,
            new_text=new_text,
        )
        resolution = ResolutionResult(
            section_ref=ref,
            resolved=True,
            normalized_section_number="106",
        )
        return DiffResult(
            amendment=amendment,
            resolution=resolution,
            change_type=change_type,
            old_text=old_text,
            new_text=new_text,
        )

    def test_diff_result_creation(self) -> None:
        result = self._make_result(
            old_text="old",
            new_text="new",
        )
        assert result.change_type == ChangeType.MODIFY
        assert result.old_text == "old"
        assert result.new_text == "new"
        assert result.validated is False

    def test_diff_result_defaults(self) -> None:
        result = self._make_result()
        assert result.subsection_path is None
        assert result.description is None
        assert result.confidence == 0.0


class TestDiffReport:
    """Tests for DiffReport dataclass."""

    def test_empty_report(self) -> None:
        report = DiffReport()
        assert report.total_amendments == 0
        assert report.diffs_generated == 0
        assert report.by_type == {}

    def test_report_with_data(self) -> None:
        report = DiffReport(
            total_amendments=10,
            diffs_generated=7,
            diffs_skipped=1,
            unresolved=2,
            by_type={"Modify": 5, "Add": 2},
        )
        assert report.total_amendments == 10
        assert report.diffs_generated == 7
        assert report.by_type["Modify"] == 5
