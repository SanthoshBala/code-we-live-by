"""GovInfo API client for fetching Public Laws and related documents."""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

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
            title=data.get("title", "").rstrip("."),
            congress=congress,
            law_number=law_number,
            law_type=law_type,
        )


@dataclass
class PLAWPackageDetail:
    """Detailed info about a Public Law from the packages endpoint."""

    package_id: str
    title: str
    short_title: str | None
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
    # Committees
    committees: list[dict[str, str]]

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

        # Strip trailing period from official title (GovInfo convention)
        raw_title = data.get("title", "")
        title = raw_title.rstrip(".")

        # Extract short title from shortTitle array
        short_title_list = data.get("shortTitle", [])
        short_title: str | None = None
        if short_title_list and isinstance(short_title_list, list):
            first = short_title_list[0]
            if isinstance(first, dict):
                short_title = first.get("title")
            elif isinstance(first, str):
                short_title = first
        if short_title:
            short_title = short_title.rstrip(".")

        return cls(
            package_id=package_id,
            title=title,
            short_title=short_title,
            congress=congress,
            law_number=law_number,
            law_type=law_type,
            date_issued=date_issued,
            government_author=data.get("governmentAuthor1"),
            publisher=data.get("publisher"),
            collection_code=data.get("collectionCode", "PLAW"),
            doc_class=data.get("docClass"),
            pdf_url=download.get("pdfLink"),
            xml_url=download.get("xmlLink") or download.get("uslmLink"),
            htm_url=download.get("htmLink") or download.get("txtLink"),
            bill_id=bill_id,
            statutes_at_large_citation=data.get("suDocClassNumber"),
            committees=data.get("committees", []),
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
        cache_dir: Path | str | None = "data/govinfo",
    ):
        """Initialize the GovInfo client.

        Args:
            api_key: GovInfo API key. If not provided, reads from app settings
                (which loads from GOVINFO_API_KEY environment variable or .env).
            timeout: HTTP request timeout in seconds.
            cache_dir: Directory for caching downloaded law texts. Set to None
                to disable caching. Defaults to "data/govinfo".

        Raises:
            ValueError: If no API key is provided or found in settings.
        """
        if api_key:
            self.api_key = api_key
        else:
            # Import here to avoid circular imports
            from app.config import settings

            self.api_key = settings.govinfo_api_key  # type: ignore[assignment]
        if not self.api_key:
            raise ValueError(
                "GovInfo API key required. Set GOVINFO_API_KEY environment "
                "variable or pass api_key parameter. "
                "Get a free key at https://api.data.gov/signup/"
            )
        self.timeout = timeout
        self.base_url = GOVINFO_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds
        self.cache_dir = Path(cache_dir) if cache_dir else None

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry logic for 5xx errors.

        Args:
            client: httpx AsyncClient instance.
            method: HTTP method (GET, POST, etc.).
            url: Request URL.
            **kwargs: Additional arguments passed to client.request().

        Returns:
            httpx.Response on success.

        Raises:
            httpx.HTTPStatusError: After all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2**attempt)  # Exponential backoff
                        logger.warning(
                            f"Server error {e.response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Request error: {e}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected error in retry logic")

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
                response = await self._request_with_retry(
                    client, "GET", url, params=params
                )
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

                # Extract offset mark from next page URL.
                # The value is already URL-encoded in the URL; decode it
                # so httpx doesn't double-encode when sending the request.
                if "offsetMark=" in next_offset:
                    raw = next_offset.split("offsetMark=")[1].split("&")[0]
                    offset_mark = unquote(raw)
                else:
                    break

        logger.info(f"Fetched {len(results)} public laws")
        return results

    async def get_public_law_detail(
        self, package_id: str, force: bool = False
    ) -> PLAWPackageDetail:
        """Fetch detailed information about a specific Public Law.

        Results are cached as JSON in {cache_dir}/plaw/{package_id}.json.

        Args:
            package_id: The GovInfo package ID (e.g., "PLAW-119publ60").
            force: If True, re-fetch even if cached.

        Returns:
            PLAWPackageDetail with full metadata and download URLs.
        """
        # Check cache first
        cache_file = None
        if self.cache_dir:
            cache_file = self.cache_dir / "plaw" / f"{package_id}.json"
            if cache_file.exists() and not force:
                logger.info(f"Using cached summary for {package_id}: {cache_file}")
                data = json.loads(cache_file.read_text())
                return PLAWPackageDetail.from_api_response(data)

        url = f"{self.base_url}/packages/{package_id}/summary"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {"api_key": self.api_key}
            logger.info(f"Fetching package detail for {package_id}")
            response = await self._request_with_retry(client, "GET", url, params=params)
            data = response.json()

        # Write to cache
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(data))
            logger.info(f"Cached summary to {cache_file}")

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
        # The collections API date range filters by lastModified on
        # govinfo.gov (not enacted date). Records are re-indexed
        # periodically, so we use a start date near the Congress start
        # with no end date (open-ended = "modified since X").
        # The congress parameter + client-side filter handle the rest.
        start_year = 1789 + (congress - 1) * 2  # Approximate start year
        start_date = datetime(start_year, 1, 1)

        all_laws = await self.get_public_laws(
            start_date=start_date,
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
            logger.info(f"Downloading XML for {detail.package_id}")
            params = {"api_key": self.api_key}
            response = await self._request_with_retry(
                client, "GET", detail.xml_url, params=params
            )
            return response.text

    def build_package_id(
        self, congress: int, law_number: int, law_type: str = "public"
    ) -> str:
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

    async def get_public_law(
        self,
        congress: int,
        law_number: int,
        law_type: str = "public",
    ) -> PLAWPackageDetail | None:
        """Fetch a specific Public Law by congress and law number.

        Args:
            congress: Congress number (e.g., 118).
            law_number: Law number (e.g., 60 for PL 118-60).
            law_type: "public" or "private".

        Returns:
            PLAWPackageDetail or None if not found.
        """
        package_id = self.build_package_id(congress, law_number, law_type)
        try:
            return await self.get_public_law_detail(package_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Law not found: PL {congress}-{law_number}")
                return None
            raise

    def _cache_path(
        self, congress: int, law_number: int, law_type: str, fmt: str
    ) -> Path | None:
        """Build cache file path for a law text, or None if caching disabled."""
        if not self.cache_dir:
            return None
        package_id = self.build_package_id(congress, law_number, law_type)
        return self.cache_dir / "plaw" / f"{package_id}.{fmt}"

    async def get_law_text(
        self,
        congress: int,
        law_number: int,
        law_type: str = "public",
        format: str = "xml",
        force: bool = False,
    ) -> str | None:
        """Fetch the text content of a Public Law.

        Downloaded texts are cached locally to avoid repeated API calls.
        Cached files are stored in {cache_dir}/plaw/{package_id}.{format}.

        Args:
            congress: Congress number.
            law_number: Law number.
            law_type: "public" or "private".
            format: "xml" for structured XML (default), "htm" for HTML text.
            force: If True, re-download even if cached file exists.

        Returns:
            Law text as string, or None if not available.
        """
        # Check cache first
        cache_file = self._cache_path(congress, law_number, law_type, format)
        if cache_file and cache_file.exists() and not force:
            logger.info(
                f"Using cached {format.upper()} for PL {congress}-{law_number}: "
                f"{cache_file}"
            )
            return cache_file.read_text()

        detail = await self.get_public_law(congress, law_number, law_type)
        if not detail:
            return None

        url = detail.htm_url if format == "htm" else detail.xml_url
        if not url:
            logger.warning(f"No {format.upper()} URL for PL {congress}-{law_number}")
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"Downloading {format.upper()} for PL {congress}-{law_number}")
            try:
                params = {"api_key": self.api_key}
                response = await self._request_with_retry(
                    client, "GET", url, params=params
                )
                text = response.text

                # Write to cache
                if cache_file:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(text)
                    logger.info(f"Cached {format.upper()} to {cache_file}")

                return text
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to download law text: {e}")
                return None
