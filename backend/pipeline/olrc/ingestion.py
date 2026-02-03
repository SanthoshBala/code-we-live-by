"""Ingest US Code data from OLRC into the database."""

import logging
import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DataIngestionLog,
    USCodeChapter,
    USCodeSection,
    USCodeSubchapter,
    USCodeTitle,
)
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.normalized_section import normalize_parsed_section
from pipeline.olrc.parser import (
    ParsedChapter,
    ParsedSection,
    ParsedSubchapter,
    ParsedTitle,
    USLMParser,
    USLMParseResult,
)

logger = logging.getLogger(__name__)


def _parse_citation_date(date_str: str | None) -> date | None:
    """Parse a date string from a citation into a Python date object.

    Handles two formats:
    - ISO format from Act hrefs: "1935-08-14" -> date(1935, 8, 14)
    - Prose format from source credits: "Oct. 19, 1976" -> date(1976, 10, 19)

    Args:
        date_str: The date string to parse, or None.

    Returns:
        A date object if parsing succeeds, None otherwise.
    """
    if not date_str:
        return None

    # Try ISO format first (YYYY-MM-DD)
    iso_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if iso_match:
        try:
            return date(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
            )
        except ValueError:
            pass

    # Try prose format (e.g., "Oct. 19, 1976" or "July 3, 1990")
    month_map = {
        "Jan": 1,
        "January": 1,
        "Feb": 2,
        "February": 2,
        "Mar": 3,
        "March": 3,
        "Apr": 4,
        "April": 4,
        "May": 5,
        "Jun": 6,
        "June": 6,
        "Jul": 7,
        "July": 7,
        "Aug": 8,
        "August": 8,
        "Sep": 9,
        "Sept": 9,
        "September": 9,
        "Oct": 10,
        "October": 10,
        "Nov": 11,
        "November": 11,
        "Dec": 12,
        "December": 12,
    }

    # Match "Oct. 19, 1976" or "July 3, 1990" formats
    match = re.match(r"([A-Z][a-z]+)\.?\s+(\d{1,2})\s*,\s+(\d{4})", date_str)
    if match:
        month_str = match.group(1)
        month = month_map.get(month_str)
        if month:
            try:
                return date(int(match.group(3)), month, int(match.group(2)))
            except ValueError:
                pass

    return None


