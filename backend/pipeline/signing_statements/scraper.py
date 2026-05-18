"""Scraper for presidential signing statements from UCSB American Presidency Project.

The UCSB American Presidency Project (presidency.ucsb.edu) maintains the most
comprehensive archive of presidential signing statements. This module searches that
archive by law number and extracts the statement text and source URL.

No API key required; the site is publicly accessible. Rate-limit scraping to avoid
overloading the server (add delays in batch jobs).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

UCSB_BASE = "https://www.presidency.ucsb.edu"
# Category 50 is "Signing Statements" on UCSB advanced search
UCSB_SEARCH_URL = f"{UCSB_BASE}/advanced-search"
UCSB_SIGNING_STATEMENT_CATEGORY = "50"

# Timeout for individual HTTP requests (seconds)
_REQUEST_TIMEOUT = 15.0


@dataclass
class SigningStatementResult:
    """A presidential signing statement fetched from UCSB."""

    text: str
    source_url: str
    title: str


def _build_search_url(query: str) -> str:
    """Return a UCSB advanced-search URL filtered to signing statement documents."""
    params = {
        "field-keywords": query,
        "items_per_page": "10",
        "category2[]": UCSB_SIGNING_STATEMENT_CATEGORY,
    }
    return f"{UCSB_SEARCH_URL}?{urlencode(params)}"


def _parse_search_results(html: str) -> list[tuple[str, str]]:
    """Return (title, relative_url) pairs from a UCSB search results page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[tuple[str, str]] = []

    # UCSB search results list document titles inside <h3 class="field-content">
    for h3 in soup.select("h3.field-content a"):
        href = h3.get("href", "")
        title = h3.get_text(strip=True)
        if href and title:
            results.append((title, str(href)))

    return results


def _parse_statement_page(html: str) -> str | None:
    """Extract the body text of a signing statement from its detail page."""
    soup = BeautifulSoup(html, "lxml")

    # The statement body lives in <div class="field-docs-content">
    body_div = soup.select_one("div.field-docs-content")
    if body_div is None:
        # Fallback: try the generic document body selector
        body_div = soup.select_one("div.field-items .field-item")
    if body_div is None:
        return None

    # Collapse whitespace but preserve paragraph breaks
    paragraphs = [p.get_text(" ", strip=True) for p in body_div.find_all("p")]
    if paragraphs:
        return "\n\n".join(p for p in paragraphs if p)

    return body_div.get_text(" ", strip=True) or None


def _query_for_law(congress: int, law_number: str) -> str:
    """Build the search query string for a public law."""
    # Try the most recognisable format first: "Public Law 118-5"
    return f"Public Law {congress}-{law_number}"


async def fetch_signing_statement(
    congress: int,
    law_number: str,
    client: httpx.AsyncClient | None = None,
) -> SigningStatementResult | None:
    """Search UCSB for a signing statement matching the given public law.

    Returns a SigningStatementResult if found, or None if no statement exists
    or the scrape fails. Errors are logged as warnings rather than raised so
    callers can treat missing statements as graceful nulls.

    Args:
        congress: Congress number (e.g. 118).
        law_number: Law number as a string (e.g. "5" or "234").
        client: Optional pre-configured httpx.AsyncClient (useful for testing).
    """
    own_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=_REQUEST_TIMEOUT,
            headers={
                "User-Agent": "CWLB-research-bot/1.0 (civic-tech; non-commercial)"
            },
        )

    try:
        query = _query_for_law(congress, law_number)
        search_url = _build_search_url(query)
        logger.debug("Searching UCSB for signing statement: %s", search_url)

        search_resp = await client.get(search_url)
        search_resp.raise_for_status()

        hits = _parse_search_results(search_resp.text)
        if not hits:
            logger.debug(
                "No UCSB signing statement found for PL %d-%s", congress, law_number
            )
            return None

        # The first result is typically the best match
        doc_title, doc_path = hits[0]
        doc_url = doc_path if doc_path.startswith("http") else f"{UCSB_BASE}{doc_path}"

        logger.debug("Fetching signing statement from %s", doc_url)
        doc_resp = await client.get(doc_url)
        doc_resp.raise_for_status()

        text = _parse_statement_page(doc_resp.text)
        if not text:
            logger.warning("Could not parse statement body from %s", doc_url)
            return None

        return SigningStatementResult(text=text, source_url=doc_url, title=doc_title)

    except httpx.HTTPError as exc:
        logger.warning(
            "HTTP error fetching signing statement for PL %d-%s: %s",
            congress,
            law_number,
            exc,
        )
        return None
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


def _normalize_law_number(raw: str) -> str:
    """Strip leading zeros from a law number string."""
    # Some sources store "005"; we want "5"
    return str(int(re.sub(r"[^0-9]", "", raw))) if re.search(r"\d", raw) else raw
