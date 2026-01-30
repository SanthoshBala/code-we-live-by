"""Parsing modes for the legal parser (Task 1.11).

This module provides different parsing mode implementations:
- RegExParsingSession: Pure programmatic parsing using regex patterns
- LLMParsingSession: (Future) LLM-assisted parsing
- HumanPlusLLMParsingSession: (Future) Human + LLM collaborative parsing
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    AmendmentReviewStatus,
    ParsingMode,
    ParsingSessionStatus,
    SpanType,
)
from app.models.validation import (
    IngestionReport,
    ParsedAmendmentRecord,
    ParsingSession,
    PatternDiscovery,
    TextSpan,
)
from pipeline.legal_parser.amendment_parser import AmendmentParser, ParsedAmendment
from pipeline.legal_parser.text_accounting import (
    CoverageReport,
    TextAccountant,
)

logger = logging.getLogger(__name__)


@dataclass
class ParsingResult:
    """Result of a parsing session."""

    session_id: int
    law_id: int
    mode: ParsingMode
    status: ParsingSessionStatus
    amendments: list[ParsedAmendment]
    coverage_report: CoverageReport
    ingestion_report_id: int | None = None
    escalation_recommended: bool = False
    escalation_reason: str | None = None
    error_message: str | None = None


class RegExParsingSession:
    """Regex-based parsing session for extracting amendments.

    This class orchestrates the parsing process using pattern-based
    extraction, tracks text coverage, and generates reports.

    Example usage:
        async with async_session_maker() as db:
            session = RegExParsingSession(db, default_title=17)
            result = await session.parse_law(law_id, law_text)
            if result.escalation_recommended:
                print(f"Escalation needed: {result.escalation_reason}")
    """

    # Coverage threshold below which escalation is recommended
    COVERAGE_THRESHOLD = 85.0

    # Percentage of amendments needing review that triggers escalation
    REVIEW_THRESHOLD = 0.20

    def __init__(
        self,
        db: AsyncSession,
        default_title: int | None = None,
        min_confidence: float = 0.0,
    ):
        """Initialize the parsing session.

        Args:
            db: Database session for persisting results.
            default_title: Default US Code title when not specified.
            min_confidence: Minimum confidence threshold for pattern matches.
        """
        self.db = db
        self.parser = AmendmentParser(
            default_title=default_title,
            min_confidence=min_confidence,
        )
        self.default_title = default_title

    async def parse_law(
        self,
        law_id: int,
        law_text: str,
        parent_session_id: int | None = None,
        save_to_db: bool = True,
    ) -> ParsingResult:
        """Parse a law and extract amendments.

        Args:
            law_id: ID of the PublicLaw being parsed.
            law_text: Full text of the law.
            parent_session_id: ID of parent session if this is an escalation.
            save_to_db: Whether to save results to database.

        Returns:
            ParsingResult with amendments and coverage report.
        """
        # Create parsing session
        session = ParsingSession(
            law_id=law_id,
            mode=ParsingMode.REGEX,
            status=ParsingSessionStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            parent_session_id=parent_session_id,
        )

        if save_to_db:
            self.db.add(session)
            await self.db.flush()

        try:
            # Parse the law text
            amendments = self.parser.parse(law_text)

            # Track text coverage
            accountant = TextAccountant(law_text)
            for i, amendment in enumerate(amendments):
                accountant.claim_span(
                    start_pos=amendment.start_pos,
                    end_pos=amendment.end_pos,
                    amendment_id=i,
                    pattern_name=amendment.pattern_name,
                )

            # Generate coverage report
            coverage = accountant.generate_coverage_report()

            # Save parsed amendments to database
            amendment_records: list[ParsedAmendmentRecord] = []
            if save_to_db:
                for _i, amendment in enumerate(amendments):
                    record = self._create_amendment_record(
                        session.session_id, amendment
                    )
                    self.db.add(record)
                    amendment_records.append(record)
                await self.db.flush()

                # Update spans with record IDs
                for i, amendment in enumerate(amendments):
                    span = TextSpan(
                        session_id=session.session_id,
                        start_pos=amendment.start_pos,
                        end_pos=amendment.end_pos,
                        span_type=SpanType.CLAIMED,
                        amendment_record_id=(
                            amendment_records[i].record_id
                            if i < len(amendment_records)
                            else None
                        ),
                        pattern_name=amendment.pattern_name,
                    )
                    self.db.add(span)

                # Save unclaimed spans and pattern discoveries
                await self._save_unclaimed_spans(session.session_id, coverage, law_text)

            # Check for escalation
            escalation_recommended, escalation_reason = self._check_escalation(
                coverage, amendments
            )

            # Create ingestion report
            report = self._create_ingestion_report(
                session.session_id,
                law_id,
                coverage,
                amendments,
                escalation_recommended,
                escalation_reason,
            )

            if save_to_db:
                self.db.add(report)
                await self.db.flush()

            # Update session status
            session.status = ParsingSessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            if escalation_recommended:
                session.status = ParsingSessionStatus.ESCALATED
                session.escalation_reason = escalation_reason
                session.escalated_by = "system"

            if save_to_db:
                await self.db.commit()

            return ParsingResult(
                session_id=session.session_id,
                law_id=law_id,
                mode=ParsingMode.REGEX,
                status=session.status,
                amendments=amendments,
                coverage_report=coverage,
                ingestion_report_id=report.report_id if save_to_db else None,
                escalation_recommended=escalation_recommended,
                escalation_reason=escalation_reason,
            )

        except Exception as e:
            logger.exception(f"Error parsing law {law_id}")
            session.status = ParsingSessionStatus.FAILED
            session.completed_at = datetime.utcnow()
            session.error_message = str(e)

            if save_to_db:
                await self.db.commit()

            return ParsingResult(
                session_id=session.session_id,
                law_id=law_id,
                mode=ParsingMode.REGEX,
                status=ParsingSessionStatus.FAILED,
                amendments=[],
                coverage_report=CoverageReport(
                    total_length=len(law_text),
                    claimed_length=0,
                    coverage_percentage=0.0,
                    claimed_spans=[],
                    unclaimed_spans=[],
                    flagged_unclaimed=[],
                    ignored_unclaimed=[],
                ),
                error_message=str(e),
            )

    def _create_amendment_record(
        self, session_id: int, amendment: ParsedAmendment
    ) -> ParsedAmendmentRecord:
        """Create a database record for a parsed amendment."""
        return ParsedAmendmentRecord(
            session_id=session_id,
            pattern_name=amendment.pattern_name,
            pattern_type=amendment.pattern_type.value,
            change_type=amendment.change_type,
            target_title=amendment.section_ref.title if amendment.section_ref else None,
            target_section=(
                amendment.section_ref.section if amendment.section_ref else None
            ),
            target_subsection_path=(
                amendment.section_ref.subsection_path if amendment.section_ref else None
            ),
            old_text=amendment.old_text,
            new_text=amendment.new_text,
            start_pos=amendment.start_pos,
            end_pos=amendment.end_pos,
            confidence=amendment.confidence,
            needs_review=amendment.needs_review,
            review_status=AmendmentReviewStatus.PENDING,
        )

    async def _save_unclaimed_spans(
        self,
        session_id: int,
        coverage: CoverageReport,
        law_text: str,
    ) -> None:
        """Save unclaimed spans and create pattern discoveries for flagged ones."""
        for span in coverage.flagged_unclaimed:
            # Save as unclaimed flagged span
            text_span = TextSpan(
                session_id=session_id,
                start_pos=span.start_pos,
                end_pos=span.end_pos,
                span_type=SpanType.UNCLAIMED_FLAGGED,
                detected_keywords=json.dumps(span.detected_keywords),
            )
            self.db.add(text_span)

            # Create pattern discovery record
            context_start = max(0, span.start_pos - 50)
            context_end = min(len(law_text), span.end_pos + 50)
            discovery = PatternDiscovery(
                session_id=session_id,
                unmatched_text=span.text,
                detected_keywords=json.dumps(span.detected_keywords),
                context_text=law_text[context_start:context_end],
                start_pos=span.start_pos,
                end_pos=span.end_pos,
            )
            self.db.add(discovery)

        for span in coverage.ignored_unclaimed:
            # Save as unclaimed ignored span
            text_span = TextSpan(
                session_id=session_id,
                start_pos=span.start_pos,
                end_pos=span.end_pos,
                span_type=SpanType.UNCLAIMED_IGNORED,
            )
            self.db.add(text_span)

    def _check_escalation(
        self,
        coverage: CoverageReport,
        amendments: list[ParsedAmendment],
    ) -> tuple[bool, str | None]:
        """Check if parsing results warrant escalation.

        Returns:
            Tuple of (escalation_recommended, reason).
        """
        reasons: list[str] = []

        # Check coverage threshold
        if coverage.coverage_percentage < self.COVERAGE_THRESHOLD:
            reasons.append(
                f"Coverage {coverage.coverage_percentage:.1f}% below threshold "
                f"({self.COVERAGE_THRESHOLD}%)"
            )

        # Check needs_review percentage
        if amendments:
            needs_review_count = sum(1 for a in amendments if a.needs_review)
            review_percentage = needs_review_count / len(amendments)
            if review_percentage > self.REVIEW_THRESHOLD:
                reasons.append(
                    f"{needs_review_count}/{len(amendments)} "
                    f"({review_percentage:.0%}) amendments need review"
                )

        # Check for flagged unclaimed spans
        if len(coverage.flagged_unclaimed) > 5:
            reasons.append(
                f"{len(coverage.flagged_unclaimed)} unclaimed spans with "
                "amendment keywords"
            )

        if reasons:
            return True, "; ".join(reasons)
        return False, None

    def _create_ingestion_report(
        self,
        session_id: int,
        law_id: int,
        coverage: CoverageReport,
        amendments: list[ParsedAmendment],
        escalation_recommended: bool,
        escalation_reason: str | None,
    ) -> IngestionReport:
        """Create an ingestion report from parsing results."""
        # Count amendments by type and pattern
        by_type: dict[str, int] = {}
        by_pattern: dict[str, int] = {}
        high_confidence = 0
        needs_review = 0
        total_confidence = 0.0

        for amendment in amendments:
            type_name = amendment.change_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            by_pattern[amendment.pattern_name] = (
                by_pattern.get(amendment.pattern_name, 0) + 1
            )
            total_confidence += amendment.confidence
            if amendment.confidence >= 0.90:
                high_confidence += 1
            if amendment.needs_review:
                needs_review += 1

        avg_confidence = total_confidence / len(amendments) if amendments else 0.0

        # Determine auto-approve eligibility
        auto_approve = (
            coverage.coverage_percentage >= self.COVERAGE_THRESHOLD
            and not escalation_recommended
            and needs_review == 0
            and len(coverage.flagged_unclaimed) == 0
        )

        return IngestionReport(
            session_id=session_id,
            law_id=law_id,
            total_text_length=coverage.total_length,
            claimed_text_length=coverage.claimed_length,
            coverage_percentage=coverage.coverage_percentage,
            unclaimed_flagged_count=len(coverage.flagged_unclaimed),
            unclaimed_ignored_count=len(coverage.ignored_unclaimed),
            total_amendments=len(amendments),
            high_confidence_count=high_confidence,
            needs_review_count=needs_review,
            avg_confidence=round(avg_confidence, 4),
            amendments_by_type=by_type,
            amendments_by_pattern=by_pattern,
            auto_approve_eligible=auto_approve,
            escalation_recommended=escalation_recommended,
            escalation_reason=escalation_reason,
        )


async def validate_against_govinfo(
    report: IngestionReport,
    congress: int,
    law_number: int,
    db: AsyncSession | None = None,
) -> tuple[bool, str | None]:
    """Validate parsing results against GovInfo metadata.

    Fetches amendment metadata from GovInfo and compares against
    the parsed amendment count. Updates the report with validation
    results if a db session is provided.

    Args:
        report: The IngestionReport to validate.
        congress: Congress number.
        law_number: Law number.
        db: Optional database session to persist validation results.

    Returns:
        Tuple of (has_mismatch, mismatch_description).
    """
    from pipeline.govinfo.client import GovInfoClient

    try:
        client = GovInfoClient()
        metadata = await client.get_amendment_metadata(congress, law_number)

        if not metadata:
            logger.warning(
                f"Could not fetch GovInfo metadata for PL {congress}-{law_number}"
            )
            return False, None

        # Compare amendment counts
        # Use the keyword count as a rough estimate of expected amendments
        # This is heuristic - GovInfo doesn't provide exact amendment counts
        expected_count = metadata.amendment_keyword_count // 3  # Rough heuristic
        actual_count = report.total_amendments

        # Allow 30% tolerance for the comparison
        tolerance = max(3, int(expected_count * 0.3))
        has_mismatch = abs(actual_count - expected_count) > tolerance

        mismatch_desc = None
        if has_mismatch:
            mismatch_desc = (
                f"Parsed {actual_count} amendments but GovInfo metadata suggests "
                f"~{expected_count} (keywords: {metadata.amendment_keyword_count}, "
                f"titles: {metadata.titles_amended})"
            )
            logger.warning(
                f"Amendment count mismatch for PL {congress}-{law_number}: {mismatch_desc}"
            )

        # Update report with GovInfo data
        report.govinfo_amendment_count = expected_count
        report.amendment_count_mismatch = has_mismatch

        if has_mismatch and not report.escalation_recommended:
            report.escalation_recommended = True
            if report.escalation_reason:
                report.escalation_reason += f"; {mismatch_desc}"
            else:
                report.escalation_reason = mismatch_desc

        if db:
            await db.commit()

        return has_mismatch, mismatch_desc

    except Exception as e:
        logger.error(f"Error validating against GovInfo: {e}")
        return False, None


# Future implementations (stubs for now)


class LLMParsingSession:
    """LLM-assisted parsing session (Future implementation).

    This will use an LLM to parse amendments when regex patterns
    fail or need verification.
    """

    def __init__(self, db: AsyncSession, default_title: int | None = None):
        """Initialize LLM parsing session."""
        self.db = db
        self.default_title = default_title
        raise NotImplementedError(
            "LLM parsing mode is not yet implemented. "
            "Use RegExParsingSession for now."
        )


class HumanPlusLLMParsingSession:
    """Human + LLM collaborative parsing session (Future implementation).

    This will provide an interactive interface for human reviewers
    to work with an LLM on parsing complex amendments.
    """

    def __init__(self, db: AsyncSession, default_title: int | None = None):
        """Initialize Human+LLM parsing session."""
        self.db = db
        self.default_title = default_title
        raise NotImplementedError(
            "Human+LLM parsing mode is not yet implemented. "
            "Use RegExParsingSession for now."
        )


def get_parsing_session(
    mode: ParsingMode,
    db: AsyncSession,
    default_title: int | None = None,
    min_confidence: float = 0.0,
) -> RegExParsingSession:
    """Factory function to get the appropriate parsing session.

    Args:
        mode: The parsing mode to use.
        db: Database session.
        default_title: Default US Code title.
        min_confidence: Minimum confidence threshold.

    Returns:
        The appropriate parsing session instance.

    Raises:
        NotImplementedError: If mode is not yet supported.
    """
    if mode == ParsingMode.REGEX:
        return RegExParsingSession(db, default_title, min_confidence)
    elif mode == ParsingMode.LLM:
        raise NotImplementedError("LLM parsing mode is not yet implemented")
    elif mode == ParsingMode.HUMAN_PLUS_LLM:
        raise NotImplementedError("Human+LLM parsing mode is not yet implemented")
    else:
        raise ValueError(f"Unknown parsing mode: {mode}")
