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

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
