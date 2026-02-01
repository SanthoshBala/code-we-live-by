"""Pydantic schemas for Public Law entities.

These schemas are used for API responses and data transfer between
the pipeline and application layers.
"""

from pydantic import BaseModel, Field, computed_field

from app.models.enums import LawLevel


class PublicLawSchema(BaseModel):
    """In-memory representation of a Public Law.

    For the database model, see PublicLaw in app/models/public_law.py.
    """

    congress: int = Field(..., description="Congress number (e.g., 94)")
    law_number: int = Field(..., description="Law number within congress (e.g., 553)")
    date: str | None = Field(None, description="Enactment date (e.g., 'Oct. 19, 1976')")
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

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return a sort key for chronological ordering.

        Uses (congress, law_number) which gives chronological order
        since congress numbers increase over time.
        """
        return (self.congress, self.law_number)


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
    """A reference to a Public Law that enacted or amended a section.

    Like an import statement, this links a section to the law that
    created or modified it. Source laws are ordered chronologically:
    - First source law (order=0) = the law that created/enacted the section
    - Subsequent source laws = amendments in historical order

    Example: "Pub. L. 94-553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
    """

    law: PublicLawSchema = Field(..., description="The referenced Public Law")
    path: list[LawPathComponent] = Field(
        default_factory=list,
        description="Hierarchical path within the law (e.g., [div. C, tit. III, §101])",
    )
    raw_text: str = Field("", description="The original citation text")
    order: int = Field(
        0, description="Position in source list (0 = original/creating law)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_law_id(self) -> str:
        """Return the Public Law identifier (e.g., 'PL 94-553')."""
        return self.law.public_law_id

    @property
    def congress(self) -> int:
        """Return the congress number."""
        return self.law.congress

    @property
    def law_number(self) -> int:
        """Return the law number."""
        return self.law.law_number

    @property
    def date(self) -> str | None:
        """Return the enactment date."""
        return self.law.date

    @property
    def stat_reference(self) -> str | None:
        """Return the Statutes at Large reference."""
        return self.law.stat_reference

    @property
    def stat_volume(self) -> int | None:
        """Return the Statutes at Large volume."""
        return self.law.stat_volume

    @property
    def stat_page(self) -> int | None:
        """Return the Statutes at Large page."""
        return self.law.stat_page

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_original(self) -> bool:
        """Return True if this is the original/creating law (first source)."""
        return self.order == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def path_display(self) -> str:
        """Return the full path as a display string (e.g., 'div. C, tit. III, §101')."""
        if not self.path:
            return ""
        return ", ".join(comp.to_display() for comp in self.path)

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return a sort key for chronological ordering."""
        return self.law.sort_key

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
