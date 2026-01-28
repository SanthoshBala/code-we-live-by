"""Download US Code XML files from OLRC (Office of Law Revision Counsel)."""

import logging
import zipfile
from io import BytesIO
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# OLRC (Office of Law Revision Counsel) Configuration
# =============================================================================
# Primary source: https://uscode.house.gov/download/download.shtml
#
# The OLRC publishes the US Code as "release points" that are updated
# continuously as Congress enacts new legislation (typically 2-4 times per
# month during active legislative periods, more frequently in Dec/Jan).
#
# To check for updates:
#   1. Visit https://uscode.house.gov/download/download.shtml
#   2. Note the current release point shown at the top of the page
#   3. Update DEFAULT_RELEASE_POINT below if changed
#
# Prior release points: https://uscode.house.gov/download/priorreleasepoints.htm
# =============================================================================

OLRC_BASE_URL = "https://uscode.house.gov"
OLRC_DOWNLOAD_BASE = f"{OLRC_BASE_URL}/download"

# HARDCODED ASSUMPTION: Default release point for US Code downloads
# Source: https://uscode.house.gov/download/download.shtml
# Last verified: January 2026
# Update cadence: Check monthly, or when ingesting new data. The OLRC updates
#   release points 2-4 times per month as new public laws are codified.
# Format: "{congress}-{public_law}[not{excluded}]"
#   - "119-72not60" = through P.L. 119-72, except P.L. 119-60
#   - Exclusions occur when large/complex laws take longer to codify
#
# About the P.L. 119-60 exclusion:
#   P.L. 119-60 is the National Defense Authorization Act (NDAA) for FY2026,
#   signed December 18, 2025. The NDAA is one of the most complex pieces of
#   legislation passed each year—typically thousands of pages affecting multiple
#   titles (defense, energy, intelligence, personnel, etc.). It also includes
#   incorporated acts like the Intelligence Authorization Act. The OLRC needs
#   extra time to properly codify all provisions across affected titles.
#   See: https://www.congress.gov/bill/119th-congress/senate-bill/1071
DEFAULT_RELEASE_POINT = "119-72not60"

# HARDCODED ASSUMPTION: URL pattern for downloading individual title XML files
# Source: https://uscode.house.gov/download/download.shtml (inspect download links)
# Last verified: January 2026
# Update cadence: Unlikely to change; this is the OLRC's established URL structure.
#   If downloads fail, verify the pattern at the source URL above.
TITLE_XML_URL_PATTERN = (
    f"{OLRC_DOWNLOAD_BASE}/releasepoints/us/pl/{{congress}}/{{public_law}}/"
    "xml_usc{title_number:02d}@{congress}-{public_law}.zip"
)

# Phase 1 target titles (from Task 0.8)
PHASE_1_TITLES = [10, 17, 18, 20, 22, 26, 42, 50]


class OLRCDownloader:
    """Download US Code XML files from the OLRC website."""

    def __init__(
        self,
        download_dir: Path | str = "data/olrc",
        release_point: str = DEFAULT_RELEASE_POINT,
        timeout: float = 120.0,
    ):
        """Initialize the downloader.

        Args:
            download_dir: Directory to store downloaded files.
            release_point: OLRC release point (e.g., "119-72not60").
            timeout: HTTP request timeout in seconds.
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.release_point = release_point
        self.timeout = timeout

        # Parse release point into congress and public_law components
        # e.g., "119-72not60" -> congress="119", public_law="72not60"
        parts = release_point.split("-", 1)
        self.congress = parts[0]
        self.public_law = parts[1] if len(parts) > 1 else ""

    def get_title_url(self, title_number: int) -> str:
        """Get the download URL for a specific title.

        Args:
            title_number: The US Code title number (1-54).

        Returns:
            The download URL for the title's XML file.
        """
        return TITLE_XML_URL_PATTERN.format(
            congress=self.congress,
            public_law=self.public_law,
            title_number=title_number,
        )

    async def download_title(
        self, title_number: int, force: bool = False
    ) -> Path | None:
        """Download XML for a specific US Code title.

        Args:
            title_number: The US Code title number (1-54).
            force: If True, download even if file exists.

        Returns:
            Path to the extracted XML file, or None if download failed.
        """
        # Check if already downloaded
        xml_dir = self.download_dir / f"title{title_number}"
        if xml_dir.exists() and not force:
            xml_files = list(xml_dir.glob("*.xml"))
            if xml_files:
                logger.info(f"Title {title_number} already downloaded: {xml_files[0]}")
                return xml_files[0]

        url = self.get_title_url(title_number)
        logger.info(f"Downloading Title {title_number} from {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Extract ZIP file
                xml_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(BytesIO(response.content)) as zf:
                    zf.extractall(xml_dir)

                # Find the extracted XML file
                xml_files = list(xml_dir.glob("*.xml"))
                if xml_files:
                    logger.info(f"Title {title_number} downloaded: {xml_files[0]}")
                    return xml_files[0]
                else:
                    logger.error(
                        f"No XML file found in downloaded archive for Title {title_number}"
                    )
                    return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading Title {title_number}: {e}")
            return None
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file for Title {title_number}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Error downloading Title {title_number}: {e}")
            return None

    async def download_phase1_titles(
        self, force: bool = False
    ) -> dict[int, Path | None]:
        """Download all Phase 1 target titles.

        Args:
            force: If True, download even if files exist.

        Returns:
            Dictionary mapping title numbers to their XML file paths.
        """
        results = {}
        for title_number in PHASE_1_TITLES:
            path = await self.download_title(title_number, force=force)
            results[title_number] = path
        return results

    def get_downloaded_titles(self) -> list[int]:
        """Get list of title numbers that have been downloaded.

        Returns:
            List of title numbers with downloaded XML files.
        """
        titles = []
        for subdir in self.download_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith("title"):
                try:
                    title_num = int(subdir.name.replace("title", ""))
                    if list(subdir.glob("*.xml")):
                        titles.append(title_num)
                except ValueError:
                    continue
        return sorted(titles)

    def get_xml_path(self, title_number: int) -> Path | None:
        """Get the path to a downloaded title's XML file.

        Args:
            title_number: The US Code title number.

        Returns:
            Path to the XML file, or None if not downloaded.
        """
        xml_dir = self.download_dir / f"title{title_number}"
        if xml_dir.exists():
            xml_files = list(xml_dir.glob("*.xml"))
            if xml_files:
                return xml_files[0]
        return None
