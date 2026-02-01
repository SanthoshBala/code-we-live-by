"""Pydantic schemas for US Code entities.

These schemas are used for API responses and data transfer between
the pipeline and application layers.
"""

from enum import Enum

from pydantic import BaseModel, Field, computed_field

from app.schemas.public_law import PublicLawSchema, SourceLawSchema


class CodeLineSchema(BaseModel):
    """A single line of statutory text (in-memory representation).

    This is the in-memory representation of a line, used during parsing
    and display. For the database model, see USCodeLine.

    Attributes:
        line_number: 1-indexed line number in the normalized output.
        content: The text content of this line (without leading indentation).
        indent_level: Nesting depth (0 = top level, 1 = (a), 2 = (1), etc.).
        marker: The list item marker if this is a list item, e.g., "(a)".
        is_header: Whether this line is a header (should be rendered bold).
        start_char: Character position in original text where this line starts.
        end_char: Character position in original text where this line ends.
    """

    line_number: int = Field(..., ge=1, description="1-indexed line number")
    content: str = Field(..., description="Text content without indentation")
    indent_level: int = Field(..., ge=0, description="Nesting depth")
    marker: str | None = Field(None, description="List item marker (e.g., '(a)')")
    is_header: bool = Field(False, description="Whether this is a header line")
    start_char: int = Field(..., ge=0, description="Start position in original text")
    end_char: int = Field(..., ge=0, description="End position in original text")

    def to_display(self, use_tabs: bool = True, indent_width: int = 4) -> str:
        """Return the line with proper indentation for display.

        Args:
            use_tabs: If True, use tab characters. If False, use spaces.
            indent_width: Number of spaces per indent level (only used if use_tabs=False).
        """
        if use_tabs:
            indent = "\t" * self.indent_level
        else:
            indent = " " * (self.indent_level * indent_width)
        return f"{indent}{self.content}"


class CodeReferenceSchema(BaseModel):
    """An in-text reference to another section of the US Code.

    Captures references like "section 106 of title 17" or "subsection (a)(1)"
    found within statutory text.
    """

    title: int | None = Field(None, description="Title number (e.g., 17)")
    section: str | None = Field(None, description="Section number (e.g., '106')")
    subsection: str | None = Field(None, description="Subsection path (e.g., '(a)(1)')")
    raw_text: str = Field("", description="The original reference text")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_citation(self) -> str:
        """Return the full citation string."""
        if self.title and self.section:
            base = f"{self.title} U.S.C. § {self.section}"
            if self.subsection:
                return f"{base}{self.subsection}"
            return base
        elif self.section:
            if self.subsection:
                return f"section {self.section}{self.subsection}"
            return f"section {self.section}"
        elif self.subsection:
            return f"subsection {self.subsection}"
        return self.raw_text


class AmendmentSchema(BaseModel):
    """A single amendment to a section.

    Represents one change made to a section by a Public Law,
    like a commit in version control.
    """

    law: PublicLawSchema = Field(
        ..., description="The Public Law that made this amendment"
    )
    year: int = Field(..., description="Year of the amendment")
    description: str = Field(..., description="Description of what changed")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_law_id(self) -> str:
        """Return normalized PL identifier."""
        return self.law.public_law_id

    @property
    def congress(self) -> int:
        """Return the congress number."""
        return self.law.congress

    @property
    def law_number(self) -> int:
        """Return the law number."""
        return self.law.law_number


class ShortTitleSchema(BaseModel):
    """A short title (common name) for an act."""

    title: str = Field(
        ..., description="The short title (e.g., 'Philanthropy Protection Act of 1995')"
    )
    year: int | None = Field(None, description="Year from the title")
    public_law: str | None = Field(None, description="Associated Public Law reference")


class NoteCategoryEnum(str, Enum):
    """Category of a section note in the US Code.

    The OLRC organizes notes into three main categories:
    - HISTORICAL: Legislative history from original codification
    - EDITORIAL: OLRC editorial annotations added for clarity
    - STATUTORY: Provisions from enacting laws not part of Code text
    """

    HISTORICAL = "historical"
    EDITORIAL = "editorial"
    STATUTORY = "statutory"


