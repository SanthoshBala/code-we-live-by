"""Title lookup for Public Laws and Acts (Task 1.11).

This module provides title information for laws referenced in US Code sections.
It uses a hybrid approach:
1. Hardcoded table for major historical laws (pre-GovInfo era)
2. GovInfo API lookup for modern laws (105th Congress onwards)
3. In-memory caching to avoid repeated API calls
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LawTitleInfo:
    """Title information for a law."""

    official_title: str | None = None
    short_title: str | None = None
    short_title_aliases: list[str] | None = None

    @property
    def display_title(self) -> str | None:
        """Return the best title for display (prefers alias > short > official)."""
        if self.short_title_aliases:
            return self.short_title_aliases[0]
        if self.short_title:
            return self.short_title
        return self.official_title


# =============================================================================
# Hardcoded title table for major historical laws
# =============================================================================
# These laws are either:
# - Pre-GovInfo era (before ~105th Congress / 1997)
# - Commonly referenced and worth having cached
#
# Format: (congress, law_number) -> LawTitleInfo
# For Acts: "ch{chapter}" -> LawTitleInfo
# =============================================================================

HARDCODED_TITLES: dict[tuple[int, int] | str, LawTitleInfo] = {
    # Pre-1957 Acts (by chapter number)
    "ch531": LawTitleInfo(short_title="Social Security Act"),
    "ch343": LawTitleInfo(short_title="National Security Act of 1947"),
    "ch121": LawTitleInfo(short_title="Administrative Procedure Act"),
    # Copyright / IP
    (94, 553): LawTitleInfo(
        short_title="Copyright Act of 1976",
        short_title_aliases=["Copyright Act"],
    ),
    (100, 568): LawTitleInfo(
        short_title="Berne Convention Implementation Act of 1988",
    ),
    (105, 304): LawTitleInfo(
        short_title="Digital Millennium Copyright Act",
        short_title_aliases=["DMCA"],
    ),
    (109, 9): LawTitleInfo(
        short_title="Class Action Fairness Act of 2005",
        short_title_aliases=["CAFA"],
    ),
    # Major modern laws (for quick lookup without API call)
    (116, 136): LawTitleInfo(
        short_title="Coronavirus Aid, Relief, and Economic Security Act",
        short_title_aliases=["CARES Act"],
    ),
    (117, 169): LawTitleInfo(
        short_title="Inflation Reduction Act of 2022",
        short_title_aliases=["IRA"],
    ),
    (117, 58): LawTitleInfo(
        short_title="Infrastructure Investment and Jobs Act",
        short_title_aliases=["IIJA", "Bipartisan Infrastructure Law"],
    ),
    (111, 148): LawTitleInfo(
        short_title="Patient Protection and Affordable Care Act",
        short_title_aliases=["ACA", "Affordable Care Act"],
    ),
    (107, 56): LawTitleInfo(
        short_title="USA PATRIOT Act",
        short_title_aliases=["Patriot Act"],
    ),
    (107, 204): LawTitleInfo(
        short_title="Sarbanes-Oxley Act of 2002",
        short_title_aliases=["SOX", "Sarbanes-Oxley"],
    ),
    (111, 203): LawTitleInfo(
        short_title="Dodd-Frank Wall Street Reform and Consumer Protection Act",
        short_title_aliases=["Dodd-Frank"],
    ),
}

# In-memory cache for GovInfo lookups
_title_cache: dict[tuple[int, int], LawTitleInfo | None] = {}


def _parse_govinfo_short_titles(short_title_data: list[dict]) -> LawTitleInfo:
    """Parse the shortTitle field from GovInfo API response.

    The API returns a list like:
    [{'title': 'Coronavirus Aid, Relief, and Economic Security Act" or the "CARES Act'}]

    We need to parse out the primary title and any aliases.
    """
    if not short_title_data:
        return LawTitleInfo()

    titles: list[str] = []
    for item in short_title_data:
        raw_title = item.get("title", "")
        if not raw_title:
            continue

        # Handle "X" or the "Y" pattern
        # Example: 'Coronavirus Aid, Relief, and Economic Security Act" or the "CARES Act'
        if '" or the "' in raw_title or "' or the '" in raw_title:
            # Split on the pattern and clean up quotes
            parts = re.split(r'["\']?\s+or the\s+["\']?', raw_title)
            for part in parts:
                clean = part.strip().strip("\"'")
                if clean:
                    titles.append(clean)
        else:
            # Single title, just clean up quotes
            clean = raw_title.strip().strip("\"'")
            if clean:
                titles.append(clean)

    if not titles:
        return LawTitleInfo()

    # First title is the primary short title, rest are aliases
    return LawTitleInfo(
        short_title=titles[0],
        short_title_aliases=titles[1:] if len(titles) > 1 else None,
    )


async def lookup_public_law_title(
    congress: int,
    law_number: int,
    use_cache: bool = True,
) -> LawTitleInfo | None:
    """Look up title information for a Public Law.

    Args:
        congress: Congress number (e.g., 116)
        law_number: Law number (e.g., 136)
        use_cache: Whether to use/update the in-memory cache

    Returns:
        LawTitleInfo or None if not found
    """
    key = (congress, law_number)

    # Check hardcoded table first
    if key in HARDCODED_TITLES:
        return HARDCODED_TITLES[key]

    # Check cache
    if use_cache and key in _title_cache:
        return _title_cache[key]

    # Try GovInfo API for modern laws (105th Congress onwards)
    if congress >= 105:
        try:
            from pipeline.govinfo.client import GovInfoClient

            client = GovInfoClient()
            import httpx

            package_id = client.build_package_id(congress, law_number)
            url = f"{client.base_url}/packages/{package_id}/summary"

            async with httpx.AsyncClient(timeout=client.timeout) as http_client:
                response = await http_client.get(
                    url, params={"api_key": client.api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    short_title_data = data.get("shortTitle", [])
                    official_title = data.get("title")

                    info = _parse_govinfo_short_titles(short_title_data)
                    info.official_title = official_title

                    if use_cache:
                        _title_cache[key] = info
                    return info
                elif response.status_code == 404:
                    logger.debug(f"Law PL {congress}-{law_number} not found in GovInfo")
                    if use_cache:
                        _title_cache[key] = None
                    return None
                else:
                    logger.warning(
                        f"GovInfo API error for PL {congress}-{law_number}: "
                        f"HTTP {response.status_code}"
                    )
        except Exception as e:
            logger.warning(f"Failed to lookup title for PL {congress}-{law_number}: {e}")

    return None


def lookup_act_title(chapter: int) -> LawTitleInfo | None:
    """Look up title information for a pre-1957 Act.

    Args:
        chapter: Chapter number in Statutes at Large

    Returns:
        LawTitleInfo or None if not found
    """
    key = f"ch{chapter}"
    return HARDCODED_TITLES.get(key)


def clear_cache() -> None:
    """Clear the in-memory title cache."""
    _title_cache.clear()


async def enrich_citations_with_titles(
    citations: list,
    skip_api: bool = False,
) -> None:
    """Enrich a list of SourceLaw citations with title information.

    Modifies citations in place, setting the title fields on each law/act.

    Args:
        citations: List of SourceLawSchema objects to enrich
        skip_api: If True, only use hardcoded table (no GovInfo API calls)
    """
    for citation in citations:
        if citation.law:
            # Public Law - look up title
            if skip_api:
                # Only check hardcoded table
                key = (citation.law.congress, citation.law.law_number)
                info = HARDCODED_TITLES.get(key)
            else:
                info = await lookup_public_law_title(
                    citation.law.congress,
                    citation.law.law_number,
                )

            if info:
                citation.law.official_title = info.official_title
                citation.law.short_title = info.short_title
                if info.short_title_aliases:
                    citation.law.short_title_aliases = info.short_title_aliases

        elif citation.act:
            # Pre-1957 Act - use hardcoded table only
            info = lookup_act_title(citation.act.chapter)
            if info:
                citation.act.short_title = info.short_title
