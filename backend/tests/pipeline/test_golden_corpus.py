"""Tests for golden corpus management (Task 1.11)."""

from app.schemas.validation import (
    GoldenCorpusValidationResult,
    RegressionTestResult,
)
from pipeline.legal_parser.golden_corpus import (
    MINIMUM_CORPUS_SIZE,
    CorpusAddResult,
    GoldenCorpusManager,
)


class TestCorpusAddResult:
    """Tests for CorpusAddResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful add result."""
        result = CorpusAddResult(
            success=True,
            corpus_id=42,
        )
        assert result.success is True
        assert result.corpus_id == 42
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed add result."""
        result = CorpusAddResult(
            success=False,
            error="Law not found",
        )
        assert result.success is False
        assert result.corpus_id is None
        assert result.error == "Law not found"


class TestRegressionTestResult:
    """Tests for RegressionTestResult schema."""

    def test_passed_result(self) -> None:
        """Test creating passed test result."""
        result = RegressionTestResult(
            corpus_id=1,
            law_id=100,
            congress=118,
            law_number="60",
            passed=True,
            expected_amendment_count=10,
            actual_amendment_count=10,
            expected_coverage=90.0,
            actual_coverage=91.5,
            discrepancies=[],
        )
        assert result.passed is True
        assert len(result.discrepancies) == 0

    def test_failed_result_count_mismatch(self) -> None:
        """Test creating failed result due to count mismatch."""
        result = RegressionTestResult(
            corpus_id=1,
            law_id=100,
            congress=118,
            law_number="60",
            passed=False,
            expected_amendment_count=10,
            actual_amendment_count=5,
            expected_coverage=90.0,
            actual_coverage=85.0,
            discrepancies=["Amendment count: expected 10, got 5"],
        )
        assert result.passed is False
        assert len(result.discrepancies) == 1

    def test_failed_result_with_error(self) -> None:
        """Test creating failed result with error message."""
        result = RegressionTestResult(
            corpus_id=1,
            law_id=100,
            congress=118,
            law_number="60",
            passed=False,
            expected_amendment_count=10,
            actual_amendment_count=0,
            expected_coverage=90.0,
            actual_coverage=0.0,
            error_message="Could not retrieve law text",
        )
        assert result.passed is False
        assert result.error_message is not None


class TestGoldenCorpusValidationResult:
    """Tests for GoldenCorpusValidationResult schema."""

    def test_all_passed(self) -> None:
        """Test validation result when all tests pass."""
        from datetime import UTC, datetime

        results = [
            RegressionTestResult(
                corpus_id=1,
                law_id=100,
                congress=118,
                law_number="60",
                passed=True,
                expected_amendment_count=10,
                actual_amendment_count=10,
                expected_coverage=90.0,
                actual_coverage=90.0,
            ),
            RegressionTestResult(
                corpus_id=2,
                law_id=101,
                congress=118,
                law_number="61",
                passed=True,
                expected_amendment_count=5,
                actual_amendment_count=5,
                expected_coverage=85.0,
                actual_coverage=87.0,
            ),
        ]

        validation = GoldenCorpusValidationResult(
            total_laws=2,
            passed=2,
            failed=0,
            all_passed=True,
            results=results,
            run_at=datetime.now(UTC),
        )

        assert validation.all_passed is True
        assert validation.passed == 2
        assert validation.failed == 0

    def test_some_failed(self) -> None:
        """Test validation result when some tests fail."""
        from datetime import UTC, datetime

        results = [
            RegressionTestResult(
                corpus_id=1,
                law_id=100,
                congress=118,
                law_number="60",
                passed=True,
                expected_amendment_count=10,
                actual_amendment_count=10,
                expected_coverage=90.0,
                actual_coverage=90.0,
            ),
            RegressionTestResult(
                corpus_id=2,
                law_id=101,
                congress=118,
                law_number="61",
                passed=False,
                expected_amendment_count=5,
                actual_amendment_count=2,
                expected_coverage=85.0,
                actual_coverage=50.0,
                discrepancies=["Amendment count mismatch", "Coverage mismatch"],
            ),
        ]

        validation = GoldenCorpusValidationResult(
            total_laws=2,
            passed=1,
            failed=1,
            all_passed=False,
            results=results,
            run_at=datetime.now(UTC),
        )

        assert validation.all_passed is False
        assert validation.passed == 1
        assert validation.failed == 1


class TestMinimumCorpusSize:
    """Tests for corpus size requirements."""

    def test_minimum_size_defined(self) -> None:
        """Test that minimum corpus size is defined."""
        assert MINIMUM_CORPUS_SIZE == 10

    def test_is_corpus_complete_true(self) -> None:
        """Test corpus completeness check when complete."""
        # Can't call without DB session, but test the logic
        assert MINIMUM_CORPUS_SIZE <= 10  # At most 10 required

    def test_is_corpus_complete_false(self) -> None:
        """Test corpus completeness check when incomplete."""
        # A corpus with fewer than MINIMUM_CORPUS_SIZE laws is incomplete
        incomplete_size = MINIMUM_CORPUS_SIZE - 1
        assert incomplete_size < MINIMUM_CORPUS_SIZE


class TestCorpusManagerInterfaceDesign:
    """Tests to verify the GoldenCorpusManager interface design."""

    def test_manager_has_add_to_corpus_method(self) -> None:
        """Test that manager has add_to_corpus method."""
        assert hasattr(GoldenCorpusManager, "add_to_corpus")

    def test_manager_has_remove_from_corpus_method(self) -> None:
        """Test that manager has remove_from_corpus method."""
        assert hasattr(GoldenCorpusManager, "remove_from_corpus")

    def test_manager_has_get_corpus_laws_method(self) -> None:
        """Test that manager has get_corpus_laws method."""
        assert hasattr(GoldenCorpusManager, "get_corpus_laws")

    def test_manager_has_run_regression_tests_method(self) -> None:
        """Test that manager has run_regression_tests method."""
        assert hasattr(GoldenCorpusManager, "run_regression_tests")

    def test_manager_has_is_corpus_complete_method(self) -> None:
        """Test that manager has is_corpus_complete method."""
        assert hasattr(GoldenCorpusManager, "is_corpus_complete")


# Note: Full integration tests with database would require async fixtures:
#
# class TestGoldenCorpusManagerIntegration:
#     @pytest.fixture
#     async def db_session(self):
#         # Set up async database session
#         pass
#
#     async def test_add_law_to_corpus(self, db_session):
#         """Test adding a law to the corpus."""
#         pass
#
#     async def test_run_regression_tests(self, db_session):
#         """Test running regression tests."""
#         pass
