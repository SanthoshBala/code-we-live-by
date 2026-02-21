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

Each pattern includes real-world examples from actual Public Laws to
document the variety of legislative drafting styles across different
Congressional eras and US Code titles.
"""

import enum
import re
from dataclasses import dataclass


class PatternType(enum.StrEnum):
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
    ADD_NOTE = "add_note"


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

# Text in quotes - handles standard quotes and GovInfo backtick-style (``text'')
QUOTED_TEXT = r'(?:``|["\'])([^"\']+?)(?:\'\'|["\'])'

# Comprehensive amendment patterns
AMENDMENT_PATTERNS: list[AmendmentPattern] = [
    # ============================================================
    # STRIKE AND INSERT PATTERNS
    # ============================================================
    #
    # Real-world examples:
    # 1. PL 105-80 (1997): by striking "120 days" and inserting "180 days"
    # 2. PL 104-272 (1996): by striking out "ten days" and inserting in lieu
    #    thereof "twenty days"
    # 3. PL 110-85 (2007): by striking "$392,783,000" and inserting
    #    "$409,510,000"
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
    # Real-world examples:
    # 1. PL 110-85 (2007): by striking "(c)(4)" each place such term appears
    #    and inserting "(c)(5)"
    # 2. PL 111-148 (2010): by striking "Secretary" each place it appears and
    #    inserting "Administrator"
    # 3. PL 104-193 (1996): by striking "AFDC" each place such term appears
    #    and inserting "TANF"
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
    # Real-world examples:
    # 1. PL 100-647 (1988): by striking the phrase "any tax year" and inserting
    #    "the taxable year"
    # 2. PL 109-280 (2006): by striking the term "plan year" and inserting
    #    "limitation year"
    # 3. PL 105-34 (1997): by striking the word "taxable" and inserting
    #    "calendar"
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
    # Real-world examples:
    # 1. PL 106-554 (2000): by striking everything before "the term" and
    #    inserting "For purposes of this section,"
    # 2. PL 108-357 (2004): by striking all that precedes "shall not apply"
    #    and inserting "Subparagraph (A)"
    # 3. PL 110-234 (2008): by striking everything through "except that" and
    #    inserting "Subject to paragraph (2),"
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
    # Real-world examples:
    # 1. PL 109-432 (2006): by striking everything after "Secretary" and
    #    inserting a period
    # 2. PL 105-206 (1998): by striking all that follows "paragraph (1)" and
    #    inserting "shall apply"
    # 3. PL 111-312 (2010): by striking everything following "2010" and
    #    inserting "2012"
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
    #
    # Real-world examples:
    # 1. PL 108-311 (2004): by striking ", and before January 1, 2005"
    # 2. PL 109-135 (2005): by striking "or (5)"
    # 3. PL 110-343 (2008): by striking the last sentence
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
    # Real-world examples:
    # 1. PL 104-188 (1996): by striking "except that" and all that follows
    #    through the period
    # 2. PL 105-34 (1997): by striking "unless" and all that follows through
    #    the semicolon
    # 3. PL 107-16 (2001): by striking "or" and all that follows through
    #    "such calendar year"
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
    # Real-world examples:
    # 1. PL 111-148 (2010): by striking paragraph (4)
    # 2. PL 109-280 (2006): by striking subparagraph (B)
    # 3. PL 105-206 (1998): by striking clause (ii)
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
    # Real-world examples:
    # 1. PL 100-647 (1988): by striking "under this section" and all that
    #    follows
    # 2. PL 104-188 (1996): by striking "but only" and everything that follows
    # 3. PL 106-170 (1999): by striking ", except" and all that follows
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
    #
    # Real-world examples:
    # 1. PL 110-85 (2007): by adding at the end the following new paragraph
    # 2. PL 111-148 (2010): by adding at the end of the subsection the
    #    following
    # 3. PL 94-553 (1976): by adding at the end thereof the following new
    #    subsection
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
    # Real-world examples:
    # 1. PL 109-280 (2006): by inserting after paragraph (8) the following new
    #    paragraphs
    # 2. PL 110-85 (2007): by adding after subparagraph (C) the following
    # 3. PL 105-34 (1997): by inserting after clause (i) the following new
    #    clause
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
    # Real-world examples:
    # 1. PL 105-304 (1998): by inserting after section 411 the following new
    #    section
    # 2. PL 110-403 (2008): by inserting after section 506 the following
    # 3. PL 111-295 (2010): by inserting after section 1204 the following new
    #    section
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
    # Real-world examples:
    # 1. PL 104-188 (1996): by inserting before "the date" the following: "the
    #    earlier of"
    # 2. PL 108-357 (2004): by inserting before the period the following: ",
    #    or any successor thereto"
    # 3. PL 109-432 (2006): by inserting before "January 1" the following:
    #    "the later of"
    AmendmentPattern(
        name="insert_before",
        pattern_type=PatternType.INSERT_BEFORE,
        regex=(
            r"(?:by\s+)?inserting\s+before\s+" + QUOTED_TEXT + r"\s+the\s+following"
        ),
        confidence=0.90,
        description='Inserting before "X" the following',
    ),
    # Real-world examples:
    # 1. PL 111-148 (2010): by inserting before paragraph (3) the following
    #    new paragraph
    # 2. PL 109-280 (2006): by inserting before subparagraph (E) the following
    # 3. PL 107-16 (2001): by inserting before clause (ii) the following new
    #    clause
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
    # Real-world examples:
    # 1. PL 110-85 (2007): by adding a new subsection (h) to read as follows
    # 2. PL 109-280 (2006): by adding new paragraph (9) as follows
    # 3. PL 111-148 (2010): by inserting a new subparagraph (C) to read as
    #    follows
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
    #
    # Real-world examples:
    # 1. PL 105-206 (1998): Section 6103(p)(4) is hereby repealed
    # 2. PL 94-455 (1976): Section 963 of the Internal Revenue Code of 1954 is
    #    repealed
    # 3. PL 111-148 (2010): Section 36B(f)(3) is repealed
    AmendmentPattern(
        name="section_repealed",
        pattern_type=PatternType.REPEAL,
        regex=SECTION_REF + r"\s+(?:is|are)\s+(?:hereby\s+)?repealed",
        confidence=0.98,
        description="Section X is hereby repealed",
    ),
    # Real-world examples:
    # 1. PL 109-280 (2006): paragraph (3) is hereby repealed
    # 2. PL 107-16 (2001): subparagraph (B) is repealed
    # 3. PL 105-34 (1997): clause (iv) is hereby stricken
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
    # Real-world examples:
    # 1. PL 108-357 (2004): by striking section 114
    # 2. PL 100-647 (1988): by striking section 89
    # 3. PL 104-188 (1996): by striking section 1256(e)(3)(C)
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
    #
    # Real-world examples:
    # 1. PL 105-206 (1998): by redesignating section 7612 as section 7613
    # 2. PL 110-343 (2008): by redesignating section 45R as section 45S
    # 3. PL 111-5 (2009): by redesignating section 1400N as section 1400O
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
    # Real-world examples:
    # 1. PL 110-85 (2007): by redesignating subparagraph (C) as subparagraph
    #    (B)
    # 2. PL 109-280 (2006): by redesignating paragraphs (3) through (5) as
    #    paragraphs (4) through (6)
    # 3. PL 111-148 (2010): by redesignating clauses (i), (ii), and (iii) as
    #    clauses (ii), (iii), and (iv)
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
    #
    # Real-world examples:
    # 1. PL 105-80 (1997): Section 115(c)(3)(D) of title 17, United States
    #    Code, is amended to read as follows
    # 2. PL 110-85 (2007): Section 505(b)(5)(C) is amended to read as follows
    # 3. PL 94-553 (1976): Section 111 of title 17 is hereby amended and
    #    reenacted to read as follows
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
    # Real-world examples:
    # 1. PL 109-280 (2006): paragraph (2) is amended to read as follows
    # 2. PL 111-148 (2010): subparagraph (A) is amended to read as follows
    # 3. PL 107-16 (2001): clause (ii) is hereby amended to read as follows
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
    #
    # Real-world examples:
    # 1. PL 103-296 (1994): Section 1148 is hereby transferred to section 234
    #    of title 42
    # 2. PL 109-163 (2006): Section 2350a is transferred to section 2350b of
    #    title 10
    # 3. PL 100-527 (1988): Section 5012 is transferred to section 301 of
    #    title 38
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
    #
    # Real-world examples:
    # 1. PL 110-85 (2007): Section 505(b)(1) of title 21, United States Code,
    #    is amended—
    # 2. PL 105-304 (1998): Section 512 of title 17, United States Code, is
    #    amended
    # 3. PL 94-553 (1976): Section 106 of title 17 is hereby amended
    AmendmentPattern(
        name="section_amended_general",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=SECTION_REF_WITH_TITLE + r",?\s+(?:is|are)\s+(?:hereby\s+)?amended",
        confidence=0.85,
        description="Section X of title Y is amended",
    ),
    # Real-world examples:
    # 1. PL 109-280 (2006): Section 401(a)(9) is amended by striking
    #    subparagraph (C)
    # 2. PL 111-148 (2010): Section 1395w-4 of title 42, United States Code,
    #    is amended by adding at the end the following
    # 3. PL 105-34 (1997): Section 453(e) is amended by inserting "or gain"
    #    after "loss"
    AmendmentPattern(
        name="section_amended_by",
        pattern_type=PatternType.AMEND_GENERAL,
        regex=(
            SECTION_REF_WITH_TITLE + r",?\s+(?:is|are)\s+(?:hereby\s+)?amended\s+by"
        ),
        confidence=0.90,
        description="Section X is amended by",
    ),
    # Real-world examples:
    # 1. PL 110-85 (2007): subsection (d) of such section is amended
    # 2. PL 109-280 (2006): paragraph (1) of section 401(a) is amended
    # 3. PL 107-16 (2001): subparagraph (B)(ii) is hereby amended
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
    # Real-world examples:
    # 1. PL 105-304 (1998): Title 17, United States Code, is amended by adding
    #    after chapter 11 the following
    # 2. PL 111-148 (2010): Title 42, United States Code, is hereby amended
    # 3. PL 110-343 (2008): Title 26, United States Code, is amended by
    #    inserting after section 45Q the following
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
    #
    # Real-world examples:
    # 1. PL 105-304 (1998): Title 17, United States Code, is amended by adding
    #    after section 1201 the following new section 1202
    # 2. PL 110-403 (2008): Title 18, United States Code, is amended by adding
    #    a new section 2323
    # 3. PL 111-5 (2009): Title 26, United States Code, is amended by inserting
    #    after section 36 the following new section 36A
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
    # Real-world examples:
    # 1. PL 105-304 (1998): Chapter 12 of title 17, United States Code, is
    #    amended by adding at the end the following new section
    # 2. PL 110-85 (2007): Chapter 5 of title 21, United States Code, is
    #    amended by inserting after section 355 the following
    # 3. PL 109-280 (2006): Chapter 43 of title 26, United States Code, is
    #    amended by adding at the end the following new section
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
