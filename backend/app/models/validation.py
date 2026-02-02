"""Validation models for legal parser ingestion (Task 1.11).

This module provides models for tracking parsing sessions, text coverage,
parsed amendments, and pattern learning for the graduated trust system.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    AmendmentReviewStatus,
    ChangeType,
    ParsingMode,
    ParsingSessionStatus,
    PatternDiscoveryStatus,
    SpanType,
    VerificationMethod,
    VerificationResult,
)

if TYPE_CHECKING:
    from app.models.public_law import PublicLaw


class ParsingSession(Base, TimestampMixin):
    """A session of parsing a Public Law for amendments.

    Tracks the mode, status, and escalation chain for parsing runs.
    Multiple parsing sessions can exist for a single law (e.g., initial
    regex parse, then LLM review, then human correction).
    """

    __tablename__ = "parsing_session"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[ParsingMode] = mapped_column(
        Enum(ParsingMode, name="parsing_mode"), nullable=False
    )
    status: Mapped[ParsingSessionStatus] = mapped_column(
        Enum(ParsingSessionStatus, name="parsing_session_status"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Escalation chain
    parent_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="SET NULL"), nullable=True
    )
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalated_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # "system" or user identifier

    # Session metadata
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    law: Mapped["PublicLaw"] = relationship()
    parent_session: Mapped[Optional["ParsingSession"]] = relationship(
        remote_side=[session_id]
    )
    text_spans: Mapped[list["TextSpan"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    parsed_amendments: Mapped[list["ParsedAmendmentRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    ingestion_report: Mapped[Optional["IngestionReport"]] = relationship(
        back_populates="session", uselist=False
    )
    verifications: Mapped[list["ParsingVerification"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_parsing_session_law", "law_id"),
        Index("idx_parsing_session_mode", "mode"),
        Index("idx_parsing_session_status", "status"),
        Index("idx_parsing_session_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<ParsingSession({self.session_id}: {self.mode.value} - {self.status.value})>"


class TextSpan(Base):
    """A span of text in a law's full text.

    Used to track which portions of the law text have been claimed by
    pattern matches and which remain unclaimed (potential gaps).
    """

    __tablename__ = "text_span"

    span_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="CASCADE"), nullable=False
    )
    # Character positions in the law's full text (0-indexed).
    # The span covers law_text[start_pos:end_pos] (Python slice notation).
    # Example: start_pos=100, end_pos=150 means characters 100-149 inclusive.
    start_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    span_type: Mapped[SpanType] = mapped_column(
        Enum(SpanType, name="span_type"), nullable=False
    )

    # For claimed spans
    amendment_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("parsed_amendment_record.record_id", ondelete="SET NULL"),
        nullable=True,
    )
    pattern_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # For unclaimed spans
    detected_keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of keywords

    # Relationships
    session: Mapped["ParsingSession"] = relationship(back_populates="text_spans")

    __table_args__ = (
        CheckConstraint("end_pos > start_pos", name="ck_text_span_valid_range"),
        CheckConstraint(
            "(span_type = 'Claimed' AND pattern_name IS NOT NULL) OR "
            "(span_type != 'Claimed')",
            name="ck_text_span_claimed_has_pattern",
        ),
        Index("idx_text_span_session", "session_id"),
        Index("idx_text_span_type", "span_type"),
        Index("idx_text_span_positions", "session_id", "start_pos", "end_pos"),
    )

    def __repr__(self) -> str:
        return f"<TextSpan({self.start_pos}-{self.end_pos}: {self.span_type.value})>"


class ParsedAmendmentRecord(Base, TimestampMixin):
    """A parsed amendment record with review workflow.

    Stores the output of parsing along with review status to enable
    correction workflows and pattern performance tracking.
    """

    __tablename__ = "parsed_amendment_record"

    record_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="CASCADE"), nullable=False
    )

    # Pattern information
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # PatternType value
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType, name="change_type"), nullable=False
    )

    # Section reference
    target_title: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_subsection_path: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Text changes
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Position in source law text (0-indexed, Python slice notation).
    # law_text[start_pos:end_pos] gives the matched text.
    start_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pos: Mapped[int] = mapped_column(Integer, nullable=False)

    # Confidence and review
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[AmendmentReviewStatus] = mapped_column(
        Enum(AmendmentReviewStatus, name="amendment_review_status"),
        default=AmendmentReviewStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Correction tracking
    corrected_pattern_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    corrected_section: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    session: Mapped["ParsingSession"] = relationship(back_populates="parsed_amendments")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_parsed_amendment_confidence_range",
        ),
        Index("idx_parsed_amendment_session", "session_id"),
        Index("idx_parsed_amendment_pattern", "pattern_name"),
        Index("idx_parsed_amendment_review", "review_status"),
        Index("idx_parsed_amendment_needs_review", "needs_review"),
        Index("idx_parsed_amendment_target", "target_title", "target_section"),
    )

    def __repr__(self) -> str:
        target = (
            f"{self.target_title} USC {self.target_section}"
            if self.target_title
            else "unknown"
        )
        return f"<ParsedAmendmentRecord({self.pattern_name}: {target})>"


class IngestionReport(Base, TimestampMixin):
    """Report on a parsing session's coverage and quality.

    Generated after a parsing session completes to track coverage stats,
    confidence scores, and auto-approve eligibility.
    """

    __tablename__ = "ingestion_report"

    report_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    law_id: Mapped[int] = mapped_column(
        ForeignKey("public_law.law_id", ondelete="CASCADE"), nullable=False
    )

    # Coverage statistics
    total_text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    unclaimed_flagged_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unclaimed_ignored_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Amendment statistics
    total_amendments: Mapped[int] = mapped_column(Integer, nullable=False)
    high_confidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Amendment counts by type (stored as JSON)
    amendments_by_type: Mapped[str | None] = mapped_column(
        JSONB, nullable=True
    )  # {"Add": 5, "Modify": 10, ...}
    amendments_by_pattern: Mapped[str | None] = mapped_column(
        JSONB, nullable=True
    )  # {"strike_insert_quoted": 8, ...}

    # Auto-approve decision
    auto_approve_eligible: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    escalation_recommended: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # External validation
    govinfo_amendment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amendment_count_mismatch: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )

    # Relationships
    session: Mapped["ParsingSession"] = relationship(back_populates="ingestion_report")
    law: Mapped["PublicLaw"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "coverage_percentage >= 0 AND coverage_percentage <= 100",
            name="ck_ingestion_report_coverage_range",
        ),
        CheckConstraint(
            "avg_confidence >= 0 AND avg_confidence <= 1",
            name="ck_ingestion_report_confidence_range",
        ),
        Index("idx_ingestion_report_law", "law_id"),
        Index("idx_ingestion_report_coverage", "coverage_percentage"),
        Index("idx_ingestion_report_eligible", "auto_approve_eligible"),
    )

    def __repr__(self) -> str:
        return f"<IngestionReport(law={self.law_id}, coverage={self.coverage_percentage:.1f}%)>"


class PatternDiscovery(Base, TimestampMixin):
    """A discovered pattern from unmatched text.

    Part of the learning loop: when text appears to contain amendments
    but doesn't match any pattern, record it for human review and
    potential pattern promotion.
    """

    __tablename__ = "pattern_discovery"

    discovery_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="CASCADE"), nullable=False
    )

    # Unmatched text and its position (0-indexed, Python slice notation).
    # law_text[start_pos:end_pos] gives the unmatched text.
    unmatched_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_pos: Mapped[int] = mapped_column(Integer, nullable=False)
    end_pos: Mapped[int] = mapped_column(Integer, nullable=False)

    # Suggested pattern (may be added during review)
    suggested_pattern_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    suggested_pattern_regex: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_pattern_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # Review workflow
    status: Mapped[PatternDiscoveryStatus] = mapped_column(
        Enum(PatternDiscoveryStatus, name="pattern_discovery_status"),
        default=PatternDiscoveryStatus.NEW,
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # If promoted, link to actual pattern
    promoted_pattern_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    __table_args__ = (
        Index("idx_pattern_discovery_session", "session_id"),
        Index("idx_pattern_discovery_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<PatternDiscovery({self.discovery_id}: {self.status.value})>"


class ParsingVerification(Base, TimestampMixin):
    """A verification of a parsing session's results.

    Multiple verifications can exist for a single parsing session,
    allowing quality to be measured by number and type of verifications.
    """

    __tablename__ = "parsing_verification"

    verification_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("parsing_session.session_id", ondelete="CASCADE"), nullable=False
    )

    # Who and when
    verified_by: Mapped[str] = mapped_column(String(100), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # How and result
    method: Mapped["VerificationMethod"] = mapped_column(
        Enum(VerificationMethod, name="verification_method"), nullable=False
    )
    result: Mapped["VerificationResult"] = mapped_column(
        Enum(VerificationResult, name="verification_result"), nullable=False
    )

    # Details
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-form notes: methodology, issues found, coverage gaps, etc.",
    )
    issues_found: Mapped[str | None] = mapped_column(
        JSONB, nullable=True
    )  # Structured list of issues if any

    # Relationships
    session: Mapped["ParsingSession"] = relationship(back_populates="verifications")

    __table_args__ = (
        Index("idx_parsing_verification_session", "session_id"),
        Index("idx_parsing_verification_result", "result"),
        Index("idx_parsing_verification_verified_at", "verified_at"),
    )

    def __repr__(self) -> str:
        return f"<ParsingVerification({self.verification_id}: {self.result.value} by {self.verified_by})>"
