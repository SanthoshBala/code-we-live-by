"""Tests for app/core/law_history_helpers — compose_sponsor_name."""

from app.core.law_history_helpers import compose_sponsor_name


class TestComposeSponsorName:
    def test_first_middle_last(self) -> None:
        assert compose_sponsor_name("Edward", "R.", "Royce") == "Edward R. Royce"

    def test_first_last_no_middle(self) -> None:
        assert compose_sponsor_name("Brad", None, "Sherman") == "Brad Sherman"

    def test_all_none_returns_none(self) -> None:
        assert compose_sponsor_name(None, None, None) is None

    def test_normalises_all_caps(self) -> None:
        # Congress.gov occasionally returns names in ALL CAPS
        assert compose_sponsor_name("DON", "E.", "YOUNG") == "Don E. Young"

    def test_mixed_case_unchanged(self) -> None:
        # Normal case should not be altered
        assert compose_sponsor_name("Gary", "C.", "Peters") == "Gary C. Peters"

    def test_at_large_district_zero_is_separate_concern(self) -> None:
        # compose_sponsor_name doesn't touch district — just verifying isolation
        result = compose_sponsor_name("Don", None, "Young")
        assert result == "Don Young"

    def test_partial_fields_first_only(self) -> None:
        assert compose_sponsor_name("Jane", None, None) == "Jane"

    def test_partial_fields_last_only(self) -> None:
        assert compose_sponsor_name(None, None, "Smith") == "Smith"
