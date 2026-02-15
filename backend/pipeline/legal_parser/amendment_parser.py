"""Parser for extracting amendments from Public Law text.

This module provides the main parser class for identifying and extracting
structured amendment information from the text of Public Laws.
"""

import contextlib
import enum
import logging
import re
from dataclasses import dataclass, field

from app.models.enums import ChangeType
from pipeline.legal_parser.patterns import (
    AMENDMENT_PATTERNS,
    AmendmentPattern,
    PatternType,
)

logger = logging.getLogger(__name__)


@dataclass
class SectionReference:
    """A reference to a US Code section or subsection.

    Attributes:
        title: US Code title number (e.g., 17 for Copyright).
        section: Section number/identifier (e.g., "106", "106A").
        subsection_path: Path to subsection at any depth (e.g., "(a)", "(a)(1)", "(a)(1)(A)").
    """

    title: int | None
    section: str
    subsection_path: str | None = None

    def __str__(self) -> str:
        """Return formatted section reference."""
        parts = []
        if self.title:
            parts.append(f"{self.title} U.S.C.")
        parts.append(f"§ {self.section}")
        if self.subsection_path:
            parts.append(self.subsection_path)
        return " ".join(parts)

    @classmethod
    def from_match(
        cls,
        section: str,
        title: int | None = None,
        subsection_path: str | None = None,
    ) -> "SectionReference":
        """Create a SectionReference from regex match groups."""
        return cls(
            title=title,
            section=section.strip(),
            subsection_path=subsection_path.strip() if subsection_path else None,
        )


class PositionType(enum.StrEnum):
    """Type of positional qualifier on an amendment."""

    AT_END = "at_end"
    BEFORE = "before"
    AFTER = "after"
    EACH_PLACE = "each_place"
    UNQUOTED_TARGET = "unquoted_target"


@dataclass
class PositionQualifier:
    """Positional context for an amendment.

    Captures where in a section the amendment applies, e.g.
    "at the end", "after 'prohibit'", "each place such term appears".

    Attributes:
        type: The kind of positional qualifier.
        anchor_text: For BEFORE/AFTER: the reference text.
        target_text: For UNQUOTED_TARGET: e.g. "the period".
    """

    type: PositionType
    anchor_text: str | None = None
    target_text: str | None = None


@dataclass
class ParsedAmendment:
    """A parsed amendment extracted from Public Law text.

    Attributes:
        pattern_name: Name of the pattern that matched.
        pattern_type: Type of amendment (strike_insert, repeal, etc.).
        change_type: Database ChangeType enum value.
        section_ref: Reference to the section being amended.
        old_text: Text being removed (if applicable).
        new_text: Text being added (if applicable).
        full_match: The full matched text from the law.
        confidence: Confidence score (0.0-1.0).
        start_pos: Start position in source text.
        end_pos: End position in source text.
        needs_review: Whether this amendment needs manual review.
        context: Surrounding text for context.
    """

    pattern_name: str
    pattern_type: PatternType
    change_type: ChangeType
    section_ref: SectionReference | None
    old_text: str | None = None
    new_text: str | None = None
    full_match: str = ""
    confidence: float = 0.0
    start_pos: int = 0
    end_pos: int = 0
    needs_review: bool = False
    context: str = ""
    position_qualifier: PositionQualifier | None = None
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """Return human-readable representation."""
        section_str = str(self.section_ref) if self.section_ref else "unknown section"
        return f"{self.change_type.value}: {section_str} ({self.pattern_name})"


