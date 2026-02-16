"""Graduation and escalation system for parsing patterns (Task 1.11).

This module provides the GraduationManager class that:
- Checks if parsing results warrant escalation to a higher mode
- Evaluates if patterns can graduate from supervised to automated
- Tracks pattern performance metrics
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AmendmentReviewStatus, ParsingMode, ParsingSessionStatus
from app.models.validation import (
    IngestionReport,
    ParsedAmendmentRecord,
    ParsingSession,
)

logger = logging.getLogger(__name__)


@dataclass
class EscalationDecision:
    """Result of escalation check."""

    should_escalate: bool
    reason: str | None
    recommended_mode: ParsingMode | None = None


@dataclass
class PatternPerformance:
    """Performance metrics for a pattern."""

    pattern_name: str
    total_uses: int
    approved_count: int
    rejected_count: int
    corrected_count: int
    pending_count: int
    success_rate: float
    consecutive_successes: int
    can_graduate: bool
    graduation_blockers: list[str]


@dataclass
class GraduationEvaluation:
    """Result of graduation evaluation for a pattern."""

    pattern_name: str
    can_graduate: bool
    current_success_rate: float
    total_uses: int
    consecutive_successes: int
    blockers: list[str]


class GraduationManager:
    """Manages escalation decisions and pattern graduation.

    Escalation triggers (recommends moving to higher oversight mode):
    - Coverage < 85%
    - needs_review_count > 20% of total amendments
    - Amendment count mismatch with GovInfo metadata
    - More than 5 flagged unclaimed spans

    Graduation criteria (allows pattern to move from supervised to automated):
    - 95%+ success rate (approved / (approved + rejected + corrected))
    - 10+ uses minimum
    - 5 consecutive successes
    """

    # Escalation thresholds
    COVERAGE_THRESHOLD = 85.0  # Minimum coverage percentage
    REVIEW_RATIO_THRESHOLD = 0.20  # Max ratio of needs_review to total
    FLAGGED_UNCLAIMED_THRESHOLD = 5  # Max flagged unclaimed spans

    # Graduation thresholds
    MIN_USES_FOR_GRADUATION = 10
    MIN_SUCCESS_RATE = 0.95  # 95%
    MIN_CONSECUTIVE_SUCCESSES = 5

    def __init__(self, db: AsyncSession):
        """Initialize the graduation manager.

        Args:
            db: Database session for querying metrics.
        """
        self.db = db

    def check_escalation_needed(
        self,
        report: IngestionReport,
        current_mode: ParsingMode = ParsingMode.REGEX,
    ) -> EscalationDecision:
        """Check if parsing results warrant escalation.

        Args:
            report: The ingestion report to evaluate.
            current_mode: The current parsing mode.

        Returns:
            EscalationDecision with recommendation.
        """
        reasons: list[str] = []

        # Check coverage threshold
        if report.coverage_percentage < self.COVERAGE_THRESHOLD:
            reasons.append(
                f"Coverage {report.coverage_percentage:.1f}% below "
                f"threshold ({self.COVERAGE_THRESHOLD}%)"
            )

        # Check needs_review ratio
        if report.total_amendments > 0:
            review_ratio = report.needs_review_count / report.total_amendments
            if review_ratio > self.REVIEW_RATIO_THRESHOLD:
                reasons.append(
                    f"Review ratio {review_ratio:.0%} exceeds "
                    f"threshold ({self.REVIEW_RATIO_THRESHOLD:.0%})"
                )

        # Check flagged unclaimed spans
        if report.unclaimed_flagged_count > self.FLAGGED_UNCLAIMED_THRESHOLD:
            reasons.append(
                f"{report.unclaimed_flagged_count} flagged unclaimed spans "
                f"(threshold: {self.FLAGGED_UNCLAIMED_THRESHOLD})"
            )

        if reasons:
            # Recommend next mode up
            next_mode = self._get_next_mode(current_mode)
            return EscalationDecision(
                should_escalate=True,
                reason="; ".join(reasons),
                recommended_mode=next_mode,
            )

        return EscalationDecision(
            should_escalate=False,
            reason=None,
            recommended_mode=None,
        )

    def _get_next_mode(self, current_mode: ParsingMode) -> ParsingMode:
        """Get the next mode up in the escalation chain."""
        if current_mode == ParsingMode.REGEX:
            return ParsingMode.LLM
        elif current_mode == ParsingMode.LLM:
            return ParsingMode.HUMAN_PLUS_LLM
        else:
            return ParsingMode.HUMAN_PLUS_LLM

    async def evaluate_pattern_graduation(
        self, pattern_name: str
    ) -> GraduationEvaluation:
        """Evaluate if a pattern can graduate to automated parsing.

        Args:
            pattern_name: Name of the pattern to evaluate.

        Returns:
            GraduationEvaluation with decision and metrics.
        """
        # Get all amendment records for this pattern
        result = await self.db.execute(
            select(ParsedAmendmentRecord).where(
                ParsedAmendmentRecord.pattern_name == pattern_name
            )
        )
        records = result.scalars().all()

        total_uses = len(records)
        if total_uses == 0:
            return GraduationEvaluation(
                pattern_name=pattern_name,
                can_graduate=False,
                current_success_rate=0.0,
                total_uses=0,
                consecutive_successes=0,
                blockers=["No usage data available"],
            )

        # Count by review status
        approved = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.APPROVED
        )
        rejected = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.REJECTED
        )
        corrected = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.CORRECTED
        )
        pending = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.PENDING
        )

        # Calculate success rate (approved / reviewed)
        reviewed = approved + rejected + corrected
        success_rate = approved / reviewed if reviewed > 0 else 0.0

        # Calculate consecutive successes (most recent first)
        sorted_records = sorted(records, key=lambda r: r.created_at, reverse=True)
        consecutive_successes = 0
        for record in sorted_records:
            if record.review_status == AmendmentReviewStatus.APPROVED:
                consecutive_successes += 1
            elif record.review_status == AmendmentReviewStatus.PENDING:
                # Pending doesn't break the streak
                continue
            else:
                break

        # Determine blockers
        blockers: list[str] = []

        if total_uses < self.MIN_USES_FOR_GRADUATION:
            blockers.append(
                f"Insufficient uses: {total_uses} < {self.MIN_USES_FOR_GRADUATION}"
            )

        if success_rate < self.MIN_SUCCESS_RATE:
            blockers.append(
                f"Success rate too low: {success_rate:.1%} < {self.MIN_SUCCESS_RATE:.0%}"
            )

        if consecutive_successes < self.MIN_CONSECUTIVE_SUCCESSES:
            blockers.append(
                f"Consecutive successes too low: {consecutive_successes} < "
                f"{self.MIN_CONSECUTIVE_SUCCESSES}"
            )

        if pending > 0:
            blockers.append(f"{pending} amendments still pending review")

        can_graduate = len(blockers) == 0

        return GraduationEvaluation(
            pattern_name=pattern_name,
            can_graduate=can_graduate,
            current_success_rate=success_rate,
            total_uses=total_uses,
            consecutive_successes=consecutive_successes,
            blockers=blockers,
        )

    async def get_pattern_performance(self, pattern_name: str) -> PatternPerformance:
        """Get detailed performance metrics for a pattern.

        Args:
            pattern_name: Name of the pattern.

        Returns:
            PatternPerformance with all metrics.
        """
        evaluation = await self.evaluate_pattern_graduation(pattern_name)

        # Get detailed counts
        result = await self.db.execute(
            select(ParsedAmendmentRecord).where(
                ParsedAmendmentRecord.pattern_name == pattern_name
            )
        )
        records = result.scalars().all()

        approved = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.APPROVED
        )
        rejected = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.REJECTED
        )
        corrected = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.CORRECTED
        )
        pending = sum(
            1 for r in records if r.review_status == AmendmentReviewStatus.PENDING
        )

        return PatternPerformance(
            pattern_name=pattern_name,
            total_uses=evaluation.total_uses,
            approved_count=approved,
            rejected_count=rejected,
            corrected_count=corrected,
            pending_count=pending,
            success_rate=evaluation.current_success_rate,
            consecutive_successes=evaluation.consecutive_successes,
            can_graduate=evaluation.can_graduate,
            graduation_blockers=evaluation.blockers,
        )

    async def get_all_pattern_metrics(self) -> list[PatternPerformance]:
        """Get performance metrics for all patterns with usage data.

        Returns:
            List of PatternPerformance for all patterns.
        """
        # Get unique pattern names
        result = await self.db.execute(
            select(ParsedAmendmentRecord.pattern_name).distinct()
        )
        pattern_names = [row[0] for row in result.all()]

        metrics = []
        for name in pattern_names:
            metrics.append(await self.get_pattern_performance(name))

        # Sort by total uses descending
        metrics.sort(key=lambda m: m.total_uses, reverse=True)

        return metrics

    async def get_graduation_candidates(self) -> list[GraduationEvaluation]:
        """Get patterns that are candidates for graduation.

        Returns:
            List of patterns that meet minimum usage but may not yet graduate.
        """
        # Get patterns with enough usage
        result = await self.db.execute(
            select(
                ParsedAmendmentRecord.pattern_name,
                func.count(ParsedAmendmentRecord.record_id).label("count"),
            )
            .group_by(ParsedAmendmentRecord.pattern_name)
            .having(
                func.count(ParsedAmendmentRecord.record_id)
                >= self.MIN_USES_FOR_GRADUATION
            )
        )
        candidates = result.all()

        evaluations = []
        for pattern_name, _ in candidates:
            eval_result = await self.evaluate_pattern_graduation(pattern_name)
            evaluations.append(eval_result)

        return evaluations

    async def get_escalation_history(
        self,
        law_id: int | None = None,
        days: int = 30,
    ) -> list[ParsingSession]:
        """Get history of escalated sessions.

        Args:
            law_id: Filter by law ID (optional).
            days: Number of days to look back.

        Returns:
            List of escalated ParsingSession records.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = select(ParsingSession).where(
            ParsingSession.status == ParsingSessionStatus.ESCALATED,
            ParsingSession.started_at >= cutoff,
        )

        if law_id is not None:
            query = query.where(ParsingSession.law_id == law_id)

        query = query.order_by(ParsingSession.started_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())