class SectionNoteSchema(BaseModel):
    """A single note within a US Code section.

    Notes are organized by the OLRC under headers like "Codification",
    "Effective Date of 1995 Amendment", "Performing Rights Society
    Consent Decrees", etc. This class captures both the header and
    content, allowing dynamic storage of any note type.

    Example headers by category:
    - HISTORICAL: "House Report No. 94-1476", "Senate Report No. 99-541"
    - EDITORIAL: "Codification", "References in Text", "Amendments", "Prior Provisions"
    - STATUTORY: "Effective Date of 1995 Amendment", "Short Title",
                 "Performing Rights Society Consent Decrees", "Regulations"
    """

    header: str = Field(..., description="Note header (e.g., 'Codification')")
    content: str = Field(..., description="Note body text")
    category: NoteCategoryEnum = Field(
        ..., description="Which section this note belongs to"
    )


class SectionNotesSchema(BaseModel):
    """Metadata notes extracted from a US Code section.

    These are separated from the law text and treated like documentation.
    The OLRC organizes notes into three main categories:

    1. Historical and Revision Notes - Legislative history from codification
    2. Editorial Notes - OLRC editorial annotations (codification, references, amendments)
    3. Statutory Notes - Provisions from enacting laws that aren't part of the Code itself

    This class uses a hybrid approach:
    - Structured fields for high-value, consistently formatted data (citations,
      amendments, effective_dates, short_titles)
    - Dynamic SectionNote list for all other notes, preserving their headers
      and content for flexible rendering

    Example section: 17 USC 106
    """

    # =========================================================================
    # STRUCTURED FIELDS - Specially parsed for rich data
    # =========================================================================

    # Citations (>90% of sections)
    # Structured references to Public Laws that enacted/amended this section.
    citations: list[SourceLawSchema] = Field(
        default_factory=list,
        description="Public Laws that enacted/amended this section",
    )

    # Amendments (~70-80% of sections) - Most common note type
    amendments: list[AmendmentSchema] = Field(
        default_factory=list,
        description="Chronological list of changes to this section",
    )

    # Short Titles (<10% of sections)
    short_titles: list[ShortTitleSchema] = Field(
        default_factory=list,
        description="Popular names for acts",
    )

    # =========================================================================
    # DYNAMIC NOTES - All other notes with header/content preserved
    # =========================================================================

    notes: list[SectionNoteSchema] = Field(
        default_factory=list,
        description="All notes organized by header",
    )

    # =========================================================================
    # SECTION STATUS - Metadata about the section's current state
    # =========================================================================

    transferred_to: str | None = Field(
        None, description="New location if section was moved"
    )
    omitted: bool = Field(
        False, description="Whether section was omitted from the Code"
    )
    renumbered_from: str | None = Field(
        None, description="Previous section number if renumbered"
    )

    # =========================================================================
    # RAW/UNPARSED CONTENT
    # =========================================================================

    raw_notes: str = Field("", description="Full raw text of all notes (fallback)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_notes(self) -> bool:
        """Return True if any notes were extracted."""
        return bool(self.raw_notes.strip()) or len(self.notes) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_citations(self) -> bool:
        """Return True if any citations were parsed."""
        return len(self.citations) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_amendments(self) -> bool:
        """Return True if any amendments were parsed."""
        return len(self.amendments) > 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_transferred(self) -> bool:
        """Return True if section was transferred to another location."""
        return self.transferred_to is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_omitted(self) -> bool:
        """Return True if section was omitted."""
        return self.omitted

    def notes_by_category(self, category: NoteCategoryEnum) -> list[SectionNoteSchema]:
        """Get all notes in a specific category."""
        return [n for n in self.notes if n.category == category]

    @property
    def historical_notes(self) -> list[SectionNoteSchema]:
        """Get all historical and revision notes."""
        return self.notes_by_category(NoteCategoryEnum.HISTORICAL)

    @property
    def editorial_notes(self) -> list[SectionNoteSchema]:
        """Get all editorial notes."""
        return self.notes_by_category(NoteCategoryEnum.EDITORIAL)

    @property
    def statutory_notes(self) -> list[SectionNoteSchema]:
        """Get all statutory notes."""
        return self.notes_by_category(NoteCategoryEnum.STATUTORY)
