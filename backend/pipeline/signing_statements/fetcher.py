"""Fetcher for presidential signing statements from GovInfo.

Signing statements live in the CPD (Compilation of Presidential Documents)
collection on api.govinfo.gov. The collection uses two package-ID prefixes:

  WCPD-YYYY-MM-DD   — Weekly Compilation (1993–2009, Clinton / Bush)
  DCPD-YYYYMMDDXXX  — Daily Compilation  (2009–present, Obama onwards)

Not every law gets a signing statement; most routine / minor bills do not.
The function returns None gracefully when no statement is found.

The GOVINFO_API_KEY environment variable (or app settings) must be set.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

GOVINFO_SEARCH_URL = "https://api.govinfo.gov/search"
GOVINFO_DETAILS_URL = "https://www.govinfo.gov/app/details"

_REQUEST_TIMEOUT = 15.0


@dataclass
class SigningStatementResult:
    """A presidential signing statement fetched from GovInfo CPD."""

    text: str
    source_url: str  # public govinfo.gov details link
    title: str
    date_issued: str  # YYYY-MM-DD


def _get_api_key() -> str:
    """Return the GovInfo API key from app settings."""
    from app.config import settings

    key: str | None = getattr(settings, "govinfo_api_key", None)
    if not key:
        raise ValueError(
            "GovInfo API key required. Set GOVINFO_API_KEY environment variable."
        )
    return key


async def _search_govinfo(
    title: str,
    congress: int,
    law_number: str,
    api_key: str,
    client: httpx.AsyncClient,
) -> dict[str, object] | None:
    """Search GovInfo for a signing statement granule.  Returns first CPD hit or None."""
    queries = [
        f'"Statement on Signing" "{title}"',
        # Fallback: search by public law number as it appears in the statement text
        f'"Statement on Signing" "Public Law No. {congress}-{law_number}"',
        f'"Statement on Signing" "Public Law {congress}-{law_number}"',
    ]

    for query in queries:
        payload = {"query": query, "pageSize": 10, "offsetMark": "*"}
        try:
            resp = await client.post(
                GOVINFO_SEARCH_URL,
                json=payload,
                params={"api_key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("GovInfo search error for %r: %s", query, exc)
            continue

        results: list[dict[str, object]] = data.get("results", [])
        for result in results:
            if result.get("collectionCode") == "CPD" and result.get("granuleId"):
                logger.debug("Found CPD signing statement: %s", result.get("title"))
                return result

    return None


async def _fetch_statement_text(
    granule_id: str,
    package_id: str,
    api_key: str,
    client: httpx.AsyncClient,
) -> str | None:
    """Fetch and clean the plain-text body of a CPD granule."""
    htm_url = (
        f"https://api.govinfo.gov/packages/{package_id}"
        f"/granules/{granule_id}/htm?api_key={api_key}"
    )
    try:
        resp = await client.get(htm_url)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(
            "Failed to fetch signing statement text from %s: %s", htm_url, exc
        )
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    pre = soup.find("pre")
    if not pre:
        return None

    raw = pre.get_text("\n")
    lines = raw.splitlines()
    # Drop bracketed GPO metadata headers and strip leading whitespace per line.
    # GovInfo right-aligns the president's signature with spaces; stripping gives
    # consistent left-aligned text for display.
    body_lines = [
        line.lstrip() for line in lines if not re.match(r"^\s*\[.*\]\s*$", line)
    ]
    # Collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip()
    return text or None


async def fetch_signing_statement(
    congress: int,
    law_number: str,
    title: str,
    api_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> SigningStatementResult | None:
    """Fetch the signing statement for a public law from GovInfo CPD.

    Returns a SigningStatementResult if a statement is found, or None if
    no statement exists for this law or the fetch fails.

    Args:
        congress: Congress number (e.g. 118).
        law_number: Law number string (e.g. "5").
        title: Short title or popular name of the law (used for search).
        api_key: GovInfo API key; reads from settings if omitted.
        client: Optional pre-configured httpx.AsyncClient (for testing).
    """
    if api_key is None:
        try:
            api_key = _get_api_key()
        except ValueError as exc:
            logger.warning("Signing statement fetch skipped: %s", exc)
            return None

    own_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=_REQUEST_TIMEOUT,
        )

    try:
        hit = await _search_govinfo(title, congress, law_number, api_key, client)
        if hit is None:
            logger.debug(
                "No signing statement in GovInfo CPD for PL %d-%s (%s)",
                congress,
                law_number,
                title,
            )
            return None

        package_id = str(hit["packageId"])
        granule_id = str(hit["granuleId"])
        public_url = f"{GOVINFO_DETAILS_URL}/{package_id}/{granule_id}"

        text = await _fetch_statement_text(granule_id, package_id, api_key, client)
        if not text:
            logger.warning("Could not extract text for %s / %s", package_id, granule_id)
            return None

        return SigningStatementResult(
            text=text,
            source_url=public_url,
            title=str(hit.get("title", "")),
            date_issued=str(hit.get("dateIssued", "")),
        )

    except Exception as exc:
        logger.warning(
            "Unexpected error fetching signing statement for PL %d-%s: %s",
            congress,
            law_number,
            exc,
        )
        return None
    finally:
        if own_client:
            await client.aclose()
