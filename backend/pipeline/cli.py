"""CLI for running data ingestion pipelines."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from pipeline.olrc.downloader import PHASE_1_TITLES, OLRCDownloader
from pipeline.olrc.parser import USLMParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def download_titles(
    titles: list[int], download_dir: Path, force: bool = False
) -> dict[int, Path | None]:
    """Download US Code titles from OLRC.

    Args:
        titles: List of title numbers to download.
        download_dir: Directory to store downloads.
        force: If True, re-download even if files exist.

    Returns:
        Dictionary mapping title numbers to XML file paths.
    """
    downloader = OLRCDownloader(download_dir=download_dir)
    results = {}

    for title_num in titles:
        logger.info(f"Downloading Title {title_num}...")
        path = await downloader.download_title(title_num, force=force)
        results[title_num] = path
        if path:
            logger.info(f"  -> {path}")
        else:
            logger.error("  -> Failed to download")

    return results


def parse_title(xml_path: Path) -> None:
    """Parse a US Code title XML file and print summary.

    Args:
        xml_path: Path to the XML file.
    """
    parser = USLMParser()
    result = parser.parse_file(xml_path)

    print(f"\nTitle {result.title.title_number}: {result.title.title_name}")
    print(f"  Positive Law: {result.title.is_positive_law}")
    print(f"  Chapters: {len(result.chapters)}")
    print(f"  Subchapters: {len(result.subchapters)}")
    print(f"  Sections: {len(result.sections)}")

    if result.chapters:
        print("\n  First 5 chapters:")
        for ch in result.chapters[:5]:
            print(f"    Chapter {ch.chapter_number}: {ch.chapter_name}")

    if result.sections:
        print("\n  First 5 sections:")
        for sec in result.sections[:5]:
            print(f"    § {sec.section_number}: {sec.heading}")


# =============================================================================
# GovInfo Public Law functions
# =============================================================================


async def list_public_laws(
    congress: int | None = None,
    days: int = 30,
    limit: int = 20,
) -> None:
    """List public laws from GovInfo API.

    Args:
        congress: Filter by Congress number (optional).
        days: Number of days to look back (default: 30).
        limit: Maximum number of results to display.
    """
    from datetime import timedelta

    from pipeline.govinfo.client import GovInfoClient

    client = GovInfoClient()

    start_date = datetime.utcnow() - timedelta(days=days)
    laws = await client.get_public_laws(start_date=start_date, congress=congress)

    print(f"\nPublic Laws (last {days} days)")
    if congress:
        print(f"Filtered to Congress {congress}")
    print(f"Found {len(laws)} laws\n")

    for i, law in enumerate(laws[:limit]):
        print(f"  PL {law.congress}-{law.law_number}: {law.title[:70]}...")
        if i >= limit - 1 and len(laws) > limit:
            print(f"\n  ... and {len(laws) - limit} more")
            break


async def ingest_public_law(
    congress: int,
    law_number: int,
    force: bool = False,
) -> int:
    """Ingest a single Public Law from GovInfo.

    Args:
        congress: Congress number.
        law_number: Law number within that Congress.
        force: If True, update existing record.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.govinfo.ingestion import PublicLawIngestionService

    async with async_session_maker() as session:
        service = PublicLawIngestionService(session)
        log = await service.ingest_law(congress, law_number, force=force)

        if log.status == "completed":
            logger.info(f"Ingested PL {congress}-{law_number}: {log.details}")
            return 0
        else:
            logger.error(
                f"Failed to ingest PL {congress}-{law_number}: {log.error_message}"
            )
            return 1


async def ingest_congress_laws(
    congress: int,
    force: bool = False,
) -> int:
    """Ingest all Public Laws for a Congress.

    Args:
        congress: Congress number.
        force: If True, update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.govinfo.ingestion import PublicLawIngestionService

    async with async_session_maker() as session:
        service = PublicLawIngestionService(session)
        log = await service.ingest_congress(congress, force=force)

        if log.status == "completed":
            logger.info(
                f"Ingested Congress {congress}: {log.records_created} created, "
                f"{log.records_updated} updated, "
                f"{log.records_processed - log.records_created - log.records_updated} skipped"
            )
            return 0
        else:
            logger.error(f"Failed to ingest Congress {congress}: {log.error_message}")
            return 1


async def ingest_recent_laws(
    days: int = 30,
    force: bool = False,
) -> int:
    """Ingest Public Laws modified in the last N days.

    Args:
        days: Number of days to look back.
        force: If True, update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.govinfo.ingestion import PublicLawIngestionService

    async with async_session_maker() as session:
        service = PublicLawIngestionService(session)
        log = await service.ingest_recent_laws(days, force=force)

        if log.status == "completed":
            logger.info(
                f"Ingested recent laws (last {days} days): "
                f"{log.records_created} created, {log.records_updated} updated"
            )
            return 0
        else:
            logger.error(f"Failed to ingest recent laws: {log.error_message}")
            return 1


# =============================================================================
# Congress.gov Legislator functions
# =============================================================================


