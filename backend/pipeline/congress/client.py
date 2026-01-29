"""Congress.gov API client for fetching legislator and bill data."""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# Congress.gov API Configuration
# =============================================================================
# Primary documentation: https://api.congress.gov
# GitHub: https://github.com/LibraryOfCongress/api.congress.gov
#
# API Key: Required. Get a free key at https://api.congress.gov/sign-up/
# Set via environment variable CONGRESS_API_KEY or pass to client.
#
# Rate limits: 5,000 requests/hour (generous for batch ingestion)
# =============================================================================

CONGRESS_BASE_URL = "https://api.congress.gov/v3"

# HARDCODED ASSUMPTION: Default page size for API requests
# Source: https://api.congress.gov (maximum is 250, default is 20)
DEFAULT_PAGE_SIZE = 250


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int, returning None if not possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@dataclass
class MemberTerm:
    """A single term served by a member of Congress."""

    chamber: str  # "House of Representatives" or "Senate"
    congress: int | None
    member_type: str | None  # Representative, Senator, Delegate, etc.
    state: str | None
    district: int | None
    start_year: int | None
    end_year: int | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "MemberTerm":
        """Create from Congress.gov API response."""
        return cls(
            chamber=data.get("chamber", ""),
            congress=data.get("congress"),
            member_type=data.get("memberType"),
            state=data.get("stateCode"),
            district=data.get("district"),
            start_year=data.get("startYear"),
            end_year=data.get("endYear"),
        )


@dataclass
class MemberInfo:
    """Basic info about a member from the list endpoint."""

    bioguide_id: str
    name: str
    state: str | None
    district: int | None
    party_name: str | None
    terms: list[MemberTerm] = field(default_factory=list)
    depiction_url: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "MemberInfo":
        """Create from Congress.gov API response item."""
        # Parse terms
        terms_data = data.get("terms", {})
        terms_list = terms_data.get("item", []) if isinstance(terms_data, dict) else []
        terms = [MemberTerm.from_api_response(t) for t in terms_list]

        # Parse depiction (photo)
        depiction = data.get("depiction", {})
        depiction_url = depiction.get("imageUrl") if depiction else None

        return cls(
            bioguide_id=data.get("bioguideId", ""),
            name=data.get("name", ""),
            state=data.get("state"),
            district=data.get("district"),
            party_name=data.get("partyName"),
            terms=terms,
            depiction_url=depiction_url,
        )


@dataclass
class MemberDetail:
    """Detailed info about a member from the individual endpoint."""

    bioguide_id: str
    first_name: str
    middle_name: str | None
    last_name: str
    suffix: str | None
    direct_order_name: str  # e.g., "Sherrod Brown"
    inverted_order_name: str  # e.g., "Brown, Sherrod"
    honorific_name: str | None  # e.g., "Mr."
    party_name: str | None
    state: str | None
    district: int | None
    current_member: bool
    birth_year: int | None
    death_year: int | None
    official_website_url: str | None
    depiction_url: str | None
    depiction_attribution: str | None
    terms: list[MemberTerm] = field(default_factory=list)
    update_date: datetime | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "MemberDetail":
        """Create from Congress.gov API member detail response."""
        # Parse terms
        terms_data = data.get("terms", [])
        terms = [MemberTerm.from_api_response(t) for t in terms_data]

        # Parse depiction (photo)
        depiction = data.get("depiction", {})
        depiction_url = depiction.get("imageUrl") if depiction else None
        depiction_attribution = depiction.get("attribution") if depiction else None

        # Parse update date
        update_date = None
        update_str = data.get("updateDate", "")
        if update_str:
            with contextlib.suppress(ValueError):
                update_date = datetime.fromisoformat(update_str.replace("Z", "+00:00"))

        return cls(
            bioguide_id=data.get("bioguideId", ""),
            first_name=data.get("firstName", ""),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName", ""),
            suffix=data.get("suffixName"),
            direct_order_name=data.get("directOrderName", ""),
            inverted_order_name=data.get("invertedOrderName", ""),
            honorific_name=data.get("honorificName"),
            party_name=data.get("partyName"),
            state=data.get("state"),
            district=data.get("district"),
            current_member=data.get("currentMember", False),
            birth_year=_safe_int(data.get("birthYear")),
            death_year=_safe_int(data.get("deathYear")),
            official_website_url=data.get("officialWebsiteUrl"),
            depiction_url=depiction_url,
            depiction_attribution=depiction_attribution,
            terms=terms,
            update_date=update_date,
        )


