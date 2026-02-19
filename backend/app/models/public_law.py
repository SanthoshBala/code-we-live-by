"""Public Law and Bill models."""

from datetime import date
from typing import TYPE_CHECKING, Optional

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

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import BillStatus, BillType, ChangeType, LawType

if TYPE_CHECKING:
    from app.models.legislator import Sponsorship, Vote


class PublicLaw(Base, TimestampMixin):
    """A public law enacted by Congress."""

    __tablename__ = "public_law"

    law_id: Mapped[int] = mapped_column(primary_key=True)
    law_number: Mapped[str] = mapped_column(String(20), nullable=False)
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    law_type: Mapped[LawType] = mapped_column(
        enum_column(LawType, "law_type"), default=LawType.PUBLIC, nullable=False
    )
    popular_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    bill_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bill_id: Mapped[int | None] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="SET NULL"), nullable=True
    )
    introduced_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    house_passed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    senate_passed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    presented_to_president_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    enacted_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    president: Mapped[str | None] = mapped_column(String(100), nullable=True)
    presidential_action: Mapped[str | None] = mapped_column(
        String(50), default="Signed", nullable=True
    )
    veto_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    veto_override_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sections_affected: Mapped[int] = mapped_column(Integer, default=0)
    sections_added: Mapped[int] = mapped_column(Integer, default=0)
    sections_modified: Mapped[int] = mapped_column(Integer, default=0)
    sections_repealed: Mapped[int] = mapped_column(Integer, default=0)
    govinfo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    congress_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    statutes_at_large_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # Relationships
    origin_bill: Mapped[Optional["Bill"]] = relationship(
        back_populates="resulting_law", foreign_keys=[bill_id]
    )
    changes: Mapped[list["LawChange"]] = relationship(
        back_populates="law", cascade="all, delete-orphan"
    )
    sponsorships: Mapped[list["Sponsorship"]] = relationship(
        back_populates="law",
        primaryjoin="PublicLaw.law_id == Sponsorship.law_id",
        cascade="all, delete-orphan",
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="law",
        primaryjoin="PublicLaw.law_id == Vote.law_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("congress", "law_number", name="uq_law_congress_number"),
        CheckConstraint(
            "congress >= 1 AND congress <= 200",
            name="ck_public_law_congress_range",
        ),
        Index("idx_law_number", "congress", "law_number"),
        Index("idx_law_congress", "congress"),
        Index("idx_law_enacted", "enacted_date"),
        Index("idx_law_effective", "effective_date"),
        Index("idx_law_popular_name", "popular_name"),
        Index("idx_law_president", "president"),
    )

    def __repr__(self) -> str:
        return f"<PublicLaw(PL {self.congress}-{self.law_number})>"


class Bill(Base, TimestampMixin):
    """A bill introduced in Congress."""

    __tablename__ = "bill"

    bill_id: Mapped[int] = mapped_column(primary_key=True)
    bill_number: Mapped[str] = mapped_column(String(50), nullable=False)
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    bill_type: Mapped[BillType] = mapped_column(
        enum_column(BillType, "bill_type"), nullable=False
    )
    status: Mapped[BillStatus] = mapped_column(
        enum_column(BillStatus, "bill_status"),
        default=BillStatus.INTRODUCED,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    introduced_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    congress_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    resulting_law: Mapped[Optional["PublicLaw"]] = relationship(
        back_populates="origin_bill", foreign_keys="PublicLaw.bill_id"
    )
    proposed_changes: Mapped[list["ProposedChange"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )
    sponsorships: Mapped[list["Sponsorship"]] = relationship(
        back_populates="bill",
        primaryjoin="Bill.bill_id == Sponsorship.bill_id",
        cascade="all, delete-orphan",
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="bill",
        primaryjoin="Bill.bill_id == Vote.bill_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("congress", "bill_number", name="uq_bill_congress_number"),
        CheckConstraint(
            "congress >= 1 AND congress <= 200",
            name="ck_bill_congress_range",
        ),
        Index("idx_bill_congress", "congress"),
        Index("idx_bill_status", "status"),
        Index(
            "idx_bill_pending",
            "status",
            postgresql_where="status NOT IN ('Became_Law', 'Failed', 'Vetoed', 'Died_in_Committee')",
        ),
    )

    def __repr__(self) -> str:
        return f"<Bill({self.bill_number}, {self.congress}th Congress)>"


class LawChange(Base, TimestampMixin):
    """A change made to a US Code section by a public law."""

    __tablename__ = "law_change"

    change_id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="CASCADE"), nullable=False
    )
    title_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(
        enum_column(ChangeType, "change_type"), nullable=False
    )
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subsection_path: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    law: Mapped["PublicLaw"] = relationship(back_populates="changes")

    __table_args__ = (
        Index("idx_change_law", "law_id"),
        Index("idx_change_title_section", "title_number", "section_number"),
        Index(
            "idx_change_law_title_section", "law_id", "title_number", "section_number"
        ),
    )

    def __repr__(self) -> str:
        return f"<LawChange({self.change_type.value} by law {self.law_id})>"


class ProposedChange(Base, TimestampMixin):
    """A proposed change to a US Code section by a pending bill."""

    __tablename__ = "proposed_change"

    change_id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("us_code_section.section_id", ondelete="SET NULL"), nullable=True
    )
    change_type: Mapped[ChangeType] = mapped_column(
        enum_column(ChangeType, "change_type"), nullable=False
    )
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subsection_path: Mapped[str | None] = mapped_column(String(100), nullable=True)
    likelihood_score: Mapped[float | None] = mapped_column(nullable=True)

    # Relationships
    bill: Mapped["Bill"] = relationship(back_populates="proposed_changes")

    __table_args__ = (
        CheckConstraint(
            "likelihood_score IS NULL OR "
            "(likelihood_score >= 0 AND likelihood_score <= 1)",
            name="ck_proposed_change_likelihood_range",
        ),
        Index("idx_proposed_change_bill", "bill_id"),
        Index("idx_proposed_change_section", "section_id"),
    )

    def __repr__(self) -> str:
        return f"<ProposedChange({self.change_type.value} by bill {self.bill_id})>"
