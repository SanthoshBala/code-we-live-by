"""GovInfo API client for fetching Public Laws and related documents."""

import contextlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# GovInfo API Configuration
# =============================================================================
# Primary source: https://api.govinfo.gov/docs/
# Developer hub: https://www.govinfo.gov/developers
# GitHub: https://github.com/usgpo/api
#
# API Key: Required. Get a free key at https://api.data.gov/signup/
# Set via environment variable GOVINFO_API_KEY or pass to client.
#
# Rate limits: Not explicitly documented, but be respectful. The API
# supports pagination with offsetMark for large result sets.
# =============================================================================

GOVINFO_BASE_URL = "https://api.govinfo.gov"

# Collection codes
# Source: https://api.govinfo.gov/docs/ (see collections endpoint)
COLLECTION_PLAW = "PLAW"  # Public and Private Laws
COLLECTION_BILLS = "BILLS"  # Congressional Bills
COLLECTION_BILLSTATUS = "BILLSTATUS"  # Bill Status
COLLECTION_USCODE = "USCODE"  # US Code

# HARDCODED ASSUMPTION: Default page size for API requests
# Source: https://github.com/usgpo/api (see collections endpoint docs)
# Maximum allowed is 1000. Using 100 for reasonable response sizes.
DEFAULT_PAGE_SIZE = 100


@dataclass
class PLAWPackageInfo:
    """Basic info about a Public Law package from the collections endpoint."""

    package_id: str
    last_modified: datetime
    title: str
    congress: int
    law_number: int
    law_type: str  # "public" or "private"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PLAWPackageInfo":
        """Create from GovInfo API response item."""
        package_id = data.get("packageId", "")

        # Parse congress and law number from packageId
        # Format: PLAW-119publ60 or PLAW-119pvt5
        congress = 0
        law_number = 0
        law_type = "public"

        if package_id.startswith("PLAW-"):
            parts = package_id[5:]  # Remove "PLAW-"
            if "publ" in parts:
                congress_str, num_str = parts.split("publ")
                law_type = "public"
            elif "pvt" in parts:
                congress_str, num_str = parts.split("pvt")
                law_type = "private"
            else:
                congress_str, num_str = "", ""

            try:
                congress = int(congress_str)
                law_number = int(num_str)
            except ValueError:
                pass

        # Parse last modified date
        last_modified_str = data.get("lastModified", "")
        try:
            last_modified = datetime.fromisoformat(
                last_modified_str.replace("Z", "+00:00")
            )
        except ValueError:
            last_modified = datetime.now()

        return cls(
            package_id=package_id,
            last_modified=last_modified,
            title=data.get("title", ""),
            congress=congress,
            law_number=law_number,
            law_type=law_type,
        )


@dataclass
class PLAWPackageDetail:
    """Detailed info about a Public Law from the packages endpoint."""

    package_id: str
    title: str
    congress: int
    law_number: int
    law_type: str
    date_issued: datetime | None
    government_author: str | None
    publisher: str | None
    collection_code: str
    doc_class: str | None
    # Download URLs
    pdf_url: str | None
    xml_url: str | None
    htm_url: str | None
    # Related documents
    bill_id: str | None
    statutes_at_large_citation: str | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PLAWPackageDetail":
        """Create from GovInfo API package summary response."""
        package_id = data.get("packageId", "")

        # Parse congress and law number
        congress = 0
        law_number = 0
        law_type = "public"

        if package_id.startswith("PLAW-"):
            parts = package_id[5:]
            if "publ" in parts:
                congress_str, num_str = parts.split("publ")
                law_type = "public"
            elif "pvt" in parts:
                congress_str, num_str = parts.split("pvt")
                law_type = "private"
            else:
                congress_str, num_str = "", ""

            try:
                congress = int(congress_str)
                law_number = int(num_str)
            except ValueError:
                pass

        # Parse date issued
        date_issued = None
        date_str = data.get("dateIssued", "")
        if date_str:
            with contextlib.suppress(ValueError):
                date_issued = datetime.fromisoformat(date_str)

        # Extract download URLs from the download dict
        download = data.get("download", {})

        # Extract related bill if available
        related = data.get("related", {})
        bill_id = None
        if "billId" in related:
            bill_id = related["billId"]

        return cls(
            package_id=package_id,
            title=data.get("title", ""),
            congress=congress,
            law_number=law_number,
            law_type=law_type,
            date_issued=date_issued,
            government_author=data.get("governmentAuthor1"),
            publisher=data.get("publisher"),
            collection_code=data.get("collectionCode", "PLAW"),
            doc_class=data.get("docClass"),
            pdf_url=download.get("pdfLink"),
            xml_url=download.get("xmlLink"),
            htm_url=download.get("htmLink"),
            bill_id=bill_id,
            statutes_at_large_citation=data.get("suDocClassNumber"),
        )


