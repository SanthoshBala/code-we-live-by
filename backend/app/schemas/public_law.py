"""Pydantic schemas for Public Law entities.

These schemas are used for API responses and data transfer between
the pipeline and application layers.
"""

from pydantic import BaseModel, Field, computed_field


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


class SourceLawSchema(BaseModel):
    """A reference to a Public Law that enacted or amended a section.

    Like an import statement, this links a section to the law that
    created or modified it. Source laws are ordered chronologically:
    - First source law (order=0) = the law that created/enacted the section
    - Subsequent source laws = amendments in historical order

    Example: "Pub. L. 94-553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
    """

    law: PublicLawSchema = Field(..., description="The referenced Public Law")
    title: str | None = Field(None, description="Title within the law (e.g., 'I')")
    section: str | None = Field(
        None, description="Section within the law (e.g., '101')"
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

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return a sort key for chronological ordering."""
        return self.law.sort_key
