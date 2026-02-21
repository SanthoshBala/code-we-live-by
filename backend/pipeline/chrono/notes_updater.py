"""Update section notes when a law change is applied.

Updates both structured normalized_notes (JSONB) and raw notes text
so that notes_hash changes when laws are applied, enabling accurate
checkpoint validation against release-point ground truth.
"""

from __future__ import annotations

import logging

from app.models.enums import ChangeType, SourceRelationship
from app.models.public_law import PublicLaw
from app.schemas.public_law import PublicLawSchema, SourceLawSchema
from app.schemas.us_code import (
    AmendmentSchema,
    NoteCategoryEnum,
    SectionNoteSchema,
    SectionNotesSchema,
)

logger = logging.getLogger(__name__)


def _law_to_schema(law: PublicLaw) -> PublicLawSchema:
    """Convert a PublicLaw ORM model to a PublicLawSchema."""
    return PublicLawSchema(
        congress=law.congress,
        law_number=int(law.law_number),
        date=law.enacted_date.isoformat() if law.enacted_date else None,
        official_title=law.official_title,
        short_title=law.short_title,
    )


def update_notes_for_applied_law(
    existing_notes: dict | None,
    raw_notes: str | None,
    law: PublicLaw,
    change_type: ChangeType,
    description: str,
    note_texts: list[str] | None = None,
) -> tuple[dict, str]:
    """Update notes metadata after applying a law change.

    Args:
        existing_notes: Current normalized_notes JSONB dict (or None).
        raw_notes: Current raw notes text (or None).
        law: The PublicLaw being applied.
        change_type: Type of change (MODIFY, ADD, DELETE, REPEAL).
        description: Human-readable description of the change.

    Returns:
        Tuple of (updated_normalized_notes_dict, updated_raw_notes_text).
    """
    # 1. Deserialize existing notes or create empty
    if existing_notes is not None:
        notes_schema = SectionNotesSchema.model_validate(existing_notes)
    else:
        notes_schema = SectionNotesSchema()

    law_schema = _law_to_schema(law)

    # 2. Append SourceLawSchema citation
    citation = SourceLawSchema(
        law=law_schema,
        relationship=SourceRelationship.AMENDMENT,
        raw_text=f"Pub. L. {law.congress}-{law.law_number}",
        order=len(notes_schema.citations),
    )
    notes_schema.citations.append(citation)

    # 3. Append AmendmentSchema entry
    year = law.enacted_date.year if law.enacted_date else 0
    amendment = AmendmentSchema(
        law=law_schema,
        year=year,
        description=description,
    )
    notes_schema.amendments.append(amendment)

    # 4. Add statutory note entries for ADD_NOTE changes
    if change_type == ChangeType.ADD_NOTE and note_texts:
        for text in note_texts:
            header = f"Pub. L. {law.congress}\u2013{law.law_number}"
            note_entry = SectionNoteSchema(
                header=header,
                content=text,
                category=NoteCategoryEnum.STATUTORY,
            )
            notes_schema.notes.append(note_entry)

    # 5. Re-serialize to dict for JSONB storage
    updated_dict = notes_schema.model_dump(mode="json")

    # 5. Append raw notes text line
    raw = raw_notes or ""
    year_str = str(year) if year else "????"
    amendment_line = (
        f"{year_str}\u2014Pub. L. {law.congress}-{law.law_number} {description}"
    )
    if raw and not raw.endswith("\n"):
        raw += "\n"
    raw += amendment_line + "\n"

    return updated_dict, raw