async def list_members(
    congress: int | None = None,
    current: bool = False,
    limit: int = 20,
) -> None:
    """List members of Congress.

    Args:
        congress: Filter by Congress number (optional).
        current: If True, show only current members.
        limit: Maximum number of results to display.
    """
    from pipeline.congress.client import CongressClient

    client = CongressClient()

    if congress:
        members = await client.get_members_by_congress(congress, current_member=current)
        print(f"\nMembers of Congress {congress}")
    else:
        members = await client.get_members(current_member=current if current else None)
        print("\nMembers of Congress")

    if current:
        print("(Current members only)")
    print(f"Found {len(members)} members\n")

    for i, member in enumerate(members[:limit]):
        party = member.party_name or "Unknown"
        state = member.state or "??"
        print(f"  {member.bioguide_id}: {member.name} ({party}, {state})")
        if i >= limit - 1 and len(members) > limit:
            print(f"\n  ... and {len(members) - limit} more")
            break


async def ingest_member(
    bioguide_id: str,
    force: bool = False,
) -> int:
    """Ingest a single member of Congress.

    Args:
        bioguide_id: The member's Bioguide ID.
        force: If True, update existing record.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.congress.ingestion import LegislatorIngestionService

    async with async_session_maker() as session:
        service = LegislatorIngestionService(session)
        log = await service.ingest_member(bioguide_id, force=force)

        if log.status == "completed":
            logger.info(f"Ingested member {bioguide_id}: {log.details}")
            return 0
        else:
            logger.error(f"Failed to ingest member {bioguide_id}: {log.error_message}")
            return 1


async def ingest_congress_members(
    congress: int,
    force: bool = False,
) -> int:
    """Ingest all members from a Congress.

    Args:
        congress: Congress number.
        force: If True, update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.congress.ingestion import LegislatorIngestionService

    async with async_session_maker() as session:
        service = LegislatorIngestionService(session)
        log = await service.ingest_congress(congress, force=force)

        if log.status == "completed":
            logger.info(
                f"Ingested Congress {congress}: {log.records_created} created, "
                f"{log.records_updated} updated, "
                f"{log.records_processed - log.records_created - log.records_updated} skipped"
            )
            return 0
        else:
            logger.error(
                f"Failed to ingest Congress {congress} members: {log.error_message}"
            )
            return 1


