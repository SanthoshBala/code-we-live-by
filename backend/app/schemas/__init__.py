"""Pydantic schemas module.

This module contains Pydantic models used for:
- API request/response validation
- Data transfer between layers (pipeline, core, API)

Naming convention:
- Schema suffix to distinguish from SQLAlchemy models
- Law* prefix for Public Law entities
- Code* prefix for US Code entities
"""

from app.models.enums import LawLevel, SourceRelationship
from app.schemas.public_law import (
    ActSchema,
    LawPathComponent,
    PublicLawSchema,
    SourceLawSchema,
)
from app.schemas.us_code import (
    AmendmentSchema,
    CodeLineSchema,
    CodeReferenceSchema,
    NoteCategoryEnum,
    SectionGroupTreeSchema,
    SectionNoteSchema,
    SectionNotesSchema,
    SectionSummarySchema,
    SectionViewerSchema,
    ShortTitleSchema,
    TitleStructureSchema,
    TitleSummarySchema,
)

__all__ = [
    # Public Law schemas
    "PublicLawSchema",
    "ActSchema",
    "SourceLawSchema",
    "LawPathComponent",
    "LawLevel",
    "SourceRelationship",
    # US Code schemas
    "CodeLineSchema",
    "CodeReferenceSchema",
    "AmendmentSchema",
    "ShortTitleSchema",
    "NoteCategoryEnum",
    "SectionNoteSchema",
    "SectionNotesSchema",
    # Section viewer schemas
    "SectionViewerSchema",
    # Tree navigation schemas
    "TitleSummarySchema",
    "SectionSummarySchema",
    "SectionGroupTreeSchema",
    "TitleStructureSchema",
]
