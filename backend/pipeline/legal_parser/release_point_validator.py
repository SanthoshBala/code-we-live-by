"""Release point validator — validate law changes against OLRC release points.

This module compares our generated LawChange records against the known-good
state of the US Code at OLRC release points. Release points serve as
"checkpoints" to verify that our per-law parsing is producing correct results.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.us_code import USCodeSection
from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.parser import USLMParser

logger = logging.getLogger(__name__)


@dataclass
class SectionComparison:
    """Comparison of a single section between DB state and release point.

    Attributes:
        title_number: US Code title number.
        section_number: Section number.
        matches: Whether the provision text matches.
        db_text: Text content from the database (current state).
        rp_text: Text content from the release point XML.
        diff_summary: Description of differences if any.
    """

    title_number: int
    section_number: str
    matches: bool = False
    db_text: str | None = None
    rp_text: str | None = None
    diff_summary: str | None = None

    @property
    def in_db(self) -> bool:
        return self.db_text is not None

    @property
    def in_rp(self) -> bool:
        return self.rp_text is not None


@dataclass
class ValidationReport:
    """Report from validating against a release point.

    Attributes:
        release_point: The release point identifier.
        titles_checked: Titles that were validated.
        total_sections: Total sections compared.
        matches: Number of sections that match.
        mismatches: Number of sections that differ.
        only_in_db: Sections present in DB but not in release point.
        only_in_rp: Sections present in release point but not in DB.
        comparisons: Detailed per-section comparisons (mismatches only).
        errors: Any errors encountered.
    """

    release_point: str
    titles_checked: list[int] = field(default_factory=list)
    total_sections: int = 0
    matches: int = 0
    mismatches: int = 0
    only_in_db: int = 0
    only_in_rp: int = 0
    comparisons: list[SectionComparison] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        if self.total_sections == 0:
            return 0.0
        return self.matches / self.total_sections

    @property
    def is_valid(self) -> bool:
        """Whether the validation passed (>95% match rate, no errors)."""
        return self.match_rate >= 0.95 and not self.errors


class ReleasePointValidator:
    """Validate database state against OLRC release point snapshots.

    This compares our current understanding of the US Code (after applying
    law commits) against the OLRC's official release point XML.
    """

    def __init__(
        self,
        session: AsyncSession,
        download_dir: str | Path = "data/olrc",
    ):
        self.session = session
        self.download_dir = Path(download_dir)
        self.downloader = OLRCDownloader(download_dir=download_dir)
        self.parser = USLMParser()

    async def validate_against_release_point(
        self,
        release_point: str,
        titles: list[int],
        verbose: bool = False,
    ) -> ValidationReport:
        """Validate current DB state against a release point.

        1. Download title XML at this release point
        2. Parse sections from the XML
        3. Compare provision text against current DB state
        4. Report matches, mismatches, and missing sections

        Args:
            release_point: Release point identifier (e.g., "113-22").
            titles: Title numbers to validate.
            verbose: If True, log detailed per-section results.

        Returns:
            ValidationReport with comparison results.
        """
        report = ValidationReport(
            release_point=release_point,
            titles_checked=titles,
        )

        for title_num in titles:
            try:
                await self._validate_title(title_num, release_point, report, verbose)
            except Exception as e:
                logger.exception(
                    f"Error validating Title {title_num} " f"at {release_point}"
                )
                report.errors.append(f"Title {title_num}: {e}")

        logger.info(
            f"Validation against {release_point}: "
            f"{report.matches}/{report.total_sections} match "
            f"({report.match_rate:.1%}), "
            f"{report.mismatches} mismatches, "
            f"{report.only_in_db} only-in-DB, "
            f"{report.only_in_rp} only-in-RP"
        )

        return report

    async def _validate_title(
        self,
        title_num: int,
        release_point: str,
        report: ValidationReport,
        verbose: bool,
    ) -> None:
        """Validate a single title against a release point."""
        # Download and parse the release point XML
        xml_path = await self.downloader.download_title_at_release_point(
            title_num, release_point
        )

        if not xml_path:
            report.errors.append(
                f"Could not download Title {title_num} at {release_point}"
            )
            return

        rp_result = self.parser.parse_file(xml_path)

        # Build lookup of RP sections
        rp_sections: dict[str, str] = {}
        for section in rp_result.sections:
            rp_sections[section.section_number] = section.text_content or ""

        # Fetch DB sections for this title
        result = await self.session.execute(
            select(USCodeSection).where(USCodeSection.title_number == title_num)
        )
        db_sections_list = result.scalars().all()
        db_sections: dict[str, str] = {
            s.section_number: (s.text_content or "") for s in db_sections_list
        }

        # Compare
        all_section_numbers = set(rp_sections.keys()) | set(db_sections.keys())

        for section_num in sorted(all_section_numbers):
            report.total_sections += 1
            db_text = db_sections.get(section_num)
            rp_text = rp_sections.get(section_num)

            if db_text is not None and rp_text is not None:
                # Both exist — compare text
                if self._texts_match(db_text, rp_text):
                    report.matches += 1
                    if verbose:
                        logger.debug(f"  MATCH: Title {title_num} § {section_num}")
                else:
                    report.mismatches += 1
                    comparison = SectionComparison(
                        title_number=title_num,
                        section_number=section_num,
                        matches=False,
                        db_text=db_text[:200] if db_text else None,
                        rp_text=rp_text[:200] if rp_text else None,
                        diff_summary=self._describe_diff(db_text, rp_text),
                    )
                    report.comparisons.append(comparison)
                    if verbose:
                        logger.info(f"  MISMATCH: Title {title_num} § {section_num}")

            elif db_text is not None:
                report.only_in_db += 1
                if verbose:
                    logger.debug(f"  DB-ONLY: Title {title_num} § {section_num}")
            else:
                report.only_in_rp += 1
                if verbose:
                    logger.debug(f"  RP-ONLY: Title {title_num} § {section_num}")

    def _texts_match(self, text_a: str, text_b: str) -> bool:
        """Compare two section texts, normalizing whitespace."""
        return _normalize_for_comparison(text_a) == _normalize_for_comparison(text_b)

    def _describe_diff(self, db_text: str, rp_text: str) -> str:
        """Generate a brief description of text differences."""
        norm_db = _normalize_for_comparison(db_text)
        norm_rp = _normalize_for_comparison(rp_text)

        if len(norm_db) != len(norm_rp):
            return (
                f"Length differs: DB={len(norm_db)}, RP={len(norm_rp)} "
                f"(delta={len(norm_rp) - len(norm_db)})"
            )

        # Find first difference position
        for i, (a, b) in enumerate(zip(norm_db, norm_rp, strict=False)):
            if a != b:
                context_start = max(0, i - 20)
                context_end = min(len(norm_db), i + 20)
                return (
                    f"First diff at char {i}: "
                    f"DB='...{norm_db[context_start:context_end]}...' vs "
                    f"RP='...{norm_rp[context_start:context_end]}...'"
                )

        return "Unknown difference"


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison — collapse whitespace, strip."""
    import re

    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass
class CrossRefResult:
    """Result of cross-referencing generated changes against OLRC notes.

    Attributes:
        congress: Congress number.
        law_number: Law number.
        sections_in_notes: Sections that OLRC notes say this law amended.
        sections_in_changes: Sections we generated LawChange records for.
        matched: Sections in both notes and changes.
        only_in_notes: Sections in notes but NOT in our changes (parser missed).
        only_in_changes: Sections in changes but NOT in notes (possible FP).
    """

    congress: int
    law_number: int
    sections_in_notes: list[tuple[int, str]] = field(default_factory=list)
    sections_in_changes: list[tuple[int, str]] = field(default_factory=list)
    matched: list[tuple[int, str]] = field(default_factory=list)
    only_in_notes: list[tuple[int, str]] = field(default_factory=list)
    only_in_changes: list[tuple[int, str]] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Fraction of our changes that are confirmed by notes."""
        if not self.sections_in_changes:
            return 0.0
        return len(self.matched) / len(self.sections_in_changes)

    @property
    def recall(self) -> float:
        """Fraction of notes-referenced sections we also found."""
        if not self.sections_in_notes:
            return 0.0
        return len(self.matched) / len(self.sections_in_notes)


class AmendmentCrossReferencer:
    """Cross-reference generated LawChange records against OLRC amendment notes.

    OLRC notes in each section contain an "Amendments" header listing which
    Public Laws amended that section. This provides a second source of truth
    to validate our parsed changes.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_sections_amended_by_law(
        self,
        _congress: int,
        law_number: int,
    ) -> list[tuple[int, str]]:
        """Find sections whose OLRC notes reference a specific law.

        Queries sections whose normalized_notes.amendments contain references
        to the given Public Law.

        Args:
            _congress: Congress number (reserved for future filtering).
            law_number: Law number.

        Returns:
            List of (title_number, section_number) tuples.
        """

        # Query sections whose normalized_notes JSONB contains amendment
        # references to this law (e.g., "Pub. L. 113-22")
        pl_pattern = f"%-{law_number}%"

        result = await self.session.execute(
            select(
                USCodeSection.title_number,
                USCodeSection.section_number,
            ).where(
                USCodeSection.normalized_notes.isnot(None),
                USCodeSection.normalized_notes["amendments"].astext.like(pl_pattern),
            )
        )

        return [(row[0], row[1]) for row in result.all()]

    async def cross_reference(
        self,
        congress: int,
        law_number: int,
        generated_changes: list,
    ) -> CrossRefResult:
        """Cross-reference generated LawChange records against OLRC notes.

        Args:
            congress: Congress number.
            law_number: Law number.
            generated_changes: List of LawChange records (or DiffResult objects).

        Returns:
            CrossRefResult with precision/recall analysis.
        """
        result = CrossRefResult(
            congress=congress,
            law_number=law_number,
        )

        # Get sections from OLRC notes
        result.sections_in_notes = await self.find_sections_amended_by_law(
            congress, law_number
        )

        # Get sections from our generated changes
        for change in generated_changes:
            if hasattr(change, "resolution") and change.resolution.section:
                section = change.resolution.section
                result.sections_in_changes.append(
                    (section.title_number, section.section_number)
                )
            elif hasattr(change, "section") and change.section:
                result.sections_in_changes.append(
                    (change.section.title_number, change.section.section_number)
                )

        # Compare
        notes_set = set(result.sections_in_notes)
        changes_set = set(result.sections_in_changes)

        result.matched = sorted(notes_set & changes_set)
        result.only_in_notes = sorted(notes_set - changes_set)
        result.only_in_changes = sorted(changes_set - notes_set)

        logger.info(
            f"Cross-ref PL {congress}-{law_number}: "
            f"precision={result.precision:.1%}, "
            f"recall={result.recall:.1%}, "
            f"matched={len(result.matched)}, "
            f"only-in-notes={len(result.only_in_notes)}, "
            f"only-in-changes={len(result.only_in_changes)}"
        )

        return result
