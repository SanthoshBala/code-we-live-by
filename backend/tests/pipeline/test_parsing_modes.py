"""Tests for parsing modes (Task 1.11)."""

import pytest

from app.models.enums import ParsingMode, ParsingSessionStatus
from pipeline.legal_parser.parsing_modes import (
    ParsingResult,
    RegExParsingSession,
    get_parsing_session,
)
from pipeline.legal_parser.text_accounting import CoverageReport


class TestParsingResult:
    """Tests for ParsingResult dataclass."""

    def test_create_successful_result(self) -> None:
        """Test creating a successful parsing result."""
        coverage = CoverageReport(
            total_length=1000,
            claimed_length=900,
            coverage_percentage=90.0,
            claimed_spans=[],
            unclaimed_spans=[],
            flagged_unclaimed=[],
            ignored_unclaimed=[],
        )

        result = ParsingResult(
            session_id=1,
            law_id=100,
            mode=ParsingMode.REGEX,
            status=ParsingSessionStatus.COMPLETED,
            amendments=[],
            coverage_report=coverage,
            ingestion_report_id=10,
        )

        assert result.session_id == 1
        assert result.law_id == 100
        assert result.mode == ParsingMode.REGEX
        assert result.status == ParsingSessionStatus.COMPLETED
        assert result.ingestion_report_id == 10
        assert result.escalation_recommended is False

    def test_create_escalated_result(self) -> None:
        """Test creating an escalated parsing result."""
        coverage = CoverageReport(
            total_length=1000,
            claimed_length=500,
            coverage_percentage=50.0,
            claimed_spans=[],
            unclaimed_spans=[],
            flagged_unclaimed=[],
            ignored_unclaimed=[],
        )

        result = ParsingResult(
            session_id=2,
            law_id=101,
            mode=ParsingMode.REGEX,
            status=ParsingSessionStatus.ESCALATED,
            amendments=[],
            coverage_report=coverage,
            escalation_recommended=True,
            escalation_reason="Coverage 50.0% below threshold (85%)",
        )

        assert result.status == ParsingSessionStatus.ESCALATED
        assert result.escalation_recommended is True
        assert "Coverage" in result.escalation_reason

    def test_create_failed_result(self) -> None:
        """Test creating a failed parsing result."""
        coverage = CoverageReport(
            total_length=0,
            claimed_length=0,
            coverage_percentage=0.0,
            claimed_spans=[],
            unclaimed_spans=[],
            flagged_unclaimed=[],
            ignored_unclaimed=[],
        )

        result = ParsingResult(
            session_id=3,
            law_id=102,
            mode=ParsingMode.REGEX,
            status=ParsingSessionStatus.FAILED,
            amendments=[],
            coverage_report=coverage,
            error_message="Failed to parse law text",
        )

        assert result.status == ParsingSessionStatus.FAILED
        assert result.error_message is not None


class TestRegExParsingSessionConstants:
    """Tests for RegExParsingSession constants."""

    def test_coverage_threshold(self) -> None:
        """Test coverage threshold value."""
        assert RegExParsingSession.COVERAGE_THRESHOLD == 85.0

    def test_review_threshold(self) -> None:
        """Test review threshold value."""
        assert RegExParsingSession.REVIEW_THRESHOLD == 0.20


class TestGetParsingSession:
    """Tests for the get_parsing_session factory function."""

    def test_get_regex_session_returns_correct_type(self) -> None:
        """Test that get_parsing_session returns correct session type."""

        # Create a mock session-like object
        class MockSession:
            pass

        # This should return a RegExParsingSession (even with mock)
        session = get_parsing_session(ParsingMode.REGEX, MockSession())  # type: ignore
        assert isinstance(session, RegExParsingSession)

    def test_llm_mode_not_implemented(self) -> None:
        """Test that LLM mode raises NotImplementedError."""

        # Create a mock session-like object
        class MockSession:
            pass

        with pytest.raises(NotImplementedError, match="LLM parsing mode"):
            get_parsing_session(ParsingMode.LLM, MockSession())  # type: ignore

    def test_human_plus_llm_mode_not_implemented(self) -> None:
        """Test that Human+LLM mode raises NotImplementedError."""

        class MockSession:
            pass

        with pytest.raises(NotImplementedError, match="Human.LLM parsing mode"):
            get_parsing_session(ParsingMode.HUMAN_PLUS_LLM, MockSession())  # type: ignore


class TestRegExParsingSessionInterfaceDesign:
    """Tests to verify the RegExParsingSession interface design."""

    def test_session_has_parse_law_method(self) -> None:
        """Test that session has parse_law method."""
        assert hasattr(RegExParsingSession, "parse_law")

    def test_session_has_coverage_threshold(self) -> None:
        """Test that session has coverage threshold."""
        assert hasattr(RegExParsingSession, "COVERAGE_THRESHOLD")

    def test_session_has_review_threshold(self) -> None:
        """Test that session has review threshold."""
        assert hasattr(RegExParsingSession, "REVIEW_THRESHOLD")


class TestParsingModeEnum:
    """Tests for ParsingMode enum values."""

    def test_regex_mode_value(self) -> None:
        """Test RegEx mode string value."""
        assert ParsingMode.REGEX.value == "RegEx"

    def test_llm_mode_value(self) -> None:
        """Test LLM mode string value."""
        assert ParsingMode.LLM.value == "LLM"

    def test_human_plus_llm_mode_value(self) -> None:
        """Test Human+LLM mode string value."""
        assert ParsingMode.HUMAN_PLUS_LLM.value == "Human_Plus_LLM"


class TestParsingSessionStatusEnum:
    """Tests for ParsingSessionStatus enum values."""

    def test_in_progress_value(self) -> None:
        """Test In_Progress status value."""
        assert ParsingSessionStatus.IN_PROGRESS.value == "In_Progress"

    def test_completed_value(self) -> None:
        """Test Completed status value."""
        assert ParsingSessionStatus.COMPLETED.value == "Completed"

    def test_failed_value(self) -> None:
        """Test Failed status value."""
        assert ParsingSessionStatus.FAILED.value == "Failed"

    def test_escalated_value(self) -> None:
        """Test Escalated status value."""
        assert ParsingSessionStatus.ESCALATED.value == "Escalated"


# Note: Full integration tests would require async database fixtures:
#
# class TestRegExParsingSessionIntegration:
#     @pytest.fixture
#     async def db_session(self):
#         # Set up async database session
#         pass
#
#     async def test_parse_law_success(self, db_session):
#         """Test successful law parsing."""
#         pass
#
#     async def test_parse_law_escalation(self, db_session):
#         """Test parsing that triggers escalation."""
#         pass
