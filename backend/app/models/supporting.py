"""Supporting models: SectionReference, Committee, DataIngestionLog, etc."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import Chamber, ReferenceType

if TYPE_CHECKING:
    from app.models.public_law import Bill
    from app.models.us_code import USCodeSection


class SectionReference(Base, TimestampMixin):
    """A cross-reference between two sections of the US Code."""

    __tablename__ = "section_reference"

    reference_id: Mapped[int] = mapped_column(primary_key=True)
    source_section_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_section.section_id", ondelete="CASCADE"), nullable=False
    )
    target_section_id: Mapped[int] = mapped_column(
        ForeignKey("us_code_section.section_id", ondelete="CASCADE"), nullable=False
    )
    reference_type: Mapped[ReferenceType] = mapped_column(
        enum_column(ReferenceType, "reference_type"), nullable=False
    )
    source_subsection_path: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    target_subsection_path: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    source_section: Mapped["USCodeSection"] = relationship(
        foreign_keys=[source_section_id]
    )
    target_section: Mapped["USCodeSection"] = relationship(
        foreign_keys=[target_section_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "source_section_id",
            "target_section_id",
            "reference_type",
            "source_subsection_path",
            name="uq_section_reference",
        ),
        CheckConstraint(
            "source_section_id != target_section_id",
            name="ck_section_reference_no_self_ref",
        ),
        Index("idx_ref_source", "source_section_id"),
        Index("idx_ref_target", "target_section_id"),
        Index("idx_ref_type", "reference_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<SectionReference({self.source_section_id} -> {self.target_section_id})>"
        )


class Committee(Base, TimestampMixin):
    """A congressional committee."""

    __tablename__ = "committee"

    committee_id: Mapped[int] = mapped_column(primary_key=True)
    committee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    chamber: Mapped[Chamber] = mapped_column(
        enum_column(Chamber, "chamber"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    parent_committee_id: Mapped[int | None] = mapped_column(
        ForeignKey("committee.committee_id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    parent_committee: Mapped[Optional["Committee"]] = relationship(
        remote_side=[committee_id]
    )
    bill_assignments: Mapped[list["BillCommitteeAssignment"]] = relationship(
        back_populates="committee"
    )

    __table_args__ = (Index("idx_committee_chamber", "chamber"),)

    def __repr__(self) -> str:
        return f"<Committee({self.committee_code}: {self.name})>"


class BillCommitteeAssignment(Base, TimestampMixin):
    """Assignment of a bill to a committee."""

    __tablename__ = "bill_committee_assignment"

    assignment_id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="CASCADE"), nullable=False
    )
    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committee.committee_id", ondelete="CASCADE"), nullable=False
    )
    referral_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    bill: Mapped["Bill"] = relationship()
    committee: Mapped["Committee"] = relationship(back_populates="bill_assignments")

    __table_args__ = (
        UniqueConstraint("bill_id", "committee_id", name="uq_bill_committee"),
        Index("idx_assignment_bill", "bill_id"),
        Index("idx_assignment_committee", "committee_id"),
    )

    def __repr__(self) -> str:
        return f"<BillCommitteeAssignment(bill={self.bill_id}, committee={self.committee_id})>"


class Amendment(Base, TimestampMixin):
    """An amendment to a bill."""

    __tablename__ = "amendment"

    amendment_id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="CASCADE"), nullable=False
    )
    amendment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    chamber: Mapped[Chamber] = mapped_column(
        enum_column(Chamber, "chamber"), nullable=False
    )
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sponsor_id: Mapped[int | None] = mapped_column(
        ForeignKey("legislator.legislator_id", ondelete="SET NULL"), nullable=True
    )
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    bill: Mapped["Bill"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "congress", "amendment_number", name="uq_amendment_congress_number"
        ),
        Index("idx_amendment_bill", "bill_id"),
        Index("idx_amendment_congress", "congress"),
    )

    def __repr__(self) -> str:
        return f"<Amendment({self.amendment_number})>"


class DataIngestionLog(Base):
    """Audit log for data pipeline operations."""

    __tablename__ = "data_ingestion_log"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ingestion_source", "source"),
        Index("idx_ingestion_status", "status"),
        Index("idx_ingestion_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<DataIngestionLog({self.source}: {self.operation})>"


class DataCorrection(Base, TimestampMixin):
    """Audit log for manual data corrections."""

    __tablename__ = "data_correction"

    correction_id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_correction_table", "table_name"),
        Index("idx_correction_record", "table_name", "record_id"),
        Index("idx_correction_date", "corrected_at"),
    )

    def __repr__(self) -> str:
        return f"<DataCorrection({self.table_name}.{self.field_name})>"
