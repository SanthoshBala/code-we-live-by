"""Tests for _extract_last_amendment in app/crud/us_code.py."""

from app.crud.us_code import _extract_last_amendment


class TestExtractLastAmendment:
    def test_none_notes(self) -> None:
        assert _extract_last_amendment(None) == (None, None)

    def test_empty_amendments(self) -> None:
        assert _extract_last_amendment({"amendments": []}) == (None, None)

    def test_single_amendment(self) -> None:
        notes = {
            "amendments": [
                {"year": 2010, "law": {"congress": 111, "law_number": 148}},
            ]
        }
        assert _extract_last_amendment(notes) == (2010, "PL 111-148")

    def test_multiple_years_picks_highest_year(self) -> None:
        notes = {
            "amendments": [
                {"year": 2010, "law": {"congress": 111, "law_number": 148}},
                {"year": 1999, "law": {"congress": 106, "law_number": 170}},
            ]
        }
        assert _extract_last_amendment(notes) == (2010, "PL 111-148")

    def test_multiple_laws_same_year_picks_last(self) -> None:
        # Issue #736: when two laws are in the same year, the last one (higher
        # law number, later enacted) should be returned.
        # 5 U.S.C. § 552a year 2010: PL 111-148 (ACA, March) then PL 111-203
        # (Dodd-Frank, July). last_amendment_law should be PL 111-203.
        notes = {
            "amendments": [
                {"year": 2010, "law": {"congress": 111, "law_number": 148}},
                {"year": 2010, "law": {"congress": 111, "law_number": 203}},
                {"year": 1999, "law": {"congress": 106, "law_number": 170}},
            ]
        }
        assert _extract_last_amendment(notes) == (2010, "PL 111-203")

    def test_multiple_laws_same_year_three_entries(self) -> None:
        notes = {
            "amendments": [
                {"year": 2020, "law": {"congress": 116, "law_number": 92}},
                {"year": 2020, "law": {"congress": 116, "law_number": 136}},
                {"year": 2020, "law": {"congress": 116, "law_number": 283}},
                {"year": 2019, "law": {"congress": 116, "law_number": 21}},
            ]
        }
        assert _extract_last_amendment(notes) == (2020, "PL 116-283")

    def test_law_none_returns_year_only(self) -> None:
        notes = {
            "amendments": [
                {"year": 1950, "law": None},
            ]
        }
        assert _extract_last_amendment(notes) == (1950, None)

    def test_missing_congress_returns_year_only(self) -> None:
        notes = {
            "amendments": [
                {"year": 2010, "law": {"congress": None, "law_number": 148}},
            ]
        }
        assert _extract_last_amendment(notes) == (2010, None)
