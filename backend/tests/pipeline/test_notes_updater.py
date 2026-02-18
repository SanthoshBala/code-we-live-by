"""Tests for pipeline.chrono.notes_updater — pure unit tests, no DB."""

from datetime import date
from unittest.mock import MagicMock

from app.models.enums import ChangeType, SourceRelationship
from app.schemas.us_code import SectionNotesSchema
from pipeline.chrono.notes_updater import update_notes_for_applied_law


def _make_law(
    congress: int = 115,
    law_number: str = "97",
    enacted_date: date | None = None,
    short_title: str | None = "Tax Cuts and Jobs Act",
) -> MagicMock:
    """Create a minimal mock PublicLaw."""
    law = MagicMock()
    law.congress = congress
    law.law_number = law_number
    law.enacted_date = enacted_date or date(2017, 12, 22)
    law.official_title = None
    law.short_title = short_title
    return law


class TestNotesUpdater:
    """Tests for update_notes_for_applied_law."""

    def test_add_citation_to_empty_notes(self) -> None:
        """Creates schema from None existing_notes."""
        law = _make_law()
        updated_dict, raw = update_notes_for_applied_law(
            existing_notes=None,
            raw_notes=None,
            law=law,
            change_type=ChangeType.MODIFY,
            description="struck 'old text' and inserted 'new text'.",
        )
        schema = SectionNotesSchema.model_validate(updated_dict)
        assert len(schema.citations) == 1
        assert schema.citations[0].relationship == SourceRelationship.AMENDMENT
        assert schema.citations[0].law is not None
        assert schema.citations[0].law.congress == 115

    def test_add_citation_to_existing(self) -> None:
        """Appends citation without disturbing existing ones."""
        existing = SectionNotesSchema(
            citations=[],
            amendments=[],
        )
        # Add a pre-existing citation
        from app.schemas.public_law import PublicLawSchema, SourceLawSchema

        existing.citations.append(
            SourceLawSchema(
                law=PublicLawSchema(congress=94, law_number=553),
                relationship=SourceRelationship.ENACTMENT,
                raw_text="Pub. L. 94-553",
                order=0,
            )
        )
        existing_dict = existing.model_dump(mode="json")

        law = _make_law()
        updated_dict, raw = update_notes_for_applied_law(
            existing_notes=existing_dict,
            raw_notes="Existing notes.\n",
            law=law,
            change_type=ChangeType.MODIFY,
            description="amended subsection (a).",
        )
        schema = SectionNotesSchema.model_validate(updated_dict)
        assert len(schema.citations) == 2
        # Original citation preserved
        assert schema.citations[0].law.congress == 94  # type: ignore[union-attr]
        # New citation appended
        assert schema.citations[1].law.congress == 115  # type: ignore[union-attr]

    def test_add_amendment_entry(self) -> None:
        """Amendment entry has correct law ref and description."""
        law = _make_law()
        updated_dict, raw = update_notes_for_applied_law(
            existing_notes=None,
            raw_notes=None,
            law=law,
            change_type=ChangeType.MODIFY,
            description="substituted '10 percent' for '5 percent'.",
        )
        schema = SectionNotesSchema.model_validate(updated_dict)
        assert len(schema.amendments) == 1
        amendment = schema.amendments[0]
        assert amendment.year == 2017
        assert amendment.law.congress == 115
        assert "10 percent" in amendment.description

    def test_raw_notes_appended(self) -> None:
        """Raw text is updated with amendment line."""
        law = _make_law()
        _, raw = update_notes_for_applied_law(
            existing_notes=None,
            raw_notes="Prior notes.",
            law=law,
            change_type=ChangeType.MODIFY,
            description="struck 'old' and inserted 'new'.",
        )
        assert "2017" in raw
        assert "Pub. L. 115-97" in raw
        assert "Prior notes." in raw

    def test_preserves_existing_content(self) -> None:
        """Short titles and other notes are untouched."""
        from app.schemas.us_code import ShortTitleSchema

        existing = SectionNotesSchema(
            short_titles=[ShortTitleSchema(title="Tax Reform Act of 1986", year=1986)],
        )
        existing_dict = existing.model_dump(mode="json")

        law = _make_law()
        updated_dict, _ = update_notes_for_applied_law(
            existing_notes=existing_dict,
            raw_notes=None,
            law=law,
            change_type=ChangeType.MODIFY,
            description="amended paragraph (1).",
        )
        schema = SectionNotesSchema.model_validate(updated_dict)
        assert len(schema.short_titles) == 1
        assert schema.short_titles[0].title == "Tax Reform Act of 1986"