async def ingest_current_members(
    force: bool = False,
) -> int:
    """Ingest all current members of Congress.

    Args:
        force: If True, update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.congress.ingestion import LegislatorIngestionService

    async with async_session_maker() as session:
        service = LegislatorIngestionService(session)
        log = await service.ingest_current_members(force=force)

        if log.status == "completed":
            logger.info(
                f"Ingested current members: {log.records_created} created, "
                f"{log.records_updated} updated"
            )
            return 0
        else:
            logger.error(f"Failed to ingest current members: {log.error_message}")
            return 1


# =============================================================================
# Line Normalizer functions (Task 1.11)
# =============================================================================


def _parse_section_reference(ref: str) -> tuple[int, str] | None:
    """Parse a section reference like '17 USC 106' or '17/106' into (title, section).

    Supported formats:
    - "17 USC 106" or "17 U.S.C. 106"
    - "17/106"
    - "17 106"
    - "Title 17 Section 106"

    Returns:
        Tuple of (title_number, section_number) or None if parsing fails.
    """
    import re

    ref = ref.strip()

    # Format: "17/106" or "17 106"
    match = re.match(r"^(\d+)[/\s]+(\d+[A-Za-z]?)$", ref)
    if match:
        return int(match.group(1)), match.group(2)

    # Format: "17 USC 106" or "17 U.S.C. 106" or "17 U.S.C. § 106"
    match = re.match(
        r"^(\d+)\s+(?:U\.?S\.?C\.?|USC)\s*§?\s*(\d+[A-Za-z]?)$", ref, re.IGNORECASE
    )
    if match:
        return int(match.group(1)), match.group(2)

    # Format: "Title 17 Section 106"
    match = re.match(
        r"^[Tt]itle\s+(\d+)\s+[Ss]ection\s+(\d+[A-Za-z]?)$", ref, re.IGNORECASE
    )
    if match:
        return int(match.group(1)), match.group(2)

    return None


async def _fetch_section_from_db(title_num: int, section_num: str) -> str | None:
    """Fetch section text from the database."""
    from sqlalchemy import select

    from app.models.base import async_session_maker
    from app.models.us_code import USCodeSection, USCodeTitle

    async with async_session_maker() as session:
        result = await session.execute(
            select(USCodeSection)
            .join(USCodeTitle)
            .where(
                USCodeTitle.title_number == title_num,
                USCodeSection.section_number == section_num,
            )
        )
        section = result.scalar_one_or_none()

        if section and section.text_content:
            return section.text_content

    return None


def _fetch_section_from_xml(
    title_num: int, section_num: str, data_dir: Path
) -> str | None:
    """Fetch section text from OLRC XML files."""
    from pipeline.olrc.downloader import OLRCDownloader
    from pipeline.olrc.parser import USLMParser

    downloader = OLRCDownloader(download_dir=data_dir)
    xml_path = downloader.get_xml_path(title_num)

    if not xml_path:
        return None

    parser = USLMParser()
    result = parser.parse_file(xml_path)

    for section in result.sections:
        if section.section_number == section_num:
            return section.text_content

    return None


def normalize_text_command(
    section_ref: str | None = None,
    text: str | None = None,
    file: Path | None = None,
    data_dir: Path = Path("data/olrc"),
    use_tabs: bool = True,
    indent_width: int = 4,
    show_metadata: bool = False,
    show_raw: bool = False,
) -> int:
    """Normalize legal text into lines and display the result.

    Args:
        section_ref: Section reference like "17 USC 106".
        text: Text to normalize (if not using section_ref or file).
        file: Path to file containing text.
        data_dir: Directory containing OLRC XML files.
        use_tabs: If True, use tabs for indentation; if False, use spaces.
        indent_width: Spaces per indent level (only used if use_tabs=False).
        show_metadata: Show line metadata (positions, markers).
        show_raw: Show raw text before normalization.

    Returns:
        0 on success, 1 on failure.
    """
    from pipeline.legal_parser.line_normalizer import normalize_section

    content = None
    source_info = None

    # Priority: section_ref > file > text > stdin
    if section_ref:
        parsed = _parse_section_reference(section_ref)
        if not parsed:
            print(f"Error: Could not parse section reference: {section_ref}")
            print("Supported formats: '17 USC 106', '17/106', 'Title 17 Section 106'")
            return 1

        title_num, section_num = parsed
        source_info = f"{title_num} U.S.C. § {section_num}"

        # Try database first
        content = asyncio.run(_fetch_section_from_db(title_num, section_num))
        if content:
            source_info += " (from database)"
        else:
            # Try XML files
            content = _fetch_section_from_xml(title_num, section_num, data_dir)
            if content:
                source_info += f" (from XML: {data_dir})"

        if not content:
            print(f"Error: Section {title_num} U.S.C. § {section_num} not found")
            print("  - Not in database")
            print(f"  - XML file not found in {data_dir}")
            print(f"\nTry downloading first: uv run python -m pipeline.cli download --titles {title_num}")
            return 1

    elif file:
        if not file.exists():
            print(f"Error: File not found: {file}")
            return 1
        content = file.read_text()
        source_info = f"file: {file}"

    elif text:
        content = text
        source_info = "command line text"

    else:
        # Read from stdin
        print("Enter text to normalize (Ctrl+D to finish):")
        content = sys.stdin.read()
        source_info = "stdin"

    if not content.strip():
        print("Error: No text provided")
        return 1

    # Normalize the text
    result = normalize_section(content, use_tabs=use_tabs, indent_width=indent_width)

    # Display results
    print()
    print("=" * 70)
    print(f"SOURCE: {source_info}")
    print("=" * 70)

    if show_raw:
        print()
        print("RAW TEXT:")
        print("-" * 70)
        # Show first 1000 chars
        if len(content) > 1000:
            print(content[:1000] + "...")
            print(f"  [truncated, {len(content)} chars total]")
        else:
            print(content)
        print("-" * 70)

    print()
    print("NORMALIZED OUTPUT:")
    print("-" * 70)
    for line in result.lines:
        prefix = f"L{line.line_number:3d} │"
        display = line.to_display(use_tabs=use_tabs, indent_width=indent_width)
        print(f"{prefix} {display}")

    print("-" * 70)
    print(f"Total lines: {result.line_count}")
    print(f"Law text: {len(result.law_text):,} chars")

    if result.notes.has_notes:
        print(f"Notes stripped: {len(result.notes.raw_notes):,} chars")

    if show_metadata:
        print()
        print("LINE METADATA:")
        print("-" * 70)
        for line in result.lines:
            marker_info = f"marker='{line.marker}'" if line.marker else "prose"
            print(
                f"  L{line.line_number}: indent={line.indent_level}, "
                f"{marker_info}, chars=[{line.start_char}:{line.end_char}]"
            )

    # Show citations (like imports at the top of a file)
    if result.notes.has_citations:
        print()
        print("CITATIONS:")
        print("-" * 70)

        # Group citations: first is enactment, rest are amendments
        enactment = [c for c in result.notes.citations if c.is_original]
        amendments = [c for c in result.notes.citations if not c.is_original]

        def format_citation(citation):
            parts = [citation.public_law_id]
            if citation.title:
                parts.append(f"title {citation.title}")
            if citation.section:
                parts.append(f"§ {citation.section}")
            if citation.date:
                parts.append(citation.date)
            if citation.stat_reference:
                parts.append(citation.stat_reference)
            return ", ".join(parts)

        if enactment:
            print("  # Enactment")
            for citation in enactment:
                print(f"  {format_citation(citation)}")

        if amendments:
            if enactment:
                print()  # Blank line between sections
            print("  # Amendments")
            for citation in amendments:
                print(f"  {format_citation(citation)}")

        print("-" * 70)

    # Show notes summary if present
    if result.notes.has_notes:
        print()
        print("NOTES (stripped from law text):")
        print("-" * 70)
        if result.notes.historical_notes:
            preview = result.notes.historical_notes[:200].replace("\n", " ")
            print(f"  Historical: {preview}...")
        if result.notes.editorial_notes:
            preview = result.notes.editorial_notes[:200].replace("\n", " ")
            print(f"  Editorial: {preview}...")
        if result.notes.statutory_notes:
            preview = result.notes.statutory_notes[:200].replace("\n", " ")
            print(f"  Statutory: {preview}...")
        print("-" * 70)

    return 0


# =============================================================================
# Legal Parser functions (Task 1.11)
# =============================================================================


async def parse_law_command(
    congress: int,
    law_number: int,
    mode: str = "regex",
    default_title: int | None = None,
    min_confidence: float = 0.0,
    dry_run: bool = False,
    validate: bool = True,
) -> int:
    """Parse a Public Law for amendments.

    Args:
        congress: Congress number.
        law_number: Law number.
        mode: Parsing mode (regex, llm, human-plus-llm).
        default_title: Default US Code title.
        min_confidence: Minimum confidence threshold.
        dry_run: If True, parse without saving.
        validate: If True, validate against GovInfo metadata.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from app.models.enums import ParsingMode
    from pipeline.govinfo.client import GovInfoClient
    from pipeline.legal_parser.parsing_modes import (
        RegExParsingSession,
        validate_against_govinfo,
    )

    # Map mode string to enum
    mode_map = {
        "regex": ParsingMode.REGEX,
        "llm": ParsingMode.LLM,
        "human-plus-llm": ParsingMode.HUMAN_PLUS_LLM,
    }
    parsing_mode = mode_map.get(mode, ParsingMode.REGEX)

    if parsing_mode != ParsingMode.REGEX:
        logger.error(f"Parsing mode '{mode}' is not yet implemented")
        return 1

    # Fetch law text from GovInfo
    client = GovInfoClient()
    law_info = await client.get_public_law(congress, law_number)
    if not law_info:
        logger.error(f"Law PL {congress}-{law_number} not found")
        return 1

    # Get full text
    law_text = await client.get_law_text(congress, law_number)
    if not law_text:
        logger.error(f"Could not retrieve text for PL {congress}-{law_number}")
        return 1

    print(f"\nParsing PL {congress}-{law_number}")
    print(
        f"  Title: {law_info.title[:70]}..."
        if len(law_info.title) > 70
        else f"  Title: {law_info.title}"
    )
    print(f"  Text length: {len(law_text):,} characters")
    print(f"  Mode: {parsing_mode.value}")
    print()

    async with async_session_maker() as session:
        # Get or create law_id
        from sqlalchemy import select

        from app.models.public_law import PublicLaw

        result = await session.execute(
            select(PublicLaw).where(
                PublicLaw.congress == congress,
                PublicLaw.law_number == str(law_number),
            )
        )
        law = result.scalar_one_or_none()

        if not law:
            logger.error(
                f"Law PL {congress}-{law_number} not in database. "
                "Run 'govinfo-ingest-law' first."
            )
            return 1

        # Parse the law
        parser_session = RegExParsingSession(
            session,
            default_title=default_title,
            min_confidence=min_confidence,
        )
        result = await parser_session.parse_law(
            law_id=law.law_id,
            law_text=law_text,
            save_to_db=not dry_run,
        )

        # Validate against GovInfo metadata
        govinfo_mismatch = None
        if validate and not dry_run and result.ingestion_report_id:
            from sqlalchemy import select

            from app.models.validation import IngestionReport

            report_result = await session.execute(
                select(IngestionReport).where(
                    IngestionReport.report_id == result.ingestion_report_id
                )
            )
            report = report_result.scalar_one_or_none()
            if report:
                has_mismatch, mismatch_desc = await validate_against_govinfo(
                    report, congress, law_number, session
                )
                if has_mismatch:
                    govinfo_mismatch = mismatch_desc

        # Display results
        print(
            f"Parsing {'completed' if result.status.value == 'Completed' else result.status.value}"
        )
        print(f"  Session ID: {result.session_id}")
        print(f"  Amendments found: {len(result.amendments)}")
        print(f"  Coverage: {result.coverage_report.coverage_percentage:.1f}%")
        print(
            f"    Claimed: {result.coverage_report.claimed_length:,} / {result.coverage_report.total_length:,} chars"
        )
        print(f"    Flagged unclaimed: {len(result.coverage_report.flagged_unclaimed)}")
        print(f"    Ignored unclaimed: {len(result.coverage_report.ignored_unclaimed)}")

        if result.amendments:
            # Show amendment stats
            stats = parser_session.parser.get_statistics(result.amendments)
            print("\n  Amendment statistics:")
            print(f"    High confidence (>=90%): {stats['high_confidence']}")
            print(f"    Needs review: {stats['needs_review']}")
            print(f"    Average confidence: {stats['avg_confidence']:.2%}")

            if stats.get("by_change_type"):
                print(f"    By type: {stats['by_change_type']}")

        # Show GovInfo validation results
        if validate and not dry_run:
            print("\n  GovInfo validation:")
            if govinfo_mismatch:
                print(f"    WARNING: {govinfo_mismatch}")
            else:
                print("    Amendment count appears reasonable")

        if result.escalation_recommended or govinfo_mismatch:
            reason = result.escalation_reason or govinfo_mismatch
            print(f"\n  ESCALATION RECOMMENDED: {reason}")

        if result.ingestion_report_id:
            print(f"\n  Ingestion report ID: {result.ingestion_report_id}")

        if dry_run:
            print("\n  [DRY RUN - results not saved to database]")

    return 0


