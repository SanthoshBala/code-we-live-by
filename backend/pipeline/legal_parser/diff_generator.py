"""Diff generator — create LawChange records from parsed amendments.

This module converts ParsedAmendment + ResolutionResult + ExtractedText into
validated LawChange records, implementing the core of the version control model.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ChangeType
from app.models.public_law import LawChange, PublicLaw
from pipeline.legal_parser.amendment_parser import ParsedAmendment
from pipeline.legal_parser.patterns import PatternType
from pipeline.legal_parser.section_resolver import ResolutionResult
from pipeline.legal_parser.text_extractor import ExtractedText

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Result of generating a diff for a single amendment.

    Attributes:
        amendment: The source ParsedAmendment.
        resolution: The section resolution result.
        change_type: The type of change.
        old_text: Text being replaced/removed (if applicable).
        new_text: Text being added/inserted (if applicable).
        subsection_path: Path to the specific subsection being changed.
        description: Human-readable description of the change.
        validated: Whether the diff was validated against section content.
        validation_notes: Notes about validation results.
        confidence: Confidence in the diff correctness.
    """

    amendment: ParsedAmendment
    resolution: ResolutionResult
    change_type: ChangeType
    old_text: str | None = None
    new_text: str | None = None
    subsection_path: str | None = None
    description: str | None = None
    validated: bool = False
    validation_notes: str | None = None
    confidence: float = 0.0


