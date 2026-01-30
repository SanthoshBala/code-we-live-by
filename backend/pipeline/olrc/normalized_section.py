"""Line normalization for legal text (Task 1.11).

This module converts continuous legal prose into line-delimited text
suitable for diff views and blame tracking. Each "line" is either:
1. A list item (subsection marker + content)
2. A sentence (when not inside a list structure)

The normalized output preserves legal structure through indentation,
making it visually similar to code while maintaining readability.

Historical notes, editorial notes, and revision notes are separated
from the law text and returned as metadata (like README/docstrings).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.olrc.parser import ParsedSection, ParsedSubsection

# Common legal abbreviations that contain periods but aren't sentence endings
LEGAL_ABBREVIATIONS = {
    "U.S.C.",
    "U.S.",
    "Sec.",
    "sec.",
    "No.",
    "no.",
    "Pub.",
    "pub.",
    "L.",
    "Stat.",
    "stat.",
    "Rev.",
    "rev.",
    "Reg.",
    "reg.",
    "Fed.",
    "fed.",
    "Corp.",
    "corp.",
    "Inc.",
    "inc.",
    "Ltd.",
    "ltd.",
    "Co.",
    "co.",
    "et.",
    "al.",
    "etc.",
    "i.e.",
    "e.g.",
    "v.",  # versus in case citations
    "vs.",
    "Mr.",
    "Mrs.",
    "Ms.",
    "Dr.",
    "Jr.",
    "Sr.",
    "Gen.",
    "Col.",
    "Gov.",
    "Rep.",
    "Sen.",
    "Dept.",
    "dept.",
    "Div.",
    "div.",
    "Ch.",
    "ch.",
    "Art.",
    "art.",
    "Amdt.",
    "amdt.",
    "Cl.",
    "cl.",
    "Para.",
    "para.",
    "Subch.",
    "subch.",
    "Pt.",
    "pt.",
}

# Pattern for list item markers: (a), (1), (A), (i), (I), etc.
# Also handles deeper nesting like (a)(1)(A)
# This pattern is permissive; we filter out references in _is_reference_not_marker()
LIST_ITEM_PATTERN = re.compile(
    r"(?:^|(?<=\s)|(?<=[.;:—]))\s*"  # Start, after whitespace, or after punctuation
    r"(\([a-zA-Z0-9]+\))"  # Primary marker like (a), (1), (A)
    r"(\s*\([a-zA-Z0-9]+\))*"  # Optional additional markers for nesting
    r"\s*",  # Trailing whitespace before content
)

# Words that indicate a reference to a subsection, not a list item marker
# These are specific legal terms that precede parenthesized references
REFERENCE_WORDS = {
    "subsection", "subsections",
    "paragraph", "paragraphs",
    "subparagraph", "subparagraphs",
    "clause", "clauses",
    "subclause", "subclauses",
}

# Pattern to detect the nesting level from a marker
MARKER_PATTERN = re.compile(r"\(([a-zA-Z0-9]+)\)")

# Words that commonly start sentences in legal text (after a subsection header)
SENTENCE_STARTERS = {
    "a", "an", "the", "no", "any", "each", "if", "for", "in", "on", "to",
    "as", "by", "under", "subject", "notwithstanding", "unless", "except",
    "upon", "after", "before", "when", "where", "this", "that", "such",
    "nothing", "whoever", "whenever", "every", "all", "there",
}

# Pattern to detect subsection headers like "Registration requirements" or "Definitions"
# Headers are typically 1-5 title-case words followed by a sentence starter or em-dash
SUBSECTION_HEADER_PATTERN = re.compile(
    r"^(\s*)"  # Leading whitespace
    r"([A-Z][a-z]+(?:\s+(?:and|or|of|the|for|in|to|a|an)?\s*[A-Za-z]+){0,6}?)"  # Header (title case words)
    r"(?="  # Followed by (lookahead):
    r"\s*—"  # em-dash, OR
    r"|"
    r"\s+[A-Z][a-z]*\s"  # Capital word + space (sentence start)
    r")",
    re.UNICODE,
)


def _extract_subsection_header(content: str) -> tuple[str | None, str]:
    """Extract a subsection header from content if present.

    Legal subsections often have a short header like "Registration requirements"
    followed by the actual content. This function detects and splits them.

    Args:
        content: The content after the marker (e.g., "Registration requirements A security...")

    Returns:
        Tuple of (header, remaining_content). Header is None if not detected.
    """
    # Check for em-dash separator (clearest case)
    if "—" in content:
        parts = content.split("—", 1)
        header_candidate = parts[0].strip()
        # Header should be short (1-6 words) and not look like a sentence
        words = header_candidate.split()
        if 1 <= len(words) <= 6 and not header_candidate.endswith((".", ",", ";")):
            return header_candidate, parts[1].strip() if len(parts) > 1 else ""

    # Try pattern matching for headers without em-dash
    match = SUBSECTION_HEADER_PATTERN.match(content)
    if match:
        header = match.group(2).strip()
        remaining = content[match.end(2):].strip()

        # Validate: header should be 1-6 words, remaining should start with sentence starter
        words = header.split()
        if 1 <= len(words) <= 6:
            # Check if remaining starts with a sentence starter
            first_word = remaining.split()[0].lower() if remaining.split() else ""
            if first_word.rstrip(".,;") in SENTENCE_STARTERS or remaining.startswith("—"):
                return header, remaining

    return None, content

# Patterns that indicate the start of notes/metadata sections (not law text)
# These appear after the actual law text in US Code sections
NOTES_SECTION_HEADERS = [
    r"Historical and Revision Notes",
    r"Editorial Notes",
    r"Statutory Notes and Related Subsidiaries",
    r"References in Text",
    r"Codification",
    r"Prior Provisions",
    r"Effective Date",
    r"Short Title",
    r"Regulations",
    r"Transfer of Functions",
    r"Savings Provision",
]

# Pattern to detect the citation block that often appears at the end of law text
# e.g., "( Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546; ..."
CITATION_BLOCK_PATTERN = re.compile(
    r"\(\s*Pub\.\s*L\.\s+\d+[–-]\d+.*?(?=Historical|Editorial|Statutory|$)",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class NormalizedLine:
    """A single normalized line of legal text.

    Attributes:
        line_number: 1-indexed line number in the normalized output.
        content: The text content of this line (without leading indentation).
        indent_level: Nesting depth (0 = top level, 1 = (a), 2 = (1), etc.).
        marker: The list item marker if this is a list item, e.g., "(a)".
        start_char: Character position in original text where this line starts.
        end_char: Character position in original text where this line ends.
    """

    line_number: int
    content: str
    indent_level: int
    marker: str | None
    start_char: int
    end_char: int

    def to_display(self, use_tabs: bool = True, indent_width: int = 4) -> str:
        """Return the line with proper indentation for display.

        Args:
            use_tabs: If True, use tab characters. If False, use spaces.
            indent_width: Number of spaces per indent level (only used if use_tabs=False).
        """
        if use_tabs:
            indent = "\t" * self.indent_level
        else:
            indent = " " * (self.indent_level * indent_width)
        return f"{indent}{self.content}"


@dataclass
class Citation:
    """A citation to a Public Law that affected this section.

    Like an import statement, this links the section to the law that
    created or modified it. Citations are ordered chronologically:
    - First citation (order=0) = the law that created/enacted the section
    - Subsequent citations = amendments in historical order

    Example: "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
    """

    congress: int  # e.g., 94
    law_number: int  # e.g., 553
    title: str | None = None  # Title within the law, e.g., "I"
    section: str | None = None  # Section within the law, e.g., "101"
    date: str | None = None  # Enactment date, e.g., "Oct. 19, 1976"
    stat_volume: int | None = None  # Statutes at Large volume, e.g., 90
    stat_page: int | None = None  # Statutes at Large page, e.g., 2546
    raw_text: str = ""  # The original citation text
    order: int = 0  # Position in citation list (0 = original/creating law)

    @property
    def public_law_id(self) -> str:
        """Return the Public Law identifier (e.g., 'PL 94-553')."""
        return f"PL {self.congress}-{self.law_number}"

    @property
    def stat_reference(self) -> str | None:
        """Return the Statutes at Large reference (e.g., '90 Stat. 2546')."""
        if self.stat_volume and self.stat_page:
            return f"{self.stat_volume} Stat. {self.stat_page}"
        return None

    @property
    def is_original(self) -> bool:
        """Return True if this is the original/creating law (first citation)."""
        return self.order == 0

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return a sort key for chronological ordering.

        Uses (congress, law_number) which gives chronological order
        since congress numbers increase over time.
        """
        return (self.congress, self.law_number)

    def __repr__(self) -> str:
        return f"<Citation({self.public_law_id})>"