async def show_ingestion_report_command(
    report_id: int,
    verbose: bool = False,
) -> int:
    """Display an ingestion report.

    Args:
        report_id: Report ID to display.
        verbose: Show detailed amendment list.

    Returns:
        0 on success, 1 on failure.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.base import async_session_maker
    from app.models.validation import IngestionReport, ParsedAmendmentRecord

    async with async_session_maker() as session:
        result = await session.execute(
            select(IngestionReport)
            .options(selectinload(IngestionReport.session))
            .where(IngestionReport.report_id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            logger.error(f"Report {report_id} not found")
            return 1

        print(f"\nIngestion Report #{report.report_id}")
        print(f"  Law ID: {report.law_id}")
        print(f"  Session ID: {report.session_id}")
        print(f"  Mode: {report.session.mode.value if report.session else 'Unknown'}")
        print(
            f"  Status: {report.session.status.value if report.session else 'Unknown'}"
        )
        print()
        print("Coverage:")
        print(f"  Total text length: {report.total_text_length:,}")
        print(f"  Claimed text length: {report.claimed_text_length:,}")
        print(f"  Coverage: {report.coverage_percentage:.1f}%")
        print(f"  Flagged unclaimed: {report.unclaimed_flagged_count}")
        print(f"  Ignored unclaimed: {report.unclaimed_ignored_count}")
        print()
        print("Amendments:")
        print(f"  Total: {report.total_amendments}")
        print(f"  High confidence: {report.high_confidence_count}")
        print(f"  Needs review: {report.needs_review_count}")
        print(f"  Average confidence: {report.avg_confidence:.2%}")

        if report.amendments_by_type:
            print(f"  By type: {report.amendments_by_type}")

        if report.amendments_by_pattern:
            print(f"  By pattern: {report.amendments_by_pattern}")

        print()
        print("Decision:")
        print(
            f"  Auto-approve eligible: {'Yes' if report.auto_approve_eligible else 'No'}"
        )
        print(
            f"  Escalation recommended: {'Yes' if report.escalation_recommended else 'No'}"
        )
        if report.escalation_reason:
            print(f"  Escalation reason: {report.escalation_reason}")

        if verbose:
            # Fetch amendments
            amend_result = await session.execute(
                select(ParsedAmendmentRecord)
                .where(ParsedAmendmentRecord.session_id == report.session_id)
                .order_by(ParsedAmendmentRecord.start_pos)
            )
            amendments = amend_result.scalars().all()

            if amendments:
                print(f"\nAmendments ({len(amendments)}):")
                for amend in amendments:
                    target = (
                        f"{amend.target_title} USC {amend.target_section}"
                        if amend.target_title
                        else "unknown"
                    )
                    review = " [NEEDS REVIEW]" if amend.needs_review else ""
                    print(
                        f"  - {amend.pattern_name}: {target} "
                        f"(conf: {amend.confidence:.0%}){review}"
                    )

    return 0


async def list_pending_patterns_command(limit: int = 20) -> int:
    """List pattern discoveries awaiting review.

    Args:
        limit: Maximum results.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.legal_parser.pattern_learning import PatternLearningService

    async with async_session_maker() as session:
        service = PatternLearningService(session)
        patterns = await service.get_pending_patterns(limit=limit)

        if not patterns:
            print("\nNo pending pattern discoveries")
            return 0

        print(f"\nPending Pattern Discoveries ({len(patterns)})")
        for p in patterns:
            keywords = p.detected_keywords if p.detected_keywords else "none"
            print(f"\n  #{p.discovery_id}")
            print(f"    Keywords: {keywords}")
            print(f"    Text: {p.unmatched_text[:100]}...")
            print(f"    Status: {p.status.value}")

    return 0


