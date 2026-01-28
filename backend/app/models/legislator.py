"""Legislator models: Legislator, LegislatorTerm, Sponsorship, Vote."""

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import Chamber, PoliticalParty, SponsorshipRole, VoteType

if TYPE_CHECKING:
    from app.models.public_law import Bill, PublicLaw


class Legislator(Base, TimestampMixin):
    """A member of Congress."""

    __tablename__ = "legislator"

    legislator_id: Mapped[int] = mapped_column(primary_key=True)
    bioguide_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    thomas_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    govtrack_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opensecrets_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fec_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    suffix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    party: Mapped[PoliticalParty | None] = mapped_column(
        Enum(PoliticalParty, name="political_party"), nullable=True
    )
    state: Mapped[str | None] = mapped_column(CHAR(2), nullable=True)
    district: Mapped[str | None] = mapped_column(String(10), nullable=True)
    current_chamber: Mapped[Chamber | None] = mapped_column(
        Enum(Chamber, name="chamber"), nullable=True
    )
    is_current_member: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    first_served: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_served: Mapped[date | None] = mapped_column(Date, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    death_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    terms: Mapped[list["LegislatorTerm"]] = relationship(
        back_populates="legislator", cascade="all, delete-orphan"
    )
    sponsorships: Mapped[list["Sponsorship"]] = relationship(
        back_populates="legislator"
    )
    individual_votes: Mapped[list["IndividualVote"]] = relationship(
        back_populates="legislator"
    )

    __table_args__ = (
        Index(
            "idx_legislator_current",
            "is_current_member",
            postgresql_where="is_current_member = TRUE",
        ),
        Index("idx_legislator_state", "state"),
        Index("idx_legislator_party", "party"),
    )

    def __repr__(self) -> str:
        return f"<Legislator({self.full_name}, {self.state})>"


class LegislatorTerm(Base, TimestampMixin):
    """A single term served by a legislator."""

    __tablename__ = "legislator_term"

    term_id: Mapped[int] = mapped_column(primary_key=True)
    legislator_id: Mapped[int] = mapped_column(
        ForeignKey("legislator.legislator_id", ondelete="CASCADE"), nullable=False
    )
    chamber: Mapped[Chamber] = mapped_column(
        Enum(Chamber, name="chamber"), nullable=False
    )
    state: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    district: Mapped[str | None] = mapped_column(String(10), nullable=True)
    party: Mapped[PoliticalParty] = mapped_column(
        Enum(PoliticalParty, name="political_party"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    congress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_rank: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    legislator: Mapped["Legislator"] = relationship(back_populates="terms")

    __table_args__ = (
        Index("idx_term_legislator", "legislator_id"),
        Index("idx_term_congress", "congress"),
        Index("idx_term_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<LegislatorTerm({self.chamber.value}, {self.state}, {self.start_date})>"
        )


class Sponsorship(Base, TimestampMixin):
    """A sponsorship or co-sponsorship of a law or bill."""

    __tablename__ = "sponsorship"

    sponsorship_id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="CASCADE"), nullable=True
    )
    bill_id: Mapped[int | None] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="CASCADE"), nullable=True
    )
    legislator_id: Mapped[int] = mapped_column(
        ForeignKey("legislator.legislator_id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[SponsorshipRole] = mapped_column(
        Enum(SponsorshipRole, name="sponsorship_role"), nullable=False
    )
    sponsorship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    withdrawn_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    law: Mapped[Optional["PublicLaw"]] = relationship(
        back_populates="sponsorships", foreign_keys=[law_id]
    )
    bill: Mapped[Optional["Bill"]] = relationship(
        back_populates="sponsorships", foreign_keys=[bill_id]
    )
    legislator: Mapped["Legislator"] = relationship(back_populates="sponsorships")

    __table_args__ = (
        CheckConstraint(
            "(law_id IS NOT NULL AND bill_id IS NULL) OR "
            "(law_id IS NULL AND bill_id IS NOT NULL)",
            name="ck_sponsorship_law_or_bill",
        ),
        Index("idx_sponsorship_legislator", "legislator_id"),
        Index(
            "idx_sponsorship_sponsor",
            "law_id",
            "role",
            postgresql_where="role = 'Sponsor'",
        ),
        Index("idx_sponsorship_law", "law_id"),
        Index("idx_sponsorship_bill", "bill_id"),
    )

    def __repr__(self) -> str:
        target = f"law {self.law_id}" if self.law_id else f"bill {self.bill_id}"
        return f"<Sponsorship({self.role.value} of {target})>"


class Vote(Base, TimestampMixin):
    """An aggregate vote record for a law or bill."""

    __tablename__ = "vote"

    vote_id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="CASCADE"), nullable=True
    )
    bill_id: Mapped[int | None] = mapped_column(
        ForeignKey("bill.bill_id", ondelete="CASCADE"), nullable=True
    )
    chamber: Mapped[Chamber] = mapped_column(
        Enum(Chamber, name="chamber"), nullable=False
    )
    vote_date: Mapped[date] = mapped_column(Date, nullable=False)
    vote_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    session: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yeas: Mapped[int] = mapped_column(Integer, default=0)
    nays: Mapped[int] = mapped_column(Integer, default=0)
    present: Mapped[int] = mapped_column(Integer, default=0)
    not_voting: Mapped[int] = mapped_column(Integer, default=0)
    required_majority: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    law: Mapped[Optional["PublicLaw"]] = relationship(
        back_populates="votes", foreign_keys=[law_id]
    )
    bill: Mapped[Optional["Bill"]] = relationship(
        back_populates="votes", foreign_keys=[bill_id]
    )
    individual_votes: Mapped[list["IndividualVote"]] = relationship(
        back_populates="vote", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_vote_chamber", "chamber"),
        Index("idx_vote_date", "vote_date"),
        Index("idx_vote_law", "law_id"),
        Index("idx_vote_bill", "bill_id"),
    )

    def __repr__(self) -> str:
        return f"<Vote({self.chamber.value}, {self.vote_date})>"


class IndividualVote(Base):
    """A single legislator's vote on a specific vote."""

    __tablename__ = "individual_vote"

    individual_vote_id: Mapped[int] = mapped_column(primary_key=True)
    vote_id: Mapped[int] = mapped_column(
        ForeignKey("vote.vote_id", ondelete="CASCADE"), nullable=False
    )
    legislator_id: Mapped[int] = mapped_column(
        ForeignKey("legislator.legislator_id", ondelete="RESTRICT"), nullable=False
    )
    vote_cast: Mapped[VoteType] = mapped_column(
        Enum(VoteType, name="vote_type"), nullable=False
    )

    # Relationships
    vote: Mapped["Vote"] = relationship(back_populates="individual_votes")
    legislator: Mapped["Legislator"] = relationship(back_populates="individual_votes")

    __table_args__ = (
        UniqueConstraint(
            "vote_id", "legislator_id", name="uq_individual_vote_vote_legislator"
        ),
        Index("idx_individual_vote_legislator", "legislator_id"),
        Index("idx_individual_vote_vote", "vote_id"),
    )

    def __repr__(self) -> str:
        return f"<IndividualVote({self.vote_cast.value})>"