# Pattern to parse individual citation components
# Matches: "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
# Also handles: "Pub. L. 107–273, div. C, title III, § 13210(4)(A), Nov. 2, 2002"
# Note: Source text may have extra whitespace around commas (e.g., " ,  ")
CITATION_PARSE_PATTERN = re.compile(
    r"Pub\.\s*L\.\s*(\d+)[–-](\d+)"  # Congress and law number
    r"(?:\s*,\s*div\.\s*[A-Z])?"  # Optional division (e.g., "div. C")
    r"(?:\s*,\s*title\s+([IVXLCDM]+))?"  # Optional title (roman numeral)
    r"(?:\s*,\s*§+\s*([\d\w]+(?:\([a-z0-9]+\))*))?"  # Optional section
    r"(?:\s*,\s*([A-Z][a-z]{2,3}\.?\s+\d{1,2}\s*,\s+\d{4}))?"  # Optional date
    r"(?:\s*,\s*(\d+)\s+Stat\.\s+(\d+))?"  # Optional Stat reference
    ,
    re.IGNORECASE,
)


def parse_citation(text: str) -> Citation | None:
    """Parse a citation string into a Citation object.

    Args:
        text: Raw citation text like "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"

    Returns:
        Citation object or None if parsing fails.
    """
    match = CITATION_PARSE_PATTERN.search(text)
    if not match:
        return None

    congress = int(match.group(1))
    law_number = int(match.group(2))
    title = match.group(3)  # May be None
    section = match.group(4)  # May be None
    date = match.group(5)  # May be None
    stat_volume = int(match.group(6)) if match.group(6) else None
    stat_page = int(match.group(7)) if match.group(7) else None

    return Citation(
        congress=congress,
        law_number=law_number,
        title=title,
        section=section,
        date=date,
        stat_volume=stat_volume,
        stat_page=stat_page,
        raw_text=text.strip(),
    )


def parse_citations(text: str) -> list[Citation]:
    """Parse all citations from a text block.

    Citations are separated by semicolons within the parenthetical block.
    They are returned in chronological order (as they appear in the source),
    with order=0 being the original/creating law.

    Args:
        text: Text containing one or more citations.

    Returns:
        List of parsed Citation objects with order field set.
    """
    citations: list[Citation] = []

    # Find the citation block - it starts with "( Pub. L." and ends with "Stat. NNNN .)"
    # We need to handle nested parentheses in section refs like § 3(d) or § 704(b)(2)
    # Strategy: find "( Pub. L." then scan forward tracking paren depth until we close
    citation_block = None
    match = re.search(r"\(\s*Pub\.\s*L\.", text, re.IGNORECASE)
    if match:
        start = match.start()
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start=start):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        citation_block = text[start:end]

    if citation_block:
        # Split by semicolons to get individual citations
        segments = re.split(r";\s*", citation_block)
        for segment in segments:
            if "Pub." in segment or re.search(r"L\.\s*\d+", segment):
                citation = parse_citation(segment)
                if citation:
                    citation.order = len(citations)  # 0 = first/original
                    citations.append(citation)
    else:
        # Try to parse the whole text as citations
        segments = re.split(r";\s*", text)
        for segment in segments:
            citation = parse_citation(segment)
            if citation:
                citation.order = len(citations)  # 0 = first/original
                citations.append(citation)

    return citations


