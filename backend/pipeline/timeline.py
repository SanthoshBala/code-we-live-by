"""Consolidated timeline builder for the chronological ingestion pipeline.

Merges OLRC release points and Public Laws into a single chronological
sequence. This is the foundation for the play-forward engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_law import PublicLaw
from pipeline.olrc.release_point import ReleasePointInfo, ReleasePointRegistry

logger = logging.getLogger(__name__)


class TimelineEventType(StrEnum):
    """Type of event in the consolidated timeline."""

    RELEASE_POINT = "release_point"
    PUBLIC_LAW = "public_law"


@dataclass
class TimelineEvent:
    """A single event in the consolidated US Code timeline.

    Either an OLRC release point (ground truth) or a Public Law (amendment).
    Events are ordered chronologically by date, with release points ordered
    after any laws they incorporate on the same date.
    """

    event_type: TimelineEventType
    identifier: str  # e.g., "118-158" for RP or "PL 118-158" for law
    congress: int
    law_number: int | None  # Primary law number
    event_date: date | None
    metadata: dict = field(default_factory=dict)

    # For release points: laws excluded by "notXX" syntax
    deferred_laws: list[int] = field(default_factory=list)

    # For release points: link to ReleasePointInfo
    release_point_info: ReleasePointInfo | None = field(default=None, repr=False)

    # For public laws: link to DB record
    law_id: int | None = None

    @property
    def sort_key(self) -> tuple:
        """Sort key for chronological ordering.

        Laws sort before release points on the same date, since the RP
        incorporates those laws.
        """
        d = self.event_date or date.min
        # 0 = law (processed first), 1 = release point (checkpoint after)
        type_order = 0 if self.event_type == TimelineEventType.PUBLIC_LAW else 1
        return (d, type_order, self.congress, self.law_number or 0)

    def __str__(self) -> str:
        date_str = self.event_date.isoformat() if self.event_date else "unknown"
        if self.event_type == TimelineEventType.RELEASE_POINT:
            return f"[RP] {self.identifier} ({date_str})"
        return f"[LAW] PL {self.congress}-{self.law_number} ({date_str})"


class TimelineBuilder:
    """Builds a consolidated chronological timeline of US Code changes.

    Merges OLRC release points and Public Laws into a single ordered
    sequence, handling cross-congress transitions and "not" exclusions.
    """

    def __init__(
        self,
        session: AsyncSession,
        registry: ReleasePointRegistry | None = None,
    ):
        self.session = session
        self.registry = registry or ReleasePointRegistry()

    async def build(
        self,
        start_congress: int = 113,
        end_congress: int | None = None,
    ) -> list[TimelineEvent]:
        """Build the consolidated timeline.

        Args:
            start_congress: First congress to include (default: 113th).
            end_congress: Last congress to include (default: latest available).

        Returns:
            Chronologically sorted list of TimelineEvents.
        """
        # Fetch release points
        await self.registry.fetch_release_points()
        all_rps = self.registry.get_release_points()

        # Filter to congress range
        rps = [
            rp
            for rp in all_rps
            if rp.congress >= start_congress
            and (end_congress is None or rp.congress <= end_congress)
        ]

        # Fetch public laws from DB
        laws = await self._fetch_laws(start_congress, end_congress)

        # Build events
        events: list[TimelineEvent] = []

        # Add release point events
        for rp in rps:
            event = TimelineEvent(
                event_type=TimelineEventType.RELEASE_POINT,
                identifier=rp.full_identifier,
                congress=rp.congress,
                law_number=rp.primary_law_number,
                event_date=rp.publication_date,
                deferred_laws=rp.excluded_laws,
                release_point_info=rp,
            )
            events.append(event)

        # Add public law events
        for law in laws:
            event = TimelineEvent(
                event_type=TimelineEventType.PUBLIC_LAW,
                identifier=f"PL {law.congress}-{law.law_number}",
                congress=law.congress,
                law_number=int(law.law_number) if law.law_number.isdigit() else None,
                event_date=law.enacted_date,
                law_id=law.law_id,
                metadata={
                    "short_title": law.short_title,
                    "popular_name": law.popular_name,
                },
            )
            events.append(event)

        # Sort chronologically
        events.sort(key=lambda e: e.sort_key)

        logger.info(
            f"Built timeline: {len(events)} events "
            f"({sum(1 for e in events if e.event_type == TimelineEventType.RELEASE_POINT)} RPs, "
            f"{sum(1 for e in events if e.event_type == TimelineEventType.PUBLIC_LAW)} laws)"
        )

        return events

    async def build_between_release_points(
        self,
        rp_before: str,
        rp_after: str,
    ) -> list[TimelineEvent]:
        """Build timeline between two release points.

        Returns events in chronological order, starting with the first RP,
        followed by laws, and ending with the second RP.

        Args:
            rp_before: Identifier of the earlier release point.
            rp_after: Identifier of the later release point.

        Returns:
            Chronologically sorted list of TimelineEvents.
        """
        full_timeline = await self.build()

        # Find indices of the two RPs
        before_idx = None
        after_idx = None
        for i, event in enumerate(full_timeline):
            if (
                event.event_type == TimelineEventType.RELEASE_POINT
                and event.identifier == rp_before
            ):
                before_idx = i
            elif (
                event.event_type == TimelineEventType.RELEASE_POINT
                and event.identifier == rp_after
            ):
                after_idx = i

        if before_idx is None:
            raise ValueError(f"Release point not found: {rp_before}")
        if after_idx is None:
            raise ValueError(f"Release point not found: {rp_after}")

        return full_timeline[before_idx : after_idx + 1]

    async def get_laws_between_release_points(
        self,
        rp_before: str,
        rp_after: str,
    ) -> list[TimelineEvent]:
        """Get only the Public Law events between two release points.

        Args:
            rp_before: Identifier of the earlier release point.
            rp_after: Identifier of the later release point.

        Returns:
            List of law events between the two RPs.
        """
        events = await self.build_between_release_points(rp_before, rp_after)
        return [e for e in events if e.event_type == TimelineEventType.PUBLIC_LAW]

    async def _fetch_laws(
        self,
        start_congress: int,
        end_congress: int | None,
    ) -> list[PublicLaw]:
        """Fetch Public Laws from the database for the given congress range."""
        stmt = select(PublicLaw).where(PublicLaw.congress >= start_congress)
        if end_congress is not None:
            stmt = stmt.where(PublicLaw.congress <= end_congress)
        stmt = stmt.order_by(PublicLaw.enacted_date, PublicLaw.law_number)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def get_summary(self, events: list[TimelineEvent]) -> dict:
        """Generate summary statistics for a timeline.

        Args:
            events: List of timeline events.

        Returns:
            Dictionary with per-congress stats and totals.
        """
        by_congress: dict[int, dict] = {}

        for event in events:
            if event.congress not in by_congress:
                by_congress[event.congress] = {
                    "rp_count": 0,
                    "law_count": 0,
                    "first_date": None,
                    "last_date": None,
                }
            stats = by_congress[event.congress]

            if event.event_type == TimelineEventType.RELEASE_POINT:
                stats["rp_count"] += 1
            else:
                stats["law_count"] += 1

            if event.event_date:
                if (
                    stats["first_date"] is None
                    or event.event_date < stats["first_date"]
                ):
                    stats["first_date"] = event.event_date
                if stats["last_date"] is None or event.event_date > stats["last_date"]:
                    stats["last_date"] = event.event_date

        return {
            "total_events": len(events),
            "total_rps": sum(
                1 for e in events if e.event_type == TimelineEventType.RELEASE_POINT
            ),
            "total_laws": sum(
                1 for e in events if e.event_type == TimelineEventType.PUBLIC_LAW
            ),
            "by_congress": by_congress,
        }
