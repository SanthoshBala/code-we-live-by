"""Unit tests for last_modified_date derivation from amendment citations.

These tests verify the fallback logic added to get_section() in
app/crud/us_code.py: when the `amendments` list is empty but `citations`
contains entries with relationship "Amendment", last_modified_date should be
derived from the most recent amendment citation date.

The tests exercise the same computation as the production code by calling
_parse_citation_date directly and running the equivalent selection logic.
"""

from datetime import date

import pytest

from pipeline.olrc.group_service import _parse_citation_date


def _compute_last_modified_date_from_citations(citations: list[dict]) -> date | None:
    """Mirror of the fallback logic in get_section() for isolated testing."""
    amendment_dates = []
    for c in citations:
        if c.get("relationship") == "Amendment":
            law_data = c.get("law") or c.get("act")
            if law_data and law_data.get("date"):
                parsed = _parse_citation_date(law_data["date"])
                if parsed is not None:
                    amendment_dates.append(parsed)
    return max(amendment_dates) if amendment_dates else None


class TestLastModifiedDateFromCitations:
    """last_modified_date fallback: derive from amendment citations."""

    def test_single_amendment_citation(self) -> None:
        """A single amendment citation yields its date as last_modified_date."""
        citations = [
            {
                "law_id": "PL 99-662",
                "law": {"date": "Nov. 17, 1986"},
                "relationship": "Enactment",
            },
            {
                "law_id": "PL 110-114",
                "law": {"date": "Nov. 8, 2007"},
                "relationship": "Amendment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(2007, 11, 8)

    def test_multiple_amendment_citations_returns_most_recent(self) -> None:
        """The most recent amendment citation date is chosen (33 USC §2215 scenario)."""
        citations = [
            {
                "law_id": "PL 99-662",
                "law": {"date": "Nov. 17, 1986"},
                "relationship": "Enactment",
            },
            {
                "law_id": "PL 101-640",
                "law": {"date": "Nov. 28, 1990"},
                "relationship": "Amendment",
            },
            {
                "law_id": "PL 104-303",
                "law": {"date": "Oct. 12, 1996"},
                "relationship": "Amendment",
            },
            {
                "law_id": "PL 106-541",
                "law": {"date": "Dec. 11, 2000"},
                "relationship": "Amendment",
            },
            {
                "law_id": "PL 110-114",
                "law": {"date": "Nov. 8, 2007"},
                "relationship": "Amendment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(2007, 11, 8)

    def test_no_amendment_citations_returns_none(self) -> None:
        """When no citation has relationship Amendment, result is None."""
        citations = [
            {
                "law_id": "PL 99-662",
                "law": {"date": "Nov. 17, 1986"},
                "relationship": "Enactment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result is None

    def test_empty_citations_returns_none(self) -> None:
        """Empty citations list yields None."""
        result = _compute_last_modified_date_from_citations([])
        assert result is None

    def test_amendment_citation_using_act_key(self) -> None:
        """Fallback also works when citation uses 'act' key instead of 'law'."""
        citations = [
            {
                "law_id": "PL 94-553",
                "act": {"date": "Oct. 19, 1976"},
                "relationship": "Amendment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(1976, 10, 19)

    def test_amendment_citation_with_missing_date_skipped(self) -> None:
        """A citation with a missing date field is skipped gracefully."""
        citations = [
            {
                "law_id": "PL 110-114",
                "law": {},
                "relationship": "Amendment",
            },
            {
                "law_id": "PL 101-640",
                "law": {"date": "Nov. 28, 1990"},
                "relationship": "Amendment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(1990, 11, 28)

    def test_amendment_citation_with_null_law_skipped(self) -> None:
        """A citation where 'law' and 'act' are both absent/None is skipped."""
        citations = [
            {
                "law_id": "PL 110-114",
                "relationship": "Amendment",
            },
            {
                "law_id": "PL 104-303",
                "law": {"date": "Oct. 12, 1996"},
                "relationship": "Amendment",
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(1996, 10, 12)
