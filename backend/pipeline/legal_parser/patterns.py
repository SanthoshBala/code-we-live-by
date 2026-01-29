"""Amendment pattern definitions for legal language parsing.

This module defines regex patterns for common legal language constructs
used in Public Laws to amend the US Code.

Pattern Categories:
- Strike and Insert: Replace specific text
- Add at End: Append new content
- Insert After: Add new subsection
- Repeal: Remove entire section
- Redesignate: Renumber sections/subsections
- Substitute: Replace entire section text
"""

import enum
import re
from dataclasses import dataclass


class PatternType(str, enum.Enum):
    """Type of amendment pattern detected."""

    STRIKE_INSERT = "strike_insert"
    STRIKE = "strike"
    INSERT_NEW_TEXT = "insert_new_text"
    ADD_AT_END = "add_at_end"
    INSERT_AFTER = "insert_after"
    INSERT_BEFORE = "insert_before"
    REPEAL = "repeal"
    REDESIGNATE = "redesignate"
    SUBSTITUTE = "substitute"
    TRANSFER = "transfer"
    AMEND_GENERAL = "amend_general"
    ADD_SECTION = "add_section"
    ADD_SUBSECTION = "add_subsection"


@dataclass
class AmendmentPattern:
    """Definition of an amendment pattern with its regex and metadata."""

    name: str
    pattern_type: PatternType
    regex: str
    confidence: float
    description: str

    def compile(self) -> re.Pattern:
        """Compile the regex pattern with multiline and case-insensitive flags."""
        return re.compile(self.regex, re.IGNORECASE | re.MULTILINE | re.DOTALL)


# Section reference pattern components
# Matches "Section 106", "section 106A", "Section 106(a)(1)(A)"
SECTION_REF = r"[Ss]ection\s+(\d+[A-Za-z]?)(?:\s*\(([^)]+)\))*"
SECTION_REF_WITH_TITLE = (
    r"[Ss]ection\s+(\d+[A-Za-z]?)(?:\s*\(([^)]+)\))*"
    r"(?:\s+of\s+[Tt]itle\s+(\d+)(?:,?\s+United\s+States\s+Code)?)?"
)

# Subsection path pattern (e.g., "(a)(1)(A)(i)")
SUBSECTION_PATH = r"(?:\s*\([a-zA-Z0-9]+\))+"

# Text in quotes - handles both single and double quotes
QUOTED_TEXT = r'["\']([^"\']+)["\']'

