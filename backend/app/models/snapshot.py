"""SectionSnapshot model — a section's content at a specific revision.

Only stores sections that changed at a given revision. For unchanged sections,
walk the parent revision chain to find the most recent snapshot.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
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
    from app.models.revision import CodeRevision


class SectionSnapshot(Base, TimestampMixin):
    """A section's content at a specific code revision.

    Keyed by (title_number, section_number), NOT FK to us_code_section.
    Old sections may not exist in the current table.

    Stores normalized_provisions (structured data) so the rendering layer
    can produce clean formatting. text_content is the plain-text extraction
    used for diffing.
    """

    __tablename__ = "section_snapshot"

    snapshot_id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("code_revision.revision_id", ondelete="CASCADE"),
        nullable=False,
    )
    title_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[str] = mapped_column(
        String(100), nullable=False, doc='e.g., "106", "80a-3a"'
    )
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_provisions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Raw notes text (historical, editorial, statutory)",
    )
    normalized_notes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Structured notes (SectionNotesSchema) for rendering",
    )
    text_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 of text_content for provision change detection",
    )
    notes_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 of notes for notes change detection",
    )
    full_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True, doc='e.g., "17 USC 106"'
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        doc="True if the section was repealed/removed at this revision",
    )

    # Relationships
    revision: Mapped["CodeRevision"] = relationship(
        back_populates="snapshots",
        foreign_keys=[revision_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "title_number",
            "section_number",
            name="uq_section_snapshot_revision_section",
        ),
        Index(
            "idx_section_snapshot_title_section",
            "title_number",
            "section_number",
        ),
        Index("idx_section_snapshot_text_hash", "text_hash"),
    )

    def __repr__(self) -> str:
        return (
            f"<SectionSnapshot("
            f"rev={self.revision_id}, "
            f"{self.title_number} USC {self.section_number}"
            f")>"
        )