@dataclass
class Amendment:
    """A single amendment to a section.

    Represents one change made to a section by a Public Law,
    like a commit in version control.
    """

    year: int
    public_law: str  # e.g., "Pub. L. 103-322"
    description: str  # What changed
    congress: int | None = None
    law_number: int | None = None

    @property
    def public_law_id(self) -> str:
        """Return normalized PL identifier."""
        if self.congress and self.law_number:
            return f"PL {self.congress}-{self.law_number}"
        return self.public_law


@dataclass
class EffectiveDate:
    """An effective date provision.

    Note: We store the full description text rather than trying to extract
    specific dates, because effective dates often involve complex calculations
    (e.g., "3 months after Nov. 1, 1995") or conditional logic that requires
    human interpretation.
    """

    description: str  # The full text describing when the provision takes effect
    public_law: str | None = None  # Related Pub. L. if specified
    amendment_year: int | None = None  # Year of the amendment this applies to


@dataclass
class ShortTitle:
    """A short title (common name) for an act."""

    title: str  # e.g., "Philanthropy Protection Act of 1995"
    year: int | None = None
    public_law: str | None = None


@dataclass
class SectionNotes:
    """Metadata notes extracted from a US Code section.

    These are separated from the law text and treated like documentation.
    The structure mirrors the OLRC's organization of notes into three
    main categories:

    1. Historical and Revision Notes - Legislative history from codification
    2. Editorial Notes - OLRC editorial annotations (codification, references, amendments)
    3. Statutory Notes - Provisions from enacting laws that aren't part of the Code itself

    Note: Some statutory note types are very law-specific (e.g., "Performing Rights
    Society Consent Decrees" in 17 USC 101). We only parse the common/universal types
    listed below. Law-specific notes remain in raw_notes.

    Field frequency estimates based on ~10,700 sections across titles 10, 17, 18, 20, 22, 26, 42, 50.
    """

    # =========================================================================
    # CITATIONS - Structured references to Public Laws that enacted/amended this section
    # =========================================================================
    # Example: 17 USC 106 cites "Pub. L. 94-553" as the enacting law
    # Frequency: >90% of sections have at least one citation
    citations: list[Citation] = field(default_factory=list)

    # =========================================================================
    # HISTORICAL AND REVISION NOTES (<10% of sections)
    # =========================================================================
    # Legislative history and explanatory notes from the original codification,
    # typically from House Reports. Common in older titles codified before 1947.
    # Contains committee explanations of the law's purpose and interpretation.
    # Example: 17 USC 102 - explains "original works of authorship" language
    # Example: 18 USC 2 - explains principals vs accessories distinction
    historical_revision_notes: str = ""

    # =========================================================================
    # EDITORIAL NOTES - Added by OLRC to clarify the Code
    # =========================================================================

    # Codification (~30-40% of sections)
    # Notes about how the section was placed in the Code, including any
    # adjustments made during codification (e.g., renumbering references).
    # Example: 18 USC 39 - notes about section's placement in chapter 2
    # Example: 42 USC 2 - codification of Public Health Service Act provisions
    codification: str = ""

    # References in Text (~40% of sections)
    # Explains where referenced laws/sections can be found in the Code.
    # Helps readers locate cross-referenced provisions.
    # Example: 17 USC 106A - explains where "Visual Artists Rights Act" is classified
    # Example: 26 USC 45B - explains references to Social Security Act sections
    references_in_text: list[str] = field(default_factory=list)

    # Amendments (~70-80% of sections) - Most common note type
    # Chronological list of changes made to this section by subsequent laws.
    # Each entry identifies the Public Law and describes what was changed.
    # Example: 17 USC 106 - lists 5 amendments from 1990-2002
    # Example: 42 USC 201 - extensive amendment history back to 1944
    amendments: list[Amendment] = field(default_factory=list)

    # Prior Provisions (~20-30% of sections)
    # References to earlier sections that covered similar subject matter
    # before being repealed, omitted, or superseded by this section.
    # Example: 18 USC 4248 - references prior civil commitment provisions
    prior_provisions: str = ""

    # =========================================================================
    # STATUTORY NOTES - Provisions from enacting laws, not part of Code text
    # =========================================================================

    # Effective Dates (~20-30% of sections)
    # When amendments or the original section took/take effect.
    # Often includes complex conditions (e.g., "effective 3 months after enactment").
    # Example: 17 USC 106 - effective dates for 1990 and 1995 amendments
    # Example: 18 USC 4285 - delayed effective date provisions
    effective_dates: list[EffectiveDate] = field(default_factory=list)

    # Short Titles (<10% of sections)
    # Popular names for acts (e.g., "USA PATRIOT Act", "Clean Air Act").
    # Helps identify which well-known law created or amended the section.
    # Example: 18 USC 3591 - "Federal Death Penalty Act of 1994"
    # Example: 42 USC 280c - various short titles for health programs
    short_titles: list[ShortTitle] = field(default_factory=list)

    # Regulations (<10% of sections)
    # Notes about regulatory authority or required rulemaking.
    # Example: 18 USC 3600A - notes about DNA testing regulations
    regulations: str = ""

    # Change of Name (<10% of sections)
    # Documents when agency or office names changed (e.g., INS → DHS).
    # Important for understanding historical references in the text.
    # Example: 18 USC 5034 - notes about agency name changes
    change_of_name: str = ""

    # Transfer of Functions (~10% of sections)
    # Documents when responsibilities moved between agencies.
    # Common after government reorganizations.
    # Example: 18 USC 4351 - transfer of Bureau of Prisons functions
    transfer_of_functions: str = ""

    # Definitions (<10% of sections)
    # Statutory definitions that apply to the section but aren't in Code text.
    # Example: 18 USC 5043 - definitions for juvenile delinquency chapter
    definitions: str = ""

    # Construction (<1% of sections)
    # How the section should be interpreted relative to other laws.
    # Example: 18 USC 2252C - construction relative to state laws
    construction: str = ""

    # Savings Provision (<10% of sections)
    # Preserves rights/proceedings under prior law during transition.
    # Example: 18 USC 6001 - savings provisions for immunity orders
    savings_provision: str = ""

    # =========================================================================
    # SECTION STATUS - Metadata about the section's current state
    # =========================================================================

    # Section was moved to another location in the Code
    transferred_to: str | None = None

    # Section was omitted from the Code (not repealed, just not carried forward)
    omitted: bool = False

    # Section was renumbered from a previous section number
    renumbered_from: str | None = None

    # =========================================================================
    # RAW/UNPARSED CONTENT
    # =========================================================================

    # Full raw text of all notes (for anything not parsed into structured fields)
    # Includes law-specific statutory notes that don't fit the common categories
    raw_notes: str = ""

    # Legacy fields (for backwards compatibility, prefer specific fields above)
    historical_notes: str = ""  # Deprecated, use historical_revision_notes
    editorial_notes: str = ""  # Deprecated, use specific fields
    statutory_notes: str = ""  # Deprecated, use specific fields

    @property
    def has_notes(self) -> bool:
        """Return True if any notes were extracted."""
        return bool(self.raw_notes.strip())

    @property
    def has_citations(self) -> bool:
        """Return True if any citations were parsed."""
        return len(self.citations) > 0

    @property
    def has_amendments(self) -> bool:
        """Return True if any amendments were parsed."""
        return len(self.amendments) > 0

    @property
    def is_transferred(self) -> bool:
        """Return True if section was transferred to another location."""
        return self.transferred_to is not None

    @property
    def is_omitted(self) -> bool:
        """Return True if section was omitted."""
        return self.omitted