class USCodeIngestionService:
    """Service for ingesting US Code data into the database."""

    def __init__(self, session: AsyncSession, download_dir: Path | str = "data/olrc"):
        """Initialize the ingestion service.

        Args:
            session: SQLAlchemy async session.
            download_dir: Directory for downloaded XML files.
        """
        self.session = session
        self.downloader = OLRCDownloader(download_dir=download_dir)
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
                    select(USCodeTitle).where(USCodeTitle.title_number == title_number)
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
            log.records_processed = (
                1 + stats["chapters"] + stats["subchapters"] + stats["sections"]
            )
            log.records_created = stats["created"]
            log.records_updated = stats["updated"]
            log.details = (
                f"Title: 1, Chapters: {stats['chapters']}, "
                f"Subchapters: {stats['subchapters']}, Sections: {stats['sections']}"
            )

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
            "chapters": 0,
            "subchapters": 0,
            "sections": 0,
            "created": 0,
            "updated": 0,
        }

        # Ingest or update title
        title_record = await self._upsert_title(result.title, force)

        # Create chapter lookup
        chapter_lookup: dict[str, USCodeChapter] = {}

        # Ingest chapters
        for chapter in result.chapters:
            chapter_record = await self._upsert_chapter(
                chapter, title_record.title_id, force
            )
            chapter_lookup[chapter.chapter_number] = chapter_record
            stats["chapters"] += 1
            stats["created" if chapter_record.chapter_id else "updated"] += 1

        # Create subchapter lookup
        subchapter_lookup: dict[str, USCodeSubchapter] = {}

        # Ingest subchapters
        for subchapter in result.subchapters:
            parent_chapter = chapter_lookup.get(subchapter.chapter_number)
            if parent_chapter:
                subch_record = await self._upsert_subchapter(
                    subchapter, parent_chapter.chapter_id, force
                )
                key = f"{subchapter.chapter_number}/{subchapter.subchapter_number}"
                subchapter_lookup[key] = subch_record
                stats["subchapters"] += 1

        # Ingest sections
        for section in result.sections:
            chapter_id = None
            subchapter_id = None

            if section.chapter_number:
                chapter_record = chapter_lookup.get(section.chapter_number)
                if chapter_record:
                    chapter_id = chapter_record.chapter_id

            if section.subchapter_number and section.chapter_number:
                key = f"{section.chapter_number}/{section.subchapter_number}"
                subch_record = subchapter_lookup.get(key)
                if subch_record:
                    subchapter_id = subch_record.subchapter_id

            await self._upsert_section(
                section,
                title_record.title_id,
                chapter_id,
                subchapter_id,
                force,
            )
            stats["sections"] += 1

        return stats

    async def _upsert_title(
        self, parsed: "ParsedTitle", force: bool = False
    ) -> USCodeTitle:
        """Insert or update a title record."""

        result = await self.session.execute(
            select(USCodeTitle).where(USCodeTitle.title_number == parsed.title_number)
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                existing.title_name = parsed.title_name
                existing.is_positive_law = parsed.is_positive_law
            return existing

        title = USCodeTitle(
            title_number=parsed.title_number,
            title_name=parsed.title_name,
            is_positive_law=parsed.is_positive_law,
        )
        self.session.add(title)
        await self.session.flush()
        return title

    async def _upsert_chapter(
        self, parsed: "ParsedChapter", title_id: int, force: bool = False
    ) -> USCodeChapter:
        """Insert or update a chapter record."""

        result = await self.session.execute(
            select(USCodeChapter).where(
                USCodeChapter.title_id == title_id,
                USCodeChapter.chapter_number == parsed.chapter_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                existing.chapter_name = parsed.chapter_name
                existing.sort_order = parsed.sort_order
            return existing

        chapter = USCodeChapter(
            title_id=title_id,
            chapter_number=parsed.chapter_number,
            chapter_name=parsed.chapter_name,
            sort_order=parsed.sort_order,
        )
        self.session.add(chapter)
        await self.session.flush()
        return chapter

    async def _upsert_subchapter(
        self, parsed: "ParsedSubchapter", chapter_id: int, force: bool = False
    ) -> USCodeSubchapter:
        """Insert or update a subchapter record."""

        result = await self.session.execute(
            select(USCodeSubchapter).where(
                USCodeSubchapter.chapter_id == chapter_id,
                USCodeSubchapter.subchapter_number == parsed.subchapter_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                existing.subchapter_name = parsed.subchapter_name
                existing.sort_order = parsed.sort_order
            return existing

        subchapter = USCodeSubchapter(
            chapter_id=chapter_id,
            subchapter_number=parsed.subchapter_number,
            subchapter_name=parsed.subchapter_name,
            sort_order=parsed.sort_order,
        )
        self.session.add(subchapter)
        await self.session.flush()
        return subchapter

    async def _upsert_section(
        self,
        parsed: "ParsedSection",
        title_id: int,
        chapter_id: int | None,
        subchapter_id: int | None,
        force: bool = False,
    ) -> USCodeSection:
        """Insert or update a section record.

        This method normalizes the parsed section and stores:
        - normalized_text in text_content (display-ready indented text)
        - section_notes as JSON in normalized_notes
        - enacted_date and statutes_at_large_citation from first citation
        """
        # Normalize the parsed section to get structured data
        normalized = normalize_parsed_section(parsed)

        # Extract text content (prefer normalized, fall back to raw)
        text_content = normalized.normalized_text or parsed.text_content

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

        result = await self.session.execute(
            select(USCodeSection).where(
                USCodeSection.title_id == title_id,
                USCodeSection.section_number == parsed.section_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if force:
                existing.heading = parsed.heading
                existing.full_citation = parsed.full_citation
                existing.text_content = text_content
                existing.chapter_id = chapter_id
                existing.subchapter_id = subchapter_id
                existing.notes = parsed.notes
                existing.normalized_notes = normalized_notes
                existing.enacted_date = enacted_date
                existing.statutes_at_large_citation = statutes_at_large_citation
                existing.sort_order = parsed.sort_order
            return existing

        section = USCodeSection(
            title_id=title_id,
            chapter_id=chapter_id,
            subchapter_id=subchapter_id,
            section_number=parsed.section_number,
            heading=parsed.heading,
            full_citation=parsed.full_citation,
            text_content=text_content,
            notes=parsed.notes,
            normalized_notes=normalized_notes,
            enacted_date=enacted_date,
            statutes_at_large_citation=statutes_at_large_citation,
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
