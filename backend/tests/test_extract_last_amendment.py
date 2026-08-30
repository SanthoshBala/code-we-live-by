"""Unit tests for `_extract_last_amendment` in `app.crud.us_code`.

Regression coverage for issue #679: sections whose most recent amendment was
enacted before the Public Law numbering system began (84th Congress, 1957)
carry a chapter-style Statutes-at-Large citation rather than a "PL X-Y"
identifier.  The structure endpoint's `last_amendment_law` field must surface
such citations instead of returning ``null``.
"""

from app.crud.us_code import _extract_last_amendment, _pre_pl_act_citation


class TestExtractLastAmendment:
    """Coverage for `_extract_last_amendment` populator."""

    def test_returns_pl_identifier_for_modern_amendment(self) -> None:
        """Post-1957 amendments with a Pub. L. reference keep the PL string."""
        notes = {
            "amendments": [
                {
                    "year": 2002,
                    "law": {"congress": 107, "law_number": 169},
                    "description": "Pub. L. 107-169 substituted 'Bureau' for 'Board'.",
                },
            ],
        }

        year, law = _extract_last_amendment(notes)

        assert year == 2002
        assert law == "PL 107-169"

    def test_returns_act_citation_for_pre_1957_amendment(self) -> None:
        """Pre-1957 chapter-style amendments surface a Statutes-at-Large citation.

        Reproduces the observed §7-of-Title-9 case from issue #679: the section
        was last amended by "Act Oct. 31, 1951, ch. 655, § 14, 65 Stat. 715"
        and the structure endpoint returned ``null`` for `last_amendment_law`.
        """
        notes = {
            "amendments": [
                {
                    "year": 1951,
                    "law": None,
                    "description": (
                        "Act Oct. 31, 1951, ch. 655, § 14, 65 Stat. 715, "
                        'substituted "United States district court for" for '
                        '"United States court in and for".'
                    ),
                },
            ],
        }

        year, law = _extract_last_amendment(notes)

        assert year == 1951
        assert law == "Act Oct. 31, 1951, ch. 655, 65 Stat. 715"

    def test_returns_none_when_notes_missing(self) -> None:
        """Absent notes produce (None, None)."""
        assert _extract_last_amendment(None) == (None, None)
        assert _extract_last_amendment({}) == (None, None)
        assert _extract_last_amendment({"amendments": []}) == (None, None)

    def test_returns_year_only_when_citation_unparseable(self) -> None:
        """A description with neither a PL nor an Act citation returns law=None."""
        notes = {
            "amendments": [
                {
                    "year": 1949,
                    "law": None,
                    "description": "Amendment note text without a recognizable citation.",
                },
            ],
        }

        year, law = _extract_last_amendment(notes)

        assert year == 1949
        assert law is None


class TestPrePlActCitation:
    """Coverage for the `_pre_pl_act_citation` extractor."""

    def test_extracts_full_citation_with_chapter_and_stat(self) -> None:
        """The chapter and Statutes-at-Large fragments are both preserved."""
        description = (
            "Act Sept. 3, 1954, ch. 1263, § 19, 68 Stat. 1233, brought section "
            "into conformity with arbitration rules."
        )

        assert (
            _pre_pl_act_citation(description)
            == "Act Sept. 3, 1954, ch. 1263, 68 Stat. 1233"
        )

    def test_extracts_date_only_when_no_chapter_or_stat(self) -> None:
        """A minimal "Act <date>" description yields just the date fragment."""
        description = (
            "Act Sept. 3, 1954, brought section into conformity with arbitration "
            "rules of the Federal Rules of Civil Procedure."
        )

        assert _pre_pl_act_citation(description) == "Act Sept. 3, 1954"

    def test_extracts_date_and_chapter_only(self) -> None:
        """A description with a chapter but no Stat. reference includes only the chapter."""
        description = (
            'Act Oct. 31, 1951, ch. 655, substituted "United States district '
            'court for" for "United States court in and for".'
        )

        assert _pre_pl_act_citation(description) == "Act Oct. 31, 1951, ch. 655"

    def test_returns_none_for_non_act_description(self) -> None:
        """A description without an "Act <date>" pattern returns None."""
        assert _pre_pl_act_citation("Pub. L. 107-169 substituted 'Bureau'.") is None
        assert _pre_pl_act_citation("") is None
