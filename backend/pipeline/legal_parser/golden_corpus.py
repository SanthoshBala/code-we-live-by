"""Golden corpus management for parser regression testing (Task 1.11).

This module provides the GoldenCorpusManager class that:
- Maintains a registry of verified laws for regression testing
- Runs regression tests against the corpus
- Tracks test results over time
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.public_law import PublicLaw
from app.models.validation import (
    GoldenCorpusLaw,
    ParsingSession,
)
from app.schemas.validation import (
    GoldenCorpusValidationResult,
    RegressionTestResult,
)

logger = logging.getLogger(__name__)


# Minimum number of laws required for a complete corpus
MINIMUM_CORPUS_SIZE = 10


@dataclass
class CorpusAddResult:
    """Result of adding a law to the golden corpus."""

    success: bool
    corpus_id: int | None = None
    error: str | None = None


class GoldenCorpusManager:
    """Manages the golden corpus of verified laws for regression testing.

    The golden corpus contains laws that have been human-verified and
    serve as ground truth for parser regression testing. When patterns
    are modified or new ones added, running against the corpus ensures
    existing functionality isn't broken.

    Example usage:
        async with async_session_maker() as db:
            manager = GoldenCorpusManager(db)

            # Add a verified law
            result = await manager.add_to_corpus(
                law_id=123,
                session_id=456,
                verified_by="reviewer@example.com",
                expected_amendment_count=15,
                expected_coverage=92.5,
            )

            # Run regression tests
            results = await manager.run_regression_tests()
            if not results.all_passed:
                print("Regression detected!")
    """

    def __init__(self, db: AsyncSession):
        """Initialize the corpus manager.

        Args:
            db: Database session.
        """
        self.db = db

    async def add_to_corpus(
        self,
        law_id: int,
        session_id: int | None,
        verified_by: str,
        expected_amendment_count: int,
        expected_coverage: float,
        verification_notes: str | None = None,
        expected_results_json: dict | None = None,
    ) -> CorpusAddResult:
        """Add a verified law to the golden corpus.

        Args:
            law_id: ID of the PublicLaw.
            session_id: ID of the verified ParsingSession (optional).
            verified_by: Identifier of the verifier (email or name).
            expected_amendment_count: Expected number of amendments.
            expected_coverage: Expected coverage percentage.
            verification_notes: Notes about the verification.
            expected_results_json: Detailed expected results.

        Returns:
            CorpusAddResult indicating success or failure.
        """
        # Check if law exists
        result = await self.db.execute(
            select(PublicLaw).where(PublicLaw.law_id == law_id)
        )
        law = result.scalar_one_or_none()
        if not law:
            return CorpusAddResult(
                success=False,
                error=f"Law {law_id} not found",
            )

        # Check if already in corpus
        existing = await self.db.execute(
            select(GoldenCorpusLaw).where(GoldenCorpusLaw.law_id == law_id)
        )
        if existing.scalar_one_or_none():
            return CorpusAddResult(
                success=False,
                error=f"Law {law_id} already in corpus",
            )

        # Validate session if provided
        if session_id:
            session_result = await self.db.execute(
                select(ParsingSession).where(ParsingSession.session_id == session_id)
            )
            session = session_result.scalar_one_or_none()
            if not session:
                return CorpusAddResult(
                    success=False,
                    error=f"Session {session_id} not found",
                )
            if session.law_id != law_id:
                return CorpusAddResult(
                    success=False,
                    error=f"Session {session_id} is for a different law",
                )

        # Create corpus entry
        corpus_law = GoldenCorpusLaw(
            law_id=law_id,
            session_id=session_id,
            verified_by=verified_by,
            verified_at=datetime.utcnow(),
            verification_notes=verification_notes,
            expected_amendment_count=expected_amendment_count,
            expected_coverage_percentage=expected_coverage,
            expected_results_json=expected_results_json,
        )

        self.db.add(corpus_law)
        await self.db.commit()
        await self.db.refresh(corpus_law)

        logger.info(
            f"Added law {law_id} to golden corpus (corpus_id={corpus_law.corpus_id})"
        )

        return CorpusAddResult(
            success=True,
            corpus_id=corpus_law.corpus_id,
        )

    async def remove_from_corpus(self, law_id: int) -> bool:
        """Remove a law from the golden corpus.

        Args:
            law_id: ID of the law to remove.

        Returns:
            True if removed, False if not found.
        """
        result = await self.db.execute(
            select(GoldenCorpusLaw).where(GoldenCorpusLaw.law_id == law_id)
        )
        corpus_law = result.scalar_one_or_none()

        if not corpus_law:
            return False

        await self.db.delete(corpus_law)
        await self.db.commit()

        logger.info(f"Removed law {law_id} from golden corpus")
        return True

    async def get_corpus_laws(self) -> list[GoldenCorpusLaw]:
        """Get all laws in the golden corpus.

        Returns:
            List of GoldenCorpusLaw records.
        """
        result = await self.db.execute(
            select(GoldenCorpusLaw)
            .options(selectinload(GoldenCorpusLaw.law))
            .order_by(GoldenCorpusLaw.verified_at)
        )
        return list(result.scalars().all())

    async def get_corpus_size(self) -> int:
        """Get the number of laws in the corpus.

        Returns:
            Number of laws.
        """
        result = await self.db.execute(select(func.count(GoldenCorpusLaw.corpus_id)))
        return result.scalar() or 0

    def is_corpus_complete(self, size: int) -> bool:
        """Check if the corpus has the minimum required laws.

        Args:
            size: Current corpus size.

        Returns:
            True if corpus is complete.
        """
        return size >= MINIMUM_CORPUS_SIZE

    async def run_regression_tests(
        self,
        verbose: bool = False,
    ) -> GoldenCorpusValidationResult:
        """Run regression tests against all laws in the corpus.

        This re-parses each law and compares results against the
        expected values stored in the corpus.

        Args:
            verbose: Log detailed results.

        Returns:
            GoldenCorpusValidationResult with all test results.
        """
        from pipeline.govinfo.client import GovInfoClient
        from pipeline.legal_parser.parsing_modes import RegExParsingSession

        corpus_laws = await self.get_corpus_laws()

        if not corpus_laws:
            return GoldenCorpusValidationResult(
                total_laws=0,
                passed=0,
                failed=0,
                all_passed=True,
                results=[],
                run_at=datetime.utcnow(),
            )

        results: list[RegressionTestResult] = []
        client = GovInfoClient()

        for corpus_law in corpus_laws:
            law = corpus_law.law
            if not law:
                # Law was deleted, skip
                continue

            try:
                # Get law text
                law_text = await client.get_law_text(law.congress, int(law.law_number))
                if not law_text:
                    results.append(
                        RegressionTestResult(
                            corpus_id=corpus_law.corpus_id,
                            law_id=corpus_law.law_id,
                            congress=law.congress,
                            law_number=law.law_number,
                            passed=False,
                            expected_amendment_count=corpus_law.expected_amendment_count,
                            actual_amendment_count=0,
                            expected_coverage=corpus_law.expected_coverage_percentage,
                            actual_coverage=0.0,
                            discrepancies=["Could not retrieve law text"],
                        )
                    )
                    continue

                # Parse the law (without saving to DB)
                parser = RegExParsingSession(self.db)
                parse_result = await parser.parse_law(
                    law_id=corpus_law.law_id,
                    law_text=law_text,
                    save_to_db=False,
                )

                # Compare results
                discrepancies: list[str] = []

                # Check amendment count
                actual_count = len(parse_result.amendments)
                expected_count = corpus_law.expected_amendment_count
                count_tolerance = max(1, int(expected_count * 0.1))  # 10% or 1

                if abs(actual_count - expected_count) > count_tolerance:
                    discrepancies.append(
                        f"Amendment count: expected {expected_count}, got {actual_count}"
                    )

                # Check coverage
                actual_coverage = parse_result.coverage_report.coverage_percentage
                expected_coverage = corpus_law.expected_coverage_percentage
                coverage_tolerance = 5.0  # 5 percentage points

                if abs(actual_coverage - expected_coverage) > coverage_tolerance:
                    discrepancies.append(
                        f"Coverage: expected {expected_coverage:.1f}%, got {actual_coverage:.1f}%"
                    )

                # Check detailed results if available
                if corpus_law.expected_results_json:
                    expected_json = corpus_law.expected_results_json
                    if isinstance(expected_json, str):
                        expected_json = json.loads(expected_json)

                    # Check pattern distribution if specified
                    if "by_pattern" in expected_json:
                        expected_patterns = expected_json["by_pattern"]
                        actual_patterns: dict[str, int] = {}
                        for amend in parse_result.amendments:
                            actual_patterns[amend.pattern_name] = (
                                actual_patterns.get(amend.pattern_name, 0) + 1
                            )

                        for pattern, expected_n in expected_patterns.items():
                            actual_n = actual_patterns.get(pattern, 0)
                            if abs(actual_n - expected_n) > 1:
                                discrepancies.append(
                                    f"Pattern '{pattern}': expected {expected_n}, got {actual_n}"
                                )

                passed = len(discrepancies) == 0

                results.append(
                    RegressionTestResult(
                        corpus_id=corpus_law.corpus_id,
                        law_id=corpus_law.law_id,
                        congress=law.congress,
                        law_number=law.law_number,
                        passed=passed,
                        expected_amendment_count=expected_count,
                        actual_amendment_count=actual_count,
                        expected_coverage=expected_coverage,
                        actual_coverage=actual_coverage,
                        discrepancies=discrepancies,
                    )
                )

                # Update corpus law with test results
                corpus_law.last_regression_test = datetime.utcnow()
                corpus_law.last_regression_passed = passed
                if discrepancies:
                    corpus_law.regression_notes = "; ".join(discrepancies)

                if verbose:
                    status = "PASS" if passed else "FAIL"
                    logger.info(
                        f"[{status}] PL {law.congress}-{law.law_number}: "
                        f"{actual_count} amendments, {actual_coverage:.1f}% coverage"
                    )
                    if discrepancies:
                        for d in discrepancies:
                            logger.info(f"  - {d}")

            except Exception as e:
                logger.exception(f"Error testing law {corpus_law.law_id}")
                results.append(
                    RegressionTestResult(
                        corpus_id=corpus_law.corpus_id,
                        law_id=corpus_law.law_id,
                        congress=law.congress if law else 0,
                        law_number=law.law_number if law else "unknown",
                        passed=False,
                        expected_amendment_count=corpus_law.expected_amendment_count,
                        actual_amendment_count=0,
                        expected_coverage=corpus_law.expected_coverage_percentage,
                        actual_coverage=0.0,
                        error_message=str(e),
                    )
                )

        await self.db.commit()

        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        return GoldenCorpusValidationResult(
            total_laws=len(results),
            passed=passed_count,
            failed=failed_count,
            all_passed=failed_count == 0,
            results=results,
            run_at=datetime.utcnow(),
        )

    async def get_law_regression_history(self, law_id: int) -> list[dict]:
        """Get regression test history for a specific law.

        Args:
            law_id: ID of the law.

        Returns:
            List of regression test results.
        """
        # For now, we only store the last result
        # Future: could store full history in a separate table
        result = await self.db.execute(
            select(GoldenCorpusLaw).where(GoldenCorpusLaw.law_id == law_id)
        )
        corpus_law = result.scalar_one_or_none()

        if not corpus_law or not corpus_law.last_regression_test:
            return []

        return [
            {
                "test_date": corpus_law.last_regression_test.isoformat(),
                "passed": corpus_law.last_regression_passed,
                "notes": corpus_law.regression_notes,
            }
        ]