@dataclass
class NormalizedSection:
    """A section of legal text normalized into lines.

    Attributes:
        lines: List of normalized lines (the actual law text).
        original_text: The original unnormalized text (including notes).
        normalized_text: The law text with line breaks and indentation.
        law_text: Just the law text portion (excluding notes).
        notes: Extracted notes/metadata (like README/docstrings).
    """

    lines: list[NormalizedLine]
    original_text: str
    normalized_text: str
    law_text: str = ""
    notes: SectionNotes = field(default_factory=SectionNotes)

    @property
    def line_count(self) -> int:
        """Return the total number of lines."""
        return len(self.lines)

    def get_line(self, line_number: int) -> NormalizedLine | None:
        """Get a line by its 1-indexed line number."""
        if 1 <= line_number <= len(self.lines):
            return self.lines[line_number - 1]
        return None

    def get_lines(self, start: int, end: int) -> list[NormalizedLine]:
        """Get lines in a range (1-indexed, inclusive)."""
        return self.lines[max(0, start - 1) : end]

    def char_to_line(self, char_pos: int) -> int | None:
        """Convert a character position to a line number."""
        for line in self.lines:
            if line.start_char <= char_pos < line.end_char:
                return line.line_number
        return None


def _is_reference_not_marker(text: str, match_start: int) -> bool:
    """Check if a marker at match_start is actually a reference, not a list item.

    References like "subsection (a)" or "paragraph (1)" should not start new lines.
    """
    if match_start == 0:
        return False  # At start of text, it's a marker

    # Look back for reference words
    # Find the word immediately before the marker
    before = text[:match_start].rstrip()
    if not before:
        return False

    # Split on whitespace and common punctuation (including em-dash)
    # to get the last word
    words = re.split(r"[\s.;:,—–-]+", before)
    words = [w for w in words if w]  # Remove empty strings

    if not words:
        return False

    last_word = words[-1].lower()

    return last_word in REFERENCE_WORDS


def _is_roman_numeral(s: str) -> bool:
    """Check if string is a valid roman numeral.

    Only returns True for unambiguous roman numerals (length > 1)
    or common single-char roman numerals in legal context.
    """
    # Multi-character roman numerals are unambiguous
    if len(s) > 1 and re.match(r"^[ivxlcdmIVXLCDM]+$", s):
        # Validate it's a proper roman numeral pattern (not just random letters)
        # Common patterns: i, ii, iii, iv, v, vi, vii, viii, ix, x, xi, xii, etc.
        lower = s.lower()
        if re.match(r"^(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{1,3}|xiv|xv|xvi{0,3}|xix|xx)$", lower):
            return True
    return False


def _detect_marker_level(marker: str) -> int:
    """Detect the indent level based on marker type.

    Legal text uses a hierarchy:
    - Level 1: (a), (b), (c) - lowercase letters
    - Level 2: (1), (2), (3) - numbers
    - Level 3: (A), (B), (C) - uppercase letters
    - Level 4: (i), (ii), (iii) - lowercase roman numerals
    - Level 5: (I), (II), (III) - uppercase roman numerals

    For compound markers like (a)(1)(A), we use the deepest level.

    Note: Single letters (i) and (I) are treated as letters, not roman numerals,
    unless they appear in a clearly roman numeral context (multi-char like ii, iii).
    """
    markers = MARKER_PATTERN.findall(marker)
    if not markers:
        return 0

    # Use the last (deepest) marker to determine level
    last_marker = markers[-1]

    # Check for roman numerals first (must be unambiguous)
    if _is_roman_numeral(last_marker):
        if last_marker.islower():
            return 4
        else:
            return 5

    # Numbers: (1)-(99)
    if re.match(r"^\d+$", last_marker):
        return 2

    # Single lowercase letter: (a)-(z)
    if re.match(r"^[a-z]$", last_marker):
        return 1

    # Single uppercase letter: (A)-(Z)
    if re.match(r"^[A-Z]$", last_marker):
        return 3

    # Default to level 1 for unknown patterns
    return 1


def _is_sentence_boundary(text: str, pos: int) -> bool:
    """Check if position is a true sentence boundary.

    Returns True if the period at `pos` ends a sentence, not an abbreviation.
    """
    if pos >= len(text) or text[pos] != ".":
        return False

    # Check what follows the period
    remaining = text[pos + 1 :]
    if not remaining:
        return True  # End of text

    if not remaining.strip():
        return True  # Only whitespace follows

    # Must be followed by whitespace + capital letter, open paren, or quote
    follows_pattern = re.match(r'\s+[A-Z("\'"\']', remaining)
    if not follows_pattern:
        return False

    # Check if this period is part of a known abbreviation
    # Look back to find the word ending at this period
    before = text[: pos + 1]  # Include the period

    # Check against known abbreviations
    for abbrev in LEGAL_ABBREVIATIONS:
        if before.endswith(abbrev):
            return False

    # Also check for single-letter abbreviations followed by period
    # e.g., "U." in "U.S.C."
    if pos >= 1 and text[pos - 1].isupper() and (pos < 2 or not text[pos - 2].isalnum()):
        # Single uppercase letter followed by period - likely abbreviation
        # unless it's the end of a sentence like "Plan B."
        pass  # Allow this for now, common abbreviations are in the list

    return True


