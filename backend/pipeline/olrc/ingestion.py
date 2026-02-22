"""Ingest US Code data from OLRC into the database."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DataIngestionLog,
    SectionGroup,
    USCodeSection,
)
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.group_service import (
    _parse_citation_date,
    upsert_groups_from_parse_result,
)
from pipeline.olrc.normalized_section import _clean_heading, normalize_parsed_section
from pipeline.olrc.parser import (
    ParsedSection,
    USLMParser,
    USLMParseResult,
)

if TYPE_CHECKING:
    from pipeline.cache import PipelineCache

logger = logging.getLogger(__name__)


class USCodeIngestionService:
    """Service for ingesting US Code data into the database."""

    def __init__(
        self,
        session: AsyncSession,
        download_dir: Path | str = "data/olrc",
        cache: PipelineCache | None = None,
    ):
        """Initialize the ingestion service.

        Args:
            session: SQLAlchemy async session.
            download_dir: Directory for downloaded XML files.
            cache: Optional PipelineCache for shared caching.
        """
        self.session = session
        self.downloader = OLRCDownloader(download_dir=download_dir, cache=cache)
        self.parser = USLMParser()

    async def ingest_title(
        self,
        title_number: int,
        force_download: bool = False,
        force_parse: bool = False,
    ) -> DataIngestionLog:
        """Ingest a single US Code title.

        Args:
            title_number: The US Code title number (1-54).
            force_download: If True, download even if file exists.
            force_parse: If True, re-parse and update even if already ingested.

        Returns:
            Ingestion log record.
        """
        # Create ingestion log
        log = DataIngestionLog(
            source="OLRC",
            operation=f"ingest_title_{title_number}",
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(log)
        await self.session.flush()

        try:
            # Check if already ingested
            if not force_parse:
                existing = await self.session.execute(
                    select(SectionGroup).where(
                        SectionGroup.group_type == "title",
                        SectionGroup.number == str(title_number),
                    )
                )
                if existing.scalar_one_or_none():
                    log.status = "skipped"
                    log.completed_at = datetime.utcnow()
                    log.details = "Title already ingested"
                    await self.session.commit()
                    return log

            # Download XML file
            xml_path = await self.downloader.download_title(
                title_number, force=force_download
            )
            if not xml_path:
                log.status = "failed"
                log.error_message = f"Failed to download Title {title_number}"
                log.completed_at = datetime.utcnow()
                await self.session.commit()
                return log

            # Parse XML
            parse_result = self.parser.parse_file(xml_path)

            # Ingest into database
            stats = await self._ingest_parse_result(parse_result, force_parse)

            # Update log
            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.records_processed = stats["groups"] + stats["sections"]
            log.records_created = stats["created"]
            log.records_updated = stats["updated"]
            log.details = f"Groups: {stats['groups']}, Sections: {stats['sections']}"

            await self.session.commit()
            return log

        except Exception as e:
            logger.exception(f"Error ingesting Title {title_number}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            await self.session.rollback()
            self.session.add(log)
            await self.session.commit()
            return log

    async def _ingest_parse_result(
        self, result: USLMParseResult, force: bool = False
    ) -> dict:
        """Ingest parsed USLM data into the database.

        Args:
            result: Parsed USLM data.
            force: If True, update existing records.

        Returns:
            Statistics dict with counts.
        """
        stats = {
            "groups": 0,
            "sections": 0,
            "created": 0,
            "updated": 0,
        }

        # Upsert groups using the shared group service
        group_lookup = await upsert_groups_from_parse_result(
            self.session, result.groups, force
        )
        stats["groups"] = len(group_lookup)

        # Extract title_number from the root title group
        title_number = result.title.title_number

        # Ingest sections
        for section in result.sections:
            group_id = None
            if section.parent_group_key:
                group_record = group_lookup.get(section.parent_group_key)
                if group_record:
                    group_id = group_record.group_id

            await self._upsert_section(
                section,
                group_id,
                title_number,
                force,
            )
            stats["sections"] += 1

        return stats

    async def _upsert_section(
        self,
        parsed: ParsedSection,
        group_id: int | None,
        title_number: int,
        force: bool = False,
    ) -> USCodeSection:
        """Insert or update a section record."""
        # Normalize the parsed section to get structured data
        normalized = normalize_parsed_section(parsed)

        # Extract text content (prefer normalized, fall back to raw)
        text_content = normalized.normalized_text or parsed.text_content

        # Serialize structured provisions for frontend display
        normalized_provisions = None
        if normalized.provisions:
            normalized_provisions = [
                line.model_dump(mode="json") for line in normalized.provisions
            ]

        # Get normalized notes as JSON
        normalized_notes = None
        enacted_date = None
        statutes_at_large_citation = None

        if normalized.section_notes:
            normalized_notes = normalized.section_notes.model_dump(mode="json")

            # Extract enacted_date and statutes_at_large_citation from first citation
            if normalized.section_notes.citations:
                first_citation = normalized.section_notes.citations[0]

                # Get date from the first citation (either Public Law or Act)
                if first_citation.law and first_citation.law.date:
                    enacted_date = _parse_citation_date(first_citation.law.date)
                elif first_citation.act and first_citation.act.date:
                    enacted_date = _parse_citation_date(first_citation.act.date)

                # Get Statutes at Large citation
                if first_citation.law:
                    if first_citation.law.stat_volume and first_citation.law.stat_page:
                        statutes_at_large_citation = (
                            f"{first_citation.law.stat_volume} Stat. "
                            f"{first_citation.law.stat_page}"
                        )
                elif (
                    first_citation.act
                    and first_citation.act.stat_volume
                    and first_citation.act.stat_page
                ):
                    statutes_at_large_citation = (
                        f"{first_citation.act.stat_volume} Stat. "
                        f"{first_citation.act.stat_page}"
                    )

        # Derive last_modified_date from the most recent amendment year
        last_modified_date = None
        if normalized.section_notes and normalized.section_notes.amendments:
            max_year = max(a.year for a in normalized.section_notes.amendments)
            last_modified_date = date(max_year, 1, 1)

        result = await self.session.execute(
            select(USCodeSection).where(
                USCodeSection.title_number == title_number,
                USCodeSection.section_number == parsed.section_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                existing.heading = _clean_heading(parsed.heading)
                existing.full_citation = parsed.full_citation
                existing.text_content = text_content
                existing.group_id = group_id
                existing.notes = parsed.notes
                existing.normalized_notes = normalized_notes
                existing.normalized_provisions = normalized_provisions
                existing.enacted_date = enacted_date
                existing.statutes_at_large_citation = statutes_at_large_citation
                existing.last_modified_date = last_modified_date
                existing.sort_order = parsed.sort_order
            return existing

        section = USCodeSection(
            group_id=group_id,
            title_number=title_number,
            section_number=parsed.section_number,
            heading=_clean_heading(parsed.heading),
            full_citation=parsed.full_citation,
            text_content=text_content,
            notes=parsed.notes,
            normalized_notes=normalized_notes,
            normalized_provisions=normalized_provisions,
            enacted_date=enacted_date,
            statutes_at_large_citation=statutes_at_large_citation,
            last_modified_date=last_modified_date,
            sort_order=parsed.sort_order,
        )
        self.session.add(section)
        await self.session.flush()
        return section

    async def ingest_phase1_titles(
        self, force_download: bool = False, force_parse: bool = False
    ) -> list[DataIngestionLog]:
        """Ingest all Phase 1 target titles.

        Args:
            force_download: If True, download even if files exist.
            force_parse: If True, re-parse and update even if already ingested.

        Returns:
            List of ingestion log records.
        """
        from pipeline.olrc.downloader import PHASE_1_TITLES

        logs = []
        for title_number in PHASE_1_TITLES:
            logger.info(f"Ingesting Title {title_number}...")
            log = await self.ingest_title(
                title_number,
                force_download=force_download,
                force_parse=force_parse,
            )
            logs.append(log)
            logger.info(f"Title {title_number}: {log.status}")

        return logs
