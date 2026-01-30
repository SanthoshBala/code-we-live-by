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

import re
from dataclasses import dataclass, field

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
    r"Termination of",
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
class SectionNotes:
    """Metadata notes extracted from a US Code section.

    These are separated from the law text and treated like documentation:
    - citations: Public Law citations (parsed as structured data)
    - historical_notes: Historical and revision notes
    - editorial_notes: Editorial notes, amendments, codification info
    - statutory_notes: Statutory notes and related subsidiaries
    """

    citations: list[Citation] = field(default_factory=list)
    historical_notes: str = ""
    editorial_notes: str = ""
    statutory_notes: str = ""
    raw_notes: str = ""  # Everything after the law text

    @property
    def has_notes(self) -> bool:
        """Return True if any notes were extracted."""
        return bool(self.raw_notes.strip())

    @property
    def has_citations(self) -> bool:
        """Return True if any citations were parsed."""
        return len(self.citations) > 0


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

        # Extract specific note sections
        # Citations (Pub. L. references) - parse into structured data
        notes.citations = parse_citations(raw_notes)

        # Historical notes
        hist_match = re.search(
            r"Historical and Revision Notes\s*(.*?)(?=Editorial Notes|Statutory Notes|$)",
            raw_notes,
            re.DOTALL | re.IGNORECASE,
        )
        if hist_match:
            notes.historical_notes = hist_match.group(1).strip()

        # Editorial notes
        edit_match = re.search(
            r"Editorial Notes\s*(.*?)(?=Statutory Notes|$)",
            raw_notes,
            re.DOTALL | re.IGNORECASE,
        )
        if edit_match:
            notes.editorial_notes = edit_match.group(1).strip()

        # Statutory notes
        stat_match = re.search(
            r"Statutory Notes and Related Subsidiaries\s*(.*)",
            raw_notes,
            re.DOTALL | re.IGNORECASE,
        )
        if stat_match:
            notes.statutory_notes = stat_match.group(1).strip()

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

            # The full line includes the marker
            full_content = f"{marker_text} {item_content}" if item_content else marker_text

            # If the content is very long, we might want to split into sentences
            # But for now, keep list items as single lines
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
