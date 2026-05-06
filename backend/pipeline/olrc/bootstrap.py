"""Bootstrap the chronological pipeline with an initial OLRC release point.

Downloads and parses every title at a given release point and stores
SectionSnapshot records for each section, creating the root CodeRevision
(initial commit) with no parent.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RevisionStatus, RevisionType
from app.models.release_point import OLRCReleasePoint
from app.models.revision import CodeRevision
from app.models.snapshot import SectionSnapshot
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.group_service import upsert_groups_from_parse_result
from pipeline.olrc.normalized_section import normalize_parsed_section
from pipeline.olrc.parser import ParsedSection, USLMParser, compute_text_hash
from pipeline.olrc.release_point import parse_release_point_identifier

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

# Default title range: all 54 titles of the US Code
ALL_TITLES = list(range(1, 55))


class _SectionRow(NamedTuple):
    """Pre-computed data for one SectionSnapshot row, built in a thread pool."""

    section_number: str
    heading: str | None
    text_content: str | None
    normalized_provisions: list | None
    notes: str | None
    normalized_notes: dict | None
    text_hash: str | None
    notes_hash: str | None
    full_citation: str | None
    parent_group_key: str | None
    sort_order: int | None


def _build_snapshot_rows(
    sections: list[ParsedSection],
    title_num: int,
) -> list[_SectionRow]:
    """Normalize sections and build snapshot row data.

    Runs in a thread pool — see ingest_title for context. Calls
    normalize_parsed_section which is CPU-bound text processing (~2s for
    large titles). Returns plain data so the caller can build ORM objects
    on the event loop after group_ids are resolved.
    """
    rows: list[_SectionRow] = []
    for section in sections:
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

        rows.append(
            _SectionRow(
                section_number=section.section_number,
                heading=section.heading,
                text_content=text_content,
                normalized_provisions=provisions_json,
                notes=section.notes,
                normalized_notes=notes_json,
                text_hash=compute_text_hash(text_content) if text_content else None,
                notes_hash=compute_text_hash(section.notes) if section.notes else None,
                full_citation=section.full_citation,
                parent_group_key=section.parent_group_key,
                sort_order=section.sort_order,
            )
        )
    return rows


async def ingest_title(
    session: AsyncSession,
    downloader: OLRCDownloader,
    title_num: int,
    rp_identifier: str,
    revision_id: int,
) -> int | None:
    """Download, parse, and store snapshots for one title.

    Shared helper used by both BootstrapService and RPIngestor.

    The two CPU-bound steps — XML parsing and section normalization — are
    offloaded to the thread pool via asyncio.to_thread so the event loop
    remains free for concurrent DB work on other titles. Each call creates
    its own USLMParser instance, making concurrent invocations thread-safe.

    Args:
        session: Database session.
        downloader: OLRC downloader instance.
        title_num: US Code title number to ingest.
        rp_identifier: Release point identifier (e.g., "113-21").
        revision_id: The revision ID to attach snapshots to.

    Returns:
        Number of sections ingested, or None if the title was skipped.
    """
    t0 = time.monotonic()

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

    # Download (async I/O)
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

    t_download = time.monotonic()

    # Parse in thread pool (CPU-bound XML parsing, ~3-4s for large titles).
    # USLMParser() is instantiated here on the event loop and its bound
    # parse_file method is dispatched to the thread — each call gets its own
    # instance so concurrent invocations from asyncio.gather are safe.
    try:
        parse_result = await asyncio.to_thread(USLMParser().parse_file, xml_path)
    except Exception:
        logger.error(f"Title {title_num}: parse failed, skipping", exc_info=True)
        return None

    t_parse = time.monotonic()

    # Upsert SectionGroup hierarchy for navigation (async DB work — runs while
    # other titles can be parsing concurrently in the thread pool).
    group_lookup = await upsert_groups_from_parse_result(session, parse_result.groups)

    t_groups = time.monotonic()

    # Normalize + build row data in thread pool (CPU-bound, ~2s for large titles).
    # Note: duplicate section numbers are allowed — Congress occasionally
    # enacts two provisions with the same number (see pipeline/olrc/README.md).
    rows = await asyncio.to_thread(
        _build_snapshot_rows, parse_result.sections, title_num
    )

    t_normalize = time.monotonic()

    # Bulk-insert all snapshots in one executemany call instead of individual
    # session.add() + flush() per row. The ORM UoW emits a separate INSERT
    # round-trip per object (plus RETURNING for the PK); for large titles
    # (1000+ sections) that serialises hundreds of network round-trips, which
    # was the dominant cost (~90% of wall-clock per title in Cloud Run).
    now = (
        datetime.utcnow()
    )  # naive, matching TimestampMixin / TIMESTAMP WITHOUT TIME ZONE
    snapshot_dicts = []
    for row in rows:
        group_id = None
        if row.parent_group_key:
            group_record = group_lookup.get(row.parent_group_key)
            if group_record:
                group_id = group_record.group_id

        snapshot_dicts.append(
            {
                "revision_id": revision_id,
                "title_number": title_num,
                "section_number": row.section_number,
                "heading": row.heading,
                "text_content": row.text_content,
                "normalized_provisions": row.normalized_provisions,
                "notes": row.notes,
                "normalized_notes": row.normalized_notes,
                "text_hash": row.text_hash,
                "notes_hash": row.notes_hash,
                "full_citation": row.full_citation,
                "is_deleted": False,
                "group_id": group_id,
                "sort_order": row.sort_order if row.sort_order is not None else 0,
                "created_at": now,
                "updated_at": now,
            }
        )

    await session.execute(insert(SectionSnapshot), snapshot_dicts)
    t_insert = time.monotonic()

    count = len(rows)
    logger.info(
        f"Title {title_num}: {count} sections ingested "
        f"[download={t_download - t0:.1f}s parse={t_parse - t_download:.1f}s "
        f"groups={t_groups - t_parse:.1f}s normalize={t_normalize - t_groups:.1f}s "
        f"insert={t_insert - t_normalize:.1f}s total={t_insert - t0:.1f}s]"
    )
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
        session_factory: SessionFactory | None = None,
        concurrency: int = 4,
    ) -> None:
        self.session = session
        self.downloader = downloader
        # concurrency=4 — the 16Gi/4-CPU Cloud Run config (PR #152) showed
        # peak utilization under 20% at concurrency=2, so 4 fits comfortably
        # while halving wall-clock on the cold-cache first run.
        self._concurrency = concurrency

        if session_factory is not None:
            self._session_factory = session_factory
        else:
            # Fallback wraps self.session — only safe with mock sessions in tests.
            _sess = session

            @asynccontextmanager
            async def _default_factory() -> AsyncIterator[AsyncSession]:
                yield _sess

            self._session_factory = _default_factory

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

            # Commit so the revision row is visible to the parallel worker
            # sessions opened below — they run in separate transactions and
            # would otherwise hit a FK violation on section_snapshot.revision_id.
            await self.session.commit()

            # Step 4: Ingest titles in parallel — each gets its own session.
            sem = asyncio.Semaphore(self._concurrency)

            async def _ingest_one(title_num: int) -> int | None:
                async with sem, self._session_factory() as s:
                    count = await ingest_title(
                        s,
                        self.downloader,
                        title_num,
                        rp_identifier,
                        revision.revision_id,
                    )
                    await s.commit()
                    return count

            gather_results = await asyncio.gather(
                *[_ingest_one(t) for t in title_list],
                return_exceptions=True,
            )

            # Re-raise the first unexpected exception so the outer handler
            # can mark the revision as FAILED.
            first_exc = next(
                (r for r in gather_results if isinstance(r, BaseException)), None
            )
            if first_exc is not None:
                raise first_exc

            titles_processed = 0
            titles_skipped = 0
            total_sections = 0

            for item in gather_results:
                if item is None:
                    titles_skipped += 1
                else:
                    titles_processed += 1
                    total_sections += item

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
