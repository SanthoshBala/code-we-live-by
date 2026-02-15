"""Tests for release point validator and amendment cross-referencer."""

import pytest

from pipeline.legal_parser.release_point_validator import (
    CrossRefResult,
    SectionComparison,
    ValidationReport,
    _normalize_for_comparison,
)


class TestNormalizeForComparison:
    """Tests for text normalization in comparisons."""

    def test_collapse_whitespace(self) -> None:
        result = _normalize_for_comparison("hello   world\n\ttest")
        assert result == "hello world test"

    def test_strip(self) -> None:
        result = _normalize_for_comparison("  hello  ")
        assert result == "hello"

    def test_empty_string(self) -> None:
        result = _normalize_for_comparison("")
        assert result == ""


class TestSectionComparison:
    """Tests for SectionComparison dataclass."""

    def test_match(self) -> None:
        comp = SectionComparison(
            title_number=17,
            section_number="106",
            matches=True,
            db_text="some text",
            rp_text="some text",
        )
        assert comp.matches
        assert comp.in_db
        assert comp.in_rp

    def test_mismatch(self) -> None:
        comp = SectionComparison(
            title_number=17,
            section_number="106",
            matches=False,
            db_text="old text",
            rp_text="new text",
            diff_summary="Text differs",
        )
        assert not comp.matches

    def test_only_in_db(self) -> None:
        comp = SectionComparison(
            title_number=17,
            section_number="106",
            db_text="some text",
        )
        assert comp.in_db
        assert not comp.in_rp

    def test_only_in_rp(self) -> None:
        comp = SectionComparison(
            title_number=17,
            section_number="106",
            rp_text="some text",
        )
        assert not comp.in_db
        assert comp.in_rp


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_empty_report(self) -> None:
        report = ValidationReport(release_point="113-22")
        assert report.match_rate == 0.0
        assert not report.is_valid

    def test_perfect_match(self) -> None:
        report = ValidationReport(
            release_point="113-22",
            total_sections=100,
            matches=100,
            mismatches=0,
        )
        assert report.match_rate == 1.0
        assert report.is_valid

    def test_partial_match(self) -> None:
        report = ValidationReport(
            release_point="113-22",
            total_sections=100,
            matches=96,
            mismatches=4,
        )
        assert report.match_rate == 0.96
        assert report.is_valid

    def test_below_threshold(self) -> None:
        report = ValidationReport(
            release_point="113-22",
            total_sections=100,
            matches=90,
            mismatches=10,
        )
        assert report.match_rate == 0.90
        assert not report.is_valid

    def test_errors_invalidate(self) -> None:
        report = ValidationReport(
            release_point="113-22",
            total_sections=100,
            matches=100,
            errors=["Something went wrong"],
        )
        assert not report.is_valid


class TestCrossRefResult:
    """Tests for CrossRefResult dataclass."""

    def test_perfect_cross_ref(self) -> None:
        result = CrossRefResult(
            congress=113,
            law_number=22,
            sections_in_notes=[(17, "106"), (17, "107")],
            sections_in_changes=[(17, "106"), (17, "107")],
            matched=[(17, "106"), (17, "107")],
        )
        assert result.precision == 1.0
        assert result.recall == 1.0

    def test_partial_cross_ref(self) -> None:
        result = CrossRefResult(
            congress=113,
            law_number=22,
            sections_in_notes=[(17, "106"), (17, "107"), (17, "108")],
            sections_in_changes=[(17, "106"), (17, "107")],
            matched=[(17, "106"), (17, "107")],
            only_in_notes=[(17, "108")],
        )
        assert result.precision == 1.0
        assert result.recall == pytest.approx(2 / 3, rel=0.01)

    def test_false_positives(self) -> None:
        result = CrossRefResult(
            congress=113,
            law_number=22,
            sections_in_notes=[(17, "106")],
            sections_in_changes=[(17, "106"), (17, "999")],
            matched=[(17, "106")],
            only_in_changes=[(17, "999")],
        )
        assert result.precision == 0.5
        assert result.recall == 1.0

    def test_empty(self) -> None:
        result = CrossRefResult(congress=113, law_number=22)
        assert result.precision == 0.0
        assert result.recall == 0.0
