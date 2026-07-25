"""Unit tests for last_modified_date derivation from amendment citations.

These tests verify the logic in get_section() (app/crud/us_code.py) that
derives last_modified_date from normalized_notes.  The correct value is the
full enactment date of the most recent amending Public Law (from the
``citations`` list), NOT a Jan-1 approximation built from a year integer.

Coverage also includes pre-Public Law chapter-numbered acts (is_original==false,
relationship=="Framework") which must be treated as amendments when deriving
last_modified_date — fixing the 9 U.S.C. § 7 scenario from issue #563.

Regression coverage for issue #510: sections such as 17 U.S.C. § 107 were
returning 1992-01-01 instead of 1992-10-24 (Pub. L. 102-492, Oct. 24, 1992)
because the primary derivation path read a year-only ``amendments`` entry and
constructed date(year, 1, 1) rather than parsing the full date from the
corresponding citation.
"""

from datetime import date

from pipeline.olrc.group_service import _parse_citation_date


def _compute_last_modified_date_from_citations(citations: list[dict]) -> date | None:
    """Mirror of the citation-based derivation in get_section() for unit testing.

    Includes citations with relationship ``"Amendment"`` OR any non-original
    citation (is_original == false) — the latter covers pre-Public Law
    chapter-numbered acts (relationship ``"Framework"``) that modified the section
    after original enactment. Returns None when no eligible citations have dates.
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


def _compute_last_modified_date_from_notes(normalized_notes: dict) -> date | None:
    """Mirror of the full last_modified_date derivation in get_section().

    Prefers the full enactment date from amendment citations; falls back to the
    year-only value from the ``amendments`` list when no citation dates exist.
    """
    citations = normalized_notes.get("citations", [])
    result = _compute_last_modified_date_from_citations(citations)
    if result is not None:
        return result
    # Fallback: year-only from amendments
    amendments = normalized_notes.get("amendments", [])
    years = [a["year"] for a in amendments if "year" in a]
    if years:
        return date(max(years), 1, 1)
    return None


class TestLastModifiedDateFromCitations:
    """last_modified_date primary path: derive full date from amendment citations."""

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
        """Works when citation uses 'act' key instead of 'law'."""
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


class TestLastModifiedDateFromNotes:
    """Full derivation from normalized_notes: citation dates preferred, year fallback."""

    def test_citation_date_wins_over_year_only_from_amendments(self) -> None:
        """Regression test for issue #510 (17 USC §107 scenario).

        When normalized_notes has both an amendments entry (year-only) AND a
        citation with relationship "Amendment" carrying a full date, the full
        date must be returned — NOT the Jan-1 approximation.
        """
        normalized_notes = {
            "citations": [
                {
                    "law": {"congress": 94, "law_number": 553, "date": "Oct. 19, 1976"},
                    "relationship": "Enactment",
                },
                {
                    "law": {
                        "congress": 102,
                        "law_number": 492,
                        "date": "Oct. 24, 1992",
                    },
                    "relationship": "Amendment",
                },
            ],
            "amendments": [
                {"law": {"congress": 102, "law_number": 492}, "year": 1992},
            ],
        }
        result = _compute_last_modified_date_from_notes(normalized_notes)
        assert result == date(1992, 10, 24), (
            "Expected full date Oct 24, not Jan 1 approximation"
        )
        assert result != date(1992, 1, 1)

    def test_17_usc_101_citation_date(self) -> None:
        """Regression: 17 USC §101 last_modified_date must be 2010-12-09, not 2010-01-01."""
        normalized_notes = {
            "citations": [
                {
                    "law": {"congress": 94, "law_number": 553, "date": "Oct. 19, 1976"},
                    "relationship": "Enactment",
                },
                {
                    "law": {"congress": 111, "law_number": 295, "date": "Dec. 9, 2010"},
                    "relationship": "Amendment",
                },
            ],
            "amendments": [
                {"law": {"congress": 111, "law_number": 295}, "year": 2010},
            ],
        }
        result = _compute_last_modified_date_from_notes(normalized_notes)
        assert result == date(2010, 12, 9)

    def test_17_usc_106_citation_date(self) -> None:
        """Regression: 17 USC §106 last_modified_date must be 2002-11-02, not 2002-01-01."""
        normalized_notes = {
            "citations": [
                {
                    "law": {"congress": 94, "law_number": 553, "date": "Oct. 19, 1976"},
                    "relationship": "Enactment",
                },
                {
                    "law": {"congress": 107, "law_number": 273, "date": "Nov. 2, 2002"},
                    "relationship": "Amendment",
                },
            ],
            "amendments": [
                {"law": {"congress": 107, "law_number": 273}, "year": 2002},
            ],
        }
        result = _compute_last_modified_date_from_notes(normalized_notes)
        assert result == date(2002, 11, 2)

    def test_fallback_to_year_only_when_no_citation_dates(self) -> None:
        """Year-only fallback is used when no amendment citations have dates."""
        normalized_notes = {
            "citations": [
                {
                    "law": {"congress": 94, "law_number": 553},
                    "relationship": "Enactment",
                },
                {
                    # Amendment citation but no date field
                    "law": {"congress": 102, "law_number": 492},
                    "relationship": "Amendment",
                },
            ],
            "amendments": [
                {"law": {"congress": 102, "law_number": 492}, "year": 1992},
            ],
        }
        result = _compute_last_modified_date_from_notes(normalized_notes)
        # Falls back to year-only since citation has no date
        assert result == date(1992, 1, 1)

    def test_no_amendments_and_no_citation_dates_returns_none(self) -> None:
        """Returns None when neither citations nor amendments provide dates."""
        normalized_notes = {
            "citations": [
                {
                    "law": {"congress": 94, "law_number": 553, "date": "Oct. 19, 1976"},
                    "relationship": "Enactment",
                },
            ],
            "amendments": [],
        }
        result = _compute_last_modified_date_from_notes(normalized_notes)
        assert result is None

    def test_empty_normalized_notes_returns_none(self) -> None:
        """Returns None for empty normalized_notes dict."""
        result = _compute_last_modified_date_from_notes({})
        assert result is None