@dataclass
class SponsorInfo:
    """Sponsor or cosponsor information from a bill."""

    bioguide_id: str
    full_name: str
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    party: str | None
    state: str | None
    district: int | None
    is_original_cosponsor: bool | None = None
    sponsorship_date: str | None = None
    sponsorship_withdrawn_date: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "SponsorInfo":
        """Create from Congress.gov API sponsor/cosponsor response."""
        return cls(
            bioguide_id=data.get("bioguideId", ""),
            full_name=data.get("fullName", ""),
            first_name=data.get("firstName"),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName"),
            party=data.get("party"),
            state=data.get("state"),
            district=data.get("district"),
            is_original_cosponsor=data.get("isOriginalCosponsor"),
            sponsorship_date=data.get("sponsorshipDate"),
            sponsorship_withdrawn_date=data.get("sponsorshipWithdrawnDate"),
        )


class CongressClient:
    """Client for the Congress.gov API.

    Provides methods to fetch legislator data, bill metadata, and
    sponsor/cosponsor information from the Library of Congress API.

    API Documentation: https://api.congress.gov
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the Congress.gov client.

        Args:
            api_key: Congress.gov API key. If not provided, reads from app settings
                (which loads from CONGRESS_API_KEY environment variable or .env).
            timeout: HTTP request timeout in seconds.

        Raises:
            ValueError: If no API key is provided or found in settings.
        """
        if api_key:
            self.api_key = api_key
        else:
            from app.config import settings

            self.api_key = settings.congress_api_key
        if not self.api_key:
            raise ValueError(
                "Congress.gov API key required. Set CONGRESS_API_KEY environment "
                "variable or pass api_key parameter. "
                "Get a free key at https://api.congress.gov/sign-up/"
            )
        self.timeout = timeout
        self.base_url = CONGRESS_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds

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

        if last_error:
            raise last_error
        raise RuntimeError("Unexpected error in retry logic")

    async def get_members(
        self,
        current_member: bool | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        limit: int | None = None,
    ) -> list[MemberInfo]:
        """Fetch list of all members of Congress.

        Args:
            current_member: If True, only current members. If False, all members.
            page_size: Number of results per page (max 250).
            limit: Maximum total results to return (optional).

        Returns:
            List of MemberInfo objects.
        """
        results: list[MemberInfo] = []
        offset = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                params: dict[str, Any] = {
                    "api_key": self.api_key,
                    "format": "json",
                    "limit": page_size,
                    "offset": offset,
                }
                if current_member is not None:
                    params["currentMember"] = str(current_member).lower()

                url = f"{self.base_url}/member"
                logger.info(f"Fetching members from {url} (offset={offset})")
                response = await self._request_with_retry(
                    client, "GET", url, params=params
                )
                data = response.json()

                # Parse members
                members = data.get("members", [])
                for member_data in members:
                    info = MemberInfo.from_api_response(member_data)
                    results.append(info)

                # Check if we've hit the limit
                if limit and len(results) >= limit:
                    results = results[:limit]
                    break

                # Check for more pages
                pagination = data.get("pagination", {})
                count = pagination.get("count", 0)
                if offset + page_size >= count or not members:
                    break

                offset += page_size

        logger.info(f"Fetched {len(results)} members")
        return results

    async def get_members_by_congress(
        self,
        congress: int,
        current_member: bool = False,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[MemberInfo]:
        """Fetch all members who served in a specific Congress.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress).
            current_member: If False (default), get all members who served.
                If True, only current members representing districts.
            page_size: Number of results per page (max 250).

        Returns:
            List of MemberInfo objects.
        """
        results: list[MemberInfo] = []
        offset = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                params: dict[str, Any] = {
                    "api_key": self.api_key,
                    "format": "json",
                    "limit": page_size,
                    "offset": offset,
                    "currentMember": str(current_member).lower(),
                }

                url = f"{self.base_url}/member/congress/{congress}"
                logger.info(f"Fetching Congress {congress} members (offset={offset})")
                response = await self._request_with_retry(
                    client, "GET", url, params=params
                )
                data = response.json()

                # Parse members
                members = data.get("members", [])
                for member_data in members:
                    info = MemberInfo.from_api_response(member_data)
                    results.append(info)

                # Check for more pages
                pagination = data.get("pagination", {})
                count = pagination.get("count", 0)
                if offset + page_size >= count or not members:
                    break

                offset += page_size

        logger.info(f"Fetched {len(results)} members for Congress {congress}")
        return results

    async def get_member_detail(self, bioguide_id: str) -> MemberDetail:
        """Fetch detailed information about a specific member.

        Args:
            bioguide_id: The member's Bioguide ID (e.g., "B000944").

        Returns:
            MemberDetail with full biographical and service information.
        """
        url = f"{self.base_url}/member/{bioguide_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {"api_key": self.api_key, "format": "json"}
            logger.info(f"Fetching member detail for {bioguide_id}")
            response = await self._request_with_retry(client, "GET", url, params=params)
            data = response.json()

        member_data = data.get("member", {})
        return MemberDetail.from_api_response(member_data)

    async def get_bill_sponsors(
        self,
        congress: int,
        bill_type: str,
        bill_number: int,
    ) -> tuple[SponsorInfo | None, list[SponsorInfo]]:
        """Fetch sponsor and cosponsors for a bill.

        Args:
            congress: Congress number (e.g., 117).
            bill_type: Bill type code (e.g., "hr", "s", "hjres").
            bill_number: Bill number.

        Returns:
            Tuple of (sponsor, list of cosponsors). Sponsor may be None for
            historical bills without sponsor data.
        """
        # Get bill details for sponsor
        url = f"{self.base_url}/bill/{congress}/{bill_type.lower()}/{bill_number}"
        sponsor: SponsorInfo | None = None
        cosponsors: list[SponsorInfo] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Fetch bill details (includes sponsor)
            params = {"api_key": self.api_key, "format": "json"}
            logger.info(f"Fetching bill {congress}/{bill_type}/{bill_number}")
            response = await self._request_with_retry(client, "GET", url, params=params)
            data = response.json()

            bill_data = data.get("bill", {})
            sponsors_data = bill_data.get("sponsors", [])
            if sponsors_data:
                sponsor = SponsorInfo.from_api_response(sponsors_data[0])

            # Fetch cosponsors
            cosponsors_url = f"{url}/cosponsors"
            offset = 0
            while True:
                params = {
                    "api_key": self.api_key,
                    "format": "json",
                    "limit": DEFAULT_PAGE_SIZE,
                    "offset": offset,
                }
                response = await self._request_with_retry(
                    client, "GET", cosponsors_url, params=params
                )
                data = response.json()

                cosponsors_data = data.get("cosponsors", [])
                for cosponsor_data in cosponsors_data:
                    cosponsors.append(SponsorInfo.from_api_response(cosponsor_data))

                # Check for more pages
                pagination = data.get("pagination", {})
                count = pagination.get("count", 0)
                if offset + DEFAULT_PAGE_SIZE >= count or not cosponsors_data:
                    break
                offset += DEFAULT_PAGE_SIZE

        logger.info(
            f"Fetched sponsor and {len(cosponsors)} cosponsors "
            f"for {bill_type.upper()} {bill_number}"
        )
        return sponsor, cosponsors

    async def get_law_bill_info(
        self,
        congress: int,
        law_number: int,
        law_type: str = "pub",
    ) -> dict[str, Any] | None:
        """Get the originating bill for a Public Law.

        Args:
            congress: Congress number.
            law_number: Law number within that Congress.
            law_type: "pub" for public law, "priv" for private law.

        Returns:
            Dictionary with bill reference info, or None if not found.
        """
        url = f"{self.base_url}/law/{congress}/{law_type}/{law_number}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {"api_key": self.api_key, "format": "json"}
            try:
                logger.info(f"Fetching law info for PL {congress}-{law_number}")
                response = await self._request_with_retry(
                    client, "GET", url, params=params
                )
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Law PL {congress}-{law_number} not found")
                    return None
                raise
