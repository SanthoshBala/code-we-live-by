"""OLRC Release Point model — a snapshot of the US Code through a specific Public Law."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class OLRCReleasePoint(Base, TimestampMixin):
    """An OLRC release point — a snapshot of the US Code through a specific Public Law.

    Release points are published by the Office of Law Revision Counsel (OLRC) 2-4
    times per month and represent the official state of the US Code after incorporating
    enacted legislation.

    In the version control analogy, release points serve as "OLRC commits" that
    aggregate changes from multiple Public Laws into validated snapshots.
    """

    __tablename__ = "olrc_release_point"

    release_point_id: Mapped[int] = mapped_column(primary_key=True)
    full_identifier: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    law_identifier: Mapped[str] = mapped_column(String(30), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    titles_updated: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    parent_release_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("olrc_release_point.release_point_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    parent: Mapped[Optional["OLRCReleasePoint"]] = relationship(
        remote_side="OLRCReleasePoint.release_point_id",
        foreign_keys=[parent_release_point_id],
    )

    __table_args__ = (
        Index("idx_release_point_congress", "congress"),
        Index("idx_release_point_parent", "parent_release_point_id"),
        UniqueConstraint("congress", "law_identifier", name="uq_release_point_congress_law"),
    )

    def __repr__(self) -> str:
        return f"<OLRCReleasePoint({self.full_identifier})>"
