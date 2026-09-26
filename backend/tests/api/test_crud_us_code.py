"""Unit tests for CRUD helper functions in app.crud.us_code."""

from app.crud.us_code import _extract_last_amendment


def _make_notes(amendments: list[dict]) -> dict:
    return {"amendments": amendments}


def _make_amendment(year: int, congress: int, law_number: int) -> dict:
    return {
        "year": year,
        "law": {
            "congress": congress,
            "law_number": law_number,
        },
    }


class TestExtractLastAmendment:
    def test_empty_notes_returns_none(self):
        assert _extract_last_amendment(None) == (None, None)

    def test_empty_amendments_list_returns_none(self):
        assert _extract_last_amendment({"amendments": []}) == (None, None)

    def test_single_law_year(self):
        notes = _make_notes([_make_amendment(2005, 109, 8)])
        year, law = _extract_last_amendment(notes)
        assert year == 2005
        assert law == "PL 109-8"

    def test_multi_law_same_year_picks_highest_law_number(self):
        """When two laws share the most recent year, pick the one with the higher
        law_number — not the first one in the list."""
        notes = _make_notes(
            [
                _make_amendment(2010, 111, 148),  # PL 111-148 (ACA, earlier)
                _make_amendment(2010, 111, 203),  # PL 111-203 (Dodd-Frank, later)
            ]
        )
        year, law = _extract_last_amendment(notes)
        assert year == 2010
        assert law == "PL 111-203"

    def test_multi_law_same_year_order_independent(self):
        """The result must be the same regardless of list order."""
        notes_forward = _make_notes(
            [
                _make_amendment(2010, 111, 148),
                _make_amendment(2010, 111, 203),
            ]
        )
        notes_reversed = _make_notes(
            [
                _make_amendment(2010, 111, 203),
                _make_amendment(2010, 111, 148),
            ]
        )
        assert _extract_last_amendment(notes_forward) == _extract_last_amendment(
            notes_reversed
        )

    def test_multiple_years_picks_most_recent_year(self):
        """Returns the law from the most recent year, not just the first entry."""
        notes = _make_notes(
            [
                _make_amendment(2015, 114, 10),
                _make_amendment(2008, 110, 343),
                _make_amendment(2020, 116, 127),
            ]
        )
        year, law = _extract_last_amendment(notes)
        assert year == 2020
        assert law == "PL 116-127"

    def test_multiple_years_multi_law_most_recent_year(self):
        """Multiple laws in the most recent year — still picks highest law_number."""
        notes = _make_notes(
            [
                _make_amendment(2010, 111, 148),
                _make_amendment(2010, 111, 203),
                _make_amendment(2005, 109, 8),
            ]
        )
        year, law = _extract_last_amendment(notes)
        assert year == 2010
        assert law == "PL 111-203"

    def test_amendment_without_law_returns_year_only(self):
        """When the winning amendment has no law data, year is still returned."""
        notes = _make_notes([{"year": 2000}])
        year, law = _extract_last_amendment(notes)
        assert year == 2000
        assert law is None
