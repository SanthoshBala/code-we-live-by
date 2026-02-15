"""Pydantic schemas for the Law Viewer QC tool.

These schemas support the /api/v1/laws endpoints used to browse
and inspect parsed law text and amendments.
"""

from pydantic import BaseModel, Field


class LawSummarySchema(BaseModel):
    """Summary of a Public Law for the index listing."""

    congress: int = Field(..., description="Congress number (e.g., 117)")
    law_number: str = Field(..., description="Law number within congress")
    official_title: str | None = Field(None, description="Formal title of the law")
    short_title: str | None = Field(None, description="Short/popular title")
    enacted_date: str = Field(..., description="Enacted date as ISO string")
    sections_affected: int = Field(0, description="Number of USC sections affected")


class LawTextSchema(BaseModel):
    """Raw text content of a Public Law (HTM and/or XML)."""

    congress: int
    law_number: str
    official_title: str | None = None
    short_title: str | None = None
    enacted_date: str | None = None
    introduced_date: str | None = None
    house_passed_date: str | None = None
    senate_passed_date: str | None = None
    presented_to_president_date: str | None = None
    effective_date: str | None = None
    htm_content: str | None = Field(None, description="HTML text of the law")
    xml_content: str | None = Field(None, description="USLM XML text of the law")


class SectionReferenceSchema(BaseModel):
    """A reference to a US Code section."""

    title: int | None = None
    section: str
    subsection_path: str | None = None
    display: str = Field("", description="Formatted display string")


class PositionQualifierSchema(BaseModel):
    """Positional context for an amendment."""

    type: str
    anchor_text: str | None = None
    target_text: str | None = None


class ParsedAmendmentSchema(BaseModel):
    """A parsed amendment extracted from Public Law text."""

    pattern_name: str = Field(..., description="Name of the matching pattern")
    pattern_type: str = Field(..., description="Type of amendment pattern")
    change_type: str = Field(..., description="Change type (Add, Modify, Delete, etc.)")
    section_ref: SectionReferenceSchema | None = None
    old_text: str | None = None
    new_text: str | None = None
    full_match: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    needs_review: bool = False
    context: str = ""
    position_qualifier: PositionQualifierSchema | None = None