class GovInfoClient:
    """Client for the GovInfo API.

    Provides methods to fetch Public Laws and related documents from the
    Government Publishing Office's GovInfo service.

    API Documentation: https://api.govinfo.gov/docs/
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the GovInfo client.

        Args:
            api_key: GovInfo API key. If not provided, reads from
                GOVINFO_API_KEY environment variable.
            timeout: HTTP request timeout in seconds.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("GOVINFO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GovInfo API key required. Set GOVINFO_API_KEY environment "
                "variable or pass api_key parameter. "
                "Get a free key at https://api.data.gov/signup/"
            )
        self.timeout = timeout
        self.base_url = GOVINFO_BASE_URL

    async def get_public_laws(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
        congress: int | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[PLAWPackageInfo]:
        """Fetch list of Public Laws modified within a date range.

        Args:
            start_date: Start of date range (required).
            end_date: End of date range (optional, defaults to now).
            congress: Filter to specific Congress number (optional).
            page_size: Number of results per page (max 1000).

        Returns:
            List of PLAWPackageInfo objects.
        """
        results: list[PLAWPackageInfo] = []
        offset_mark = "*"

        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{self.base_url}/collections/{COLLECTION_PLAW}/{start_str}"

        if end_date:
            end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            url = f"{url}/{end_str}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                params = {
                    "api_key": self.api_key,
                    "offsetMark": offset_mark,
                    "pageSize": page_size,
                }
                if congress:
                    params["congress"] = congress

                logger.info(f"Fetching PLAW collection from {url}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Parse packages
                packages = data.get("packages", [])
                for pkg in packages:
                    info = PLAWPackageInfo.from_api_response(pkg)
                    # Filter by congress if specified
                    if congress is None or info.congress == congress:
                        results.append(info)

                # Check for more pages
                next_offset = data.get("nextPage")
                if not next_offset or not packages:
                    break

                # Extract offset mark from next page URL
                # nextPage format: "...&offsetMark=XXXXX&..."
                if "offsetMark=" in next_offset:
                    offset_mark = next_offset.split("offsetMark=")[1].split("&")[0]
                else:
                    break

        logger.info(f"Fetched {len(results)} public laws")
        return results

    async def get_public_law_detail(self, package_id: str) -> PLAWPackageDetail:
        """Fetch detailed information about a specific Public Law.

        Args:
            package_id: The GovInfo package ID (e.g., "PLAW-119publ60").

        Returns:
            PLAWPackageDetail with full metadata and download URLs.
        """
        url = f"{self.base_url}/packages/{package_id}/summary"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {"api_key": self.api_key}
            logger.info(f"Fetching package detail for {package_id}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        return PLAWPackageDetail.from_api_response(data)

    async def get_public_laws_for_congress(
        self,
        congress: int,
        law_type: str = "public",
    ) -> list[PLAWPackageInfo]:
        """Fetch all Public Laws for a specific Congress.

        Args:
            congress: Congress number (e.g., 119 for 119th Congress).
            law_type: "public" or "private" (default: "public").

        Returns:
            List of PLAWPackageInfo objects for that Congress.
        """
        # Use a wide date range to get all laws
        # Congress sessions span ~2 years; use a 3-year window to be safe
        start_year = 1789 + (congress - 1) * 2  # Approximate start year
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(start_year + 3, 12, 31)

        all_laws = await self.get_public_laws(
            start_date=start_date,
            end_date=end_date,
            congress=congress,
        )

        # Filter by law type
        return [law for law in all_laws if law.law_type == law_type]

    async def download_law_xml(self, detail: PLAWPackageDetail) -> str | None:
        """Download the XML content of a Public Law.

        Args:
            detail: PLAWPackageDetail with xml_url.

        Returns:
            XML content as string, or None if not available.
        """
        if not detail.xml_url:
            logger.warning(f"No XML URL for {detail.package_id}")
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # XML downloads don't need API key
            logger.info(f"Downloading XML for {detail.package_id}")
            response = await client.get(detail.xml_url)
            response.raise_for_status()
            return response.text

    def build_package_id(self, congress: int, law_number: int, law_type: str = "public") -> str:
        """Build a GovInfo package ID for a Public Law.

        Args:
            congress: Congress number.
            law_number: Law number within that Congress.
            law_type: "public" or "private".

        Returns:
            Package ID string (e.g., "PLAW-119publ60").
        """
        type_code = "publ" if law_type == "public" else "pvt"
        return f"PLAW-{congress}{type_code}{law_number}"