def _pattern_type_to_change_type(pattern_type: PatternType) -> ChangeType:
    """Convert PatternType to database ChangeType enum."""
    mapping = {
        PatternType.STRIKE_INSERT: ChangeType.MODIFY,
        PatternType.STRIKE: ChangeType.DELETE,
        PatternType.INSERT_NEW_TEXT: ChangeType.ADD,
        PatternType.ADD_AT_END: ChangeType.ADD,
        PatternType.INSERT_AFTER: ChangeType.ADD,
        PatternType.INSERT_BEFORE: ChangeType.ADD,
        PatternType.REPEAL: ChangeType.REPEAL,
        PatternType.REDESIGNATE: ChangeType.REDESIGNATE,
        PatternType.SUBSTITUTE: ChangeType.MODIFY,
        PatternType.TRANSFER: ChangeType.TRANSFER,
        PatternType.AMEND_GENERAL: ChangeType.MODIFY,
        PatternType.ADD_SECTION: ChangeType.ADD,
        PatternType.ADD_SUBSECTION: ChangeType.ADD,
    }
    return mapping.get(pattern_type, ChangeType.MODIFY)


def _extract_subsection_path(text: str) -> str | None:
    """Extract subsection path from text like '(a)(1)(A)'."""
    # Match sequences of parenthesized identifiers
    pattern = r"(\([a-zA-Z0-9]+\)(?:\s*\([a-zA-Z0-9]+\))*)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).replace(" ", "")
    return None


def _parse_multiple_sections(text: str) -> list[str]:
    """Parse text containing multiple section references.

    Handles:
    - "Sections 106, 107, and 108"
    - "sections 106 and 107"
    - "sections 106 through 110"
    """
    sections = []

    # Pattern for "sections X, Y, and Z" or "sections X and Y"
    multi_pattern = r"[Ss]ections?\s+(\d+[A-Za-z]?)(?:\s*,\s*(\d+[A-Za-z]?))*(?:\s*(?:,\s*)?(?:and|&)\s*(\d+[A-Za-z]?))?"
    match = re.search(multi_pattern, text)

    if match:
        # Extract all captured groups
        for group in match.groups():
            if group:
                sections.append(group)

    # Also handle "through" ranges like "sections 106 through 110"
    range_pattern = r"[Ss]ections?\s+(\d+)\s+through\s+(\d+)"
    range_match = re.search(range_pattern, text)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        sections = [str(i) for i in range(start, end + 1)]

    return sections if sections else []


