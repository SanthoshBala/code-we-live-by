"""Bootstrap the chronological pipeline with an initial OLRC release point.

Downloads and parses every title at a given release point and stores
SectionSnapshot records for each section, creating the root CodeRevision
(initial commit) with no parent.
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
from app.models.snapshot import SectionSnapshot
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.normalized_section import normalize_parsed_section
from pipeline.olrc.parser import USLMParser, compute_text_hash
from pipeline.olrc.release_point import parse_release_point_identifier

logger = logging.getLogger(__name__)

# Default title range: all 54 titles of the US Code
ALL_TITLES = list(range(1, 55))


async def ingest_title(
    session: AsyncSession,
    downloader: OLRCDownloader,
    parser: USLMParser,
    title_num: int,
    rp_identifier: str,
    revision_id: int,
) -> int | None:
    """Download, parse, and store snapshots for one title.

    Shared helper used by both BootstrapService and RPIngestor.

    Args:
        session: Database session.
        downloader: OLRC downloader instance.
        parser: USLM parser instance.
        title_num: US Code title number to ingest.
        rp_identifier: Release point identifier (e.g., "113-21").
        revision_id: The revision ID to attach snapshots to.

    Returns:
        Number of sections ingested, or None if the title was skipped.
    """
    # Check if this title already has snapshots at this revision
    stmt = (
        select(SectionSnapshot.snapshot_id)
        .where(
            SectionSnapshot.revision_id == revision_id,
            SectionSnapshot.title_number == title_num,
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        logger.info(f"Title {title_num}: already ingested, skipping")
        return 0

    # Download
    try:
        xml_path = await downloader.download_title_at_release_point(
            title_num, rp_identifier
        )
    except Exception:
        logger.warning(f"Title {title_num}: download failed, skipping", exc_info=True)
        return None

    if xml_path is None:
        logger.info(f"Title {title_num}: not available at {rp_identifier}, skipping")
        return None

    # Parse
    try:
        parse_result = parser.parse_file(xml_path)
    except Exception:
        logger.error(f"Title {title_num}: parse failed, skipping", exc_info=True)
        return None

    # Create snapshots
    count = 0
    for section in parse_result.sections:
        try:
            normalized = normalize_parsed_section(section)
        except Exception:
            logger.warning(
                f"Title {title_num} § {section.section_number}: "
                "normalization failed, using raw data",
                exc_info=True,
            )
            normalized = section

        text_content = normalized.normalized_text or section.text_content
        provisions_json = None
        if normalized.provisions:
            provisions_json = [
                line.model_dump(mode="json") for line in normalized.provisions
            ]

        notes_json = None
        if normalized.section_notes is not None:
            notes_json = normalized.section_notes.model_dump(mode="json")

        snapshot = SectionSnapshot(
            revision_id=revision_id,
            title_number=title_num,
            section_number=section.section_number,
            heading=section.heading,
            text_content=text_content,
            normalized_provisions=provisions_json,
            notes=section.notes,
            normalized_notes=notes_json,
            text_hash=compute_text_hash(text_content) if text_content else None,
            notes_hash=compute_text_hash(section.notes) if section.notes else None,
            full_citation=section.full_citation,
            is_deleted=False,
        )
        session.add(snapshot)
        count += 1

    await session.flush()
    logger.info(f"Title {title_num}: {count} sections ingested")
    return count


@dataclass
class BootstrapResult:
    """Summary returned by BootstrapService.create_initial_commit."""

    revision_id: int
    rp_identifier: str
    titles_processed: int
    titles_skipped: int
    total_sections: int
    elapsed_seconds: float


class BootstrapService:
    """Populates the initial commit from an OLRC release point."""

    def __init__(
        self,
        session: AsyncSession,
        downloader: OLRCDownloader,
        parser: USLMParser,
    ) -> None:
        self.session = session
        self.downloader = downloader
        self.parser = parser

    async def create_initial_commit(
        self,
        rp_identifier: str,
        titles: list[int] | None = None,
        force: bool = False,
    ) -> BootstrapResult:
        """Create the root revision from an OLRC release point.

        Args:
            rp_identifier: Release point identifier (e.g., "113-21").
            titles: Title numbers to ingest (default: 1-54).
            force: Re-ingest even if already completed.

        Returns:
            BootstrapResult with summary statistics.
        """
        start_time = time.monotonic()
        title_list = titles or ALL_TITLES

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
                return BootstrapResult(
                    revision_id=revision.revision_id,
                    rp_identifier=rp_identifier,
                    titles_processed=0,
                    titles_skipped=0,
                    total_sections=0,
                    elapsed_seconds=elapsed,
                )

            # Step 2: Create or reuse release point record
            if release_point is None:
                release_point = await self._upsert_release_point(rp_identifier)

            # Step 3: Create or reuse revision record
            if revision is None:
                revision = await self._create_revision(release_point)

            # Step 4: Ingest titles
            titles_processed = 0
            titles_skipped = 0
            total_sections = 0

            for title_num in title_list:
                count = await self._ingest_title(
                    title_num, rp_identifier, revision.revision_id
                )
                if count is None:
                    titles_skipped += 1
                else:
                    titles_processed += 1
                    total_sections += count

            # Step 5: Mark complete
            revision.status = RevisionStatus.INGESTED.value
            await self.session.commit()

            elapsed = time.monotonic() - start_time
            logger.info(
                f"Bootstrap complete: {titles_processed} titles, "
                f"{total_sections} sections in {elapsed:.1f}s"
            )
            return BootstrapResult(
                revision_id=revision.revision_id,
                rp_identifier=rp_identifier,
                titles_processed=titles_processed,
                titles_skipped=titles_skipped,
                total_sections=total_sections,
                elapsed_seconds=elapsed,
            )

        except Exception:
            # Mark revision as failed if it exists
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

        # Look up existing release point
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
            existing.is_initial = True
            await self.session.flush()
            return existing

        rp = OLRCReleasePoint(
            full_identifier=rp_identifier,
            congress=congress,
            law_identifier=law_id,
            is_initial=True,
        )
        self.session.add(rp)
        await self.session.flush()
        return rp

    async def _create_revision(self, release_point: OLRCReleasePoint) -> CodeRevision:
        """Create the root CodeRevision record."""
        effective = release_point.publication_date or date(2013, 1, 1)

        revision = CodeRevision(
            revision_type=RevisionType.RELEASE_POINT.value,
            release_point_id=release_point.release_point_id,
            parent_revision_id=None,
            is_ground_truth=True,
            status=RevisionStatus.INGESTING.value,
            sequence_number=0,
            effective_date=effective,
            summary=f"Initial commit: OLRC release point {release_point.full_identifier}",
        )
        self.session.add(revision)
        await self.session.flush()
        return revision

    async def _ingest_title(
        self,
        title_num: int,
        rp_identifier: str,
        revision_id: int,
    ) -> int | None:
        """Download, parse, and store snapshots for one title."""
        return await ingest_title(
            self.session,
            self.downloader,
            self.parser,
            title_num,
            rp_identifier,
            revision_id,
        )
