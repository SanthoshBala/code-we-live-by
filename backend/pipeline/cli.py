"""CLI for running data ingestion pipelines."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.olrc.downloader import PHASE_1_TITLES, OLRCDownloader
from pipeline.olrc.parser import USLMParser

if TYPE_CHECKING:
    from pipeline.olrc.parser import ParsedSection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5.5s [%(name)s] %(message)s",
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
    print(f"  Groups: {len(result.groups)}")
    print(f"  Sections: {len(result.sections)}")

    chapters = [g for g in result.groups if g.group_type == "chapter"]
    if chapters:
        print("\n  First 5 chapters:")
        for ch in chapters[:5]:
            print(f"    Chapter {ch.number}: {ch.name}")

    if result.sections:
        print("\n  First 5 sections:")
        for sec in result.sections[:5]:
            print(f"    § {sec.section_number}: {sec.heading}")


async def ingest_title(
    title_number: int,
    download_dir: Path = Path("data/olrc"),
    force_download: bool = False,
    force_parse: bool = False,
) -> int:
    """Ingest a US Code title into the database.

    Args:
        title_number: Title number to ingest.
        download_dir: Directory for OLRC XML files.
        force_download: If True, re-download even if file exists.
        force_parse: If True, re-parse and update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.olrc.ingestion import USCodeIngestionService

    async with async_session_maker() as session:
        service = USCodeIngestionService(session, download_dir=download_dir)
        log = await service.ingest_title(
            title_number,
            force_download=force_download,
            force_parse=force_parse,
        )

        if log.status == "completed":
            logger.info(
                f"Ingested Title {title_number}: "
                f"{log.records_processed} records, "
                f"{log.records_created} created, "
                f"{log.records_updated} updated"
            )
            if log.details:
                logger.info(f"  {log.details}")
            return 0
        elif log.status == "skipped":
            logger.info(f"Title {title_number}: {log.details}")
            return 0
        else:
            logger.error(f"Failed to ingest Title {title_number}: {log.error_message}")
            return 1


async def ingest_phase1(
    download_dir: Path = Path("data/olrc"),
    force_download: bool = False,
    force_parse: bool = False,
) -> int:
    """Ingest all Phase 1 US Code titles into the database.

    Args:
        download_dir: Directory for OLRC XML files.
        force_download: If True, re-download even if files exist.
        force_parse: If True, re-parse and update existing records.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.olrc.ingestion import USCodeIngestionService

    async with async_session_maker() as session:
        service = USCodeIngestionService(session, download_dir=download_dir)
        logs = await service.ingest_phase1_titles(
            force_download=force_download,
            force_parse=force_parse,
        )

        succeeded = sum(1 for log in logs if log.status in ("completed", "skipped"))
        failed = sum(1 for log in logs if log.status == "failed")
        total_created = sum(log.records_created or 0 for log in logs)
        total_updated = sum(log.records_updated or 0 for log in logs)

        logger.info(
            f"Phase 1 ingestion complete: {succeeded} succeeded, {failed} failed, "
            f"{total_created} created, {total_updated} updated"
        )

        for log in logs:
            if log.status == "failed":
                logger.error(f"  {log.operation}: {log.error_message}")

        return 1 if failed > 0 else 0


# =============================================================================
# Seed laws for local development
# =============================================================================

# Curated set of Public Laws spanning Phase 1 titles with varying complexity.
# Each entry: (congress, law_number, default_title, short_name)
SEED_LAWS: list[tuple[int, int, int | None, str]] = [
    # Simple (1-3 amendments)
    (113, 22, 26, "Kay Bailey Hutchison Spousal IRA"),
    (117, 107, 18, "Emmett Till Antilynching Act"),
    (117, 224, None, "Speak Out Act"),
    # Small-medium (4-6 amendments)
    (114, 153, 18, "Defend Trade Secrets Act"),
    (116, 128, 42, "PPP Flexibility Act"),
    # Medium (7-20 amendments)
    (115, 264, 17, "Music Modernization Act"),
    (115, 118, 50, "FISA Amendments Reauthorization"),
    (118, 49, 50, "Reforming Intelligence and Securing America Act"),
    # Large (many amendments)
    (115, 97, 26, "Tax Cuts and Jobs Act"),
    (117, 169, 26, "Inflation Reduction Act"),
]


async def seed_laws_command() -> int:
    """Ingest the curated set of seed laws into the database.

    Returns:
        0 on success, 1 if any law failed.
    """
    from app.models.base import async_session_maker
    from pipeline.govinfo.ingestion import PublicLawIngestionService

    print(f"\nSeeding {len(SEED_LAWS)} Public Laws...")
    print()

    failed = 0
    async with async_session_maker() as session:
        service = PublicLawIngestionService(session)
        for congress, law_number, _default_title, short_name in SEED_LAWS:
            label = f"PL {congress}-{law_number}"
            try:
                log = await service.ingest_law(congress, law_number, force=False)
                if log.status in ("completed", "skipped"):
                    status = "ok" if log.status == "completed" else "exists"
                    print(f"  [{status:<6}] {label:<14} {short_name}")
                else:
                    print(f"  [FAIL  ] {label:<14} {short_name}: {log.error_message}")
                    failed += 1
            except Exception as exc:
                print(f"  [ERROR ] {label:<14} {short_name}: {exc}")
                failed += 1

    print()
    if failed:
        print(
            f"  {len(SEED_LAWS) - failed}/{len(SEED_LAWS)} succeeded, {failed} failed"
        )
    else:
        print(f"  All {len(SEED_LAWS)} laws seeded successfully.")

    # Print parse-law quick-reference
    print()
    print("Try parsing with:")
    for congress, law_number, default_title, _short_name in SEED_LAWS[:3]:
        cmd = f"  uv run python -m pipeline.cli parse-law {congress} {law_number}"
        if default_title:
            cmd += f" --default-title {default_title}"
        cmd += " --dry-run"
        print(cmd)
    print("  ...")
    print()

    return 1 if failed else 0


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
    - "15 USC 80a-3a" (hyphenated section numbers)

    Returns:
        Tuple of (title_number, section_number) or None if parsing fails.
    """
    import re

    ref = ref.strip()

    # Section number pattern: digits, letters, and hyphens (e.g., 106, 106a, 80a-3a)
    section_pattern = r"(\d+[A-Za-z0-9-]*)"

    # Format: "17/106" or "17 106"
    match = re.match(rf"^(\d+)[/\s]+{section_pattern}$", ref)
    if match:
        return int(match.group(1)), match.group(2)

    # Format: "17 USC 106" or "17 U.S.C. 106" or "17 U.S.C. § 106"
    match = re.match(
        rf"^(\d+)\s+(?:U\.?S\.?C\.?|USC)\s*§?\s*{section_pattern}$", ref, re.IGNORECASE
    )
    if match:
        return int(match.group(1)), match.group(2)

    # Format: "Title 17 Section 106"
    match = re.match(
        rf"^[Tt]itle\s+(\d+)\s+[Ss]ection\s+{section_pattern}$", ref, re.IGNORECASE
    )
    if match:
        return int(match.group(1)), match.group(2)

    return None


