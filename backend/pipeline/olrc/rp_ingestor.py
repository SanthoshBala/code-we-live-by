"""Release Point ingestor for the chronological pipeline.

Ingests a subsequent OLRC release point (after bootstrap) by downloading,
parsing, and storing SectionSnapshot records, then running the diff engine
to classify changes relative to the parent revision.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RevisionStatus, RevisionType
from app.models.release_point import OLRCReleasePoint
from app.models.revision import CodeRevision
from pipeline.olrc.bootstrap import ALL_TITLES, ingest_title
from pipeline.olrc.diff_engine import RevisionDiffEngine, RevisionDiffResult
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.parser import USLMParser
from pipeline.olrc.release_point import parse_release_point_identifier

logger = logging.getLogger(__name__)


@dataclass
class RPIngestResult:
    """Summary returned by RPIngestor.ingest_release_point."""

    revision_id: int
    rp_identifier: str
    parent_revision_id: int
    titles_processed: int
    titles_skipped: int
    total_sections: int
    diff_summary: RevisionDiffResult | None
    elapsed_seconds: float


class RPIngestor:
    """Ingests a subsequent OLRC release point and diffs against the parent."""

    def __init__(
        self,
        session: AsyncSession,
        downloader: OLRCDownloader,
        parser: USLMParser,
    ) -> None:
        self.session = session
        self.downloader = downloader
        self.parser = parser

    async def ingest_release_point(
        self,
        rp_identifier: str,
        parent_revision_id: int,
        sequence_number: int,
        titles: list[int] | None = None,
        force: bool = False,
    ) -> RPIngestResult:
        """Ingest a release point and diff against the parent revision.

        Args:
            rp_identifier: Release point identifier (e.g., "113-37").
            parent_revision_id: Revision ID of the parent (earlier RP).
            sequence_number: Global ordering position in the timeline.
            titles: Title numbers to ingest (default: 1-54).
            force: Re-ingest even if already completed.

        Returns:
            RPIngestResult with summary statistics and diff.
        """
        start_time = time.monotonic()
        title_list = titles or ALL_TITLES
        revision: CodeRevision | None = None

        try:
            # Step 1: Check idempotency
            release_point, revision = await self._get_or_create_records(rp_identifier)

            if (
                revision
                and revision.status == RevisionStatus.INGESTED.value
                and not force
            ):
                elapsed = time.monotonic() - start_time
                logger.info(
                    f"Release point {rp_identifier} already ingested "
                    f"(revision {revision.revision_id})"
                )
                return RPIngestResult(
                    revision_id=revision.revision_id,
                    rp_identifier=rp_identifier,
                    parent_revision_id=parent_revision_id,
                    titles_processed=0,
                    titles_skipped=0,
                    total_sections=0,
                    diff_summary=None,
                    elapsed_seconds=elapsed,
                )

            # Step 2: Create or reuse release point record
            if release_point is None:
                release_point = await self._upsert_release_point(rp_identifier)

            # Step 3: Create or reuse revision record
            if revision is None:
                revision = await self._create_revision(
                    release_point, parent_revision_id, sequence_number
                )

            # Step 4: Ingest titles
            titles_processed = 0
            titles_skipped = 0
            total_sections = 0

            for title_num in title_list:
                count = await ingest_title(
                    self.session,
                    self.downloader,
                    self.parser,
                    title_num,
                    rp_identifier,
                    revision.revision_id,
                )
                if count is None:
                    titles_skipped += 1
                else:
                    titles_processed += 1
                    total_sections += count

            # Step 5: Run diff
            diff_engine = RevisionDiffEngine(self.session)
            diff_result = await diff_engine.diff(
                parent_revision_id, revision.revision_id
            )

            # Step 6: Mark complete
            revision.status = RevisionStatus.INGESTED.value
            await self.session.commit()

            elapsed = time.monotonic() - start_time
            logger.info(
                f"RP ingestion complete: {rp_identifier}, "
                f"{titles_processed} titles, {total_sections} sections, "
                f"+{diff_result.sections_added} ~{diff_result.sections_modified} "
                f"-{diff_result.sections_deleted} in {elapsed:.1f}s"
            )
            return RPIngestResult(
                revision_id=revision.revision_id,
                rp_identifier=rp_identifier,
                parent_revision_id=parent_revision_id,
                titles_processed=titles_processed,
                titles_skipped=titles_skipped,
                total_sections=total_sections,
                diff_summary=diff_result,
                elapsed_seconds=elapsed,
            )

        except Exception:
            if revision is not None:
                revision.status = RevisionStatus.FAILED.value
                await self.session.commit()
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_create_records(
        self, rp_identifier: str
    ) -> tuple[OLRCReleasePoint | None, CodeRevision | None]:
        """Check for existing release point and revision records."""
        stmt = select(OLRCReleasePoint).where(
            OLRCReleasePoint.full_identifier == rp_identifier
        )
        result = await self.session.execute(stmt)
        release_point = result.scalar_one_or_none()

        revision = None
        if release_point is not None:
            stmt = select(CodeRevision).where(
                CodeRevision.release_point_id == release_point.release_point_id
            )
            result = await self.session.execute(stmt)
            revision = result.scalar_one_or_none()

        return release_point, revision

    async def _upsert_release_point(self, rp_identifier: str) -> OLRCReleasePoint:
        """Create or fetch the OLRCReleasePoint record."""
        congress, law_id = parse_release_point_identifier(rp_identifier)

        stmt = select(OLRCReleasePoint).where(
            OLRCReleasePoint.full_identifier == rp_identifier
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            await self.session.flush()
            return existing

        rp = OLRCReleasePoint(
            full_identifier=rp_identifier,
            congress=congress,
            law_identifier=law_id,
            is_initial=False,
        )
        self.session.add(rp)
        await self.session.flush()
        return rp

    async def _create_revision(
        self,
        release_point: OLRCReleasePoint,
        parent_revision_id: int,
        sequence_number: int,
    ) -> CodeRevision:
        """Create a CodeRevision linked to the parent."""
        effective = release_point.publication_date or date(2013, 1, 1)

        revision = CodeRevision(
            revision_type=RevisionType.RELEASE_POINT.value,
            release_point_id=release_point.release_point_id,
            parent_revision_id=parent_revision_id,
            is_ground_truth=True,
            status=RevisionStatus.INGESTING.value,
            sequence_number=sequence_number,
            effective_date=effective,
            summary=f"OLRC release point {release_point.full_identifier}",
        )
        self.session.add(revision)
        await self.session.flush()
        return revision