async def promote_pattern_command(
    discovery_id: int,
    pattern_name: str | None = None,
) -> int:
    """Promote a discovered pattern.

    Args:
        discovery_id: Discovery ID to promote.
        pattern_name: Name for the new pattern.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.legal_parser.pattern_learning import PatternLearningService

    async with async_session_maker() as session:
        service = PatternLearningService(session)
        try:
            await service.promote_pattern(
                discovery_id=discovery_id,
                pattern_name=pattern_name,
            )
            print(f"\nPattern discovery #{discovery_id} promoted successfully")
            return 0
        except Exception as e:
            logger.error(f"Failed to promote pattern: {e}")
            return 1


# =============================================================================
# House Vote functions
# =============================================================================


async def list_house_votes(
    congress: int,
    session: int | None = None,
    limit: int = 20,
) -> None:
    """List House roll call votes.

    Args:
        congress: Congress number (118+).
        session: Session number (1 or 2, optional).
        limit: Maximum results to display.
    """
    from pipeline.congress.client import CongressClient

    client = CongressClient()

    votes = await client.get_house_votes(congress, session=session, limit=limit)

    session_str = f"/{session}" if session else ""
    print(f"\nHouse Votes for Congress {congress}{session_str}")
    print(f"Found {len(votes)} votes\n")

    for i, vote in enumerate(votes[:limit]):
        bill_info = ""
        if vote.bill_type and vote.bill_number:
            bill_info = f" ({vote.bill_type} {vote.bill_number})"
        question = (vote.question or "")[:50]
        print(f"  Roll {vote.roll_number}: {question}...{bill_info} - {vote.result}")
        if i >= limit - 1 and len(votes) > limit:
            print(f"\n  ... and {len(votes) - limit} more")
            break


async def ingest_house_vote(
    congress: int,
    session: int,
    roll_number: int,
    force: bool = False,
) -> int:
    """Ingest a single House roll call vote.

    Args:
        congress: Congress number (118+).
        session: Session number (1 or 2).
        roll_number: Roll call vote number.
        force: If True, update existing record.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.congress.vote_ingestion import VoteIngestionService

    async with async_session_maker() as session_db:
        service = VoteIngestionService(session_db)
        log = await service.ingest_house_vote(
            congress, session, roll_number, force=force
        )

        if log.status == "completed":
            logger.info(
                f"Ingested House vote {congress}/{session}/{roll_number}: {log.details}"
            )
            return 0
        else:
            logger.error(
                f"Failed to ingest House vote {congress}/{session}/{roll_number}: "
                f"{log.error_message}"
            )
            return 1


