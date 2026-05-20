"""CODEOWNERS models: CommitteeCongressInstance, CommitteeUSCodeMapping."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
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
    from app.models.supporting import Committee


class CommitteeCongressInstance(Base, TimestampMixin):
    """Per-Congress metadata for a committee, including raw Rule X jurisdiction text.

    Keyed to (committee_id, congress) so that committee renames and restructuring
    across Congresses are captured without modifying the stable Committee record.
    """

    __tablename__ = "committee_congress_instance"

    instance_id: Mapped[int] = mapped_column(primary_key=True)
    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committee.committee_id", ondelete="CASCADE"), nullable=False
    )
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    official_name: Mapped[str] = mapped_column(String(300), nullable=False)
    rule_citation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    jurisdiction_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    committee: Mapped["Committee"] = relationship()

    __table_args__ = (
        UniqueConstraint("committee_id", "congress", name="uq_cci_committee_congress"),
        Index("idx_cci_congress", "congress"),
        Index("idx_cci_committee_id", "committee_id"),
    )

    def __repr__(self) -> str:
        return f"<CommitteeCongressInstance({self.committee_id}, congress={self.congress})>"


class CommitteeUSCodeMapping(Base, TimestampMixin):
    """Human-curated mapping from a committee to a US Code title/chapter path.

    This is the authoritative CODEOWNERS layer — it bridges the prose jurisdiction
    language in Rule X (which never references the US Code directly) to actual
    US Code title/chapter paths. Maintained as a YAML fixture and loaded via CLI.

    congress_start/congress_end define the range of Congresses this mapping applies to.
    congress_end = NULL means the mapping is still current.
    chapter_number = NULL means the mapping applies at the Title level.
    """

    __tablename__ = "committee_usc_mapping"

    mapping_id: Mapped[int] = mapped_column(primary_key=True)
    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committee.committee_id", ondelete="CASCADE"), nullable=False
    )
    congress_start: Mapped[int] = mapped_column(Integer, nullable=False)
    congress_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    jurisdiction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    committee: Mapped["Committee"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "committee_id",
            "congress_start",
            "title_number",
            "chapter_number",
            "jurisdiction_type",
            name="uq_cum_committee_congress_path_type",
        ),
        CheckConstraint(
            "jurisdiction_type IN ('primary', 'secondary', 'oversight')",
            name="cum_jurisdiction_type",
        ),
        CheckConstraint(
            "congress_end IS NULL OR congress_end >= congress_start",
            name="cum_congress_range",
        ),
        Index("idx_cum_title", "title_number"),
        Index("idx_cum_title_chapter", "title_number", "chapter_number"),
        Index("idx_cum_committee_id", "committee_id"),
        Index("idx_cum_congress_range", "congress_start", "congress_end"),
    )

    def __repr__(self) -> str:
        path = (
            f"title {self.title_number}"
            if self.chapter_number is None
            else f"title {self.title_number} ch. {self.chapter_number}"
        )
        return f"<CommitteeUSCodeMapping({self.committee_id} → {path}, {self.jurisdiction_type})>"
