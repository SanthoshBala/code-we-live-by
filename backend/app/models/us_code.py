"""US Code models: Title, Chapter, Section, Line."""

from datetime import date
from typing import TYPE_CHECKING, Optional

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.history import LineHistory, SectionHistory
    from app.models.public_law import LawChange, PublicLaw


class USCodeTitle(Base, TimestampMixin):
    """A title of the US Code (e.g., Title 17 - Copyrights)."""

    __tablename__ = "us_code_title"

    title_id: Mapped[int] = mapped_column(primary_key=True)
    title_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title_name: Mapped[str] = mapped_column(String(500), nullable=False)
    is_positive_law: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    positive_law_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    positive_law_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # Relationships
    chapters: Mapped[list["USCodeChapter"]] = relationship(
        back_populates="title", cascade="all, delete-orphan"
    )
    sections: Mapped[list["USCodeSection"]] = relationship(back_populates="title")

    __table_args__ = (
        CheckConstraint(
            "(is_positive_law = FALSE AND positive_law_date IS NULL) OR "
            "(is_positive_law = TRUE AND positive_law_date IS NOT NULL)",
            name="ck_us_code_title_positive_law_consistency",
        ),
    )

    def __repr__(self) -> str:
        return f"<USCodeTitle({self.title_number}: {self.title_name})>"


class USCodeChapter(Base, TimestampMixin):
    """A chapter within a US Code title."""

    __tablename__ = "us_code_chapter"

    chapter_id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_title.title_id", ondelete="CASCADE"), nullable=False
    )
    chapter_number: Mapped[str] = mapped_column(String(50), nullable=False)
    chapter_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    title: Mapped["USCodeTitle"] = relationship(back_populates="chapters")
    subchapters: Mapped[list["USCodeSubchapter"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )
    sections: Mapped[list["USCodeSection"]] = relationship(back_populates="chapter")

    __table_args__ = (
        UniqueConstraint("title_id", "chapter_number", name="uq_chapter_title_number"),
        Index("idx_chapter_sort", "title_id", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<USCodeChapter({self.chapter_number}: {self.chapter_name})>"


class USCodeSubchapter(Base, TimestampMixin):
    """A subchapter within a US Code chapter."""

    __tablename__ = "us_code_subchapter"

    subchapter_id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_chapter.chapter_id", ondelete="CASCADE"), nullable=False
    )
    subchapter_number: Mapped[str] = mapped_column(String(50), nullable=False)
    subchapter_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    chapter: Mapped["USCodeChapter"] = relationship(back_populates="subchapters")
    sections: Mapped[list["USCodeSection"]] = relationship(back_populates="subchapter")

    __table_args__ = (
        UniqueConstraint(
            "chapter_id", "subchapter_number", name="uq_subchapter_chapter_number"
        ),
        Index("idx_subchapter_chapter", "chapter_id"),
        Index("idx_subchapter_sort", "chapter_id", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<USCodeSubchapter({self.subchapter_number}: {self.subchapter_name})>"


class USCodeSection(Base, TimestampMixin):
    """An individual section of the US Code."""

    __tablename__ = "us_code_section"

    section_id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_title.title_id", ondelete="RESTRICT"), nullable=False
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("us_code_chapter.chapter_id", ondelete="SET NULL"), nullable=True
    )
    subchapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("us_code_subchapter.subchapter_id", ondelete="SET NULL"),
        nullable=True,
    )
    section_number: Mapped[str] = mapped_column(String(50), nullable=False)
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
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
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    title: Mapped["USCodeTitle"] = relationship(back_populates="sections")
    chapter: Mapped[Optional["USCodeChapter"]] = relationship(back_populates="sections")
    subchapter: Mapped[Optional["USCodeSubchapter"]] = relationship(
        back_populates="sections"
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
        UniqueConstraint("title_id", "section_number", name="uq_section_title_number"),
        CheckConstraint(
            "(is_repealed = FALSE AND repealed_date IS NULL) OR "
            "(is_repealed = TRUE AND repealed_date IS NOT NULL)",
            name="ck_us_code_section_repealed_consistency",
        ),
        Index("idx_section_title", "title_id"),
        Index("idx_section_chapter", "chapter_id"),
        Index("idx_section_subchapter", "subchapter_id"),
        Index("idx_section_number", "title_id", "section_number"),
        Index("idx_section_citation", "full_citation"),
        Index(
            "idx_section_active",
            "is_repealed",
            postgresql_where="is_repealed = FALSE",
        ),
        Index("idx_section_sort", "chapter_id", "sort_order"),
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
