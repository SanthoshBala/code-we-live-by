"""OLRC Release Point registry — tracks and manages release point metadata.

Release points are snapshots of the US Code published by the OLRC at:
https://uscode.house.gov/download/priorreleasepoints.htm

Each release point identifies the US Code "through" a specific Public Law,
sometimes excluding certain laws that haven't yet been codified.
"""

import contextlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import httpx
from lxml import html

logger = logging.getLogger(__name__)

# URL for the prior release points listing page
PRIOR_RELEASE_POINTS_URL = "https://uscode.house.gov/download/priorreleasepoints.htm"


@dataclass
class ReleasePointInfo:
    """Metadata about a single OLRC release point.

    Attributes:
        full_identifier: e.g., "118-158" or "119-72not60"
        congress: Congress number (e.g., 118)
        law_identifier: Law part of the identifier (e.g., "158" or "72not60")
        publication_date: Date the release point was published (if available)
        titles_available: List of title numbers available at this release point
        download_url_pattern: URL pattern for downloading title XMLs
    """

    full_identifier: str
    congress: int
    law_identifier: str
    publication_date: date | None = None
    titles_available: list[int] = field(default_factory=list)
    download_url_pattern: str | None = None

    @property
    def primary_law_number(self) -> int | None:
        """Extract the primary law number (ignoring 'not' exclusions)."""
        match = re.match(r"(\d+)", self.law_identifier)
        if match:
            return int(match.group(1))
        return None

    @property
    def excluded_laws(self) -> list[int]:
        """Extract excluded law numbers from 'notXX' suffix."""
        excluded = []
        for match in re.finditer(r"not(\d+)", self.law_identifier):
            excluded.append(int(match.group(1)))
        return excluded

    @property
    def update_number(self) -> int:
        """Extract update number from 'uN' suffix (e.g., u1, u2). Returns 0 if none."""
        match = re.search(r"u(\d+)", self.law_identifier)
        if match:
            return int(match.group(1))
        return 0

    def __str__(self) -> str:
        return f"PL {self.full_identifier}"


def parse_release_point_identifier(identifier: str) -> tuple[int, str]:
    """Parse a release point identifier into (congress, law_identifier).

    Args:
        identifier: e.g., "118-158", "119-72not60", "113-21"

    Returns:
        Tuple of (congress, law_identifier).

    Raises:
        ValueError: If the identifier format is invalid.
    """
    parts = identifier.split("-", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid release point identifier: {identifier}. "
            "Expected format: 'congress-law' (e.g., '118-158')"
        )
    try:
        congress = int(parts[0])
    except ValueError as exc:
        raise ValueError(
            f"Invalid congress number in release point: {parts[0]}"
        ) from exc
    return congress, parts[1]


