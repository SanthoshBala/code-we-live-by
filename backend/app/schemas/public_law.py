"""Pydantic schemas for Public Law entities.

These schemas are used for API responses and data transfer between
the pipeline and application layers.
"""

from pydantic import BaseModel, Field, computed_field

from app.models.enums import LawLevel, SourceRelationship


class PublicLawSchema(BaseModel):
    """In-memory representation of a Public Law (post-1957).

    For the database model, see PublicLaw in app/models/public_law.py.
    """

    congress: int = Field(..., description="Congress number (e.g., 94)")
    law_number: int = Field(..., description="Law number within congress (e.g., 553)")
    date: str | None = Field(None, description="Enactment date (e.g., 'Oct. 19, 1976')")
    official_title: str | None = Field(
        None, description="Formal title (e.g., 'An act to amend...')"
    )
    short_title: str | None = Field(
        None,
        description="Primary short title (e.g., 'Coronavirus Aid, Relief, and Economic Security Act')",
    )
    short_title_aliases: list[str] = Field(
        default_factory=list,
        description="Alternative short titles (e.g., ['CARES Act'])",
    )
    stat_volume: int | None = Field(None, description="Statutes at Large volume")
    stat_page: int | None = Field(None, description="Statutes at Large page")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_law_id(self) -> str:
        """Return the Public Law identifier (e.g., 'PL 94-553')."""
        return f"PL {self.congress}-{self.law_number}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stat_reference(self) -> str | None:
        """Return the Statutes at Large reference (e.g., '90 Stat. 2546')."""
        if self.stat_volume and self.stat_page:
            return f"{self.stat_volume} Stat. {self.stat_page}"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_title(self) -> str | None:
        """Return the best title for display purposes.

        Prefers shorter/common names since the PL ID is shown separately.
        Priority: alias > short_title > official_title
        """
        if self.short_title_aliases:
            return self.short_title_aliases[0]
        if self.short_title:
            return self.short_title
        return self.official_title

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return a sort key for chronological ordering.

        Uses (congress, law_number) which gives chronological order
        since congress numbers increase over time.
        """
        return (self.congress, self.law_number)


class ActSchema(BaseModel):
    """Pre-1957 Act reference using date + chapter citation.

    Before 1957, laws were cited by enactment date and chapter number
    rather than congress and law number. Example: "Aug. 14, 1935, ch. 531"
    refers to the Social Security Act.
    """

    date: str = Field(..., description="Enactment date (e.g., 'Aug. 14, 1935')")
    chapter: int = Field(..., description="Chapter number in Statutes at Large")
    short_title: str | None = Field(
        None, description="Short title (e.g., 'Social Security Act')"
    )
    stat_volume: int | None = Field(None, description="Statutes at Large volume")
    stat_page: int | None = Field(None, description="Statutes at Large page")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def act_id(self) -> str:
        """Return the Act identifier.

        Returns just 'Act' since the date is shown separately and chapter
        is part of the path (like division/title for Public Laws).
        """
        return "Act"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stat_reference(self) -> str | None:
        """Return the Statutes at Large reference."""
        if self.stat_volume and self.stat_page:
            return f"{self.stat_volume} Stat. {self.stat_page}"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_title(self) -> str | None:
        """Return the title for display purposes."""
        return self.short_title

    @property
    def sort_key(self) -> tuple[str, int]:
        """Return a sort key for chronological ordering.

        Uses (date, chapter) for ordering pre-1957 acts.
        """
        return (self.date, self.chapter)


class LawPathComponent(BaseModel):
    """A single component in a hierarchical path within a Public Law.

    Represents one level in the structure, e.g., "div. C" or "§13210(4)(A)".
    """

    level: LawLevel = Field(..., description="The hierarchical level type")
    value: str = Field(
        ..., description="The identifier at this level (e.g., 'C', 'III')"
    )

    # Bluebook standard abbreviations for each level
    _ABBREVIATIONS: dict[LawLevel, str] = {
        LawLevel.DIVISION: "div.",
        LawLevel.TITLE: "tit.",
        LawLevel.SUBTITLE: "subtit.",
        LawLevel.CHAPTER: "ch.",
        LawLevel.SUBCHAPTER: "subch.",
        LawLevel.PART: "pt.",
        LawLevel.SUBPART: "subpt.",
        LawLevel.SECTION: "§",
    }

    def to_display(self) -> str:
        """Return abbreviated display like 'div. C' or '§13210(4)(A)'.

        Section is special-cased to omit the space after §.
        """
        abbrev = self._ABBREVIATIONS[self.level]
        if self.level == LawLevel.SECTION:
            return f"{abbrev}{self.value}"  # No space: §101
        return f"{abbrev} {self.value}"  # With space: div. C


class SourceLawSchema(BaseModel):
    """A reference to a law that enacted, amended, or provides framework for a section.

    Like an import statement, this links a section to laws that created or
    modified it. Source laws are ordered chronologically and include:
    - Framework: Pre-1957 Act providing structural context (where section is classified)
    - Enactment: The law that created/added the section content
    - Amendment: Laws that modified the section

    Can reference either a PublicLaw (post-1957) or an Act (pre-1957).

    Example: "Pub. L. 94-553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
    Example: "Aug. 14, 1935, ch. 531, title VI, § 601" (pre-1957 Act)
    """

    law: PublicLawSchema | None = Field(
        None, description="Post-1957 Public Law reference"
    )
    act: ActSchema | None = Field(None, description="Pre-1957 Act reference")
    path: list[LawPathComponent] = Field(
        default_factory=list,
        description="Hierarchical path within the law (e.g., [div. C, tit. III, §101])",
    )
    relationship: SourceRelationship = Field(
        SourceRelationship.ENACTMENT,
        description="How this law relates to the section (Framework, Enactment, Amendment)",
    )
    raw_text: str = Field("", description="The original citation text")
    order: int = Field(
        0, description="Position in source list (0 = first/oldest reference)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def law_id(self) -> str:
        """Return the law identifier (e.g., 'PL 94-553' or 'Act ch. 531')."""
        if self.law:
            return self.law.public_law_id
        elif self.act:
            return self.act.act_id
        return ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def law_title(self) -> str | None:
        """Return the law's display title (prefers short/common names)."""
        if self.law:
            return self.law.display_title
        elif self.act:
            return self.act.display_title
        return None

    # Keep public_law_id for backwards compatibility
    @property
    def public_law_id(self) -> str:
        """Return the Public Law identifier (e.g., 'PL 94-553')."""
        if self.law:
            return self.law.public_law_id
        return ""

    @property
    def congress(self) -> int | None:
        """Return the congress number (None for pre-1957 Acts)."""
        return self.law.congress if self.law else None

    @property
    def law_number(self) -> int | None:
        """Return the law number (None for pre-1957 Acts)."""
        return self.law.law_number if self.law else None

    @property
    def date(self) -> str | None:
        """Return the enactment date."""
        if self.law:
            return self.law.date
        elif self.act:
            return self.act.date
        return None

    @property
    def stat_reference(self) -> str | None:
        """Return the Statutes at Large reference."""
        if self.law:
            return self.law.stat_reference
        elif self.act:
            return self.act.stat_reference
        return None

    @property
    def stat_volume(self) -> int | None:
        """Return the Statutes at Large volume."""
        if self.law:
            return self.law.stat_volume
        elif self.act:
            return self.act.stat_volume
        return None

    @property
    def stat_page(self) -> int | None:
        """Return the Statutes at Large page."""
        if self.law:
            return self.law.stat_page
        elif self.act:
            return self.act.stat_page
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_original(self) -> bool:
        """Return True if this is the original/creating law (first source)."""
        return self.order == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_framework(self) -> bool:
        """Return True if this is a framework reference (pre-1957 Act structure)."""
        return self.relationship == SourceRelationship.FRAMEWORK

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_act(self) -> bool:
        """Return True if this references a pre-1957 Act."""
        return self.act is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def path_display(self) -> str:
        """Return the full path as a display string (e.g., 'div. C, tit. III, §101')."""
        if not self.path:
            return ""
        return ", ".join(comp.to_display() for comp in self.path)

    @property
    def sort_key(self) -> tuple[int, int] | tuple[str, int]:
        """Return a sort key for chronological ordering."""
        if self.law:
            return self.law.sort_key
        elif self.act:
            return self.act.sort_key
        return (0, 0)

    def get_component(self, level: LawLevel) -> str | None:
        """Get the value for a specific level in the path, or None if not present."""
        for comp in self.path:
            if comp.level == level:
                return comp.value
        return None

    @property
    def division(self) -> str | None:
        """Return the division identifier if present (e.g., 'C')."""
        return self.get_component(LawLevel.DIVISION)

    @property
    def title(self) -> str | None:
        """Return the title identifier if present (e.g., 'I', 'III')."""
        return self.get_component(LawLevel.TITLE)

    @property
    def section(self) -> str | None:
        """Return the section identifier if present (e.g., '101', '13210(4)(A)')."""
        return self.get_component(LawLevel.SECTION)