def _split_into_sentences(text: str, start_offset: int = 0) -> list[tuple[str, int, int]]:
    """Split text into sentences, returning (content, start_char, end_char) tuples.

    The start_char and end_char are relative to the original text using start_offset.
    """
    sentences = []
    current_start = 0
    i = 0

    while i < len(text):
        if text[i] == "." and _is_sentence_boundary(text, i):
            # Found sentence boundary
            sentence = text[current_start : i + 1].strip()
            if sentence:
                sentences.append(
                    (sentence, start_offset + current_start, start_offset + i + 1)
                )
            current_start = i + 1
            # Skip whitespace after sentence
            while current_start < len(text) and text[current_start] in " \t\n":
                current_start += 1
            i = current_start
        else:
            i += 1

    # Don't forget the last segment if it doesn't end with a period
    remaining = text[current_start:].strip()
    if remaining:
        sentences.append((remaining, start_offset + current_start, start_offset + len(text)))

    return sentences


def _parse_amendments(text: str) -> list[Amendment]:
    """Parse amendment entries from the Amendments subsection.

    Amendments are listed chronologically (newest first) like:
    "2010—Pub. L. 111-203 substituted 'Bureau' for 'Board'."
    "1976—Subsec. (e). Pub. L. 94-239 substituted provisions..."

    Multiple amendments can occur in the same year:
    "1990— Pub. L. 101–650 substituted...
     Pub. L. 101–318 substituted..."

    Args:
        text: The amendments subsection text.

    Returns:
        List of Amendment objects, one per Pub. L. reference.
    """
    amendments = []

    # First, split by year markers to get year blocks
    # Pattern: "YYYY—" at start of line or after whitespace
    year_pattern = re.compile(r"(\d{4})\s*[—–-]\s*", re.MULTILINE)

    # Find all year markers and their positions
    year_matches = list(year_pattern.finditer(text))

    for i, year_match in enumerate(year_matches):
        year = int(year_match.group(1))
        start = year_match.end()

        # End is either next year marker or end of text
        if i + 1 < len(year_matches):
            end = year_matches[i + 1].start()
        else:
            end = len(text)

        year_block = text[start:end].strip()

        # Now find all Pub. L. references within this year block
        # Each Pub. L. reference is a separate amendment
        pub_l_pattern = re.compile(
            r"(Pub\.\s*L\.\s*(\d+)[—–-](\d+))"  # Pub. L. reference
            r"(.*?)"  # Description
            r"(?=Pub\.\s*L\.\s*\d+[—–-]\d+|$)",  # Until next Pub. L. or end
            re.DOTALL,
        )

        for pub_match in pub_l_pattern.finditer(year_block):
            public_law_text = pub_match.group(1)
            congress = int(pub_match.group(2))
            law_number = int(pub_match.group(3))
            description = (public_law_text + pub_match.group(4)).strip()

            # Clean up description - remove trailing whitespace and normalize
            description = " ".join(description.split())

            amendments.append(Amendment(
                year=year,
                public_law=f"Pub. L. {congress}-{law_number}",
                description=description,
                congress=congress,
                law_number=law_number,
            ))

        # If no Pub. L. found in the block, still record the year with the description
        if not list(pub_l_pattern.finditer(year_block)) and year_block:
            # Try to extract any Pub. L. reference
            simple_pub_match = re.search(r"Pub\.\s*L\.\s*(\d+)[—–-](\d+)", year_block)
            if simple_pub_match:
                congress = int(simple_pub_match.group(1))
                law_number = int(simple_pub_match.group(2))
                public_law = f"Pub. L. {congress}-{law_number}"
            else:
                congress = None
                law_number = None
                public_law = ""

            amendments.append(Amendment(
                year=year,
                public_law=public_law,
                description=" ".join(year_block.split()),
                congress=congress,
                law_number=law_number,
            ))

    return amendments


def _parse_effective_dates(text: str) -> list[EffectiveDate]:
    """Parse effective date entries from the Statutory Notes.

    We capture the full description text rather than trying to extract
    specific dates, since effective dates often involve complex calculations
    or conditional logic.

    Args:
        text: The statutory notes text.

    Returns:
        List of EffectiveDate objects.
    """
    effective_dates = []

    # Look for "Effective Date" sections, including "Effective Date of YYYY Amendment"
    eff_pattern = re.compile(
        r"Effective Date(?: of (\d{4}) Amendment)?\s+"
        r"(.*?)"
        r"(?=Effective Date|Short Title|Change of Name|Transfer of Functions|Regulations|$)",
        re.DOTALL | re.IGNORECASE,
    )

    for match in eff_pattern.finditer(text):
        amendment_year = int(match.group(1)) if match.group(1) else None
        description = match.group(2).strip()
        if not description:
            continue

        # Clean up description - normalize whitespace
        description = " ".join(description.split())

        # Try to extract Pub. L.
        pub_l_match = re.search(r"Pub\.\s*L\.\s*\d+[—–-]\d+", description)
        public_law = pub_l_match.group(0) if pub_l_match else None

        effective_dates.append(EffectiveDate(
            description=description[:500],  # Limit length
            public_law=public_law,
            amendment_year=amendment_year,
        ))

    return effective_dates


