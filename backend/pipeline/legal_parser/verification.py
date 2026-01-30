"""Parsing verification management (Task 1.11).

This module provides the VerificationManager class for creating and
querying verifications of parsing sessions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VerificationMethod, VerificationResult
from app.models.validation import ParsingSession, ParsingVerification
from app.schemas.validation import VerificationSummary

logger = logging.getLogger(__name__)


@dataclass
class VerificationCreateResult:
    """Result of creating a verification."""

    success: bool
    verification_id: int | None = None
    error: str | None = None


class VerificationManager:
    """Manages verifications of parsing sessions.

    Verifications record human or automated review of parsing results.
    Multiple verifications can exist for a single session, allowing
    quality to be measured by number and type of verifications.

    Example usage:
        async with async_session_maker() as db:
            manager = VerificationManager(db)

            # Add a verification
            result = await manager.add_verification(
                session_id=123,
                verified_by="reviewer@example.com",
                method=VerificationMethod.MANUAL_REVIEW,
                result=VerificationResult.PASSED,
                notes="Verified against GPO PDF",
            )

            # Get verification summary
            summary = await manager.get_session_summary(session_id=123)
            print(f"Total verifications: {summary.total_verifications}")
    """

    def __init__(self, db: AsyncSession):
        """Initialize the verification manager.

        Args:
            db: Database session.
        """
        self.db = db

    async def add_verification(
        self,
        session_id: int,
        verified_by: str,
        method: VerificationMethod,
        result: VerificationResult,
        notes: str | None = None,
        issues_found: list[str] | None = None,
    ) -> VerificationCreateResult:
        """Add a verification to a parsing session.

        Args:
            session_id: ID of the ParsingSession to verify.
            verified_by: Identifier of the verifier (email or name).
            method: How the verification was performed.
            result: Result of the verification.
            notes: Free-form notes about the verification.
            issues_found: List of issues found during verification.

        Returns:
            VerificationCreateResult indicating success or failure.
        """
        # Check if session exists
        session_result = await self.db.execute(
            select(ParsingSession).where(ParsingSession.session_id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return VerificationCreateResult(
                success=False,
                error=f"Session {session_id} not found",
            )

        # Create verification
        verification = ParsingVerification(
            session_id=session_id,
            verified_by=verified_by,
            verified_at=datetime.utcnow(),
            method=method,
            result=result,
            notes=notes,
            issues_found=issues_found,
        )

        self.db.add(verification)
        await self.db.commit()
        await self.db.refresh(verification)

        logger.info(
            f"Added verification for session {session_id} "
            f"(verification_id={verification.verification_id}, result={result.value})"
        )

        return VerificationCreateResult(
            success=True,
            verification_id=verification.verification_id,
        )

    async def get_session_verifications(
        self, session_id: int
    ) -> list[ParsingVerification]:
        """Get all verifications for a session.

        Args:
            session_id: ID of the ParsingSession.

        Returns:
            List of verifications ordered by date.
        """
        result = await self.db.execute(
            select(ParsingVerification)
            .where(ParsingVerification.session_id == session_id)
            .order_by(ParsingVerification.verified_at)
        )
        return list(result.scalars().all())

    async def get_session_summary(self, session_id: int) -> VerificationSummary:
        """Get a summary of verifications for a session.

        Args:
            session_id: ID of the ParsingSession.

        Returns:
            VerificationSummary with counts and verifiers.
        """
        verifications = await self.get_session_verifications(session_id)

        passed = sum(1 for v in verifications if v.result == VerificationResult.PASSED)
        failed = sum(1 for v in verifications if v.result == VerificationResult.FAILED)
        passed_with_issues = sum(
            1
            for v in verifications
            if v.result == VerificationResult.PASSED_WITH_ISSUES
        )
        verifiers = list({v.verified_by for v in verifications})
        latest = max((v.verified_at for v in verifications), default=None)

        return VerificationSummary(
            session_id=session_id,
            total_verifications=len(verifications),
            passed_count=passed,
            failed_count=failed,
            passed_with_issues_count=passed_with_issues,
            verifiers=verifiers,
            latest_verification=latest,
        )

    async def get_well_verified_sessions(
        self,
        min_verifications: int = 1,
        required_result: VerificationResult | None = VerificationResult.PASSED,
    ) -> list[int]:
        """Get session IDs that meet verification criteria.

        Useful for finding sessions suitable for regression testing.

        Args:
            min_verifications: Minimum number of verifications required.
            required_result: If specified, at least one verification must have this result.

        Returns:
            List of session IDs meeting the criteria.
        """
        # Get sessions with enough verifications
        query = (
            select(ParsingVerification.session_id)
            .group_by(ParsingVerification.session_id)
            .having(
                func.count(ParsingVerification.verification_id) >= min_verifications
            )
        )

        result = await self.db.execute(query)
        session_ids = [row[0] for row in result.fetchall()]

        if not required_result or not session_ids:
            return session_ids

        # Filter to those with the required result
        result = await self.db.execute(
            select(ParsingVerification.session_id)
            .where(ParsingVerification.session_id.in_(session_ids))
            .where(ParsingVerification.result == required_result)
            .distinct()
        )
        return [row[0] for row in result.fetchall()]
