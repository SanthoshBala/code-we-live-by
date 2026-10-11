"""Unit tests for _extract_last_amendment in app/crud/us_code.py.

Covers both post-1957 Public Law citations and pre-1957 chapter-style Act
citations (issue #679: last_amendment_law was null for pre-1957 statutes).
"""

from app.crud.us_code import _extract_last_amendment


class TestExtractLastAmendmentPostPublicLaw:
    """Post-1957 amendments carry congress + law_number → 'PL X-Y' format."""

    def test_post_1957_returns_pl_citation(self) -> None:
        """Normal PL citation is returned as 'PL {congress}-{law_number}'."""
        notes = {
            "amendments": [
                {"law": {"congress": 83, "law_number": 703}, "year": 1954},
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1954
        assert law == "PL 83-703"

    def test_most_recent_amendment_used(self) -> None:
        """First entry in the amendments list (newest-first) is used."""
        notes = {
            "amendments": [
                {"law": {"congress": 102, "law_number": 492}, "year": 1992},
                {"law": {"congress": 94, "law_number": 553}, "year": 1976},
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1992
        assert law == "PL 102-492"


class TestExtractLastAmendmentPrePublicLaw:
    """Pre-1957 amendments have law=None; citation is extracted from description."""

    def test_pre_1957_act_with_chapter_returns_short_citation(self) -> None:
        """Regression test for issue #679: pre-1957 act with ch. number in
        description returns 'Act {date}, ch. {N}' instead of null.

        Input mirrors the 9 U.S.C. § 4 scenario:
          description = "Act Sept. 3, 1954, ch. 1263, § 19, 68 Stat. 1233, struck out..."
        Expected: last_amendment_law = "Act Sept. 3, 1954, ch. 1263"
        """
        notes = {
            "amendments": [
                {
                    "law": None,
                    "year": 1954,
                    "description": (
                        "Act Sept. 3, 1954, ch. 1263, § 19, 68 Stat. 1233, "
                        "struck out subsec. (b) relating to removal."
                    ),
                }
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1954
        assert law == "Act Sept. 3, 1954, ch. 1263"

    def test_pre_1957_act_without_chapter_returns_date_only_citation(self) -> None:
        """When description has no ch. clause, the date portion is still returned."""
        notes = {
            "amendments": [
                {
                    "law": None,
                    "year": 1947,
                    "description": "Act July 30, 1947 substituted new text.",
                }
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1947
        assert law == "Act July 30, 1947"

    def test_pre_1957_act_missing_description_returns_none_law(self) -> None:
        """When law is None and description is empty, law falls back to None."""
        notes = {
            "amendments": [
                {
                    "law": None,
                    "year": 1950,
                    "description": "",
                }
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1950
        assert law is None

    def test_pre_1957_law_missing_entirely_falls_back_to_description(self) -> None:
        """Amendment entry with no 'law' key at all uses description fallback."""
        notes = {
            "amendments": [
                {
                    "year": 1951,
                    "description": "Act Oct. 31, 1951, ch. 655, § 14, 65 Stat. 722.",
                }
            ]
        }
        year, law = _extract_last_amendment(notes)
        assert year == 1951
        assert law == "Act Oct. 31, 1951, ch. 655"


class TestExtractLastAmendmentEdgeCases:
    """Edge-case guards: empty / null inputs."""

    def test_none_notes_returns_none_none(self) -> None:
        year, law = _extract_last_amendment(None)
        assert year is None
        assert law is None

    def test_empty_notes_returns_none_none(self) -> None:
        year, law = _extract_last_amendment({})
        assert year is None
        assert law is None

    def test_empty_amendments_list_returns_none_none(self) -> None:
        year, law = _extract_last_amendment({"amendments": []})
        assert year is None
        assert law is None