def _parse_short_titles(text: str) -> list[ShortTitle]:
    """Parse short title entries from the Statutory Notes.

    Args:
        text: The statutory notes text.

    Returns:
        List of ShortTitle objects.
    """
    short_titles = []

    # Look for "Short Title" sections
    title_pattern = re.compile(
        r"Short Title(?: of \d{4} (?:Amendment|Act))?\s+"
        r"(.*?)"
        r"(?=Short Title|Effective Date|Change of Name|Transfer of Functions|Regulations|$)",
        re.DOTALL | re.IGNORECASE,
    )

    for match in title_pattern.finditer(text):
        description = match.group(1).strip()
        if not description:
            continue

        # Try to extract the actual title name (usually in quotes)
        name_match = re.search(r'"([^"]+(?:Act|Law)[^"]*)"', description)
        if name_match:
            title = name_match.group(1)
        else:
            # Try without quotes
            name_match = re.search(r"(?:cited as|known as)(?: the)?\s+['\"]?([^'\"]+(?:Act|Law)[^'\"]*)", description, re.IGNORECASE)
            title = name_match.group(1).strip() if name_match else description[:100]

        # Extract year
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        year = int(year_match.group(1)) if year_match else None

        # Extract Pub. L.
        pub_l_match = re.search(r"Pub\.\s*L\.\s*\d+[—–-]\d+", description)
        public_law = pub_l_match.group(0) if pub_l_match else None

        short_titles.append(ShortTitle(
            title=title,
            year=year,
            public_law=public_law,
        ))

    return short_titles


