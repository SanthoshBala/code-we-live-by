"""Tests for graduation and escalation system (Task 1.11)."""

import pytest

from app.models.enums import ParsingMode
from pipeline.legal_parser.graduation import (
    EscalationDecision,
    GraduationEvaluation,
    GraduationManager,
    PatternPerformance,
)


class TestEscalationDecision:
    """Tests for EscalationDecision dataclass."""

    def test_create_no_escalation(self) -> None:
        """Test creating decision with no escalation."""
        decision = EscalationDecision(
            should_escalate=False,
            reason=None,
        )
        assert decision.should_escalate is False
        assert decision.reason is None
        assert decision.recommended_mode is None

    def test_create_with_escalation(self) -> None:
        """Test creating decision with escalation."""
        decision = EscalationDecision(
            should_escalate=True,
            reason="Coverage below threshold",
            recommended_mode=ParsingMode.LLM,
        )
        assert decision.should_escalate is True
        assert decision.reason == "Coverage below threshold"
        assert decision.recommended_mode == ParsingMode.LLM


class TestGraduationEvaluation:
    """Tests for GraduationEvaluation dataclass."""

    def test_create_can_graduate(self) -> None:
        """Test creating evaluation that can graduate."""
        eval = GraduationEvaluation(
            pattern_name="test_pattern",
            can_graduate=True,
            current_success_rate=0.98,
            total_uses=50,
            consecutive_successes=10,
            blockers=[],
        )
        assert eval.can_graduate is True
        assert eval.blockers == []

    def test_create_cannot_graduate(self) -> None:
        """Test creating evaluation that cannot graduate."""
        eval = GraduationEvaluation(
            pattern_name="test_pattern",
            can_graduate=False,
            current_success_rate=0.80,
            total_uses=5,
            consecutive_successes=2,
            blockers=["Insufficient uses: 5 < 10", "Success rate too low"],
        )
        assert eval.can_graduate is False
        assert len(eval.blockers) == 2


class TestPatternPerformance:
    """Tests for PatternPerformance dataclass."""

    def test_create_performance(self) -> None:
        """Test creating performance metrics."""
        perf = PatternPerformance(
            pattern_name="strike_insert_quoted",
            total_uses=100,
            approved_count=95,
            rejected_count=2,
            corrected_count=3,
            pending_count=0,
            success_rate=0.95,
            consecutive_successes=20,
            can_graduate=True,
            graduation_blockers=[],
        )
        assert perf.total_uses == 100
        assert perf.success_rate == 0.95
        assert perf.can_graduate is True


class TestGraduationManagerThresholds:
    """Tests for GraduationManager threshold constants."""

    def test_coverage_threshold(self) -> None:
        """Test coverage threshold value."""
        assert GraduationManager.COVERAGE_THRESHOLD == 85.0

    def test_review_ratio_threshold(self) -> None:
        """Test review ratio threshold value."""
        assert GraduationManager.REVIEW_RATIO_THRESHOLD == 0.20

    def test_min_uses_for_graduation(self) -> None:
        """Test minimum uses for graduation."""
        assert GraduationManager.MIN_USES_FOR_GRADUATION == 10

    def test_min_success_rate(self) -> None:
        """Test minimum success rate for graduation."""
        assert GraduationManager.MIN_SUCCESS_RATE == 0.95

    def test_min_consecutive_successes(self) -> None:
        """Test minimum consecutive successes."""
        assert GraduationManager.MIN_CONSECUTIVE_SUCCESSES == 5


class TestEscalationChecks:
    """Tests for escalation decision logic (unit tests without DB)."""

    def test_next_mode_from_regex(self) -> None:
        """Test next mode escalation from regex."""
        # We can't instantiate GraduationManager without a real DB session,
        # but we can test the _get_next_mode method directly if needed
        # For now, verify the expected escalation chain
        assert ParsingMode.REGEX.value == "RegEx"
        assert ParsingMode.LLM.value == "LLM"
        assert ParsingMode.HUMAN_PLUS_LLM.value == "Human_Plus_LLM"


class TestGraduationCriteria:
    """Tests for graduation criteria logic."""

    def test_graduation_criteria_constants(self) -> None:
        """Test that graduation criteria are reasonable."""
        # 10 uses is reasonable minimum for statistical significance
        assert GraduationManager.MIN_USES_FOR_GRADUATION >= 5
        assert GraduationManager.MIN_USES_FOR_GRADUATION <= 50

        # 95% success rate is high but achievable
        assert GraduationManager.MIN_SUCCESS_RATE >= 0.90
        assert GraduationManager.MIN_SUCCESS_RATE <= 1.0

        # 5 consecutive successes prevents random spikes
        assert GraduationManager.MIN_CONSECUTIVE_SUCCESSES >= 3
        assert GraduationManager.MIN_CONSECUTIVE_SUCCESSES <= 10


# Note: Full integration tests with database would go in a separate file
# or use fixtures for async database sessions.
# The following tests would require a database session:
#
# class TestGraduationManagerIntegration:
#     @pytest.fixture
#     async def db_session(self):
#         # Set up async database session
#         pass
#
#     async def test_check_escalation_coverage_below_threshold(self, db_session):
#         """Test escalation when coverage is below threshold."""
#         pass
#
#     async def test_evaluate_pattern_graduation_success(self, db_session):
#         """Test successful pattern graduation evaluation."""
#         pass
