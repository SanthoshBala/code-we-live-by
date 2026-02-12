"""Tests for section resolver."""

import pytest

from pipeline.legal_parser.section_resolver import (
    ResolutionResult,
    normalize_section_number,
)


class TestNormalizeSectionNumber:
    """Tests for section number normalization."""

    def test_hyphen_to_en_dash(self) -> None:
        result = normalize_section_number("80a-3a")
        assert result == "80a\u20133a"  # en-dash

    def test_no_hyphen(self) -> None:
        result = normalize_section_number("106")
        assert result == "106"

    def test_multiple_hyphens(self) -> None:
        result = normalize_section_number("80a-3a-1")
        assert result == "80a\u20133a\u20131"

    def test_already_en_dash(self) -> None:
        result = normalize_section_number("80a\u20133a")
        assert result == "80a\u20133a"


class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_unresolved_result(self) -> None:
        from pipeline.legal_parser.amendment_parser import SectionReference

        ref = SectionReference(title=17, section="106")
        result = ResolutionResult(
            section_ref=ref,
            error="Not found",
        )
        assert not result.resolved
        assert result.section is None
        assert result.error == "Not found"

    def test_resolved_result(self) -> None:
        from pipeline.legal_parser.amendment_parser import SectionReference

        ref = SectionReference(title=17, section="106")
        # Can't create a real USCodeSection without DB, just test the structure
        result = ResolutionResult(
            section_ref=ref,
            resolved=True,
            normalized_section_number="106",
        )
        assert result.resolved
        assert result.normalized_section_number == "106"