class AmendmentParser:
    """Parser for extracting amendments from Public Law text.

    This parser uses regex patterns to identify common legal language
    constructs that describe amendments to the US Code.

    Attributes:
        default_title: Default US Code title when not specified.
        patterns: List of amendment patterns to use.
    """

    def __init__(
        self,
        default_title: int | None = None,
        patterns: list[AmendmentPattern] | None = None,
        min_confidence: float = 0.0,
    ):
        """Initialize the parser.

        Args:
            default_title: Default US Code title when not specified in text.
            patterns: Custom patterns to use (defaults to AMENDMENT_PATTERNS).
            min_confidence: Minimum confidence threshold for results.
        """
        self.default_title = default_title
        self.patterns = patterns or AMENDMENT_PATTERNS
        self.min_confidence = min_confidence
        self._compiled_patterns: dict[str, re.Pattern] = {}

        # Pre-compile all patterns
        for pattern in self.patterns:
            self._compiled_patterns[pattern.name] = pattern.compile()

    def parse(self, text: str, context_chars: int = 100) -> list[ParsedAmendment]:
        """Parse text and extract all amendments.

        Args:
            text: The Public Law text to parse.
            context_chars: Number of characters of context to include.

        Returns:
            List of parsed amendments found in the text.
        """
        amendments: list[ParsedAmendment] = []

        for pattern in self.patterns:
            if pattern.confidence < self.min_confidence:
                continue

            compiled = self._compiled_patterns[pattern.name]

            for match in compiled.finditer(text):
                amendment = self._process_match(match, pattern, text, context_chars)
                if amendment:
                    amendments.append(amendment)

        # Sort by position in text
        amendments.sort(key=lambda a: a.start_pos)

        # Deduplicate overlapping matches (prefer higher confidence)
        amendments = self._deduplicate(amendments)

        return amendments

    def parse_section_reference(self, text: str) -> SectionReference | None:
        """Parse a section reference from text.

        Args:
            text: Text containing a section reference.

        Returns:
            SectionReference or None if not found.
        """
        # Pattern for section with optional title and subsection
        pattern = (
            r"[Ss]ection\s+(\d+[A-Za-z]?)"
            r"((?:\s*\([a-zA-Z0-9]+\))+)?"
            r"(?:\s+of\s+[Tt]itle\s+(\d+))?"
        )

        match = re.search(pattern, text)
        if match:
            section = match.group(1)
            subsection = match.group(2)
            title = int(match.group(3)) if match.group(3) else self.default_title

            return SectionReference(
                title=title,
                section=section,
                subsection_path=subsection.strip() if subsection else None,
            )

        return None

    def _process_match(
        self,
        match: re.Match,
        pattern: AmendmentPattern,
        text: str,
        context_chars: int,
    ) -> ParsedAmendment | None:
        """Process a regex match into a ParsedAmendment."""
        full_match = match.group(0)
        start_pos = match.start()
        end_pos = match.end()

        # Extract section reference from the match
        section_ref = self._extract_section_ref(match, pattern, text)

        # Extract old/new text based on pattern type
        old_text, new_text = self._extract_text_changes(match, pattern)

        # Determine if manual review is needed
        needs_review = self._needs_review(pattern, section_ref, old_text, new_text)

        # Calculate adjusted confidence
        confidence = self._calculate_confidence(
            pattern, section_ref, old_text, new_text
        )

        # Extract context
        context_start = max(0, start_pos - context_chars)
        context_end = min(len(text), end_pos + context_chars)
        context = text[context_start:context_end]

        return ParsedAmendment(
            pattern_name=pattern.name,
            pattern_type=pattern.pattern_type,
            change_type=_pattern_type_to_change_type(pattern.pattern_type),
            section_ref=section_ref,
            old_text=old_text,
            new_text=new_text,
            full_match=full_match,
            confidence=confidence,
            start_pos=start_pos,
            end_pos=end_pos,
            needs_review=needs_review,
            context=context,
        )

    def _extract_section_ref(
        self,
        match: re.Match,
        pattern: AmendmentPattern,  # noqa: ARG002 - may be used in future
        text: str,
    ) -> SectionReference | None:
        """Extract section reference from match based on pattern type."""
        # Try to find section number in the captured groups
        groups = match.groups()

        # Look for section number in groups (usually first numeric group)
        section = None
        title = self.default_title
        subsection = None

        for _i, group in enumerate(groups):
            if group is None:
                continue

            # Check if this looks like a section number
            if re.match(r"^\d+[A-Za-z]?$", group):
                if section is None:
                    section = group
                elif title is None or title == self.default_title:
                    # Could be title number
                    with contextlib.suppress(ValueError):
                        title = int(group)

            # Check if this looks like a subsection path
            elif re.match(r"^[a-zA-Z0-9]+$", group) and subsection is None:
                subsection = f"({group})"

        # If no section found in groups, try parsing the full match
        if section is None:
            parsed = self.parse_section_reference(match.group(0))
            if parsed:
                return parsed

            # Try finding in surrounding context
            context_start = max(0, match.start() - 200)
            context_end = match.start()
            context = text[context_start:context_end]
            parsed = self.parse_section_reference(context)
            if parsed:
                return parsed

        if section:
            return SectionReference(
                title=title,
                section=section,
                subsection_path=subsection,
            )

        return None

    def _extract_text_changes(
        self,
        match: re.Match,
        pattern: AmendmentPattern,
    ) -> tuple[str | None, str | None]:
        """Extract old and new text from match based on pattern type."""
        groups = match.groups()
        old_text = None
        new_text = None

        if pattern.pattern_type == PatternType.STRIKE_INSERT:
            # Typically groups are: (old_text, new_text)
            # Find quoted text groups
            quoted = [g for g in groups if g and not re.match(r"^\d+[A-Za-z]?$", g)]
            if len(quoted) >= 2:
                old_text = quoted[0]
                new_text = quoted[1]
            elif len(quoted) == 1:
                old_text = quoted[0]

        elif pattern.pattern_type == PatternType.STRIKE:
            # Only old text
            quoted = [g for g in groups if g and not re.match(r"^\d+[A-Za-z]?$", g)]
            if quoted:
                old_text = quoted[0]

        # For other patterns, text extraction requires looking ahead in the document
        # which is handled separately during ingestion

        return old_text, new_text

    def _needs_review(
        self,
        pattern: AmendmentPattern,
        section_ref: SectionReference | None,
        old_text: str | None,  # noqa: ARG002 - reserved for future use
        new_text: str | None,  # noqa: ARG002 - reserved for future use
    ) -> bool:
        """Determine if this amendment needs manual review."""
        # No section reference = definitely needs review
        if section_ref is None:
            return True

        # Low confidence patterns need review
        if pattern.confidence < 0.85:
            return True

        # Certain pattern types always need review for text extraction
        if pattern.pattern_type in (
            PatternType.ADD_AT_END,
            PatternType.INSERT_AFTER,
            PatternType.INSERT_BEFORE,
            PatternType.SUBSTITUTE,
            PatternType.ADD_SECTION,
            PatternType.ADD_SUBSECTION,
        ):
            # These patterns need to extract text from following content
            return True

        # General amendment patterns need review
        return pattern.pattern_type == PatternType.AMEND_GENERAL

    def _calculate_confidence(
        self,
        pattern: AmendmentPattern,
        section_ref: SectionReference | None,
        old_text: str | None,
        new_text: str | None,
    ) -> float:
        """Calculate adjusted confidence score."""
        base_confidence = pattern.confidence

        # Reduce confidence if no section reference
        if section_ref is None:
            base_confidence *= 0.5

        # Reduce confidence if no title specified
        elif section_ref.title is None:
            base_confidence *= 0.9

        # Boost confidence if we have both old and new text for strike/insert
        if pattern.pattern_type == PatternType.STRIKE_INSERT:
            if old_text and new_text:
                base_confidence = min(1.0, base_confidence * 1.05)
            elif not old_text and not new_text:
                base_confidence *= 0.7

        return base_confidence

    def _deduplicate(self, amendments: list[ParsedAmendment]) -> list[ParsedAmendment]:
        """Remove overlapping amendments, keeping higher confidence ones."""
        if len(amendments) <= 1:
            return amendments

        result: list[ParsedAmendment] = []

        for amendment in amendments:
            # Check if this overlaps with any existing amendment
            overlaps = False
            for i, existing in enumerate(result):
                if self._overlaps(amendment, existing):
                    overlaps = True
                    # Keep the higher confidence one
                    if amendment.confidence > existing.confidence:
                        result[i] = amendment
                    break

            if not overlaps:
                result.append(amendment)

        return result

    def _overlaps(self, a: ParsedAmendment, b: ParsedAmendment) -> bool:
        """Check if two amendments overlap in the source text."""
        return not (a.end_pos <= b.start_pos or b.end_pos <= a.start_pos)

    def get_statistics(
        self, amendments: list[ParsedAmendment]
    ) -> dict[str, int | float]:
        """Get statistics about parsed amendments.

        Args:
            amendments: List of parsed amendments.

        Returns:
            Dictionary with statistics.
        """
        if not amendments:
            return {
                "total": 0,
                "needs_review": 0,
                "high_confidence": 0,
                "avg_confidence": 0.0,
            }

        needs_review = sum(1 for a in amendments if a.needs_review)
        high_confidence = sum(1 for a in amendments if a.confidence >= 0.90)
        avg_confidence = sum(a.confidence for a in amendments) / len(amendments)

        by_type: dict[str, int] = {}
        for amendment in amendments:
            type_name = amendment.change_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total": len(amendments),
            "needs_review": needs_review,
            "high_confidence": high_confidence,
            "avg_confidence": round(avg_confidence, 3),
            "by_change_type": by_type,
        }