async def ingest_house_votes(
    congress: int,
    session: int | None = None,
    limit: int | None = None,
    force: bool = False,
) -> int:
    """Ingest House votes for a Congress/session.

    Args:
        congress: Congress number (118+).
        session: Session number (1 or 2, optional).
        limit: Maximum votes to ingest.
        force: If True, update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.congress.vote_ingestion import VoteIngestionService

    async with async_session_maker() as session_db:
        service = VoteIngestionService(session_db)
        log = await service.ingest_house_votes_for_congress(
            congress, session_num=session, force=force, limit=limit
        )

        if log.status == "completed":
            logger.info(
                f"Ingested House votes for Congress {congress}: "
                f"{log.records_created} created, {log.records_updated} updated"
            )
            return 0
        else:
            logger.error(f"Failed to ingest House votes: {log.error_message}")
            return 1


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="US Code data ingestion pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download US Code titles")
    download_parser.add_argument(
        "--titles",
        type=int,
        nargs="+",
        help="Title numbers to download (default: Phase 1 titles)",
    )
    download_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="Download directory (default: data/olrc)",
    )
    download_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist",
    )

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a downloaded title")
    parse_parser.add_argument(
        "title",
        type=int,
        help="Title number to parse",
    )
    parse_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="Download directory (default: data/olrc)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List downloaded titles")
    list_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="Download directory (default: data/olrc)",
    )

    # =========================================================================
    # GovInfo Public Law commands
    # =========================================================================

    # govinfo-list command
    govinfo_list_parser = subparsers.add_parser(
        "govinfo-list", help="List public laws from GovInfo API"
    )
    govinfo_list_parser.add_argument(
        "--congress",
        type=int,
        help="Filter by Congress number",
    )
    govinfo_list_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)",
    )
    govinfo_list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum results to display (default: 20)",
    )

    # govinfo-ingest-law command
    govinfo_law_parser = subparsers.add_parser(
        "govinfo-ingest-law", help="Ingest a single Public Law from GovInfo"
    )
    govinfo_law_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (e.g., 119)",
    )
    govinfo_law_parser.add_argument(
        "law_number",
        type=int,
        help="Law number (e.g., 60 for PL 119-60)",
    )
    govinfo_law_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing record if present",
    )

    # govinfo-ingest-congress command
    govinfo_congress_parser = subparsers.add_parser(
        "govinfo-ingest-congress", help="Ingest all Public Laws for a Congress"
    )
    govinfo_congress_parser.add_argument(
        "congress",
        type=int,
        help="Congress number to ingest (e.g., 119)",
    )
    govinfo_congress_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing records if present",
    )

    # govinfo-ingest-recent command
    govinfo_recent_parser = subparsers.add_parser(
        "govinfo-ingest-recent", help="Ingest recently modified Public Laws"
    )
    govinfo_recent_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)",
    )
    govinfo_recent_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing records if present",
    )

    # =========================================================================
    # Congress.gov Legislator commands
    # =========================================================================

    # congress-list-members command
    congress_list_parser = subparsers.add_parser(
        "congress-list-members", help="List members of Congress"
    )
    congress_list_parser.add_argument(
        "--congress",
        type=int,
        help="Filter by Congress number (e.g., 118)",
    )
    congress_list_parser.add_argument(
        "--current",
        action="store_true",
        help="Show only currently serving members",
    )
    congress_list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum results to display (default: 20)",
    )

    # congress-ingest-member command
    congress_member_parser = subparsers.add_parser(
        "congress-ingest-member", help="Ingest a single member of Congress"
    )
    congress_member_parser.add_argument(
        "bioguide_id",
        type=str,
        help="Bioguide ID (e.g., B000944)",
    )
    congress_member_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing record if present",
    )

    # congress-ingest-congress command
    congress_congress_parser = subparsers.add_parser(
        "congress-ingest-congress", help="Ingest all members from a Congress"
    )
    congress_congress_parser.add_argument(
        "congress",
        type=int,
        help="Congress number to ingest (e.g., 118)",
    )
    congress_congress_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing records if present",
    )

    # congress-ingest-current command
    congress_current_parser = subparsers.add_parser(
        "congress-ingest-current", help="Ingest all current members of Congress"
    )
    congress_current_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing records if present",
    )

    # =========================================================================
    # House Vote commands
    # =========================================================================

    # house-list-votes command
    house_list_parser = subparsers.add_parser(
        "house-list-votes", help="List House roll call votes (118th Congress+)"
    )
    house_list_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (118+)",
    )
    house_list_parser.add_argument(
        "--session",
        type=int,
        help="Session number (1 or 2)",
    )
    house_list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum results to display (default: 20)",
    )

    # house-ingest-vote command
    house_vote_parser = subparsers.add_parser(
        "house-ingest-vote", help="Ingest a single House roll call vote"
    )
    house_vote_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (118+)",
    )
    house_vote_parser.add_argument(
        "session",
        type=int,
        help="Session number (1 or 2)",
    )
    house_vote_parser.add_argument(
        "roll_number",
        type=int,
        help="Roll call vote number",
    )
    house_vote_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing record if present",
    )

    # house-ingest-votes command
    house_votes_parser = subparsers.add_parser(
        "house-ingest-votes", help="Ingest House votes for a Congress/session"
    )
    house_votes_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (118+)",
    )
    house_votes_parser.add_argument(
        "--session",
        type=int,
        help="Session number (1 or 2)",
    )
    house_votes_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum votes to ingest",
    )
    house_votes_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing records if present",
    )

    # =========================================================================
    # Line Normalizer commands (Task 1.11)
    # =========================================================================

    # normalize-text command
    normalize_parser = subparsers.add_parser(
        "normalize-text",
        help="Normalize legal text into lines (for testing line normalization)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch and normalize a US Code section
  %(prog)s "17 USC 106"
  %(prog)s "17/106"
  %(prog)s "Title 17 Section 106"

  # Normalize text from a file
  %(prog)s --file section.txt

  # Normalize text directly
  %(prog)s --text "(a) First item. (b) Second item."

  # Show metadata and raw text
  %(prog)s "17 USC 106" --metadata --raw
""",
    )
    normalize_parser.add_argument(
        "section",
        nargs="?",
        type=str,
        help="Section reference (e.g., '17 USC 106', '17/106')",
    )
    normalize_parser.add_argument(
        "--text",
        "-t",
        type=str,
        help="Text to normalize directly (instead of section reference)",
    )
    normalize_parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="File containing text to normalize",
    )
    normalize_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="Directory containing OLRC XML files (default: data/olrc)",
    )
    normalize_parser.add_argument(
        "--spaces",
        "-s",
        action="store_true",
        help="Use spaces for indentation instead of tabs",
    )
    normalize_parser.add_argument(
        "--indent-width",
        type=int,
        default=4,
        help="Spaces per indent level when using --spaces (default: 4)",
    )
    normalize_parser.add_argument(
        "--metadata",
        "-m",
        action="store_true",
        help="Show line metadata (positions, markers)",
    )
    normalize_parser.add_argument(
        "--raw",
        "-r",
        action="store_true",
        help="Show raw text before normalization",
    )

    # =========================================================================
    # Legal Parser commands (Task 1.11)
    # =========================================================================

    # parse-law command
    parse_law_parser = subparsers.add_parser(
        "parse-law", help="Parse a Public Law for amendments"
    )
    parse_law_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (e.g., 118)",
    )
    parse_law_parser.add_argument(
        "law_number",
        type=int,
        help="Law number (e.g., 60 for PL 118-60)",
    )
    parse_law_parser.add_argument(
        "--mode",
        type=str,
        choices=["regex", "llm", "human-plus-llm"],
        default="regex",
        help="Parsing mode (default: regex)",
    )
    parse_law_parser.add_argument(
        "--default-title",
        type=int,
        help="Default US Code title when not specified in text",
    )
    parse_law_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold (0.0-1.0, default: 0.0)",
    )
    parse_law_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse without saving to database",
    )
    parse_law_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip GovInfo metadata validation",
    )

    # show-ingestion-report command
    show_report_parser = subparsers.add_parser(
        "show-ingestion-report", help="Display an ingestion report"
    )
    show_report_parser.add_argument(
        "report_id",
        type=int,
        help="Report ID to display",
    )
    show_report_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed amendment list",
    )

    # list-pending-patterns command
    list_patterns_parser = subparsers.add_parser(
        "list-pending-patterns", help="List pattern discoveries awaiting review"
    )
    list_patterns_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum results to display (default: 20)",
    )

    # promote-pattern command
    promote_pattern_parser = subparsers.add_parser(
        "promote-pattern", help="Promote a discovered pattern"
    )
    promote_pattern_parser.add_argument(
        "discovery_id",
        type=int,
        help="Discovery ID to promote",
    )
    promote_pattern_parser.add_argument(
        "--pattern-name",
        type=str,
        help="Name for the new pattern",
    )

    args = parser.parse_args()

    if args.command == "download":
        titles = args.titles or PHASE_1_TITLES
        logger.info(f"Downloading titles: {titles}")
        results = asyncio.run(download_titles(titles, args.dir, args.force))

        success = sum(1 for p in results.values() if p is not None)
        failed = len(results) - success
        logger.info(f"Download complete: {success} succeeded, {failed} failed")
        return 0 if failed == 0 else 1

    elif args.command == "parse":
        downloader = OLRCDownloader(download_dir=args.dir)
        xml_path = downloader.get_xml_path(args.title)

        if not xml_path:
            logger.error(f"Title {args.title} not downloaded. Run download first.")
            return 1

        parse_title(xml_path)
        return 0

    elif args.command == "list":
        downloader = OLRCDownloader(download_dir=args.dir)
        titles = downloader.get_downloaded_titles()

        if titles:
            print(f"Downloaded titles: {titles}")
        else:
            print("No titles downloaded yet.")
        return 0

    # =========================================================================
    # GovInfo command handlers
    # =========================================================================

    elif args.command == "govinfo-list":
        asyncio.run(
            list_public_laws(
                congress=args.congress,
                days=args.days,
                limit=args.limit,
            )
        )
        return 0

    elif args.command == "govinfo-ingest-law":
        return asyncio.run(
            ingest_public_law(
                congress=args.congress,
                law_number=args.law_number,
                force=args.force,
            )
        )

    elif args.command == "govinfo-ingest-congress":
        return asyncio.run(
            ingest_congress_laws(
                congress=args.congress,
                force=args.force,
            )
        )

    elif args.command == "govinfo-ingest-recent":
        return asyncio.run(
            ingest_recent_laws(
                days=args.days,
                force=args.force,
            )
        )

    # =========================================================================
    # Congress.gov command handlers
    # =========================================================================

    elif args.command == "congress-list-members":
        asyncio.run(
            list_members(
                congress=args.congress,
                current=args.current,
                limit=args.limit,
            )
        )
        return 0

    elif args.command == "congress-ingest-member":
        return asyncio.run(
            ingest_member(
                bioguide_id=args.bioguide_id,
                force=args.force,
            )
        )

    elif args.command == "congress-ingest-congress":
        return asyncio.run(
            ingest_congress_members(
                congress=args.congress,
                force=args.force,
            )
        )

    elif args.command == "congress-ingest-current":
        return asyncio.run(
            ingest_current_members(
                force=args.force,
            )
        )

    # =========================================================================
    # House Vote command handlers
    # =========================================================================

    elif args.command == "house-list-votes":
        asyncio.run(
            list_house_votes(
                congress=args.congress,
                session=args.session,
                limit=args.limit,
            )
        )
        return 0

    elif args.command == "house-ingest-vote":
        return asyncio.run(
            ingest_house_vote(
                congress=args.congress,
                session=args.session,
                roll_number=args.roll_number,
                force=args.force,
            )
        )

    elif args.command == "house-ingest-votes":
        return asyncio.run(
            ingest_house_votes(
                congress=args.congress,
                session=args.session,
                limit=args.limit,
                force=args.force,
            )
        )

    # =========================================================================
    # Line Normalizer command handlers (Task 1.11)
    # =========================================================================

    elif args.command == "normalize-text":
        return normalize_text_command(
            section_ref=args.section,
            text=args.text,
            file=args.file,
            data_dir=args.dir,
            use_tabs=not args.spaces,
            indent_width=args.indent_width,
            show_metadata=args.metadata,
            show_raw=args.raw,
        )

    # =========================================================================
    # Legal Parser command handlers (Task 1.11)
    # =========================================================================

    elif args.command == "parse-law":
        return asyncio.run(
            parse_law_command(
                congress=args.congress,
                law_number=args.law_number,
                mode=args.mode,
                default_title=args.default_title,
                min_confidence=args.min_confidence,
                dry_run=args.dry_run,
                validate=not args.no_validate,
            )
        )

    elif args.command == "show-ingestion-report":
        return asyncio.run(
            show_ingestion_report_command(
                report_id=args.report_id,
                verbose=args.verbose,
            )
        )

    elif args.command == "list-pending-patterns":
        return asyncio.run(
            list_pending_patterns_command(
                limit=args.limit,
            )
        )

    elif args.command == "promote-pattern":
        return asyncio.run(
            promote_pattern_command(
                discovery_id=args.discovery_id,
                pattern_name=args.pattern_name,
            )
        )

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