async def _fetch_section_from_db(title_num: int, section_num: str) -> str | None:
    """Fetch section text from the database."""
    from sqlalchemy import select

    from app.models.base import async_session_maker
    from app.models.us_code import USCodeSection

    async with async_session_maker() as session:
        result = await session.execute(
            select(USCodeSection).where(
                USCodeSection.title_number == title_num,
                USCodeSection.section_number == section_num,
            )
        )
        section = result.scalar_one_or_none()

        if section and section.text_content:
            return section.text_content

    return None


def _normalize_section_number(section_num: str) -> str:
    """Normalize section number for comparison.

    Converts hyphens to en-dashes since OLRC XML uses en-dashes.
    """
    return section_num.replace("-", "–")  # hyphen to en-dash


def _fetch_section_from_xml(
    title_num: int, section_num: str, data_dir: Path
) -> tuple[str | None, ParsedSection | None]:
    """Fetch section text from OLRC XML files.

    Returns:
        Tuple of (text_content, ParsedSection).
        ParsedSection is returned if structured subsections are available.
    """
    from pipeline.olrc.downloader import OLRCDownloader
    from pipeline.olrc.parser import USLMParser

    downloader = OLRCDownloader(download_dir=data_dir)
    xml_path = downloader.get_xml_path(title_num)

    if not xml_path:
        return None, None

    parser = USLMParser()
    result = parser.parse_file(xml_path)

    # Normalize input for comparison (OLRC uses en-dashes)
    normalized_input = _normalize_section_number(section_num)

    for section in result.sections:
        if section.section_number == normalized_input:
            return section.text_content, section

    return None, None


