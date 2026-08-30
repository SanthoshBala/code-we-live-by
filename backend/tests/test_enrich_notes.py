"""Unit tests for amendment law metadata enrichment helpers (issue #561).

Tests for _format_enacted_date, _parse_stat_citation, and the
_enrich_notes_with_titles amendment join path in app.crud.us_code.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.us_code import _format_enacted_date, _parse_stat_citation
from app.models.enums import SourceRelationship
from app.schemas.public_law import PublicLawSchema, SourceLawSchema
from app.schemas.us_code import AmendmentSchema, SectionNotesSchema


class TestFormatEnactedDate:
    """Tests for the _format_enacted_date helper."""

    def test_december(self) -> None:
        assert _format_enacted_date(date(1990, 12, 1)) == "Dec. 1, 1990"

    def test_october(self) -> None:
        assert _format_enacted_date(date(1976, 10, 19)) == "Oct. 19, 1976"

    def test_may_no_period(self) -> None:
        # May has no trailing period by convention
        assert _format_enacted_date(date(2021, 5, 7)) == "May 7, 2021"

    def test_january(self) -> None:
        assert _format_enacted_date(date(2002, 1, 5)) == "Jan. 5, 2002"

    def test_single_digit_day(self) -> None:
        assert _format_enacted_date(date(1990, 12, 1)) == "Dec. 1, 1990"


class TestParseStatCitation:
    """Tests for the _parse_stat_citation helper."""

    def test_standard(self) -> None:
        assert _parse_stat_citation("104 Stat. 5134") == ("104", 5134)

    def test_letter_suffix_volume(self) -> None:
        # Pre-1957 codification volumes have a letter suffix (e.g. 70A)
        assert _parse_stat_citation("70A Stat. 1") == ("70A", 1)

    def test_none_input(self) -> None:
        assert _parse_stat_citation(None) == (None, None)

    def test_empty_string(self) -> None:
        assert _parse_stat_citation("") == (None, None)

    def test_malformed(self) -> None:
        assert _parse_stat_citation("not a citation") == (None, None)


class TestEnrichNotesWithTitlesAmendmentPath:
    """Regression tests for issue #561: amendments[].law.date/stat_volume/stat_page null.

    The _enrich_notes_with_titles function must apply the same DB join for
    amendments that it already uses for citations when those fields are null.
    """

    @pytest.mark.asyncio
    async def test_amendment_law_date_backfilled_from_db(self) -> None:
        """Amendment law.date is populated from public_law.enacted_date when null in JSONB."""
        from app.crud.us_code import _enrich_notes_with_titles

        notes = SectionNotesSchema(
            amendments=[
                AmendmentSchema(
                    law=PublicLawSchema(congress=101, law_number=650),
                    year=1990,
                    description="Pub. L. 101-650 amended subsection (a).",
                )
            ],
        )

        # Mock a DB row for PL 101-650 with date and stat info
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda _, i: [
            101,  # congress
            "650",  # law_number
            None,  # short_title
            None,  # official_title
            date(1990, 12, 1),  # enacted_date
            "104 Stat. 5134",  # statutes_at_large_citation
        ][i]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda _: iter([mock_row])

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        await _enrich_notes_with_titles(mock_session, notes)

        law = notes.amendments[0].law
        assert law is not None
        assert law.date == "Dec. 1, 1990"
        assert law.stat_volume == "104"
        assert law.stat_page == 5134

    @pytest.mark.asyncio
    async def test_amendment_already_has_all_fields_no_db_call(self) -> None:
        """No DB query is made when all enrichable fields are already set in JSONB."""
        from app.crud.us_code import _enrich_notes_with_titles

        notes = SectionNotesSchema(
            amendments=[
                AmendmentSchema(
                    law=PublicLawSchema(
                        congress=101,
                        law_number=650,
                        short_title="Judicial Improvements Act",  # all fields set
                        date="Dec. 1, 1990",
                        stat_volume="104",
                        stat_page=5134,
                    ),
                    year=1990,
                    description="Pub. L. 101-650 amended subsection (a).",
                )
            ],
        )

        # Pairs collection should skip this law since all enrichable fields are present
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        await _enrich_notes_with_titles(mock_session, notes)

        # execute should not have been called (pairs was empty)
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_amendment_date_not_overridden_when_already_set(self) -> None:
        """Amendment law.date is preserved when already in JSONB; DB value is not applied."""
        from app.crud.us_code import _enrich_notes_with_titles

        notes = SectionNotesSchema(
            amendments=[
                AmendmentSchema(
                    law=PublicLawSchema(
                        congress=101,
                        law_number=650,
                        # date and stat already in JSONB but short_title is missing
                        date="Dec. 1, 1990",
                        stat_volume="104",
                        stat_page=5134,
                    ),
                    year=1990,
                    description="Pub. L. 101-650 amended subsection (a).",
                )
            ],
        )

        # DB row would return a different date to confirm the existing value is not overridden
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda _, i: [
            101,
            "650",
            "Judicial Improvements Act",  # short_title from DB
            None,
            date(1990, 12, 1),
            "104 Stat. 5134",
        ][i]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda _: iter([mock_row])

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        await _enrich_notes_with_titles(mock_session, notes)

        law = notes.amendments[0].law
        assert law is not None
        # short_title was null so it gets backfilled from DB
        assert law.short_title == "Judicial Improvements Act"
        # date and stat were already set — must not be overridden
        assert law.date == "Dec. 1, 1990"
        assert law.stat_volume == "104"
        assert law.stat_page == 5134

    @pytest.mark.asyncio
    async def test_citation_and_amendment_same_pl_both_enriched(self) -> None:
        """When the same PL appears in both citations and amendments, both are enriched."""
        from app.crud.us_code import _enrich_notes_with_titles

        notes = SectionNotesSchema(
            citations=[
                SourceLawSchema(
                    law=PublicLawSchema(congress=101, law_number=650),
                    relationship=SourceRelationship.AMENDMENT,
                    raw_text="Pub. L. 101-650",
                    order=1,
                )
            ],
            amendments=[
                AmendmentSchema(
                    law=PublicLawSchema(congress=101, law_number=650),
                    year=1990,
                    description="Pub. L. 101-650 amended subsection (a).",
                )
            ],
        )

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda _, i: [
            101,
            "650",
            None,
            None,
            date(1990, 12, 1),
            "104 Stat. 5134",
        ][i]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda _: iter([mock_row])

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        await _enrich_notes_with_titles(mock_session, notes)

        citation_law = notes.citations[0].law
        assert citation_law is not None
        assert citation_law.date == "Dec. 1, 1990"
        assert citation_law.stat_volume == "104"

        amendment_law = notes.amendments[0].law
        assert amendment_law is not None
        assert amendment_law.date == "Dec. 1, 1990"
        assert amendment_law.stat_volume == "104"
        assert amendment_law.stat_page == 5134
