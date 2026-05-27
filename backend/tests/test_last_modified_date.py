"""Unit tests for last_modified_date derivation from amendment citations.

These tests verify the logic in get_section() in app/crud/us_code.py:
last_modified_date is derived from the most recent amendment citation date,
using the full ISO date (YYYY-MM-DD) rather than falling back to {year}-01-01.

The tests exercise the same computation as the production code by calling
_parse_citation_date directly and running the equivalent selection logic.
"""

from datetime import date

from pipeline.olrc.group_service import _parse_citation_date


def _compute_last_modified_date(
    citations: list[dict],
    amendments: list[dict] | None = None,
) -> date | None:
    """Mirror of the primary + fallback logic in get_section() for isolated testing.

    Primary path: derive the full date from amendment citations (relationship == "Amendment").
    Fallback path: when no citation dates are available, use the year from the amendments
    list and default to {year}-01-01.
    """
    # Primary: use full date from amendment citations
    amendment_dates = []
    for c in citations:
        if c.get("relationship") == "Amendment":
            law_data = c.get("law") or c.get("act")
            if law_data and law_data.get("date"):
                parsed = _parse_citation_date(law_data["date"])
                if parsed is not None:
                    amendment_dates.append(parsed)
    if amendment_dates:
        return max(amendment_dates)

    # Fallback: use year from amendments list
    if amendments:
        years = [a["year"] for a in amendments if "year" in a]
        if years:
            return date(max(years), 1, 1)

    return None


def _compute_last_modified_date_from_citations(citations: list[dict]) -> date | None:
    """Mirror of the citation-only logic in get_section() for isolated testing."""
    return _compute_last_modified_date(citations, amendments=None)


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


class TestLastModifiedDateFullDateNotYearStart:
    """Verify that last_modified_date uses the full ISO date, not {year}-01-01.

    Regression tests for issue #466: 2 U.S.C. § 33 was returning
    last_modified_date=1981-01-01 instead of 1981-10-01 because the code
    extracted only the year from the amendments list and constructed
    date(year, 1, 1) rather than parsing the full date from citations.
    """

    def test_2usc33_oct_1981_full_date(self) -> None:
        """2 U.S.C. § 33 scenario: Oct. 1, 1981 must yield 1981-10-01, not 1981-01-01.

        OLRC source credit:
            (June 19, 1934, ch. 648, title I, § 1, 48 Stat. 1022;
             Pub. L. 97–51, § 112(b)(2), Oct. 1, 1981, 95 Stat. 963.)
        The amendment date Oct. 1, 1981 must be fully parsed, not truncated to year-start.
        """
        citations = [
            {
                "law_id": "PL 97-51",
                "law": {"date": "Oct. 1, 1981", "congress": 97, "law_number": 51},
                "relationship": "Amendment",
            },
        ]
        amendments = [
            {"year": 1981, "law": {"congress": 97, "law_number": 51}},
        ]
        result = _compute_last_modified_date(citations, amendments)
        assert result == date(1981, 10, 1), (
            f"Expected 1981-10-01 (full date from citation), got {result} "
            f"(year-start fallback would give 1981-01-01)"
        )

    def test_citation_date_preferred_over_year_start(self) -> None:
        """When both citations and amendments are present, citation date wins over year-start."""
        citations = [
            {
                "law_id": "PL 100-1",
                "law": {"date": "Nov. 15, 1987", "congress": 100, "law_number": 1},
                "relationship": "Enactment",
            },
            {
                "law_id": "PL 101-5",
                "law": {"date": "Mar. 7, 1990", "congress": 101, "law_number": 5},
                "relationship": "Amendment",
            },
        ]
        # amendments list only has year, not full date
        amendments = [
            {"year": 1990, "law": {"congress": 101, "law_number": 5}},
        ]
        result = _compute_last_modified_date(citations, amendments)
        # Must be Mar. 7 not Jan. 1
        assert result == date(1990, 3, 7)

    def test_fallback_to_year_start_when_no_citation_dates(self) -> None:
        """When citation dates are absent, fall back to {year}-01-01 from amendments list."""
        # Citations exist but none are amendments with dates
        citations = [
            {
                "law_id": "PL 100-1",
                "law": {"congress": 100, "law_number": 1},  # no date field
                "relationship": "Amendment",
            },
        ]
        amendments = [
            {"year": 1988, "law": {"congress": 100, "law_number": 1}},
        ]
        result = _compute_last_modified_date(citations, amendments)
        assert result == date(1988, 1, 1)
