"""Tests for section resolver."""

from pipeline.legal_parser.amendment_parser import SectionReference
from pipeline.legal_parser.section_resolver import (
    ResolutionResult,
    SectionResolver,
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
        ref = SectionReference(title=17, section="106")
        result = ResolutionResult(
            section_ref=ref,
            error="Not found",
        )
        assert not result.resolved
        assert result.title_number is None
        assert result.section_number is None
        assert result.error == "Not found"

    def test_resolved_result(self) -> None:
        ref = SectionReference(title=17, section="106")
        result = ResolutionResult(
            section_ref=ref,
            title_number=17,
            section_number="106",
            resolved=True,
            normalized_section_number="106",
        )
        assert result.resolved
        assert result.title_number == 17
        assert result.section_number == "106"
        assert result.normalized_section_number == "106"


class TestSectionResolver:
    """Tests for the pure SectionResolver."""

    def test_resolve_with_title(self) -> None:
        resolver = SectionResolver()
        ref = SectionReference(title=17, section="106")
        result = resolver.resolve(ref)
        assert result.resolved
        assert result.title_number == 17
        assert result.section_number == "106"

    def test_resolve_with_default_title(self) -> None:
        resolver = SectionResolver()
        ref = SectionReference(title=None, section="106")
        result = resolver.resolve(ref, default_title=17)
        assert result.resolved
        assert result.title_number == 17

    def test_resolve_no_title_fails(self) -> None:
        resolver = SectionResolver()
        ref = SectionReference(title=None, section="106")
        result = resolver.resolve(ref)
        assert not result.resolved
        assert result.error is not None

    def test_resolve_normalizes_hyphens(self) -> None:
        resolver = SectionResolver()
        ref = SectionReference(title=15, section="80a-3a")
        result = resolver.resolve(ref)
        assert result.resolved
        assert result.section_number == "80a\u20133a"

    def test_resolve_batch(self) -> None:
        resolver = SectionResolver()
        refs = [
            SectionReference(title=17, section="106"),
            SectionReference(title=17, section="107"),
        ]
        results = resolver.resolve_batch(refs)
        assert len(results) == 2
        assert all(r.resolved for r in results)
