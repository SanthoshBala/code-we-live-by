"""CodeRevision model — the 'commit' in the chronological pipeline.

Each revision represents a point in time in the US Code's history: either an
OLRC release point (ground truth from XML) or a Public Law (derived by applying
amendments to the previous revision's state).
"""

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import RevisionStatus, RevisionType

if TYPE_CHECKING:
    from app.models.public_law import PublicLaw
    from app.models.release_point import OLRCReleasePoint
    from app.models.snapshot import SectionSnapshot


class CodeRevision(Base, TimestampMixin):
    """A point-in-time revision of the US Code.

    In the version control analogy, this is a "commit". Release point
    revisions are ground truth (parsed from OLRC XML). Public law revisions
    are derived (by applying amendments to the previous state).

    The parent chain forms a linked list: initial commit -> RP -> law -> law -> RP -> ...
    """

    __tablename__ = "code_revision"

    revision_id: Mapped[int] = mapped_column(primary_key=True)
    revision_type: Mapped[str] = mapped_column(
        enum_column(RevisionType, "revision_type_enum"),
        nullable=False,
    )
    release_point_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("olrc_release_point.release_point_id", ondelete="SET NULL"),
        nullable=True,
    )
    law_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("public_law.law_id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_revision_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("code_revision.revision_id", ondelete="SET NULL"),
        nullable=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_ground_truth: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[str] = mapped_column(
        enum_column(RevisionStatus, "revision_status_enum"),
        default=RevisionStatus.PENDING.value,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Global ordering position in the timeline"
    )

    # Relationships
    release_point: Mapped[Optional["OLRCReleasePoint"]] = relationship(
        foreign_keys=[release_point_id],
    )
    law: Mapped[Optional["PublicLaw"]] = relationship(
        foreign_keys=[law_id],
    )
    parent: Mapped[Optional["CodeRevision"]] = relationship(
        remote_side="CodeRevision.revision_id",
        foreign_keys=[parent_revision_id],
    )
    snapshots: Mapped[list["SectionSnapshot"]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Each release point and law should only have one revision
        UniqueConstraint(
            "release_point_id",
            name="uq_code_revision_release_point",
        ),
        UniqueConstraint(
            "law_id",
            name="uq_code_revision_law",
        ),
        UniqueConstraint(
            "sequence_number",
            name="uq_code_revision_sequence",
        ),
        Index("idx_code_revision_parent", "parent_revision_id"),
        Index("idx_code_revision_effective_date", "effective_date"),
        Index("idx_code_revision_status", "status"),
    )

    def __repr__(self) -> str:
        if self.revision_type == RevisionType.RELEASE_POINT.value:
            return f"<CodeRevision(RP, id={self.revision_id})>"
        return f"<CodeRevision(Law, id={self.revision_id})>"
