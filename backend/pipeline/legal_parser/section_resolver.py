"""Section resolver — map SectionReference to database USCodeSection records.

This module resolves parsed amendment targets (SectionReference objects) to
their corresponding database records, handling normalization quirks like
hyphen vs. en-dash in section numbers.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.us_code import USCodeSection
from pipeline.legal_parser.amendment_parser import SectionReference

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of resolving a SectionReference to a database record.

    Attributes:
        section_ref: The original SectionReference being resolved.
        section: The matching USCodeSection, or None if not found.
        resolved: Whether resolution succeeded.
        error: Description of why resolution failed, if applicable.
        normalized_section_number: The section number after normalization.
    """

    section_ref: SectionReference
    section: USCodeSection | None = None
    resolved: bool = False
    error: str | None = None
    normalized_section_number: str | None = None


def normalize_section_number(section_num: str) -> str:
    """Normalize section number for database lookup.

    The OLRC uses en-dashes in section numbers (e.g., "80a–3a") while law text
    uses regular hyphens (e.g., "80a-3a"). This normalizes to en-dashes to
    match the database.
    """
    return section_num.replace("-", "\u2013")  # hyphen to en-dash


class SectionResolver:
    """Resolve SectionReference objects to USCodeSection database records."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[tuple[int, str], USCodeSection | None] = {}

    async def resolve(
        self,
        section_ref: SectionReference,
        default_title: int | None = None,
    ) -> ResolutionResult:
        """Resolve a single SectionReference to a USCodeSection.

        Args:
            section_ref: The section reference to resolve.
            default_title: Default title if not specified in the reference.

        Returns:
            ResolutionResult with the matched section or error details.
        """
        title = section_ref.title or default_title
        if title is None:
            return ResolutionResult(
                section_ref=section_ref,
                error="No title number specified and no default title",
            )

        section_number = section_ref.section
        normalized = normalize_section_number(section_number)

        # Check cache first
        cache_key = (title, normalized)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached:
                return ResolutionResult(
                    section_ref=section_ref,
                    section=cached,
                    resolved=True,
                    normalized_section_number=normalized,
                )
            else:
                return ResolutionResult(
                    section_ref=section_ref,
                    error=f"Section {title} USC {section_number} not found",
                    normalized_section_number=normalized,
                )

        # Try exact match first
        section = await self._lookup(title, normalized)

        # If not found, try original (unnormalized) section number
        if section is None and normalized != section_number:
            section = await self._lookup(title, section_number)

        self._cache[cache_key] = section

        if section:
            return ResolutionResult(
                section_ref=section_ref,
                section=section,
                resolved=True,
                normalized_section_number=normalized,
            )

        return ResolutionResult(
            section_ref=section_ref,
            error=f"Section {title} USC {section_number} not found in database",
            normalized_section_number=normalized,
        )

    async def resolve_batch(
        self,
        refs: list[SectionReference],
        default_title: int | None = None,
    ) -> list[ResolutionResult]:
        """Resolve multiple SectionReferences with pre-fetching.

        Pre-fetches all sections for referenced titles to minimize DB queries.

        Args:
            refs: List of section references to resolve.
            default_title: Default title if not specified in references.

        Returns:
            List of ResolutionResults in the same order as input.
        """
        # Collect all title numbers we need
        titles = set()
        for ref in refs:
            title = ref.title or default_title
            if title is not None:
                titles.add(title)

        # Pre-fetch all sections for those titles
        if titles:
            await self._prefetch_titles(list(titles))

        # Resolve each reference using cached data
        results = []
        for ref in refs:
            result = await self.resolve(ref, default_title)
            results.append(result)

        return results

    async def _lookup(self, title: int, section_number: str) -> USCodeSection | None:
        """Look up a section in the database."""
        result = await self.session.execute(
            select(USCodeSection).where(
                USCodeSection.title_number == title,
                USCodeSection.section_number == section_number,
            )
        )
        return result.scalar_one_or_none()

    async def _prefetch_titles(self, titles: list[int]) -> None:
        """Pre-fetch all sections for the given titles into the cache."""
        for title in titles:
            # Skip if we already have sections for this title cached
            if any(k[0] == title for k in self._cache):
                continue

            result = await self.session.execute(
                select(USCodeSection).where(USCodeSection.title_number == title)
            )
            sections = result.scalars().all()

            for section in sections:
                cache_key = (title, section.section_number)
                self._cache[cache_key] = section

            logger.debug(
                f"Pre-fetched {len(sections)} sections for Title {title}"
            )
