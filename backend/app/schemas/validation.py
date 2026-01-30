"""Pydantic schemas for validation and ingestion reporting (Task 1.11).

These schemas are used for API responses and internal data transfer
related to the ingestion validation system.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AmendmentReviewStatus,
    ChangeType,
    ParsingMode,
    ParsingSessionStatus,
    PatternDiscoveryStatus,
)

# =============================================================================
# Text Span Schemas
# =============================================================================


class TextSpanClaimed(BaseModel):
    """A claimed span of text from parsing."""

    start_pos: int = Field(..., ge=0, description="Start position in source text")
    end_pos: int = Field(..., gt=0, description="End position in source text")
    amendment_id: int = Field(..., description="ID of the amendment record")
    pattern_name: str = Field(..., description="Name of the pattern that matched")

    @property
    def length(self) -> int:
        """Calculate span length."""
        return self.end_pos - self.start_pos


class TextSpanUnclaimed(BaseModel):
    """An unclaimed span of text that may contain amendments."""

    start_pos: int = Field(..., ge=0, description="Start position in source text")
    end_pos: int = Field(..., gt=0, description="End position in source text")
    text: str = Field(..., description="The unclaimed text content")
    contains_keywords: bool = Field(
        default=False, description="Whether amendment keywords were detected"
    )
    detected_keywords: list[str] = Field(
        default_factory=list, description="List of detected amendment keywords"
    )

    @property
    def length(self) -> int:
        """Calculate span length."""
        return self.end_pos - self.start_pos


# =============================================================================
# Coverage Report Schemas
# =============================================================================


class CoverageReport(BaseModel):
    """Report on text coverage from a parsing session."""

    total_length: int = Field(..., ge=0, description="Total text length")
    claimed_length: int = Field(..., ge=0, description="Length of claimed text")
    coverage_percentage: float = Field(
        ..., ge=0, le=100, description="Percentage of text covered"
    )
    claimed_spans: list[TextSpanClaimed] = Field(
        default_factory=list, description="All claimed spans"
    )
    flagged_unclaimed: list[TextSpanUnclaimed] = Field(
        default_factory=list,
        description="Unclaimed spans with amendment keywords (needs review)",
    )
    ignored_unclaimed_count: int = Field(
        default=0, description="Count of unclaimed spans without keywords"
    )


# =============================================================================
# Parsed Amendment Schemas
# =============================================================================


class SectionReferenceSchema(BaseModel):
    """Reference to a US Code section."""

    title: int | None = Field(None, description="US Code title number")
    section: str = Field(..., description="Section number/identifier")
    subsection_path: str | None = Field(
        None, description="Path to subsection (e.g., '(a)(1)(A)')"
    )


class ParsedAmendmentSchema(BaseModel):
    """A parsed amendment from the legal text."""

    record_id: int | None = Field(None, description="Database record ID (if saved)")
    pattern_name: str = Field(..., description="Name of the matched pattern")
    pattern_type: str = Field(..., description="Type of pattern")
    change_type: ChangeType = Field(..., description="Type of change")
    section_ref: SectionReferenceSchema | None = Field(
        None, description="Reference to affected section"
    )
    old_text: str | None = Field(None, description="Text being removed")
    new_text: str | None = Field(None, description="Text being added")
    start_pos: int = Field(..., ge=0, description="Start position in source")
    end_pos: int = Field(..., gt=0, description="End position in source")
    full_match_text: str = Field(..., description="The full matched text")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    needs_review: bool = Field(
        default=False, description="Whether manual review is needed"
    )
    review_status: AmendmentReviewStatus = Field(
        default=AmendmentReviewStatus.PENDING, description="Review status"
    )


# =============================================================================
# Ingestion Report Schemas
# =============================================================================


class IngestionReportCreate(BaseModel):
    """Data for creating an ingestion report."""

    session_id: int
    law_id: int
    total_text_length: int
    claimed_text_length: int
    coverage_percentage: float
    unclaimed_flagged_count: int
    unclaimed_ignored_count: int
    total_amendments: int
    high_confidence_count: int
    needs_review_count: int
    avg_confidence: float
    amendments_by_type: dict[str, int] | None = None
    amendments_by_pattern: dict[str, int] | None = None
    auto_approve_eligible: bool = False
    escalation_recommended: bool = False
    escalation_reason: str | None = None
    govinfo_amendment_count: int | None = None
    amendment_count_mismatch: bool | None = None


class IngestionReportResponse(BaseModel):
    """Response schema for ingestion report."""

    report_id: int
    session_id: int
    law_id: int
    parsing_mode: ParsingMode
    session_status: ParsingSessionStatus

    # Coverage stats
    total_text_length: int
    claimed_text_length: int
    coverage_percentage: float = Field(..., ge=0, le=100)
    unclaimed_flagged_count: int
    unclaimed_ignored_count: int

    # Amendment stats
    total_amendments: int
    high_confidence_count: int
    needs_review_count: int
    avg_confidence: float = Field(..., ge=0, le=1)

    # Breakdown
    amendments_by_type: dict[str, int] | None = None
    amendments_by_pattern: dict[str, int] | None = None

    # Auto-approve decision
    auto_approve_eligible: bool
    escalation_recommended: bool
    escalation_reason: str | None = None

    # External validation
    govinfo_amendment_count: int | None = None
    amendment_count_mismatch: bool | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionReportSummary(BaseModel):
    """Summary view of an ingestion report for lists."""

    report_id: int
    law_id: int
    congress: int
    law_number: str
    parsing_mode: ParsingMode
    coverage_percentage: float
    total_amendments: int
    needs_review_count: int
    auto_approve_eligible: bool
    escalation_recommended: bool
    created_at: datetime


# =============================================================================
# Parsing Session Schemas
# =============================================================================


class ParsingSessionCreate(BaseModel):
    """Data for creating a parsing session."""

    law_id: int
    mode: ParsingMode
    parent_session_id: int | None = None


class ParsingSessionUpdate(BaseModel):
    """Data for updating a parsing session."""

    status: ParsingSessionStatus | None = None
    completed_at: datetime | None = None
    escalation_reason: str | None = None
    escalated_by: str | None = None
    error_message: str | None = None
    notes: str | None = None


class ParsingSessionResponse(BaseModel):
    """Response schema for parsing session."""

    session_id: int
    law_id: int
    mode: ParsingMode
    status: ParsingSessionStatus
    started_at: datetime
    completed_at: datetime | None = None
    parent_session_id: int | None = None
    escalation_reason: str | None = None
    escalated_by: str | None = None
    error_message: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Pattern Discovery Schemas
# =============================================================================


class PatternDiscoveryCreate(BaseModel):
    """Data for creating a pattern discovery record."""

    session_id: int
    unmatched_text: str
    detected_keywords: list[str] | None = None
    context_text: str | None = None
    start_pos: int
    end_pos: int


class PatternDiscoveryResponse(BaseModel):
    """Response schema for pattern discovery."""

    discovery_id: int
    session_id: int
    unmatched_text: str
    detected_keywords: str | None = None
    context_text: str | None = None
    start_pos: int
    end_pos: int
    suggested_pattern_name: str | None = None
    suggested_pattern_regex: str | None = None
    suggested_pattern_type: str | None = None
    status: PatternDiscoveryStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    promoted_pattern_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Golden Corpus Schemas
# =============================================================================


class GoldenCorpusLawCreate(BaseModel):
    """Data for adding a law to the golden corpus."""

    law_id: int
    session_id: int | None = None
    verified_by: str
    verification_notes: str | None = Field(
        default=None,
        description="Free-form notes: why this law was chosen, verification methodology, "
        "known acceptable gaps in coverage, any parser quirks specific to this law",
    )
    expected_amendment_count: int
    expected_coverage_percentage: float
    expected_results_json: dict[str, Any] | None = None


class GoldenCorpusLawResponse(BaseModel):
    """Response schema for golden corpus law."""

    corpus_id: int
    law_id: int
    session_id: int | None = None
    verified_by: str
    verified_at: datetime
    verification_notes: str | None = Field(
        default=None,
        description="Free-form notes: why this law was chosen, verification methodology, "
        "known acceptable gaps in coverage, any parser quirks specific to this law",
    )
    expected_amendment_count: int
    expected_coverage_percentage: float
    last_regression_test: datetime | None = None
    last_regression_passed: bool | None = None
    regression_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegressionTestResult(BaseModel):
    """Result of a regression test against the golden corpus."""

    corpus_id: int
    law_id: int
    congress: int
    law_number: str
    passed: bool
    expected_amendment_count: int
    actual_amendment_count: int
    expected_coverage: float
    actual_coverage: float
    discrepancies: list[str] = Field(default_factory=list)
    error_message: str | None = None


class GoldenCorpusValidationResult(BaseModel):
    """Result of validating the entire golden corpus."""

    total_laws: int
    passed: int
    failed: int
    all_passed: bool
    results: list[RegressionTestResult]
    run_at: datetime
