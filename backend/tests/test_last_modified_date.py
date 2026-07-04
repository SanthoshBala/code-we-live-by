"""Unit tests for last_modified_date derivation from amendment citations.

These tests verify the fallback logic added to get_section() in
app/crud/us_code.py: when the `amendments` list is empty but `citations`
contains entries with relationship "Amendment" or non-original chapter acts
(is_original == false), last_modified_date should be derived from the most
recent such citation date.

The tests exercise the same computation as the production code by calling
_parse_citation_date directly and running the equivalent selection logic.
"""

from datetime import date

from pipeline.olrc.group_service import _parse_citation_date


def _compute_last_modified_date_from_citations(citations: list[dict]) -> date | None:
    """Mirror of the fallback logic in get_section() for isolated testing.

    Includes citations with relationship "Amendment" OR any non-original
    citation (is_original == false) — the latter covers pre-Public Law
    chapter-numbered acts whose relationship is stored as "Framework".
    """
    amendment_dates = []
    for c in citations:
        if c.get("relationship") == "Amendment" or not c.get("is_original", True):
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

    def test_framework_chapter_act_not_original_counts_as_amendment(self) -> None:
        """Pre-Public Law chapter acts with is_original=False are counted.

        Reproduces the 9 U.S.C. § 7 bug: a 1951 chapter-numbered act has
        relationship 'Framework' (not 'Amendment'), but is_original=False
        indicates it modified the section after enactment.
        """
        citations = [
            {
                "raw_text": "July 30, 1947, ch. 392, § 7",
                "relationship": "Framework",
                "is_original": True,
                "is_framework": True,
                "is_act": True,
                "act": {
                    "date": "1947-07-30",
                    "chapter": 392,
                },
            },
            {
                "raw_text": "Oct. 31, 1951, ch. 655, § 14",
                "relationship": "Framework",
                "is_original": False,
                "is_framework": True,
                "is_act": True,
                "act": {
                    "date": "1951-10-31",
                    "chapter": 655,
                },
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(1951, 10, 31)

    def test_original_chapter_act_excluded(self) -> None:
        """The original enacting chapter act (is_original=True) is not counted."""
        citations = [
            {
                "raw_text": "July 30, 1947, ch. 392, § 1",
                "relationship": "Framework",
                "is_original": True,
                "is_framework": True,
                "is_act": True,
                "act": {
                    "date": "1947-07-30",
                    "chapter": 392,
                },
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result is None

    def test_chapter_act_amendment_mixed_with_public_law_amendment(self) -> None:
        """When both chapter acts and Public Law amendments exist, most recent wins."""
        citations = [
            {
                "raw_text": "July 30, 1947, ch. 392, § 1",
                "relationship": "Framework",
                "is_original": True,
                "is_act": True,
                "act": {"date": "1947-07-30", "chapter": 392},
            },
            {
                "raw_text": "Oct. 31, 1951, ch. 655, § 14",
                "relationship": "Framework",
                "is_original": False,
                "is_act": True,
                "act": {"date": "1951-10-31", "chapter": 655},
            },
            {
                "law_id": "PL 95-598",
                "law": {"date": "Nov. 6, 1978"},
                "relationship": "Amendment",
                "is_original": False,
            },
        ]
        result = _compute_last_modified_date_from_citations(citations)
        assert result == date(1978, 11, 6)