@dataclass
class DiffReport:
    """Summary report of diff generation for a law.

    Attributes:
        total_amendments: Total amendments processed.
        diffs_generated: Number of successful diffs.
        diffs_skipped: Number of amendments skipped.
        unresolved: Number of amendments with unresolved section refs.
        validation_failures: Number of diffs that failed validation.
        by_type: Count of diffs by ChangeType.
        errors: List of error descriptions.
    """

    total_amendments: int = 0
    diffs_generated: int = 0
    diffs_skipped: int = 0
    unresolved: int = 0
    validation_failures: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class DiffGenerator:
    """Generate LawChange records from parsed amendments.

    This class implements the core diff logic, converting parser output into
    structured change records that can be stored in the database.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_diffs(
        self,
        amendments: list[ParsedAmendment],
        resolutions: list[ResolutionResult],
        extractions: dict[int, ExtractedText],
        law: PublicLaw,
    ) -> tuple[list[DiffResult], DiffReport]:
        """Generate diffs from parsed amendments.

        Args:
            amendments: Parsed amendments from the law text.
            resolutions: Resolution results (same length as amendments).
            extractions: Map of amendment index -> extracted text.
            law: The PublicLaw record this diff is for.

        Returns:
            Tuple of (list of DiffResult, DiffReport summary).
        """
        report = DiffReport(total_amendments=len(amendments))
        diffs: list[DiffResult] = []

        for i, (amendment, resolution) in enumerate(
            zip(amendments, resolutions, strict=False)
        ):
            extraction = extractions.get(i)

            if not resolution.resolved:
                report.unresolved += 1
                report.errors.append(f"Amendment {i}: {resolution.error}")
                continue

            diff = self._generate_single_diff(amendment, resolution, extraction, law)

            if diff:
                # Validate against current section content
                self._validate_diff(diff)

                diffs.append(diff)
                report.diffs_generated += 1

                type_name = diff.change_type.value
                report.by_type[type_name] = report.by_type.get(type_name, 0) + 1

                if not diff.validated:
                    report.validation_failures += 1
            else:
                report.diffs_skipped += 1

        return diffs, report

    def _generate_single_diff(
        self,
        amendment: ParsedAmendment,
        resolution: ResolutionResult,
        extraction: ExtractedText | None,
        _law: PublicLaw,
    ) -> DiffResult | None:
        """Generate a diff for a single amendment.

        Returns:
            DiffResult or None if the amendment can't produce a meaningful diff.
        """
        change_type = amendment.change_type
        old_text = amendment.old_text
        new_text = amendment.new_text
        subsection_path = (
            amendment.section_ref.subsection_path if amendment.section_ref else None
        )

        # Dispatch based on pattern type
        if amendment.pattern_type == PatternType.STRIKE_INSERT:
            # Both old and new text should come from the parser
            if not old_text:
                return None
            description = f"Strike '{_truncate(old_text)}'"
            if new_text:
                description += f" and insert '{_truncate(new_text)}'"

        elif amendment.pattern_type == PatternType.STRIKE:
            if not old_text:
                return None
            description = f"Strike '{_truncate(old_text)}'"

        elif amendment.pattern_type in (
            PatternType.ADD_AT_END,
            PatternType.INSERT_AFTER,
            PatternType.INSERT_BEFORE,
            PatternType.ADD_SECTION,
            PatternType.ADD_SUBSECTION,
            PatternType.INSERT_NEW_TEXT,
        ):
            # New text from extraction
            if extraction:
                new_text = extraction.text
            if not new_text:
                return DiffResult(
                    amendment=amendment,
                    resolution=resolution,
                    change_type=change_type,
                    subsection_path=subsection_path,
                    description="Text extraction needed (not yet available)",
                    confidence=0.3,
                )
            description = f"Add '{_truncate(new_text)}'"

        elif amendment.pattern_type == PatternType.REPEAL:
            # Old text is the entire section/subsection content
            section = resolution.section
            if section and section.text_content:
                old_text = section.text_content
            description = "Repeal section"

        elif amendment.pattern_type == PatternType.SUBSTITUTE:
            # Old text from section, new text from extraction
            if extraction:
                new_text = extraction.text
            description = "Substitute text"

        elif amendment.pattern_type in (
            PatternType.REDESIGNATE,
            PatternType.TRANSFER,
        ):
            # Structural changes — record descriptively
            description = amendment.full_match[:200]
            change_type = amendment.change_type

        elif amendment.pattern_type == PatternType.AMEND_GENERAL:
            # General amendment — needs manual review
            description = f"General amendment: {_truncate(amendment.full_match)}"

        else:
            description = f"Unknown pattern: {amendment.pattern_name}"

        return DiffResult(
            amendment=amendment,
            resolution=resolution,
            change_type=change_type,
            old_text=old_text,
            new_text=new_text,
            subsection_path=subsection_path,
            description=description,
            confidence=amendment.confidence,
        )

    def _validate_diff(self, diff: DiffResult) -> None:
        """Validate a diff against the current section content.

        Checks that old_text actually exists in the section for STRIKE/MODIFY ops.
        """
        section = diff.resolution.section
        if not section or not section.text_content:
            diff.validation_notes = "No section content available for validation"
            return

        content = section.text_content

        if diff.old_text and diff.change_type in (
            ChangeType.MODIFY,
            ChangeType.DELETE,
        ):
            if diff.old_text in content:
                diff.validated = True
                diff.validation_notes = "old_text found in section"
            else:
                # Try case-insensitive match
                if diff.old_text.lower() in content.lower():
                    diff.validated = True
                    diff.validation_notes = "old_text found (case-insensitive)"
                else:
                    diff.validation_notes = "old_text NOT found in section content"
        elif diff.change_type in (ChangeType.ADD, ChangeType.REPEAL):
            # ADD doesn't need old_text validation
            # REPEAL is validated by section existence
            diff.validated = True
            diff.validation_notes = "No old_text validation needed"
        else:
            # REDESIGNATE, TRANSFER — structural, can't validate against text
            diff.validated = True
            diff.validation_notes = "Structural change, no text validation"

    async def persist_law_changes(
        self,
        diffs: list[DiffResult],
        law: PublicLaw,
    ) -> list[LawChange]:
        """Create LawChange records from validated diffs.

        Args:
            diffs: List of validated diff results.
            law: The PublicLaw these changes belong to.

        Returns:
            List of created LawChange records.
        """
        changes: list[LawChange] = []

        for diff in diffs:
            if not diff.resolution.section:
                continue

            effective = law.effective_date or law.enacted_date

            change = LawChange(
                law_id=law.law_id,
                section_id=diff.resolution.section.section_id,
                change_type=diff.change_type,
                old_text=diff.old_text,
                new_text=diff.new_text,
                effective_date=effective,
                description=diff.description,
                subsection_path=diff.subsection_path,
            )
            self.session.add(change)
            changes.append(change)

        if changes:
            await self.session.flush()
            logger.info(f"Created {len(changes)} LawChange records for {law}")

        return changes


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text for display in descriptions."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