def normalize_text_command(
    section_ref: str | None = None,
    text: str | None = None,
    file: Path | None = None,
    data_dir: Path = Path("data/olrc"),
    use_tabs: bool = True,
    indent_width: int = 4,
    show_metadata: bool = False,
    show_raw: bool = False,
    show_section: str | None = None,
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
        show_section: Show only one section with full content. Values:
            provisions/p, source-laws/s, historical/h, editorial/e,
            statutory/st, amendments/a.

    Returns:
        0 on success, 1 on failure.
    """
    from pipeline.olrc.normalized_section import (
        normalize_parsed_section,
        normalize_section,
    )

    content = None
    source_info = None
    parsed_section = None  # Structured section from XML (if available)

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
            # Try XML files - get structured section if available
            content, parsed_section = _fetch_section_from_xml(
                title_num, section_num, data_dir
            )
            if content:
                source_info += f" (from XML: {data_dir})"

        if not content:
            print(f"Error: Section {title_num} U.S.C. § {section_num} not found")
            print("  - Not in database")
            print(f"  - XML file not found in {data_dir}")
            print(
                f"\nTry downloading first: uv run python -m pipeline.cli download --titles {title_num}"
            )
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

    # Normalize the text - use structured data if available
    if parsed_section and parsed_section.subsections:
        # Use structured subsections from XML (explicit headings, no heuristics)
        result = normalize_parsed_section(
            parsed_section, use_tabs=use_tabs, indent_width=indent_width
        )
        source_info += " [structured]"
    else:
        # Fall back to heuristic-based normalization
        result = normalize_section(
            content, use_tabs=use_tabs, indent_width=indent_width
        )
        # If we have XML-parsed notes, use those instead (they're cleaner than heuristic extraction)
        if parsed_section and parsed_section.notes:
            from pipeline.olrc.normalized_section import (
                SectionNotes,
                _parse_notes_structure,
                citations_from_source_credit_refs,
            )

            result.section_notes = SectionNotes()
            result.section_notes.raw_notes = parsed_section.notes

            # Use structured citation refs from XML if available
            citations = None
            if parsed_section.source_credit_refs or parsed_section.act_refs:
                citations = citations_from_source_credit_refs(
                    parsed_section.source_credit_refs,
                    act_refs=parsed_section.act_refs,
                )

            _parse_notes_structure(
                parsed_section.notes, result.section_notes, citations=citations
            )

    # Display results
    # Normalize shorthand section names
    section_map = {
        "p": "provisions",
        "s": "source-laws",
        "h": "historical",
        "e": "editorial",
        "st": "statutory",
        "a": "amendments",
    }
    if show_section:
        show_section = section_map.get(show_section, show_section)

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

    if show_section is None or show_section == "provisions":
        print()
        print("PROVISIONS:")
        print("-" * 70)
        for provision in result.provisions:
            prefix = f"L{provision.line_number:3d} │"
            # Always use spaces for CLI display (tabs don't align well with prefix)
            display = provision.to_display(use_tabs=False, indent_width=indent_width)
            print(f"{prefix} {display}")

        print("-" * 70)

    if show_metadata and (show_section is None or show_section == "provisions"):
        # Count headers and total lines
        num_headers = sum(1 for p in result.provisions if p.is_header)
        num_lines = result.provision_count
        print()
        print(f"PROVISION METADATA ({num_headers} headers, {num_lines} lines):")
        print("-" * 70)
        for provision in result.provisions:
            # Build provision type description
            parts = []
            if provision.marker:
                parts.append(f"marker='{provision.marker}'")
            if provision.is_header:
                parts.append("header")
            if not parts:
                parts.append("blank" if provision.content == "" else "prose")
            provision_info = ", ".join(parts)
            print(
                f"L{provision.line_number}: indent={provision.indent_level}, {provision_info}"
            )

    # Show source laws in changelog format
    if (
        (show_section is None or show_section == "source-laws")
        and result.section_notes
        and result.section_notes.has_citations
    ):
        # Enrich citations with titles from GovInfo API / hardcoded table
        from pipeline.olrc.title_lookup import enrich_citations_with_titles

        asyncio.run(enrich_citations_with_titles(result.section_notes.citations))

        print()
        print("SOURCE LAWS:")
        print("-" * 70)

        def parse_date_to_ymd(date_str: str | None) -> str:
            """Convert various date formats to 'YYYY.MM.DD' format.

            Handles:
            - 'Oct. 19, 1976' or 'July 3, 1990' (prose format)
            - '1935-08-14' (ISO format from Act hrefs)
            """
            if not date_str:
                return "          "  # 10 chars placeholder

            import re

            # Check for ISO format first (YYYY-MM-DD)
            iso_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
            if iso_match:
                return f"{iso_match.group(1)}.{iso_match.group(2)}.{iso_match.group(3)}"

            # Map both full and abbreviated month names
            month_map = {
                "Jan": "01",
                "January": "01",
                "Feb": "02",
                "February": "02",
                "Mar": "03",
                "March": "03",
                "Apr": "04",
                "April": "04",
                "May": "05",
                "Jun": "06",
                "June": "06",
                "Jul": "07",
                "July": "07",
                "Aug": "08",
                "August": "08",
                "Sep": "09",
                "Sept": "09",
                "September": "09",
                "Oct": "10",
                "October": "10",
                "Nov": "11",
                "November": "11",
                "Dec": "12",
                "December": "12",
            }

            # Match "Oct. 19, 1976" or "July 3, 1990" formats
            match = re.match(r"([A-Z][a-z]+)\.?\s+(\d{1,2})\s*,\s+(\d{4})", date_str)
            if match:
                month = month_map.get(match.group(1), "??")
                day = match.group(2).zfill(2)
                year = match.group(3)
                return f"{year}.{month}.{day}"
            return "          "  # 10 chars placeholder

        def format_source_law(citation) -> str:
            """Format a source law in changelog style.

            Format: # {date}  {relationship} {law_id} {path} {title}
            Uses fixed-width columns for alignment.

            For Acts, the date column is omitted since date is part of the
            identifier (e.g., "Act of Aug. 14, 1935").
            """
            relationship = (
                citation.relationship.value
            )  # Framework, Enactment, Amendment
            law_id = citation.law_id  # Works for both PL and Act
            path = citation.path_display
            title = citation.law_title or ""

            date_col = parse_date_to_ymd(citation.date)

            # Build the line with fixed-width columns
            # law_id column is 22 chars to fit "Act of Aug. 14, 1935"
            # Path column is 26 chars to accommodate "div. LL, tit. X, §5001(a)"
            line = (
                f"# {date_col}  "
                f"{relationship.ljust(10)} "
                f"{law_id.ljust(22)} "
                f"{path.ljust(26)} "
                f"{title}"
            )

            return line.rstrip()  # Remove trailing spaces if no title

        for i, citation in enumerate(result.section_notes.citations, start=1):
            formatted = format_source_law(citation)
            if show_section:
                print(f"L{i:3d} │ {formatted}")
            else:
                print(formatted)

    # Show notes if present
    if result.section_notes and result.section_notes.has_notes:
        # Section status (always show if applicable)
        if show_section is None:
            if result.section_notes.is_transferred:
                print()
                print(f"** TRANSFERRED to {result.section_notes.transferred_to}")
            if result.section_notes.is_omitted:
                print()
                print("** OMITTED")

        # Display notes by category using the new file-based structure
        historical = result.section_notes.historical_notes
        editorial = result.section_notes.editorial_notes
        statutory = result.section_notes.statutory_notes

        def format_note_lines(
            note,
            max_lines: int | None = 5,
            max_width: int | None = 70,
            with_line_numbers: bool = False,
            start_line: int = 1,
        ) -> tuple[list[str], int]:
            """Format note lines for display.

            Args:
                note: The note to format.
                max_lines: Maximum lines to show (None for unlimited).
                max_width: Maximum content width before truncation (None for unlimited).
                with_line_numbers: If True, prefix each line with line numbers.
                start_line: Starting line number (for continuous numbering across notes).

            Returns:
                Tuple of (formatted lines, next line number).
            """
            output = []
            line_num = start_line
            if note.lines:
                for i, line in enumerate(note.lines):
                    if max_lines is not None and i >= max_lines:
                        output.append(
                            f"        ... and {len(note.lines) - max_lines} more lines"
                        )
                        break
                    # Add blank line before headers (H1 at indent_level=1, H2 at indent_level=2)
                    # but not for the first line
                    if i > 0 and line.is_header and line.indent_level in (1, 2):
                        if with_line_numbers:
                            output.append(f"L{line_num:3d} │")
                            line_num += 1
                        else:
                            output.append("")
                    indent = "    " * line.indent_level
                    # Clean up content (remove extra whitespace/newlines)
                    content = " ".join(line.content.split())
                    if max_width is not None and len(content) > max_width:
                        content = content[: max_width - 3] + "..."
                    if with_line_numbers:
                        output.append(f"L{line_num:3d} │ {indent}{content}")
                    else:
                        output.append(f"    {indent}{content}")
                    line_num += 1
            return output, line_num

        # When showing a specific section, remove truncation and add line numbers
        note_max_lines = None if show_section else 5
        note_max_width = None if show_section else 70
        use_line_numbers = show_section is not None

        if (show_section is None or show_section == "historical") and historical:
            print()
            print("HISTORICAL_NOTES:")
            print("-" * 70)
            line_num = 1
            for i, note in enumerate(historical):
                # Add blank line before each note header after the first
                if i > 0:
                    if use_line_numbers:
                        print(f"L{line_num:3d} │")
                        line_num += 1
                    else:
                        print()
                if use_line_numbers:
                    print(f"L{line_num:3d} │ # {note.header}")
                    line_num += 1
                else:
                    print(f"# {note.header}")
                lines, line_num = format_note_lines(
                    note,
                    max_lines=note_max_lines,
                    max_width=note_max_width,
                    with_line_numbers=use_line_numbers,
                    start_line=line_num,
                )
                for line in lines:
                    print(line)
                if not use_line_numbers:
                    print()

        # Filter out "Amendments" from editorial since we have a dedicated section
        editorial_filtered = [n for n in editorial if n.header != "Amendments"]
        if (show_section is None or show_section == "editorial") and editorial_filtered:
            print()
            print("EDITORIAL_NOTES:")
            print("-" * 70)
            line_num = 1
            for i, note in enumerate(editorial_filtered):
                # Add blank line before each note header after the first
                if i > 0:
                    if use_line_numbers:
                        print(f"L{line_num:3d} │")
                        line_num += 1
                    else:
                        print()
                if use_line_numbers:
                    print(f"L{line_num:3d} │ # {note.header}")
                    line_num += 1
                else:
                    print(f"# {note.header}")
                lines, line_num = format_note_lines(
                    note,
                    max_lines=note_max_lines,
                    max_width=note_max_width,
                    with_line_numbers=use_line_numbers,
                    start_line=line_num,
                )
                for line in lines:
                    print(line)
                if not use_line_numbers:
                    print()

        if (show_section is None or show_section == "statutory") and statutory:
            print()
            print("STATUTORY_NOTES:")
            print("-" * 70)
            line_num = 1
            for i, note in enumerate(statutory):
                # Add blank line before each note header after the first
                if i > 0:
                    if use_line_numbers:
                        print(f"L{line_num:3d} │")
                        line_num += 1
                    else:
                        print()
                if use_line_numbers:
                    print(f"L{line_num:3d} │ # {note.header}")
                    line_num += 1
                else:
                    print(f"# {note.header}")
                lines, line_num = format_note_lines(
                    note,
                    max_lines=note_max_lines,
                    max_width=note_max_width,
                    with_line_numbers=use_line_numbers,
                    start_line=line_num,
                )
                for line in lines:
                    print(line)
                if not use_line_numbers:
                    print()

        # Structured amendments display (CHANGELOG style)
        if (
            show_section is None or show_section == "amendments"
        ) and result.section_notes.has_amendments:
            print()
            print("AMENDMENTS:")
            print("-" * 70)
            # Group by year
            amendments_by_year: dict[int, list] = {}
            for amend in result.section_notes.amendments:
                if amend.year not in amendments_by_year:
                    amendments_by_year[amend.year] = []
                amendments_by_year[amend.year].append(amend)

            # Display in reverse chronological order
            line_num = 1
            for year in sorted(amendments_by_year.keys(), reverse=True):
                if use_line_numbers:
                    print(f"L{line_num:3d} │ # {year}")
                    line_num += 1
                else:
                    print(f"# {year}")
                for amend in amendments_by_year[year]:
                    desc = " ".join(amend.description.split())
                    # Truncate description only if not showing full section
                    if show_section is None and len(desc) > 60:
                        desc = desc[:57] + "..."
                    if use_line_numbers:
                        print(
                            f"L{line_num:3d} │     {amend.public_law_id.ljust(12)} {desc}"
                        )
                        line_num += 1
                    else:
                        print(f"    {amend.public_law_id.ljust(12)} {desc}")
                if not use_line_numbers:
                    print()

        if show_section is None:
            print("-" * 70)

    return 0


# =============================================================================
# Legal Parser functions (Task 1.11)
# =============================================================================


def _extract_short_title(law_text: str) -> str | None:
    """Extract the short title from law text.

    Looks for the common pattern: "may be cited as the '<short title>'"
    in both plain text and XML (where quotes may be inside <quotedText> tags).
    """
    import re

    # Plain text: "may be cited as the 'Foo Bar Act of 2023'"
    m = re.search(
        r"""may be cited as (?:the\s+)?["\u2018\u201c'`]+([^"'\u2019\u201d`]+)""",
        law_text,
    )
    if m:
        return m.group(1).strip().rstrip(".")

    # XML: may be cited as ... <quotedText>Foo Bar Act</quotedText>
    m = re.search(
        r"may be cited as.*?<quotedText[^>]*>(.*?)</quotedText>",
        law_text,
        re.DOTALL,
    )
    if m:
        # Strip any nested XML tags from inside the quotedText
        return re.sub(r"<[^>]+>", "", m.group(1)).strip().rstrip(".")

    return None


async def parse_law_command(
    congress: int,
    law_number: int,
    mode: str = "regex",
    default_title: int | None = None,
    min_confidence: float = 0.0,
    dry_run: bool = False,
) -> int:
    """Parse a Public Law for amendments.

    Args:
        congress: Congress number.
        law_number: Law number.
        mode: Parsing mode (regex, llm, human-plus-llm).
        default_title: Default US Code title.
        min_confidence: Minimum confidence threshold.
        dry_run: If True, parse without saving.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from app.models.enums import ParsingMode
    from pipeline.govinfo.client import GovInfoClient
    from pipeline.legal_parser.parsing_modes import RegExParsingSession

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

    from pipeline.olrc.title_lookup import lookup_public_law_title

    # Look up short title: GovInfo API > text extraction > DB field
    title_info = await lookup_public_law_title(congress, law_number)
    short_title = (
        title_info.short_title if title_info and title_info.short_title else None
    )
    if not short_title:
        short_title = _extract_short_title(law_text)

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

        # Use DB short_title if available, else use extracted
        if law.short_title:
            short_title = law.short_title

        # --- METADATA section ---
        print()
        print("=" * 72)
        print("METADATA")
        print("=" * 72)
        print(f"  Law:            PL {congress}-{law_number}")
        if short_title:
            print(f"  Short title:    {short_title}")
        if title_info and title_info.short_title_aliases:
            for alias in title_info.short_title_aliases:
                print(f"                  aka {alias}")
        official = law.official_title or law_info.title
        if official:
            if len(official) > 100:
                official = official[:97] + "..."
            print(f"  Official title: {official}")
        if law.enacted_date:
            print(f"  Enacted:        {law.enacted_date}")
        if law_info.bill_id:
            print(f"  Bill:           {law_info.bill_id}")
        if law_info.committees:
            names = [
                c.get("committeeName", "")
                for c in law_info.committees
                if c.get("committeeName")
            ]
            if names:
                print(f"  Committees:     {names[0]}")
                for name in names[1:]:
                    print(f"                  {name}")
        if default_title:
            print(f"  Default title:  {default_title}")
        print(f"  Parse mode:     {parsing_mode.value}")

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

        # --- RESULTS summary ---
        status_label = (
            "completed" if result.status.value == "Completed" else result.status.value
        )
        print()
        print("=" * 72)
        print("RESULTS")
        print("=" * 72)
        print(f"  Status:         {status_label}")
        print(f"  Amendments:     {len(result.amendments)}")
        print(
            f"  Coverage:       {result.coverage_report.coverage_percentage:.1f}% "
            f"({result.coverage_report.claimed_length:,} / "
            f"{result.coverage_report.total_length:,} chars)"
        )

        if result.amendments:
            stats = parser_session.parser.get_statistics(result.amendments)
            print(f"  Avg confidence: {stats['avg_confidence']:.0%}")
            if stats.get("by_change_type"):
                print(f"  By type:        {stats['by_change_type']}")

        # --- AMENDMENTS detail ---
        if result.amendments:
            print()
            print("=" * 72)
            print("AMENDMENTS")
            print("=" * 72)
            for i, a in enumerate(result.amendments, 1):
                section_str = str(a.section_ref) if a.section_ref else "??"
                review_flag = " [REVIEW]" if a.needs_review else ""
                source = a.metadata.get("source", "regex")
                print()
                print(f"  #{i}  {a.change_type.value:<10}  {section_str}")
                print(f"      Pattern:    {a.pattern_name} ({source})")
                print(f"      Confidence: {a.confidence:.0%}{review_flag}")
                if a.old_text:
                    old_preview = a.old_text[:120]
                    if len(a.old_text) > 120:
                        old_preview += "..."
                    print(f'      Old text:   "{old_preview}"')
                if a.new_text:
                    new_preview = a.new_text[:120]
                    if len(a.new_text) > 120:
                        new_preview += "..."
                    print(f'      New text:   "{new_preview}"')
                if not a.old_text and not a.new_text:
                    # Show a snippet of the full match for context
                    snippet = a.full_match[:140]
                    if len(a.full_match) > 140:
                        snippet += "..."
                    print(f"      Context:    {snippet}")
            print()
            print("-" * 72)

        if result.escalation_recommended:
            print(f"\n  ESCALATION RECOMMENDED: {result.escalation_reason}")

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


# =============================================================================
# Law Change Pipeline functions (Task 1.12-1.13)
# =============================================================================


async def initial_commit_command(
    release_point: str,
    titles: list[int] | None = None,
    download_dir: Path = Path("data/olrc"),
) -> int:
    """Create initial commit from an OLRC release point.

    Args:
        release_point: Release point identifier (e.g., "113-21").
        titles: Title numbers to process (default: Phase 1 titles).
        download_dir: Directory for OLRC XML files.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.olrc.initial_commit import InitialCommitService

    async with async_session_maker() as session:
        service = InitialCommitService(session, download_dir=str(download_dir))
        try:
            rp = await service.create_initial_commit(
                release_point=release_point,
                titles=titles,
            )
            logger.info(
                f"Initial commit created from {rp.full_identifier} "
                f"(titles: {rp.titles_updated})"
            )
            return 0
        except Exception as e:
            logger.error(f"Failed to create initial commit: {e}")
            return 1


async def process_law_command(
    congress: int,
    law_number: int,
    default_title: int | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Process a Public Law to generate LawChange records.

    Args:
        congress: Congress number.
        law_number: Law number.
        default_title: Default US Code title.
        dry_run: If True, don't persist changes.
        verbose: If True, show detailed progress.

    Returns:
        0 on success, 1 on failure.
    """
    from app.models.base import async_session_maker
    from pipeline.legal_parser.law_change_service import LawChangeService

    async with async_session_maker() as session:
        service = LawChangeService(session)
        result = await service.process_law(
            congress=congress,
            law_number=law_number,
            default_title=default_title,
            dry_run=dry_run,
            verbose=verbose,
        )

        print(f"\nPL {congress}-{law_number} Processing Results:")
        print(f"  Amendments found: {len(result.amendments)}")
        print(f"  Diffs generated: {len(result.diffs)}")
        print(f"  LawChange records: {len(result.changes)}")

        if result.report:
            report = result.report
            print("\n  Diff Report:")
            print(f"    Unresolved: {report.unresolved}")
            print(f"    Skipped: {report.diffs_skipped}")
            print(f"    Validation failures: {report.validation_failures}")
            if report.by_type:
                print(f"    By type: {report.by_type}")

        if result.errors:
            print("\n  Errors:")
            for error in result.errors:
                print(f"    - {error}")
            return 1

        if dry_run:
            print("\n  [DRY RUN - changes not persisted]")

        return 0


async def validate_release_point_command(
    release_point: str,
    titles: list[int] | None = None,
    download_dir: Path = Path("data/olrc"),
    verbose: bool = False,
) -> int:
    """Validate database state against an OLRC release point.

    Args:
        release_point: Release point identifier (e.g., "113-22").
        titles: Title numbers to validate (default: Phase 1 titles).
        download_dir: Directory for OLRC XML files.
        verbose: If True, show per-section results.

    Returns:
        0 on success/valid, 1 on failure/invalid.
    """
    from app.models.base import async_session_maker
    from pipeline.legal_parser.release_point_validator import ReleasePointValidator

    titles = titles or PHASE_1_TITLES

    async with async_session_maker() as session:
        validator = ReleasePointValidator(session, download_dir=download_dir)
        report = await validator.validate_against_release_point(
            release_point=release_point,
            titles=titles,
            verbose=verbose,
        )

        print(f"\nValidation Report: {release_point}")
        print(f"  Titles checked: {report.titles_checked}")
        print(f"  Total sections: {report.total_sections}")
        print(f"  Matches: {report.matches} ({report.match_rate:.1%})")
        print(f"  Mismatches: {report.mismatches}")
        print(f"  Only in DB: {report.only_in_db}")
        print(f"  Only in RP: {report.only_in_rp}")

        if report.comparisons:
            print("\n  Mismatched sections (first 10):")
            for comp in report.comparisons[:10]:
                print(
                    f"    {comp.title_number} USC {comp.section_number}: "
                    f"{comp.diff_summary}"
                )

        if report.errors:
            print("\n  Errors:")
            for error in report.errors:
                print(f"    - {error}")

        print(f"\n  Valid: {'YES' if report.is_valid else 'NO'}")

        return 0 if report.is_valid else 1


async def cross_ref_law_command(
    congress: int,
    law_number: int,
    verbose: bool = False,
) -> int:
    """Cross-reference a law's changes against OLRC amendment notes.

    Args:
        congress: Congress number.
        law_number: Law number.
        verbose: If True, show detailed results.

    Returns:
        0 on success, 1 on failure.
    """
    from sqlalchemy import select

    from app.models.base import async_session_maker
    from app.models.public_law import LawChange, PublicLaw
    from pipeline.legal_parser.release_point_validator import AmendmentCrossReferencer

    async with async_session_maker() as session:
        # Get law
        result = await session.execute(
            select(PublicLaw).where(
                PublicLaw.congress == congress,
                PublicLaw.law_number == str(law_number),
            )
        )
        law = result.scalar_one_or_none()
        if not law:
            logger.error(f"PL {congress}-{law_number} not in database")
            return 1

        # Get generated changes
        changes_result = await session.execute(
            select(LawChange).where(LawChange.law_id == law.law_id)
        )
        changes = changes_result.scalars().all()

        if not changes:
            print(f"No LawChange records for PL {congress}-{law_number}")
            print("Run 'process-law' first to generate changes.")
            return 1

        cross_ref = AmendmentCrossReferencer(session)
        xref = await cross_ref.cross_reference(
            congress=congress,
            law_number=law_number,
            generated_changes=changes,
        )

        print(f"\nCross-Reference: PL {congress}-{law_number}")
        print(f"  Sections in OLRC notes: {len(xref.sections_in_notes)}")
        print(f"  Sections in our changes: {len(xref.sections_in_changes)}")
        print(f"  Matched: {len(xref.matched)}")
        print(f"  Only in notes (parser missed): {len(xref.only_in_notes)}")
        print(f"  Only in changes (possible FP): {len(xref.only_in_changes)}")
        print(f"  Precision: {xref.precision:.1%}")
        print(f"  Recall: {xref.recall:.1%}")

        if verbose and xref.only_in_notes:
            print("\n  Sections in notes but NOT in changes:")
            for title, section in xref.only_in_notes:
                print(f"    {title} USC {section}")

        if verbose and xref.only_in_changes:
            print("\n  Sections in changes but NOT in notes:")
            for title, section in xref.only_in_changes:
                print(f"    {title} USC {section}")

        return 0


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

    # Ingest-title command
    ingest_title_parser = subparsers.add_parser(
        "ingest-title", help="Ingest a US Code title into the database"
    )
    ingest_title_parser.add_argument(
        "title",
        type=int,
        help="Title number to ingest",
    )
    ingest_title_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="OLRC XML directory (default: data/olrc)",
    )
    ingest_title_parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download XML even if file exists",
    )
    ingest_title_parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Re-parse and update existing records",
    )

    # Ingest-phase1 command
    ingest_phase1_parser = subparsers.add_parser(
        "ingest-phase1", help="Ingest all Phase 1 US Code titles into the database"
    )
    ingest_phase1_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="OLRC XML directory (default: data/olrc)",
    )
    ingest_phase1_parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download XML even if files exist",
    )
    ingest_phase1_parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Re-parse and update existing records",
    )

    # seed-laws command
    subparsers.add_parser(
        "seed-laws",
        help="Ingest curated seed laws for local development and parse-law testing",
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
    normalize_parser.add_argument(
        "--show",
        type=str,
        choices=[
            "provisions",
            "p",
            "source-laws",
            "s",
            "historical",
            "h",
            "editorial",
            "e",
            "statutory",
            "st",
            "amendments",
            "a",
        ],
        help="Show only one section with full content (no truncation)",
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

    # =========================================================================
    # Law Change Pipeline commands (Task 1.12-1.13)
    # =========================================================================

    # initial-commit command
    initial_commit_parser = subparsers.add_parser(
        "initial-commit",
        help="Create initial commit from an OLRC release point",
    )
    initial_commit_parser.add_argument(
        "release_point",
        type=str,
        help="Release point identifier (e.g., '113-21')",
    )
    initial_commit_parser.add_argument(
        "--titles",
        type=int,
        nargs="+",
        help="Title numbers to process (default: Phase 1 titles)",
    )
    initial_commit_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="OLRC XML directory (default: data/olrc)",
    )

    # process-law command
    process_law_parser = subparsers.add_parser(
        "process-law",
        help="Process a Public Law to generate LawChange records",
    )
    process_law_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (e.g., 113)",
    )
    process_law_parser.add_argument(
        "law_number",
        type=int,
        help="Law number (e.g., 22 for PL 113-22)",
    )
    process_law_parser.add_argument(
        "--default-title",
        type=int,
        help="Default US Code title when not specified in text",
    )
    process_law_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate diffs without persisting to database",
    )
    process_law_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )

    # validate-release-point command
    validate_rp_parser = subparsers.add_parser(
        "validate-release-point",
        help="Validate database state against an OLRC release point",
    )
    validate_rp_parser.add_argument(
        "release_point",
        type=str,
        help="Release point identifier (e.g., '113-22')",
    )
    validate_rp_parser.add_argument(
        "--titles",
        type=int,
        nargs="+",
        help="Title numbers to validate (default: Phase 1 titles)",
    )
    validate_rp_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/olrc"),
        help="OLRC XML directory (default: data/olrc)",
    )
    validate_rp_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-section comparison results",
    )

    # cross-ref-law command
    cross_ref_parser = subparsers.add_parser(
        "cross-ref-law",
        help="Cross-reference a law's changes against OLRC amendment notes",
    )
    cross_ref_parser.add_argument(
        "congress",
        type=int,
        help="Congress number (e.g., 113)",
    )
    cross_ref_parser.add_argument(
        "law_number",
        type=int,
        help="Law number (e.g., 22)",
    )
    cross_ref_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed section-level results",
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

    elif args.command == "ingest-title":
        return asyncio.run(
            ingest_title(
                title_number=args.title,
                download_dir=args.dir,
                force_download=args.force_download,
                force_parse=args.force_parse,
            )
        )

    elif args.command == "ingest-phase1":
        return asyncio.run(
            ingest_phase1(
                download_dir=args.dir,
                force_download=args.force_download,
                force_parse=args.force_parse,
            )
        )

    elif args.command == "seed-laws":
        return asyncio.run(seed_laws_command())

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
            show_section=args.show,
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

    # =========================================================================
    # Law Change Pipeline command handlers (Task 1.12-1.13)
    # =========================================================================

    elif args.command == "initial-commit":
        return asyncio.run(
            initial_commit_command(
                release_point=args.release_point,
                titles=args.titles,
                download_dir=args.dir,
            )
        )

    elif args.command == "process-law":
        return asyncio.run(
            process_law_command(
                congress=args.congress,
                law_number=args.law_number,
                default_title=args.default_title,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        )

    elif args.command == "validate-release-point":
        return asyncio.run(
            validate_release_point_command(
                release_point=args.release_point,
                titles=args.titles,
                download_dir=args.dir,
                verbose=args.verbose,
            )
        )

    elif args.command == "cross-ref-law":
        return asyncio.run(
            cross_ref_law_command(
                congress=args.congress,
                law_number=args.law_number,
                verbose=args.verbose,
            )
        )

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
