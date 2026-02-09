"""US Code models: SectionGroup, Section, Line."""

from datetime import date
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.history import LineHistory, SectionHistory
    from app.models.public_law import LawChange, PublicLaw


class SectionGroup(Base, TimestampMixin):
    """A recursive structural node in the US Code hierarchy.

    Replaces USCodeTitle, USCodeChapterGroup, USCodeChapter, and
    USCodeSubchapter with a single self-referential model.  The
    ``group_type`` discriminator indicates the level (title, subtitle,
    part, division, chapter, subchapter, etc.) and ``parent_id`` forms
    the tree.  Root nodes (titles) have ``parent_id IS NULL``.
    """

    __tablename__ = "section_group"

    group_id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("section_group.group_id", ondelete="CASCADE"), nullable=True
    )
    group_type: Mapped[str] = mapped_column(String(50), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Title-specific fields (nullable, only populated for group_type='title')
    is_positive_law: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    positive_law_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    positive_law_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # Self-referential relationships
    parent: Mapped[Optional["SectionGroup"]] = relationship(
        remote_side="SectionGroup.group_id",
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children: Mapped[list["SectionGroup"]] = relationship(
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan",
    )
    sections: Mapped[list["USCodeSection"]] = relationship(
        back_populates="group", foreign_keys="USCodeSection.group_id"
    )

    __table_args__ = (
        # No duplicate children under the same parent
        UniqueConstraint(
            "parent_id",
            "group_type",
            "number",
            name="uq_section_group_child",
        ),
        Index("idx_section_group_parent", "parent_id"),
        Index("idx_section_group_type", "group_type"),
        Index("idx_section_group_sort", "parent_id", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<SectionGroup({self.group_type} {self.number}: {self.name})>"


class USCodeSection(Base, TimestampMixin):
    """An individual section of the US Code."""

    __tablename__ = "us_code_section"

    section_id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("section_group.group_id", ondelete="SET NULL"), nullable=True
    )
    title_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[str] = mapped_column(String(50), nullable=False)
    heading: Mapped[str] = mapped_column(Text, nullable=False)
    full_citation: Mapped[str] = mapped_column(String(200), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    enacted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_modified_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_positive_law: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    title_positive_law_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    statutes_at_large_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    is_repealed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    repealed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    repealed_by_law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_notes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    normalized_provisions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped[Optional["SectionGroup"]] = relationship(
        back_populates="sections", foreign_keys=[group_id]
    )
    repealed_by_law: Mapped[Optional["PublicLaw"]] = relationship(
        foreign_keys=[repealed_by_law_id]
    )
    lines: Mapped[list["USCodeLine"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    history: Mapped[list["SectionHistory"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    changes: Mapped[list["LawChange"]] = relationship(back_populates="section")

    __table_args__ = (
        UniqueConstraint(
            "title_number", "section_number", name="uq_section_title_number"
        ),
        CheckConstraint(
            "(is_repealed = FALSE AND repealed_date IS NULL) OR "
            "(is_repealed = TRUE AND repealed_date IS NOT NULL)",
            name="ck_us_code_section_repealed_consistency",
        ),
        Index("idx_section_group", "group_id"),
        Index("idx_section_title_number", "title_number"),
        Index("idx_section_number", "title_number", "section_number"),
        Index("idx_section_citation", "full_citation"),
        Index(
            "idx_section_active",
            "is_repealed",
            postgresql_where="is_repealed = FALSE",
        ),
        Index("idx_section_sort", "group_id", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<USCodeSection({self.full_citation})>"


class USCodeLine(Base):
    """A single line of text within a section, for blame view support."""

    __tablename__ = "us_code_line"

    line_id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_section.section_id", ondelete="CASCADE"), nullable=False
    )
    parent_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("us_code_line.line_id", ondelete="SET NULL"), nullable=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_header: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    subsection_path: Mapped[str | None] = mapped_column(String(100), nullable=True)
    depth_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="SET NULL"), nullable=True
    )
    last_modified_by_law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="SET NULL"), nullable=True
    )
    codified_by_law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="SET NULL"), nullable=True
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    codification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    section: Mapped["USCodeSection"] = relationship(back_populates="lines")
    parent_line: Mapped[Optional["USCodeLine"]] = relationship(
        remote_side=[line_id], foreign_keys=[parent_line_id]
    )
    created_by_law: Mapped[Optional["PublicLaw"]] = relationship(
        foreign_keys=[created_by_law_id]
    )
    modified_by_law: Mapped[Optional["PublicLaw"]] = relationship(
        foreign_keys=[last_modified_by_law_id]
    )
    codified_by_law: Mapped[Optional["PublicLaw"]] = relationship(
        foreign_keys=[codified_by_law_id]
    )
    history: Mapped[list["LineHistory"]] = relationship(
        back_populates="line", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("section_id", "line_number", name="uq_line_section_number"),
        CheckConstraint("depth_level >= 0", name="ck_us_code_line_depth_positive"),
        Index("idx_line_section", "section_id"),
        Index("idx_line_section_order", "section_id", "line_number"),
        Index(
            "idx_line_current",
            "section_id",
            "is_current",
            postgresql_where="is_current = TRUE",
        ),
        Index("idx_line_created_by", "created_by_law_id"),
        Index("idx_line_modified_by", "last_modified_by_law_id"),
        Index("idx_line_codified_by", "codified_by_law_id"),
        Index("idx_line_parent", "parent_line_id"),
        Index("idx_line_depth", "section_id", "depth_level"),
        Index("idx_line_hash", "text_hash"),
    )

    def __repr__(self) -> str:
        return f"<USCodeLine({self.section_id}:{self.line_number})>"