class ReleasePointRegistry:
    """Registry for tracking OLRC release points.

    Provides methods to fetch, query, and manage release point metadata.
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._release_points: list[ReleasePointInfo] | None = None

    async def fetch_release_points(self) -> list[ReleasePointInfo]:
        """Fetch the list of prior release points from the OLRC website.

        Scrapes the prior release points page to build a registry of available
        release points with their metadata (date, affected titles).

        Returns:
            List of ReleasePointInfo objects, sorted chronologically.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(PRIOR_RELEASE_POINTS_URL, follow_redirects=True)
            response.raise_for_status()

        tree = html.fromstring(response.content)
        release_points = []

        # Each release point is an <a> inside an <li>. The link text contains
        # the date and affected titles:
        #   "Public Law 119-72 (01/20/2026), except 119-60, affecting titles 38, 42."
        links = tree.xpath("//a[contains(@href, 'releasepoint')]")

        for link_elem in links:
            href = link_elem.get("href", "")
            link_text = link_elem.text_content().strip()
            rp_info = self._parse_release_point_link(href, link_text)
            if rp_info:
                release_points.append(rp_info)

        # Deduplicate by identifier
        seen = set()
        unique_rps = []
        for rp in release_points:
            if rp.full_identifier not in seen:
                seen.add(rp.full_identifier)
                unique_rps.append(rp)

        # Sort chronologically:
        # 1. Publication date (primary ordering)
        # 2. Congress number (tiebreaker for same-day across congresses)
        # 3. Primary law number (sequential within a congress)
        # 4. Exclusion count descending (more exclusions = earlier state)
        # 5. Update number (u1, u2 — multiple updates on the same day)
        unique_rps.sort(
            key=lambda rp: (
                rp.publication_date or date.min,
                rp.congress,
                rp.primary_law_number or 0,
                -len(rp.excluded_laws),
                rp.update_number,
            )
        )

        self._release_points = unique_rps
        logger.debug(f"Fetched {len(unique_rps)} total release points from OLRC")
        return unique_rps

    def _parse_release_point_link(
        self, href: str, link_text: str = ""
    ) -> ReleasePointInfo | None:
        """Parse a release point from a download page link and its text.

        Args:
            href: Link href from the prior release points page.
            link_text: The visible text of the link, containing date and titles.

        Returns:
            ReleasePointInfo or None if the link doesn't match expected pattern.
        """
        # Pattern: .../releasepoints/us/pl/{congress}/{law_id}/...
        match = re.search(
            r"releasepoints/us/pl/(\d+)/([^/]+)",
            href,
        )
        if not match:
            return None

        congress = int(match.group(1))
        law_identifier = match.group(2)
        full_identifier = f"{congress}-{law_identifier}"

        # Parse date from link text: "Public Law 119-72 (01/20/2026) ..."
        publication_date = None
        date_match = re.search(r"\((\d{2}/\d{2}/\d{4})\)", link_text)
        if date_match:
            with contextlib.suppress(ValueError):
                publication_date = datetime.strptime(
                    date_match.group(1), "%m/%d/%Y"
                ).date()

        # Parse affected titles: "affecting title(s) 2, 16, 26, 33, 43."
        titles_available: list[int] = []
        titles_match = re.search(r"affecting titles?\s+(.+?)\.?\s*$", link_text)
        if titles_match:
            titles_text = titles_match.group(1).rstrip(".")
            for part in titles_text.split(","):
                part = part.strip()
                # Handle "11A" style titles by stripping letter suffix
                num_match = re.match(r"(\d+)", part)
                if num_match:
                    titles_available.append(int(num_match.group(1)))

        return ReleasePointInfo(
            full_identifier=full_identifier,
            congress=congress,
            law_identifier=law_identifier,
            publication_date=publication_date,
            titles_available=sorted(set(titles_available)),
        )

    def get_release_points(self) -> list[ReleasePointInfo]:
        """Return cached release points. Must call fetch_release_points first."""
        if self._release_points is None:
            raise RuntimeError(
                "Release points not loaded. Call fetch_release_points() first."
            )
        return self._release_points

    def get_by_identifier(self, identifier: str) -> ReleasePointInfo | None:
        """Look up a release point by its full identifier.

        Args:
            identifier: e.g., "118-158"

        Returns:
            ReleasePointInfo or None if not found.
        """
        for rp in self.get_release_points():
            if rp.full_identifier == identifier:
                return rp
        return None

    def get_for_congress(self, congress: int) -> list[ReleasePointInfo]:
        """Get all release points for a specific congress.

        Args:
            congress: Congress number (e.g., 118).

        Returns:
            List of release points for that congress, sorted by law number.
        """
        return [rp for rp in self.get_release_points() if rp.congress == congress]

    def get_adjacent_pairs(
        self, congress: int | None = None
    ) -> list[tuple[ReleasePointInfo, ReleasePointInfo]]:
        """Return consecutive release point pairs for diffing/validation.

        Args:
            congress: If provided, filter to only this congress.

        Returns:
            List of (before, after) release point pairs.
        """
        rps = self.get_release_points()
        if congress is not None:
            rps = [rp for rp in rps if rp.congress == congress]

        pairs = []
        for i in range(len(rps) - 1):
            pairs.append((rps[i], rps[i + 1]))
        return pairs

    def get_laws_in_range(
        self,
        rp_before: str,
        rp_after: str,
        last_law_of_congress: dict[int, int] | None = None,
    ) -> list[tuple[int, int]]:
        """Return (congress, law_number) pairs enacted between two release points.

        This identifies which Public Laws were enacted between two release
        points, useful for attributing changes.

        Args:
            rp_before: Identifier of the earlier release point (e.g., "118-22").
            rp_after: Identifier of the later release point (e.g., "118-30").
            last_law_of_congress: Optional mapping of congress -> last law number
                for cross-congress boundary handling.

        Returns:
            List of (congress, law_number) tuples for laws in the range.
        """
        before_congress, before_law_id = parse_release_point_identifier(rp_before)
        after_congress, after_law_id = parse_release_point_identifier(rp_after)

        # Extract primary law numbers
        before_match = re.match(r"(\d+)", before_law_id)
        after_match = re.match(r"(\d+)", after_law_id)

        if not before_match or not after_match:
            return []

        before_num = int(before_match.group(1))
        after_num = int(after_match.group(1))

        laws = []

        if before_congress == after_congress:
            # Same congress — laws are numbered sequentially
            for law_num in range(before_num + 1, after_num + 1):
                laws.append((before_congress, law_num))
        else:
            # Cross-congress boundary
            if last_law_of_congress and before_congress in last_law_of_congress:
                # Finish out the earlier congress
                last_law = last_law_of_congress[before_congress]
                for law_num in range(before_num + 1, last_law + 1):
                    laws.append((before_congress, law_num))
                # Start the new congress up to the target law
                for law_num in range(1, after_num + 1):
                    laws.append((after_congress, law_num))
            else:
                logger.warning(
                    f"Cross-congress range ({rp_before} -> {rp_after}): "
                    "provide last_law_of_congress for accurate enumeration"
                )

        return laws

    def get_titles_at_release_point(self, identifier: str) -> list[int]:
        """Get the list of available titles at a release point.

        Args:
            identifier: Release point identifier (e.g., "118-158").

        Returns:
            List of title numbers available, or empty if unknown.
        """
        rp = self.get_by_identifier(identifier)
        if rp is None:
            return []
        return rp.titles_available
