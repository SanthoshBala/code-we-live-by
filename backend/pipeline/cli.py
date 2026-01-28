"""CLI for running data ingestion pipelines."""

import argparse
import asyncio
import logging
import sys
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

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
