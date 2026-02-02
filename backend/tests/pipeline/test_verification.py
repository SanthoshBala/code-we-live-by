"""Tests for parsing verification management (Task 1.11)."""

from app.models.enums import VerificationMethod, VerificationResult
from app.schemas.validation import VerificationSummary
from pipeline.legal_parser.verification import (
    VerificationCreateResult,
    VerificationManager,
)


class TestVerificationCreateResult:
    """Tests for VerificationCreateResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful create result."""
        result = VerificationCreateResult(success=True, verification_id=1)
        assert result.success is True
        assert result.verification_id == 1
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed create result."""
        result = VerificationCreateResult(success=False, error="Session not found")
        assert result.success is False
        assert result.verification_id is None
        assert result.error == "Session not found"


class TestVerificationManager:
    """Tests for VerificationManager class."""

    def test_manager_init(self) -> None:
        """Test manager can be created with a db session."""
        # Just verify the class exists and can be instantiated
        # Full integration tests would require a database
        manager = VerificationManager(db=None)  # type: ignore
        assert manager.db is None


class TestVerificationSummary:
    """Tests for VerificationSummary schema."""

    def test_create_summary(self) -> None:
        """Test creating a verification summary."""
        summary = VerificationSummary(
            session_id=123,
            total_verifications=3,
            passed_count=2,
            failed_count=0,
            passed_with_issues_count=1,
            verifiers=["alice@example.com", "bob@example.com"],
            latest_verification=None,
        )
        assert summary.session_id == 123
        assert summary.total_verifications == 3
        assert summary.passed_count == 2
        assert len(summary.verifiers) == 2


class TestVerificationEnums:
    """Tests for verification enums."""

    def test_verification_result_values(self) -> None:
        """Test VerificationResult enum values."""
        assert VerificationResult.PASSED.value == "Passed"
        assert VerificationResult.FAILED.value == "Failed"
        assert VerificationResult.PASSED_WITH_ISSUES.value == "Passed_With_Issues"

    def test_verification_method_values(self) -> None:
        """Test VerificationMethod enum values."""
        assert VerificationMethod.MANUAL_REVIEW.value == "Manual_Review"
        assert VerificationMethod.AUTOMATED_COMPARISON.value == "Automated_Comparison"
        assert VerificationMethod.THIRD_PARTY_AUDIT.value == "Third_Party_Audit"