# Comprehensive amendment patterns
AMENDMENT_PATTERNS: list[AmendmentPattern] = [
    # ============================================================
    # STRIKE AND INSERT PATTERNS
    # ============================================================
    AmendmentPattern(
        name="strike_insert_quoted",
        pattern_type=PatternType.STRIKE_INSERT,
        regex=(
            r"(?:by\s+)?striking(?:\s+out)?\s+" + QUOTED_TEXT + r"\s+"
            r"and\s+inserting(?:\s+in\s+lieu\s+thereof)?\s+" + QUOTED_TEXT
        ),
        confidence=0.95,
        description='Striking "X" and inserting "Y" (including older "striking out" / "in lieu thereof")',
    ),
    AmendmentPattern(
        name="strike_insert_each_place",
        pattern_type=PatternType.STRIKE_INSERT,
        regex=(
            r"(?:by\s+)?striking\s+"
            + QUOTED_TEXT
            + r"\s+each\s+place\s+(?:such\s+term\s+|it\s+)?appears?"
            + r"(?:\s+and\s+inserting\s+"
            + QUOTED_TEXT
            + r")?"
        ),
        confidence=0.95,
        description='Striking "X" each place it appears and inserting "Y"',
    ),
    AmendmentPattern(
        name="strike_insert_phrase",
        pattern_type=PatternType.STRIKE_INSERT,
        regex=(
            r"(?:by\s+)?striking\s+(?:the\s+)?(?:phrase|words?|term)\s+"
            + QUOTED_TEXT
            + r"\s+and\s+inserting\s+"
            + QUOTED_TEXT
        ),
        confidence=0.95,
        description='Striking the phrase "X" and inserting "Y"',
    ),
    AmendmentPattern(
        name="strike_insert_everything_before",
        pattern_type=PatternType.STRIKE_INSERT,
        regex=(
            r"(?:by\s+)?striking\s+(?:everything|all\s+that\s+follows?)\s+"
            r"(?:before|preceding|through)\s+" + QUOTED_TEXT + r"\s+and\s+inserting"
        ),
        confidence=0.90,
        description="Striking everything before X and inserting",
    ),
    AmendmentPattern(
        name="strike_insert_everything_after",
        pattern_type=PatternType.STRIKE_INSERT,
        regex=(
            r"(?:by\s+)?striking\s+(?:everything|all\s+that\s+follows?)\s+"
            r"(?:after|following)\s+" + QUOTED_TEXT + r"\s+and\s+inserting"
        ),
        confidence=0.90,
        description="Striking everything after X and inserting",
    ),
    # ============================================================
    # STRIKE-ONLY PATTERNS
    # ============================================================
    AmendmentPattern(
        name="strike_quoted",
        pattern_type=PatternType.STRIKE,
        regex=(
            r"(?:by\s+)?striking(?:\s+out)?\s+"
            + QUOTED_TEXT
            + r"(?!\s+(?:and\s+inserting|each\s+place))"
        ),
        confidence=0.90,
        description='Striking "X" (without insertion)',
    ),
    AmendmentPattern(
        name="strike_through_period",
        pattern_type=PatternType.STRIKE,
        regex=(
            r"(?:by\s+)?striking\s+"
            + QUOTED_TEXT
            + r"\s+and\s+all\s+that\s+follows\s+through\s+"
            r"(?:the\s+period|the\s+semicolon|" + QUOTED_TEXT + r")"
        ),
        confidence=0.93,
        description='Striking "X" and all that follows through the period',
    ),
    AmendmentPattern(
        name="strike_paragraph",
        pattern_type=PatternType.STRIKE,
        regex=(
            r"(?:by\s+)?striking\s+(?:paragraph|subparagraph|clause|"
            r"subsection|subdivision)\s+\(([a-zA-Z0-9]+)\)"
        ),
        confidence=0.90,
        description="Striking paragraph (X)",
    ),
    AmendmentPattern(
        name="strike_and_following",
        pattern_type=PatternType.STRIKE,
        regex=(
            r"(?:by\s+)?striking\s+"
            + QUOTED_TEXT
            + r"\s+and\s+(?:all\s+that|everything\s+that)\s+follows"
        ),
        confidence=0.85,
        description='Striking "X" and all that follows',
    ),
    # ============================================================
    # ADD/INSERT PATTERNS
    # ============================================================
    AmendmentPattern(
        name="add_at_end",
        pattern_type=PatternType.ADD_AT_END,
        regex=(
            r"(?:by\s+)?(?:adding|inserting)\s+(?:at\s+the\s+end)"
            r"(?:\s+(?:of\s+)?(?:thereof|the\s+(?:section|subsection|paragraph)))?"
            r"\s+the\s+following"
        ),
        confidence=0.95,
        description="Adding at the end the following",
    ),
    AmendmentPattern(
        name="add_after_paragraph",
        pattern_type=PatternType.INSERT_AFTER,
        regex=(
            r"(?:by\s+)?(?:adding|inserting)\s+after\s+"
            r"(?:paragraph|subparagraph|clause|subsection)\s+"
            r"\(([a-zA-Z0-9]+)\)\s+the\s+following"
        ),
        confidence=0.95,
        description="Adding after paragraph (X) the following",
    ),
    AmendmentPattern(
        name="insert_after_section",
        pattern_type=PatternType.INSERT_AFTER,
        regex=(
            r"(?:by\s+)?inserting\s+after\s+"
            r"[Ss]ection\s+(\d+[A-Za-z]?)\s+the\s+following(?:\s+new\s+section)?"
        ),
        confidence=0.95,
        description="Inserting after section X the following new section",
    ),
    AmendmentPattern(
        name="insert_before",
        pattern_type=PatternType.INSERT_BEFORE,
        regex=(
            r"(?:by\s+)?inserting\s+before\s+" + QUOTED_TEXT + r"\s+the\s+following"
        ),
        confidence=0.90,
        description='Inserting before "X" the following',
    ),
    AmendmentPattern(
        name="insert_before_paragraph",
        pattern_type=PatternType.INSERT_BEFORE,
        regex=(
            r"(?:by\s+)?inserting\s+before\s+"
            r"(?:paragraph|subparagraph|clause|subsection)\s+"
            r"\(([a-zA-Z0-9]+)\)\s+the\s+following"
        ),
        confidence=0.95,
        description="Inserting before paragraph (X) the following",
    ),
    AmendmentPattern(
        name="add_new_subsection",
        pattern_type=PatternType.ADD_SUBSECTION,
        regex=(
            r"(?:by\s+)?(?:adding|inserting)\s+(?:a\s+)?new\s+"
            r"(?:subsection|paragraph|subparagraph|clause)\s+"
            r"(?:\(([a-zA-Z0-9]+)\)\s+)?(?:to\s+read\s+as\s+follows|as\s+follows)"
        ),
        confidence=0.90,
        description="Adding a new subsection to read as follows",
    ),
    # ============================================================
    # REPEAL PATTERNS
    # ============================================================
    AmendmentPattern(
        name="section_repealed",
        pattern_type=PatternType.REPEAL,
        regex=SECTION_REF + r"\s+(?:is|are)\s+(?:hereby\s+)?repealed",
        confidence=0.98,
        description="Section X is hereby repealed",
    ),
    AmendmentPattern(
        name="paragraph_repealed",
        pattern_type=PatternType.REPEAL,
        regex=(
            r"(?:paragraph|subparagraph|clause|subsection)\s+"
            r"\(([a-zA-Z0-9]+)\)\s+(?:is|are)\s+(?:hereby\s+)?(?:repealed|stricken)"
        ),
        confidence=0.95,
        description="Paragraph (X) is repealed",
    ),
    AmendmentPattern(
        name="striking_section",
        pattern_type=PatternType.REPEAL,
        regex=r"(?:by\s+)?striking\s+" + SECTION_REF,
        confidence=0.90,
        description="Striking section X",
    ),
    # ============================================================
    # REDESIGNATE PATTERNS
    # ============================================================
    AmendmentPattern(
        name="redesignate_section",
        pattern_type=PatternType.REDESIGNATE,
        regex=(
            r"(?:by\s+)?redesignating\s+"
            r"[Ss]ection\s+(\d+[A-Za-z]?)\s+"
            r"as\s+[Ss]ection\s+(\d+[A-Za-z]?)"
        ),
        confidence=0.98,
        description="Redesignating section X as section Y",
    ),
    AmendmentPattern(
        name="redesignate_paragraph",
        pattern_type=PatternType.REDESIGNATE,
        regex=(
            r"(?:by\s+)?redesignating\s+"
            r"(?:paragraphs?|subparagraphs?|clauses?|subsections?)\s+"
            r"\(([a-zA-Z0-9]+)\)(?:\s*(?:and|through|,)\s*\(([a-zA-Z0-9]+)\))*\s+"
            r"as\s+"
            r"(?:paragraphs?|subparagraphs?|clauses?|subsections?)\s+"
            r"\(([a-zA-Z0-9]+)\)(?:\s*(?:and|through|,)\s*\(([a-zA-Z0-9]+)\))*"
        ),
        confidence=0.95,
        description="Redesignating paragraphs (X) through (Y) as (A) through (B)",
    ),
    # ============================================================
    # SUBSTITUTE PATTERNS
    # ============================================================
    AmendmentPattern(
        name="substitute_section",
        pattern_type=PatternType.SUBSTITUTE,
        regex=(
            SECTION_REF_WITH_TITLE + r",?\s+(?:is|are)\s+(?:hereby\s+)?(?:amended\s+)?"
            r"(?:to\s+read|and\s+reenacted\s+to\s+read)\s+as\s+follows"
        ),
        confidence=0.95,
        description="Section X is amended to read as follows",
    ),
    AmendmentPattern(
        name="substitute_subsection",
        pattern_type=PatternType.SUBSTITUTE,
        regex=(
            r"(?:subsection|paragraph|subparagraph|clause)\s+"
            r"\(([a-zA-Z0-9]+)\)\s+"
            r"(?:is|are)\s+(?:hereby\s+)?(?:amended\s+)?"
            r"to\s+read\s+as\s+follows"
        ),
        confidence=0.95,
        description="Subsection (X) is amended to read as follows",
    ),
    # ============================================================
    # TRANSFER PATTERNS
    # ============================================================
    AmendmentPattern(
        name="transfer_section",
        pattern_type=PatternType.TRANSFER,
        regex=(
            SECTION_REF
            + r"\s+(?:is|are)\s+(?:hereby\s+)?transferred\s+to\s+"
            + SECTION_REF
        ),
        confidence=0.90,
        description="Section X is transferred to section Y",
    ),
    # ============================================================
    # GENERAL AMENDMENT PATTERNS
    # ============================================================
    AmendmentPattern(
        name="section_amended_general",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=SECTION_REF_WITH_TITLE + r",?\s+(?:is|are)\s+(?:hereby\s+)?amended",
        confidence=0.85,
        description="Section X of title Y is amended",
    ),
    AmendmentPattern(
        name="section_amended_by",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=(
            SECTION_REF_WITH_TITLE + r",?\s+(?:is|are)\s+(?:hereby\s+)?amended\s+by"
        ),
        confidence=0.90,
        description="Section X is amended by",
    ),
    AmendmentPattern(
        name="subsection_amended",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=(
            r"(?:subsection|paragraph|subparagraph|clause)\s+"
            r"\(([a-zA-Z0-9]+)\)(?:" + SUBSECTION_PATH + r")?\s+"
            r"(?:of\s+(?:such\s+)?[Ss]ection(?:\s+(\d+[A-Za-z]?))?)?\s*"
            r"(?:is|are)\s+(?:hereby\s+)?amended"
        ),
        confidence=0.85,
        description="Subsection (X) is amended",
    ),
    AmendmentPattern(
        name="title_amended",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=(
            r"[Tt]itle\s+(\d+)(?:,?\s+United\s+States\s+Code)?,?\s+"
            r"(?:is|are)\s+(?:hereby\s+)?amended"
        ),
        confidence=0.80,
        description="Title X, United States Code, is amended",
    ),
    # ============================================================
    # ADD NEW SECTION PATTERNS
    # ============================================================
    AmendmentPattern(
        name="add_new_section",
        pattern_type=PatternType.ADD_SECTION,
        regex=(
            r"[Tt]itle\s+(\d+)(?:,?\s+United\s+States\s+Code)?,?\s+"
            r"(?:is|are)\s+(?:hereby\s+)?amended\s+by\s+"
            r"(?:adding|inserting)\s+(?:at\s+the\s+end\s+)?"
            r"(?:a\s+)?(?:new\s+)?[Ss]ection\s+(\d+[A-Za-z]?)"
        ),
        confidence=0.90,
        description="Title X is amended by adding new section Y",
    ),
    AmendmentPattern(
        name="chapter_amended_add_section",
        pattern_type=PatternType.ADD_SECTION,
        regex=(
            r"[Cc]hapter\s+(\d+)\s+of\s+[Tt]itle\s+(\d+)(?:,?\s+United\s+States\s+Code)?,?\s+"
            r"(?:is|are)\s+(?:hereby\s+)?amended\s+by\s+"
            r"(?:adding|inserting)\s+(?:at\s+the\s+end\s+)?"
            r"the\s+following(?:\s+new\s+section)?"
        ),
        confidence=0.90,
        description="Chapter X of title Y is amended by adding the following new section",
    ),
]


def get_patterns_by_type(pattern_type: PatternType) -> list[AmendmentPattern]:
    """Get all patterns of a specific type."""
    return [p for p in AMENDMENT_PATTERNS if p.pattern_type == pattern_type]


def get_high_confidence_patterns(threshold: float = 0.90) -> list[AmendmentPattern]:
    """Get patterns with confidence above threshold."""
    return [p for p in AMENDMENT_PATTERNS if p.confidence >= threshold]
