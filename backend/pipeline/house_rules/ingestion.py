"""House Rules ingestion service: fetches HMAN HTM and populates CommitteeCongressInstance."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.codeowners import CommitteeCongressInstance
from app.models.supporting import Committee, DataIngestionLog
from pipeline.house_rules.parser import CommitteeJurisdictionData, parse_rule_x

if TYPE_CHECKING:
    from pipeline.cache import PipelineCache

logger = logging.getLogger(__name__)

_HMAN_URL_TEMPLATE = "https://www.govinfo.gov/content/pkg/HMAN-{congress}/html/HMAN-{congress}-houserules.htm"
_HTTP_TIMEOUT = 60.0


class HouseRulesIngestionService:
    """Fetches HMAN HTM from GovInfo and upserts CommitteeCongressInstance rows.

    The HMAN static content URL does not require a GovInfo API key.
    Responses are cached via PipelineCache to avoid repeated downloads.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache: PipelineCache | None = None,
    ) -> None:
        self._session = session
        self._cache = cache

    def _hman_url(self, congress: int) -> str:
        return _HMAN_URL_TEMPLATE.format(congress=congress)

    def _cache_key(self, congress: int) -> str:
        return f"govinfo/hman/HMAN-{congress}-houserules.htm"

    async def _fetch_html(self, congress: int, force: bool = False) -> str | None:
        """Fetch and optionally cache the HMAN HTM for a Congress."""
        cache_key = self._cache_key(congress)
        url = self._hman_url(congress)

        if self._cache and not force:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", cache_key)
                return cached if isinstance(cached, str) else cached.decode()

        logger.info("Fetching %s", url)
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP %d fetching %s: %s", exc.response.status_code, url, exc)
            return None
        except httpx.RequestError as exc:
            logger.error("Request error fetching %s: %s", url, exc)
            return None

        html = response.text
        if self._cache:
            self._cache.set(cache_key, html)
        return html

    async def _get_committee_id_map(self) -> dict[str, int]:
        """Return a mapping of committee_code → committee_id from the DB."""
        result = await self._session.execute(
            select(Committee.committee_code, Committee.committee_id)
        )
        return {row[0]: row[1] for row in result}

    async def ingest_congress(
        self,
        congress: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Fetch Rule X for a Congress and upsert CommitteeCongressInstance rows.

        Args:
            congress: Congress number (e.g. 119).
            force: If True, re-fetch even if the HTML is cached.

        Returns:
            DataIngestionLog summarising the operation.
        """
        log = DataIngestionLog(
            source="govinfo/hman",
            operation=f"ingest_house_rules/{congress}",
            started_at=datetime.utcnow(),
            status="running",
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_failed=0,
        )
        self._session.add(log)
        await self._session.flush()

        try:
            html = await self._fetch_html(congress, force=force)
            if html is None:
                log.status = "failed"
                log.error_message = f"Could not fetch HMAN-{congress}"
                log.completed_at = datetime.utcnow()
                await self._session.commit()
                return log

            committees: list[CommitteeJurisdictionData] = parse_rule_x(html)
            log.records_processed = len(committees)

            if not committees:
                logger.warning("No committee data parsed from HMAN-%d", congress)

            code_to_id = await self._get_committee_id_map()
            source_url = self._hman_url(congress)

            for entry in committees:
                if entry.committee_code is None:
                    logger.warning(
                        "Unknown committee name %r in HMAN-%d — skipping",
                        entry.committee_name,
                        congress,
                    )
                    log.records_failed += 1
                    continue

                committee_id = code_to_id.get(entry.committee_code)
                if committee_id is None:
                    logger.warning(
                        "committee_code %r not found in Committee table for HMAN-%d — "
                        "run seed-committees first",
                        entry.committee_code,
                        congress,
                    )
                    log.records_failed += 1
                    continue

                stmt = (
                    insert(CommitteeCongressInstance)
                    .values(
                        committee_id=committee_id,
                        congress=congress,
                        official_name=entry.committee_name,
                        rule_citation=entry.rule_citation,
                        jurisdiction_text=entry.jurisdiction_text or None,
                        source_url=source_url,
                    )
                    .on_conflict_do_update(
                        constraint="uq_cci_committee_congress",
                        set_={
                            "official_name": entry.committee_name,
                            "rule_citation": entry.rule_citation,
                            "jurisdiction_text": entry.jurisdiction_text or None,
                            "source_url": source_url,
                        },
                    )
                )
                result = await self._session.execute(stmt)
                # rowcount == 1 for both INSERT and UPDATE
                if result.rowcount:
                    log.records_created += 1

            log.status = "completed"
            log.completed_at = datetime.utcnow()
            await self._session.commit()

        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
            log.completed_at = datetime.utcnow()
            await self._session.commit()
            logger.error("house-rules-ingest/%d failed: %s", congress, exc)

        return log

    async def ingest_range(
        self,
        start: int,
        end: int,
        force: bool = False,
    ) -> DataIngestionLog:
        """Ingest Rule X for a range of Congresses.

        Creates a single summary DataIngestionLog aggregating all congresses.

        Args:
            start: First Congress number (inclusive).
            end: Last Congress number (inclusive).
            force: If True, re-fetch even if cached.

        Returns:
            Aggregated DataIngestionLog for the range.
        """
        summary = DataIngestionLog(
            source="govinfo/hman",
            operation=f"ingest_house_rules_range/{start}-{end}",
            started_at=datetime.utcnow(),
            status="running",
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_failed=0,
        )
        self._session.add(summary)
        await self._session.flush()

        for congress in range(start, end + 1):
            log = await self.ingest_congress(congress, force=force)
            summary.records_processed += log.records_processed
            summary.records_created += log.records_created
            summary.records_updated += log.records_updated
            summary.records_failed += log.records_failed

        summary.status = (
            "completed" if summary.records_failed == 0 else "completed_with_errors"
        )
        summary.completed_at = datetime.utcnow()
        await self._session.commit()
        return summary