def _parse_references_in_text(text: str) -> list[str]:
    """Parse References in Text entries.

    Args:
        text: The editorial notes text.

    Returns:
        List of reference descriptions.
    """
    references = []

    # Look for "References in Text" section
    ref_match = re.search(
        r"References in Text\s+(.*?)(?=Codification|Amendments|Prior Provisions|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if ref_match:
        ref_text = ref_match.group(1).strip()
        # Split by sentence-like boundaries
        # References often start with "The X, referred to in..."
        parts = re.split(r"(?<=\.)\s+(?=[A-Z])", ref_text)
        for part in parts:
            part = part.strip()
            if part and len(part) > 20:  # Skip very short fragments
                references.append(part[:500])  # Limit length

    return references


def _parse_notes_structure(raw_notes: str, notes: SectionNotes) -> None:
    """Parse all structured fields from raw notes text.

    Args:
        raw_notes: The raw notes text.
        notes: SectionNotes object to populate.
    """
    # Citations
    notes.citations = parse_citations(raw_notes)

    # Check for section status
    if re.search(r"\bTransferred\b", raw_notes[:100], re.IGNORECASE):
        # Try to find where it was transferred to
        transfer_match = re.search(
            r"reclassified as section (\d+[a-z]?) of Title (\d+)",
            raw_notes,
            re.IGNORECASE,
        )
        if transfer_match:
            notes.transferred_to = f"{transfer_match.group(2)} U.S.C. § {transfer_match.group(1)}"
        else:
            notes.transferred_to = "another location"

    if re.search(r"\bOmitted\b", raw_notes[:100], re.IGNORECASE):
        notes.omitted = True

    # Historical and Revision Notes
    hist_match = re.search(
        r"Historical and Revision Notes\s*(.*?)(?=Editorial Notes|Statutory Notes|$)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if hist_match:
        notes.historical_revision_notes = hist_match.group(1).strip()
        notes.historical_notes = notes.historical_revision_notes  # Legacy

    # Editorial Notes section
    edit_match = re.search(
        r"Editorial Notes\s*(.*?)(?=Statutory Notes|$)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if edit_match:
        editorial_text = edit_match.group(1).strip()
        notes.editorial_notes = editorial_text  # Legacy

        # Parse subsections within Editorial Notes
        # Codification
        codif_match = re.search(
            r"Codification\s+(.*?)(?=References in Text|Amendments|Prior Provisions|$)",
            editorial_text,
            re.DOTALL | re.IGNORECASE,
        )
        if codif_match:
            notes.codification = codif_match.group(1).strip()

        # References in Text
        notes.references_in_text = _parse_references_in_text(editorial_text)

        # Amendments
        amend_match = re.search(
            r"Amendments\s+(.*?)(?=Prior Provisions|$)",
            editorial_text,
            re.DOTALL | re.IGNORECASE,
        )
        if amend_match:
            notes.amendments = _parse_amendments(amend_match.group(1))

        # Prior Provisions
        prior_match = re.search(
            r"Prior Provisions?\s+(.*?)$",
            editorial_text,
            re.DOTALL | re.IGNORECASE,
        )
        if prior_match:
            notes.prior_provisions = prior_match.group(1).strip()

    # Statutory Notes section
    stat_match = re.search(
        r"Statutory Notes and Related Subsidiaries\s*(.*)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if stat_match:
        statutory_text = stat_match.group(1).strip()
        notes.statutory_notes = statutory_text  # Legacy

        # Parse subsections within Statutory Notes
        # Effective Dates
        notes.effective_dates = _parse_effective_dates(statutory_text)

        # Short Titles
        notes.short_titles = _parse_short_titles(statutory_text)

        # Regulations
        reg_match = re.search(
            r"Regulations?\s+(.*?)(?=Change of Name|Transfer of Functions|Termination|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if reg_match:
            notes.regulations = reg_match.group(1).strip()[:500]

        # Change of Name
        name_match = re.search(
            r"Change of Name\s+(.*?)(?=Transfer of Functions|Termination|Effective Date|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if name_match:
            notes.change_of_name = name_match.group(1).strip()[:500]

        # Transfer of Functions
        transfer_match = re.search(
            r"Transfer of Functions\s+(.*?)(?=Termination|Effective Date|Change of Name|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if transfer_match:
            notes.transfer_of_functions = transfer_match.group(1).strip()[:500]

        # Definitions
        def_match = re.search(
            r"Definitions?\s+(.*?)(?=Effective Date|Short Title|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if def_match:
            notes.definitions = def_match.group(1).strip()[:500]

        # Construction
        const_match = re.search(
            r"Construction\s+(.*?)(?=Effective Date|Short Title|Regulations|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if const_match:
            notes.construction = const_match.group(1).strip()[:500]

        # Savings Provision
        save_match = re.search(
            r"Savings? Provisions?\s+(.*?)(?=Effective Date|Short Title|$)",
            statutory_text,
            re.DOTALL | re.IGNORECASE,
        )
        if save_match:
            notes.savings_provision = save_match.group(1).strip()[:500]


def _separate_notes_from_text(text: str) -> tuple[str, SectionNotes]:
    """Separate law text from notes/metadata sections.

    US Code sections often include historical notes, editorial notes,
    and other metadata after the actual law text. This function splits
    them apart.

    Args:
        text: The full section text including notes.

    Returns:
        Tuple of (law_text, SectionNotes).
    """
    notes = SectionNotes()

    # Find the earliest notes section header
    earliest_notes_pos = len(text)
    for header in NOTES_SECTION_HEADERS:
        # Look for the header, possibly with leading whitespace/newlines
        pattern = re.compile(rf"[\s\n]+{re.escape(header)}", re.IGNORECASE)
        match = pattern.search(text)
        if match and match.start() < earliest_notes_pos:
            earliest_notes_pos = match.start()

    # Also check for citation blocks like "( Pub. L. 94–553..."
    # These often appear right before the notes sections
    citation_match = CITATION_BLOCK_PATTERN.search(text)
    if citation_match and citation_match.start() < earliest_notes_pos:
        # Only use citation as split point if it's near the end of the content
        # (not a citation reference in the middle of the text)
        text_before_citation = text[:citation_match.start()].strip()
        # Check if the text before citation looks complete (ends with period or list item)
        if text_before_citation and (
            text_before_citation.endswith(".")
            or text_before_citation.endswith(";")
            or re.search(r"\([a-zA-Z0-9]+\)\s*$", text_before_citation)
        ):
            earliest_notes_pos = citation_match.start()

    # Split the text
    law_text = text[:earliest_notes_pos].strip()
    raw_notes = text[earliest_notes_pos:].strip()

    if raw_notes:
        notes.raw_notes = raw_notes
        _parse_notes_structure(raw_notes, notes)

    return law_text, notes


def normalize_section(
    text: str,
    use_tabs: bool = True,
    indent_width: int = 4,
    strip_notes: bool = True,
) -> NormalizedSection:
    """Normalize a section of legal text into lines.

    Args:
        text: The raw legal text to normalize.
        use_tabs: If True, use tab characters for indentation. If False, use spaces.
        indent_width: Number of spaces per indent level (only used if use_tabs=False).
        strip_notes: If True, separate historical/editorial notes from law text.

    Returns:
        NormalizedSection with lines and metadata.
    """
    # Separate notes from law text if requested
    if strip_notes:
        law_text, notes = _separate_notes_from_text(text)
    else:
        law_text = text
        notes = SectionNotes()

    lines: list[NormalizedLine] = []
    line_number = 0

    # Process the law text (not the notes)
    # Split by list item markers and sentences

    pos = 0
    current_indent = 0

    while pos < len(law_text):
        # Check if we're at a list item marker
        match = LIST_ITEM_PATTERN.match(law_text, pos)

        # Skip if this is a reference like "subsection (a)" rather than a marker
        if match and _is_reference_not_marker(law_text, match.start(1)):
            match = None

        if match:
            # Found a list item
            marker_text = match.group(0).strip()
            marker_end = match.end()

            # Find the end of this list item (next marker or end of meaningful content)
            # Skip any matches that are references
            search_pos = marker_end
            next_marker = None
            while search_pos < len(law_text):
                candidate = LIST_ITEM_PATTERN.search(law_text, search_pos)
                if not candidate:
                    break
                if not _is_reference_not_marker(law_text, candidate.start(1)):
                    next_marker = candidate
                    break
                search_pos = candidate.end()

            if next_marker:
                item_end = next_marker.start()
            else:
                item_end = len(law_text)

            # Get the content of this list item
            item_content = law_text[marker_end:item_end].strip()

            # Determine indent level from marker
            indent_level = _detect_marker_level(marker_text)
            current_indent = indent_level

            # Check if content has a subsection header (e.g., "Registration requirements")
            header, remaining_content = _extract_subsection_header(item_content)

            if header and remaining_content:
                # Split into header line and content line
                # Header line: marker + header
                line_number += 1
                lines.append(
                    NormalizedLine(
                        line_number=line_number,
                        content=f"{marker_text} {header}",
                        indent_level=indent_level,
                        marker=marker_text,
                        start_char=pos,
                        end_char=marker_end + len(header),
                    )
                )

                # Content line: indented under the header
                line_number += 1
                lines.append(
                    NormalizedLine(
                        line_number=line_number,
                        content=remaining_content,
                        indent_level=indent_level + 1,  # Indent under header
                        marker=None,
                        start_char=marker_end + len(header),
                        end_char=item_end,
                    )
                )
            else:
                # No header detected - keep as single line
                full_content = f"{marker_text} {item_content}" if item_content else marker_text
                line_number += 1
                lines.append(
                    NormalizedLine(
                        line_number=line_number,
                        content=full_content,
                        indent_level=indent_level,
                        marker=marker_text,
                        start_char=pos,
                        end_char=item_end,
                    )
                )

            pos = item_end

        else:
            # Not a list item - process as sentences
            # Find the next list item marker to know where to stop
            # Skip any matches that are references
            search_pos = pos
            next_marker = None
            while search_pos < len(law_text):
                candidate = LIST_ITEM_PATTERN.search(law_text, search_pos)
                if not candidate:
                    break
                if not _is_reference_not_marker(law_text, candidate.start(1)):
                    next_marker = candidate
                    break
                search_pos = candidate.end()

            if next_marker:
                segment_end = next_marker.start()
            else:
                segment_end = len(law_text)

            segment = law_text[pos:segment_end]

            # Split this segment into sentences
            sentences = _split_into_sentences(segment, start_offset=pos)

            for sentence_text, start_char, end_char in sentences:
                if sentence_text.strip():
                    line_number += 1
                    lines.append(
                        NormalizedLine(
                            line_number=line_number,
                            content=sentence_text.strip(),
                            indent_level=current_indent,
                            marker=None,
                            start_char=start_char,
                            end_char=end_char,
                        )
                    )

            pos = segment_end

    # Normalize indentation to be relative (minimum indent becomes 1, not 0)
    # This handles cases like § 106 where (1), (2) are top-level (no parent (a))
    indented_lines = [line for line in lines if line.indent_level > 0]
    if indented_lines:
        min_indent = min(line.indent_level for line in indented_lines)
        if min_indent > 1:
            # Shift all indents down so the minimum becomes 1
            shift = min_indent - 1
            for line in indented_lines:
                line.indent_level -= shift

    # Build the normalized text with proper indentation
    normalized_lines = [line.to_display(use_tabs=use_tabs, indent_width=indent_width) for line in lines]
    normalized_text = "\n".join(normalized_lines)

    return NormalizedSection(
        lines=lines,
        original_text=text,
        normalized_text=normalized_text,
        law_text=law_text,
        notes=notes,
    )


def char_span_to_line_span(
    normalized: NormalizedSection,
    start_char: int,
    end_char: int,
) -> tuple[int, int] | None:
    """Convert a character span to a line span.

    Args:
        normalized: The normalized section.
        start_char: Start character position in original text.
        end_char: End character position in original text.

    Returns:
        Tuple of (start_line, end_line) as 1-indexed line numbers,
        or None if the span doesn't map to any lines.
    """
    start_line = None
    end_line = None

    for line in normalized.lines:
        # Check if this line overlaps with the character span
        if line.end_char > start_char and line.start_char < end_char:
            if start_line is None:
                start_line = line.line_number
            end_line = line.line_number

    if start_line is not None and end_line is not None:
        return (start_line, end_line)
    return None


def _add_blank_line(
    lines: list[NormalizedLine],
    line_counter: list[int],
    char_pos: list[int],
) -> None:
    """Add a blank line for visual separation."""
    line_counter[0] += 1
    start_pos = char_pos[0]
    char_pos[0] += 1  # Just the newline
    lines.append(
        NormalizedLine(
            line_number=line_counter[0],
            content="",
            indent_level=0,
            marker=None,
            start_char=start_pos,
            end_char=char_pos[0],
        )
    )


def _normalize_subsection_recursive(
    subsection: ParsedSubsection,
    lines: list[NormalizedLine],
    line_counter: list[int],  # Mutable counter passed by reference
    char_pos: list[int],  # Mutable position tracker
    base_indent: int = 0,  # Starting indent level for this subsection
) -> None:
    """Recursively normalize a subsection and its children into lines.

    Args:
        subsection: The subsection to normalize.
        lines: List to append lines to.
        line_counter: Mutable list containing [current_line_number].
        char_pos: Mutable list containing [current_char_position].
        base_indent: The indent level for this subsection's header/marker line.
    """
    # If there's a heading, create a separate header line
    if subsection.heading:
        # Add blank line before headers (for readability), except for the first line
        if lines:
            _add_blank_line(lines, line_counter, char_pos)

        line_counter[0] += 1
        header_content = f"{subsection.marker} {subsection.heading}"
        start_pos = char_pos[0]
        char_pos[0] += len(header_content) + 1  # +1 for newline
        lines.append(
            NormalizedLine(
                line_number=line_counter[0],
                content=header_content,
                indent_level=base_indent,
                marker=subsection.marker,
                start_char=start_pos,
                end_char=char_pos[0],
            )
        )

        # Content goes on a separate line, indented under the header
        if subsection.content:
            line_counter[0] += 1
            start_pos = char_pos[0]
            char_pos[0] += len(subsection.content) + 1
            lines.append(
                NormalizedLine(
                    line_number=line_counter[0],
                    content=subsection.content,
                    indent_level=base_indent + 1,  # Indent under header
                    marker=None,
                    start_char=start_pos,
                    end_char=char_pos[0],
                )
            )

        # Children are indented under the content (base + 2)
        child_indent = base_indent + 2
    else:
        # No heading - marker and content on one line
        if subsection.content:
            line_counter[0] += 1
            content = f"{subsection.marker} {subsection.content}" if subsection.marker else subsection.content
            start_pos = char_pos[0]
            char_pos[0] += len(content) + 1
            lines.append(
                NormalizedLine(
                    line_number=line_counter[0],
                    content=content,
                    indent_level=base_indent,
                    marker=subsection.marker if subsection.marker else None,
                    start_char=start_pos,
                    end_char=char_pos[0],
                )
            )
        elif subsection.marker:
            # Just a marker with no content (rare but possible)
            line_counter[0] += 1
            start_pos = char_pos[0]
            char_pos[0] += len(subsection.marker) + 1
            lines.append(
                NormalizedLine(
                    line_number=line_counter[0],
                    content=subsection.marker,
                    indent_level=base_indent,
                    marker=subsection.marker,
                    start_char=start_pos,
                    end_char=char_pos[0],
                )
            )

        # Children are indented one level deeper
        child_indent = base_indent + 1

    # Process children recursively with increased indent
    for child in subsection.children:
        _normalize_subsection_recursive(child, lines, line_counter, char_pos, child_indent)


def normalize_parsed_section(
    parsed_section: ParsedSection,
    use_tabs: bool = True,
    indent_width: int = 4,
) -> NormalizedSection:
    """Normalize a ParsedSection using its structured subsection data.

    This function uses the explicit heading/content structure from XML
    rather than heuristic-based header detection.

    Args:
        parsed_section: A ParsedSection with subsections populated.
        use_tabs: If True, use tab characters for indentation.
        indent_width: Number of spaces per indent level (if use_tabs=False).

    Returns:
        NormalizedSection with lines generated from structured data.
    """
    lines: list[NormalizedLine] = []
    line_counter = [0]  # Mutable counter
    char_pos = [0]  # Mutable position tracker

    # Process each top-level subsection
    for subsection in parsed_section.subsections:
        _normalize_subsection_recursive(subsection, lines, line_counter, char_pos)

    # Build normalized text
    normalized_lines = [
        line.to_display(use_tabs=use_tabs, indent_width=indent_width)
        for line in lines
    ]
    normalized_text = "\n".join(normalized_lines)

    # Parse notes/citations from the notes text
    notes = SectionNotes()
    if parsed_section.notes:
        notes.raw_notes = parsed_section.notes
        _parse_notes_structure(parsed_section.notes, notes)

    return NormalizedSection(
        lines=lines,
        original_text=parsed_section.text_content,
        normalized_text=normalized_text,
        law_text=parsed_section.text_content,
        notes=notes,
    )
