"""Section resolver — normalize section references to natural keys.

Resolves parsed amendment targets (SectionReference objects) to
(title_number, section_number) pairs, handling normalization quirks
like hyphen vs. en-dash in section numbers. No database access needed.
"""

import logging
from dataclasses import dataclass

from pipeline.legal_parser.amendment_parser import SectionReference

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of resolving a SectionReference to natural keys.

    Attributes:
        section_ref: The original SectionReference being resolved.
        title_number: The resolved title number, or None if unresolved.
        section_number: The resolved (normalized) section number, or None.
        resolved: Whether resolution succeeded.
        error: Description of why resolution failed, if applicable.
        normalized_section_number: The section number after normalization.
    """

    section_ref: SectionReference
    title_number: int | None = None
    section_number: str | None = None
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
    """Resolve SectionReference objects to (title_number, section_number) pairs.

    Pure normalizer — no database access.
    """

    def resolve(
        self,
        section_ref: SectionReference,
        default_title: int | None = None,
    ) -> ResolutionResult:
        """Resolve a single SectionReference to natural keys.

        Args:
            section_ref: The section reference to resolve.
            default_title: Default title if not specified in the reference.

        Returns:
            ResolutionResult with title_number and section_number, or error.
        """
        title = section_ref.title or default_title
        if title is None:
            return ResolutionResult(
                section_ref=section_ref,
                error="No title number specified and no default title",
            )

        normalized = normalize_section_number(section_ref.section)

        return ResolutionResult(
            section_ref=section_ref,
            title_number=title,
            section_number=normalized,
            resolved=True,
            normalized_section_number=normalized,
        )

    def resolve_batch(
        self,
        refs: list[SectionReference],
        default_title: int | None = None,
    ) -> list[ResolutionResult]:
        """Resolve multiple SectionReferences.

        Args:
            refs: List of section references to resolve.
            default_title: Default title if not specified in references.

        Returns:
            List of ResolutionResults in the same order as input.
        """
        return [self.resolve(ref, default_title) for ref in refs]
