"""Pattern learning service for discovering new amendment patterns (Task 1.11).

This module provides the PatternLearningService class that:
- Records pattern discoveries from unmatched text
- Manages the review workflow for discovered patterns
- Handles pattern promotion to the production pattern set
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PatternDiscoveryStatus
from app.models.validation import (
    PatternDiscovery,
)

logger = logging.getLogger(__name__)


@dataclass
class PatternPromotion:
    """Result of promoting a discovered pattern."""

    success: bool
    discovery_id: int
    pattern_name: str | None = None
    error: str | None = None


class PatternLearningService:
    """Service for managing pattern discovery and learning.

    When parsing encounters text that contains amendment keywords but
    doesn't match any existing pattern, a PatternDiscovery record is
    created. Human reviewers can then:
    - Reject false positives
    - Suggest new patterns for the unmatched text
    - Promote successful patterns to production

    Example workflow:
        1. Parser creates PatternDiscovery for unmatched amendment text
        2. Human reviews and suggests a regex pattern
        3. Pattern is tested against historical data
        4. If successful, pattern is promoted to AMENDMENT_PATTERNS
    """

    def __init__(self, db: AsyncSession):
        """Initialize the learning service.

        Args:
            db: Database session.
        """
        self.db = db

    async def record_pattern_discovery(
        self,
        session_id: int,
        unmatched_text: str,
        detected_keywords: list[str] | None = None,
        context_text: str | None = None,
        start_pos: int = 0,
        end_pos: int = 0,
    ) -> PatternDiscovery:
        """Record a new pattern discovery from unmatched text.

        Args:
            session_id: ID of the parsing session.
            unmatched_text: The unmatched text that may contain an amendment.
            detected_keywords: Keywords that triggered the discovery.
            context_text: Surrounding context for the text.
            start_pos: Start position in source text.
            end_pos: End position in source text.

        Returns:
            The created PatternDiscovery record.
        """
        discovery = PatternDiscovery(
            session_id=session_id,
            unmatched_text=unmatched_text,
            detected_keywords=(
                json.dumps(detected_keywords) if detected_keywords else None
            ),
            context_text=context_text,
            start_pos=start_pos,
            end_pos=end_pos,
            status=PatternDiscoveryStatus.NEW,
        )

        self.db.add(discovery)
        await self.db.commit()
        await self.db.refresh(discovery)

        logger.info(
            f"Recorded pattern discovery {discovery.discovery_id} for session {session_id}"
        )

        return discovery

    async def get_pending_patterns(
        self,
        limit: int = 50,
        status: PatternDiscoveryStatus | None = None,
    ) -> list[PatternDiscovery]:
        """Get pattern discoveries awaiting review.

        Args:
            limit: Maximum number of results.
            status: Filter by specific status (default: NEW or UNDER_REVIEW).

        Returns:
            List of PatternDiscovery records.
        """
        query = select(PatternDiscovery)

        if status:
            query = query.where(PatternDiscovery.status == status)
        else:
            query = query.where(
                PatternDiscovery.status.in_(
                    [
                        PatternDiscoveryStatus.NEW,
                        PatternDiscoveryStatus.UNDER_REVIEW,
                    ]
                )
            )

        query = query.order_by(PatternDiscovery.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_discovery(self, discovery_id: int) -> PatternDiscovery | None:
        """Get a specific pattern discovery.

        Args:
            discovery_id: ID of the discovery.

        Returns:
            PatternDiscovery or None if not found.
        """
        result = await self.db.execute(
            select(PatternDiscovery).where(
                PatternDiscovery.discovery_id == discovery_id
            )
        )
        return result.scalar_one_or_none()

    async def start_review(
        self,
        discovery_id: int,
        reviewer: str,
    ) -> PatternDiscovery | None:
        """Mark a discovery as under review.

        Args:
            discovery_id: ID of the discovery.
            reviewer: Identifier of the reviewer.

        Returns:
            Updated PatternDiscovery or None if not found.
        """
        discovery = await self.get_discovery(discovery_id)
        if not discovery:
            return None

        discovery.status = PatternDiscoveryStatus.UNDER_REVIEW
        discovery.reviewed_by = reviewer
        discovery.reviewed_at = datetime.utcnow()

        await self.db.commit()
        return discovery

    async def suggest_pattern(
        self,
        discovery_id: int,
        pattern_name: str,
        pattern_regex: str,
        pattern_type: str,
        reviewer: str,
    ) -> PatternDiscovery | None:
        """Add a suggested pattern to a discovery.

        Args:
            discovery_id: ID of the discovery.
            pattern_name: Suggested name for the pattern.
            pattern_regex: Suggested regex.
            pattern_type: Suggested PatternType value.
            reviewer: Identifier of the reviewer.

        Returns:
            Updated PatternDiscovery or None if not found.
        """
        discovery = await self.get_discovery(discovery_id)
        if not discovery:
            return None

        discovery.suggested_pattern_name = pattern_name
        discovery.suggested_pattern_regex = pattern_regex
        discovery.suggested_pattern_type = pattern_type
        discovery.status = PatternDiscoveryStatus.UNDER_REVIEW
        discovery.reviewed_by = reviewer
        discovery.reviewed_at = datetime.utcnow()

        await self.db.commit()
        return discovery

    async def reject_discovery(
        self,
        discovery_id: int,
        reviewer: str,
        notes: str | None = None,
    ) -> PatternDiscovery | None:
        """Reject a pattern discovery (false positive).

        Args:
            discovery_id: ID of the discovery.
            reviewer: Identifier of the reviewer.
            notes: Reason for rejection.

        Returns:
            Updated PatternDiscovery or None if not found.
        """
        discovery = await self.get_discovery(discovery_id)
        if not discovery:
            return None

        discovery.status = PatternDiscoveryStatus.REJECTED
        discovery.reviewed_by = reviewer
        discovery.reviewed_at = datetime.utcnow()
        discovery.review_notes = notes

        await self.db.commit()
        logger.info(f"Rejected pattern discovery {discovery_id}")

        return discovery

    async def promote_pattern(
        self,
        discovery_id: int,
        pattern_name: str | None = None,
        reviewer: str | None = None,
    ) -> PatternPromotion:
        """Promote a discovered pattern to production.

        Note: This marks the discovery as promoted but doesn't automatically
        add the pattern to AMENDMENT_PATTERNS. That requires a code change
        to patterns.py.

        Args:
            discovery_id: ID of the discovery.
            pattern_name: Final name for the pattern (uses suggested if not provided).
            reviewer: Identifier of the reviewer.

        Returns:
            PatternPromotion result.
        """
        discovery = await self.get_discovery(discovery_id)
        if not discovery:
            return PatternPromotion(
                success=False,
                discovery_id=discovery_id,
                error=f"Discovery {discovery_id} not found",
            )

        if not discovery.suggested_pattern_regex:
            return PatternPromotion(
                success=False,
                discovery_id=discovery_id,
                error="No suggested pattern regex defined",
            )

        final_name = pattern_name or discovery.suggested_pattern_name
        if not final_name:
            return PatternPromotion(
                success=False,
                discovery_id=discovery_id,
                error="No pattern name provided",
            )

        discovery.status = PatternDiscoveryStatus.PROMOTED
        discovery.promoted_pattern_name = final_name
        if reviewer:
            discovery.reviewed_by = reviewer
            discovery.reviewed_at = datetime.utcnow()

        await self.db.commit()

        logger.info(
            f"Promoted pattern discovery {discovery_id} as '{final_name}'. "
            "Add to patterns.py to activate."
        )

        return PatternPromotion(
            success=True,
            discovery_id=discovery_id,
            pattern_name=final_name,
        )

    async def get_similar_discoveries(
        self,
        text: str,
        limit: int = 10,
    ) -> list[PatternDiscovery]:
        """Find similar pattern discoveries (for deduplication).

        Args:
            text: Text to match against.
            limit: Maximum results.

        Returns:
            List of similar discoveries.
        """
        # Simple substring matching for now
        # Future: could use fuzzy matching or embeddings
        result = await self.db.execute(
            select(PatternDiscovery)
            .where(PatternDiscovery.unmatched_text.contains(text[:50]))
            .order_by(PatternDiscovery.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_promoted_patterns(self) -> list[PatternDiscovery]:
        """Get all promoted patterns (for adding to patterns.py).

        Returns:
            List of promoted PatternDiscovery records.
        """
        result = await self.db.execute(
            select(PatternDiscovery)
            .where(PatternDiscovery.status == PatternDiscoveryStatus.PROMOTED)
            .order_by(PatternDiscovery.reviewed_at.desc())
        )
        return list(result.scalars().all())

    async def get_discovery_stats(self) -> dict:
        """Get statistics on pattern discoveries.

        Returns:
            Dictionary with counts by status.
        """
        from sqlalchemy import func

        result = await self.db.execute(
            select(
                PatternDiscovery.status,
                func.count(PatternDiscovery.discovery_id).label("count"),
            ).group_by(PatternDiscovery.status)
        )

        stats = {status.value: 0 for status in PatternDiscoveryStatus}
        for status, count in result.all():
            stats[status.value] = count

        return stats

    async def export_pattern_for_code(self, discovery_id: int) -> str | None:
        """Export a promoted pattern as Python code for patterns.py.

        Args:
            discovery_id: ID of the promoted discovery.

        Returns:
            Python code string to add to patterns.py, or None if not found.
        """
        discovery = await self.get_discovery(discovery_id)
        if not discovery or discovery.status != PatternDiscoveryStatus.PROMOTED:
            return None

        if not discovery.suggested_pattern_regex or not discovery.promoted_pattern_name:
            return None

        # Generate the Python code
        code = f"""    # Discovered from parsing session {discovery.session_id}
    # Original text: {discovery.unmatched_text[:100]}...
    AmendmentPattern(
        name="{discovery.promoted_pattern_name}",
        pattern_type=PatternType.{discovery.suggested_pattern_type or "AMEND_GENERAL"},
        regex=r"{discovery.suggested_pattern_regex}",
        confidence=0.85,  # Start with lower confidence, raise after validation
        description="{discovery.review_notes or 'Auto-discovered pattern'}",
    ),"""

        return code
