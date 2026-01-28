"""History models for time travel functionality: SectionHistory, LineHistory."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.models.public_law import PublicLaw
    from app.models.us_code import USCodeLine, USCodeSection


class SectionHistory(Base, TimestampMixin):
    """Historical snapshot of a section at a point in time."""

    __tablename__ = "section_history"

    history_id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_section.section_id", ondelete="CASCADE"), nullable=False
    )
    law_id: Mapped[int] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    superseded_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    section: Mapped["USCodeSection"] = relationship(back_populates="history")
    law: Mapped["PublicLaw"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "section_id", "version_number", name="uq_section_history_version"
        ),
        CheckConstraint(
            "superseded_date IS NULL OR superseded_date > effective_date",
            name="ck_section_history_dates",
        ),
        Index("idx_history_section", "section_id"),
        Index("idx_history_section_date", "section_id", "effective_date"),
        Index("idx_history_version", "section_id", "version_number"),
        Index("idx_history_law", "law_id"),
    )

    def __repr__(self) -> str:
        return f"<SectionHistory(section={self.section_id}, v{self.version_number})>"


class LineHistory(Base, TimestampMixin):
    """Historical snapshot of a line at a point in time."""

    __tablename__ = "line_history"

    line_history_id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_line.line_id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    subsection_path: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modified_by_law_id: Mapped[int] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="RESTRICT"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    superseded_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    line: Mapped["USCodeLine"] = relationship(back_populates="history")
    modified_by_law: Mapped["PublicLaw"] = relationship()

    __table_args__ = (
        UniqueConstraint("line_id", "version_number", name="uq_line_history_version"),
        CheckConstraint(
            "superseded_date IS NULL OR superseded_date > effective_date",
            name="ck_line_history_dates",
        ),
        Index("idx_line_history_line", "line_id"),
        Index("idx_line_history_line_date", "line_id", "effective_date"),
        Index("idx_line_history_version", "line_id", "version_number"),
        Index("idx_line_history_law", "modified_by_law_id"),
    )

    def __repr__(self) -> str:
        return f"<LineHistory(line={self.line_id}, v{self.version_number})>"
