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
from typing import TYPE_CHECKING

from app.models.enums import LawLevel, SourceRelationship
from app.schemas import (
    ActSchema,
    AmendmentSchema,
    CodeLineSchema,
    CodeReferenceSchema,
    LawPathComponent,
    NoteCategoryEnum,
    PublicLawSchema,
    SectionNoteSchema,
    SectionNotesSchema,
    ShortTitleSchema,
    SourceLawSchema,
)

if TYPE_CHECKING:
    from pipeline.olrc.parser import (
        ActRef,
        ParsedSection,
        ParsedSubsection,
        SourceCreditRef,
    )

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
    "subsection",
    "subsections",
    "paragraph",
    "paragraphs",
    "subparagraph",
    "subparagraphs",
    "clause",
    "clauses",
    "subclause",
    "subclauses",
}

# Pattern to detect the nesting level from a marker
MARKER_PATTERN = re.compile(r"\(([a-zA-Z0-9]+)\)")

# Words that commonly start sentences in legal text (after a subsection header)
SENTENCE_STARTERS = {
    "a",
    "an",
    "the",
    "no",
    "any",
    "each",
    "if",
    "for",
    "in",
    "on",
    "to",
    "as",
    "by",
    "under",
    "subject",
    "notwithstanding",
    "unless",
    "except",
    "upon",
    "after",
    "before",
    "when",
    "where",
    "this",
    "that",
    "such",
    "nothing",
    "whoever",
    "whenever",
    "every",
    "all",
    "there",
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
        remaining = content[match.end(2) :].strip()

        # Validate: header should be 1-6 words, remaining should start with sentence starter
        words = header.split()
        if 1 <= len(words) <= 6:
            # Check if remaining starts with a sentence starter
            first_word = remaining.split()[0].lower() if remaining.split() else ""
            if first_word.rstrip(".,;") in SENTENCE_STARTERS or remaining.startswith(
                "—"
            ):
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
    r"Prior ParsedLines",
    r"Effective Date",
    r"Short Title",
    r"Regulations",
    r"Transfer of Functions",
    r"Savings ParsedLine",
]

# Pattern to detect the citation block that often appears at the end of law text
# e.g., "( Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546; ..."
CITATION_BLOCK_PATTERN = re.compile(
    r"\(\s*Pub\.\s*L\.\s+\d+[–-]\d+.*?(?=Historical|Editorial|Statutory|$)",
    re.DOTALL | re.IGNORECASE,
)


# =============================================================================
# Type aliases for backwards compatibility
# These map old names to new Pydantic schema names
# =============================================================================
ParsedLine = CodeLineSchema
ParsedPublicLaw = PublicLawSchema
SourceLaw = SourceLawSchema
CodeReference = CodeReferenceSchema
Amendment = AmendmentSchema
ShortTitle = ShortTitleSchema
NoteCategory = NoteCategoryEnum
SectionNote = SectionNoteSchema
SectionNotes = SectionNotesSchema


# Pattern to parse individual citation components
# Matches: "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
# Also handles: "Pub. L. 107–273, div. C, title III, § 13210(4)(A), Nov. 2, 2002"
# Note: Source text may have extra whitespace around commas (e.g., " ,  ")
CITATION_PARSE_PATTERN = re.compile(
    r"Pub\.\s*L\.\s*(\d+)[–-](\d+)"  # Congress and law number
    r"(?:\s*,\s*div\.\s*([A-Z]))?"  # Optional division (e.g., "div. C") - capture letter
    r"(?:\s*,\s*title\s+([IVXLCDM]+))?"  # Optional title (roman numeral)
    r"(?:\s*,\s*§+\s*([\d\w]+(?:\([a-z0-9]+\))*))?"  # Optional section
    r"(?:\s*,\s*([A-Z][a-z]{2,3}\.?\s+\d{1,2}\s*,\s+\d{4}))?"  # Optional date
    r"(?:\s*,\s*(\d+)\s+Stat\.\s+(\d+))?",  # Optional Stat reference
    re.IGNORECASE,
)


def _build_law_path(
    division: str | None = None,
    chapter: str | None = None,
    title: str | None = None,
    section: str | None = None,
) -> list[LawPathComponent]:
    """Build a hierarchical path from citation components.

    Args:
        division: Division identifier (e.g., "C")
        chapter: Chapter identifier (e.g., "531") - used for pre-1957 Acts
        title: Title identifier (e.g., "III")
        section: Section identifier (e.g., "101", "13210(4)(A)")

    Returns:
        List of LawPathComponent in hierarchical order.
    """
    path: list[LawPathComponent] = []
    if division:
        path.append(LawPathComponent(level=LawLevel.DIVISION, value=division))
    if chapter:
        path.append(LawPathComponent(level=LawLevel.CHAPTER, value=chapter))
    if title:
        path.append(LawPathComponent(level=LawLevel.TITLE, value=title))
    if section:
        path.append(LawPathComponent(level=LawLevel.SECTION, value=section))
    return path


def parse_citation(text: str) -> SourceLaw | None:
    """Parse a citation string into a SourceLaw object.

    Args:
        text: Raw citation text like "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"

    Returns:
        SourceLaw object or None if parsing fails.
    """
    match = CITATION_PARSE_PATTERN.search(text)
    if not match:
        return None

    congress = int(match.group(1))
    law_number = int(match.group(2))
    division = match.group(3)  # May be None
    title = match.group(4)  # May be None
    section = match.group(5)  # May be None
    date = match.group(6)  # May be None
    stat_volume = int(match.group(7)) if match.group(7) else None
    stat_page = int(match.group(8)) if match.group(8) else None

    law = ParsedPublicLaw(
        congress=congress,
        law_number=law_number,
        date=date,
        stat_volume=stat_volume,
        stat_page=stat_page,
    )

    return SourceLaw(
        law=law,
        path=_build_law_path(division=division, title=title, section=section),
        raw_text=text.strip(),
    )


def parse_citations(text: str) -> list[SourceLaw]:
    """Parse all citations from a text block.

    Citations are separated by semicolons within the parenthetical block.
    They are returned in chronological order (as they appear in the source),
    with order=0 being the original/creating law.

    Args:
        text: Text containing one or more citations.

    Returns:
        List of parsed SourceLaw objects with order field set.
    """
    citations: list[SourceLaw] = []

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


def citations_from_source_credit_refs(
    refs: list[SourceCreditRef],
    act_refs: list[ActRef] | None = None,
) -> list[SourceLaw]:
    """Convert structured SourceCreditRef and ActRef objects to SourceLaw objects.

    This is the preferred method for getting citations when XML structure
    is available, as it avoids regex parsing pitfalls.

    Args:
        refs: List of SourceCreditRef from parser (Public Laws, post-1957).
        act_refs: List of ActRef from parser (Acts, pre-1957).

    Returns:
        List of SourceLaw objects with order field set.
        Framework (Act) references come first, then Enactment, then Amendments.
    """
    citations: list[SourceLaw] = []
    order = 0

    # First, add any Act references as Framework
    if act_refs:
        for act_ref in act_refs:
            act = ActSchema(
                date=act_ref.date,
                chapter=act_ref.chapter,
                short_title=act_ref.short_title,
                stat_volume=act_ref.stat_volume,
                stat_page=act_ref.stat_page,
            )
            citation = SourceLaw(
                act=act,
                path=_build_law_path(
                    chapter=str(act_ref.chapter),
                    title=act_ref.title,
                    section=act_ref.section,
                ),
                relationship=SourceRelationship.FRAMEWORK,
                raw_text=act_ref.raw_text,
                order=order,
            )
            citations.append(citation)
            order += 1

    # Then add Public Law references
    for i, ref in enumerate(refs):
        law = ParsedPublicLaw(
            congress=ref.congress,
            law_number=ref.law_number,
            date=ref.date,
            stat_volume=ref.stat_volume,
            stat_page=ref.stat_page,
        )
        # First PL is Enactment, rest are Amendments
        relationship = (
            SourceRelationship.ENACTMENT if i == 0 else SourceRelationship.AMENDMENT
        )
        citation = SourceLaw(
            law=law,
            path=_build_law_path(
                division=ref.division, title=ref.title, section=ref.section
            ),
            relationship=relationship,
            raw_text=ref.raw_text,
            order=order,
        )
        citations.append(citation)
        order += 1

    return citations


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
        if re.match(
            r"^(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{1,3}|xiv|xv|xvi{0,3}|xix|xx)$", lower
        ):
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
    if (
        pos >= 1
        and text[pos - 1].isupper()
        and (pos < 2 or not text[pos - 2].isalnum())
    ):
        # Single uppercase letter followed by period - likely abbreviation
        # unless it's the end of a sentence like "Plan B."
        pass  # Allow this for now, common abbreviations are in the list

    return True


PARAGRAPH_BREAK_MARKER = "[__PARA_BREAK__]"


def _split_into_sentences(
    text: str, start_offset: int = 0
) -> list[tuple[str, int, int]]:
    """Split text into sentences, returning (content, start_char, end_char) tuples.

    The start_char and end_char are relative to the original text using start_offset.
    A tuple with PARAGRAPH_BREAK_MARKER as content indicates a paragraph break.
    """
    sentences = []
    current_start = 0
    i = 0

    while i < len(text):
        # Check for paragraph break (double newline)
        if text[i : i + 2] == "\n\n":
            # Emit any pending sentence before the paragraph break
            sentence = text[current_start:i].strip()
            if sentence:
                sentences.append(
                    (sentence, start_offset + current_start, start_offset + i)
                )
            # Add paragraph break marker
            sentences.append((PARAGRAPH_BREAK_MARKER, 0, 0))
            # Skip the double newline and any additional whitespace
            i += 2
            while i < len(text) and text[i] in " \t\n":
                i += 1
            current_start = i
        elif text[i] == "." and _is_sentence_boundary(text, i):
            # Found sentence boundary
            sentence = text[current_start : i + 1].strip()
            if sentence:
                sentences.append(
                    (sentence, start_offset + current_start, start_offset + i + 1)
                )
            current_start = i + 1
            # Skip whitespace after sentence, but detect paragraph breaks
            while current_start < len(text) and text[current_start] in " \t\n":
                # Check for paragraph break while skipping whitespace
                if text[current_start : current_start + 2] == "\n\n":
                    sentences.append((PARAGRAPH_BREAK_MARKER, 0, 0))
                    current_start += 2
                    # Continue skipping any remaining whitespace
                    while current_start < len(text) and text[current_start] in " \t\n":
                        current_start += 1
                    break
                current_start += 1
            i = current_start
        else:
            i += 1

    # Don't forget the last segment if it doesn't end with a period
    remaining = text[current_start:].strip()
    if remaining:
        sentences.append(
            (remaining, start_offset + current_start, start_offset + len(text))
        )

    return sentences


def normalize_note_content(text: str) -> list[ParsedLine]:
    """Normalize note content into ParsedLine structures.

    Converts note text with header markers into structured lines suitable for
    the "law-flavored plain text" format.

    Header markers (inserted by parser):
    - [H1]...[/H1]: Bold headers (section-level)
    - [H2]...[/H2]: Italic sub-headers
    - [QC:level]...[/QC]: Quoted content items with indent level

    Args:
        text: The note content text with optional header markers.

    Returns:
        List of ParsedLine objects representing the normalized content.
    """
    lines: list[ParsedLine] = []
    line_number = 0

    # Clean up the text
    text = text.strip()
    if not text:
        return lines

    # First, process any quoted content markers [QC:level]...[/QC]
    # These should be converted to properly indented lines
    qc_pattern = re.compile(r"\[QC:(\d+)\](.*?)\[/QC\]", re.DOTALL)

    def extract_marker(content: str) -> tuple[str | None, str]:
        """Extract marker like '(a)' or '(1)' from start of content."""
        marker_match = re.match(r'^("[(\[]\w+[)\]]"?)\s*', content)
        if marker_match:
            marker = marker_match.group(1)
            rest = content[marker_match.end():].strip()
            return marker, rest
        return None, content

    # Replace QC markers with structured lines
    # Process QC markers in order, building lines
    qc_matches = list(qc_pattern.finditer(text))
    if qc_matches:
        # Split text into parts: before first QC, QC blocks, and between/after
        new_text_parts = []
        last_qc_end = 0

        for qc_match in qc_matches:
            # Add text before this QC block
            before = text[last_qc_end:qc_match.start()]
            if before.strip():
                new_text_parts.append(before)

            # Process the QC content
            level = int(qc_match.group(1))
            content = qc_match.group(2).strip()
            marker, rest = extract_marker(content)

            # Add as a special marker that will be processed later
            # Format: [QCLINE:level:marker]content
            marker_str = marker if marker else ""
            new_text_parts.append(f"[QCLINE:{level}:{marker_str}]{rest}[/QCLINE]")

            last_qc_end = qc_match.end()

        # Add any remaining text after last QC
        after = text[last_qc_end:]
        if after.strip():
            new_text_parts.append(after)

        text = "\n".join(new_text_parts)

    # Pattern to split text into header and non-header segments
    # Matches [H1]...[/H1] or [H2]...[/H2] or [QCLINE:...] or regular text
    header_pattern = re.compile(
        r"\[H1\](.*?)\[/H1\]|\[H2\](.*?)\[/H2\]|\[QCLINE:(\d+):([^\]]*)\](.*?)\[/QCLINE\]",
        re.DOTALL,
    )

    # Track current indent level (increases after headers)
    current_indent = 1  # Base indent for notes content

    # Process the text, extracting headers and content
    last_end = 0
    for match in header_pattern.finditer(text):
        # Process any text before this header
        before_text = text[last_end : match.start()].strip()
        if before_text:
            # Split into sentences
            sentences = _split_into_sentences(before_text, start_offset=last_end)
            for sentence_text, start_char, end_char in sentences:
                # Check for paragraph break marker
                if sentence_text == PARAGRAPH_BREAK_MARKER:
                    # Insert blank line for paragraph break
                    line_number += 1
                    lines.append(
                        ParsedLine(
                            line_number=line_number,
                            content="",
                            indent_level=0,
                            marker=None,
                            is_header=False,
                            start_char=0,
                            end_char=0,
                        )
                    )
                    continue
                sentence_text = sentence_text.strip()
                # Skip ".—" artifacts and clean up sub-header separators
                if sentence_text:
                    # Strip leading ".—" or "—" from content following sub-headers
                    sentence_text = re.sub(r"^\.?—\s*", "", sentence_text)
                if sentence_text and sentence_text not in (".—", "—", ".", ""):
                    line_number += 1
                    lines.append(
                        ParsedLine(
                            line_number=line_number,
                            content=sentence_text,
                            indent_level=current_indent,
                            marker=None,
                            is_header=False,
                            start_char=start_char,
                            end_char=end_char,
                        )
                    )

        # Process the header
        h1_text = match.group(1)
        h2_text = match.group(2)

        if h1_text:
            # H1 is a bold header (section-level)
            header_text = h1_text.strip().rstrip(".")
            if header_text:
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content=header_text,
                        indent_level=1,  # H1 headers at indent 1
                        marker=None,
                        is_header=True,
                        start_char=match.start(),
                        end_char=match.end(),
                    )
                )
                current_indent = 2  # Content after H1 is indented

        elif h2_text:
            # H2 is an italic sub-header
            header_text = h2_text.strip().rstrip(".")
            if header_text:
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content=header_text,
                        indent_level=2,  # H2 headers at indent 2
                        marker=None,
                        is_header=True,
                        start_char=match.start(),
                        end_char=match.end(),
                    )
                )
                current_indent = 3  # Content after H2 is indented further

        else:
            # QCLINE - quoted content item with indent level and optional marker
            qc_level = match.group(3)
            qc_marker = match.group(4)
            qc_content = match.group(5)

            if qc_level is not None:
                level = int(qc_level)
                marker = qc_marker.strip() if qc_marker else None
                content = qc_content.strip() if qc_content else ""

                if content or marker:
                    line_number += 1
                    # Indent level: base (current_indent) + level from QC
                    # Quoted content is always indented relative to intro text
                    indent = current_indent + level
                    lines.append(
                        ParsedLine(
                            line_number=line_number,
                            content=content,
                            indent_level=indent,
                            marker=marker,
                            is_header=False,
                            start_char=match.start(),
                            end_char=match.end(),
                        )
                    )

        last_end = match.end()

    # Process any remaining text after the last header
    remaining_text = text[last_end:].strip()
    if remaining_text:
        sentences = _split_into_sentences(remaining_text, start_offset=last_end)
        for sentence_text, start_char, end_char in sentences:
            # Check for paragraph break marker
            if sentence_text == PARAGRAPH_BREAK_MARKER:
                # Insert blank line for paragraph break
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content="",
                        indent_level=0,
                        marker=None,
                        is_header=False,
                        start_char=0,
                        end_char=0,
                    )
                )
                continue
            sentence_text = sentence_text.strip()
            # Skip ".—" artifacts and clean up sub-header separators
            if sentence_text:
                sentence_text = re.sub(r"^\.?—\s*", "", sentence_text)
            if sentence_text and sentence_text not in (".—", "—", ".", ""):
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content=sentence_text,
                        indent_level=current_indent,
                        marker=None,
                        is_header=False,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )

    return lines


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
        end = year_matches[i + 1].start() if i + 1 < len(year_matches) else len(text)

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

            law = ParsedPublicLaw(congress=congress, law_number=law_number)
            amendments.append(
                Amendment(
                    law=law,
                    year=year,
                    description=description,
                )
            )

        # If no Pub. L. found in the block, still record the year with the description
        if not list(pub_l_pattern.finditer(year_block)) and year_block:
            # Try to extract any Pub. L. reference
            simple_pub_match = re.search(r"Pub\.\s*L\.\s*(\d+)[—–-](\d+)", year_block)
            if simple_pub_match:
                congress = int(simple_pub_match.group(1))
                law_number = int(simple_pub_match.group(2))
                law = ParsedPublicLaw(congress=congress, law_number=law_number)
                amendments.append(
                    Amendment(
                        law=law,
                        year=year,
                        description=" ".join(year_block.split()),
                    )
                )
            # Skip amendments where we can't extract congress/law_number
            # since we need valid law references

    return amendments


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
            name_match = re.search(
                r"(?:cited as|known as)(?: the)?\s+['\"]?([^'\"]+(?:Act|Law)[^'\"]*)",
                description,
                re.IGNORECASE,
            )
            title = name_match.group(1).strip() if name_match else description[:100]

        # Extract year
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        year = int(year_match.group(1)) if year_match else None

        # Extract Pub. L.
        pub_l_match = re.search(r"Pub\.\s*L\.\s*\d+[—–-]\d+", description)
        public_law = pub_l_match.group(0) if pub_l_match else None

        short_titles.append(
            ShortTitle(
                title=title,
                year=year,
                public_law=public_law,
            )
        )

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
        r"References in Text\s+(.*?)(?=Codification|Amendments|Prior ParsedLines|$)",
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


def _parse_notes_structure(
    raw_notes: str,
    notes: SectionNotes,
    citations: list[SourceLaw] | None = None,
) -> None:
    """Parse all structured fields from raw notes text.

    Extracts both structured fields (citations, amendments, effective_dates,
    short_titles) and dynamic SectionNote objects for all other notes.

    Args:
        raw_notes: The raw notes text.
        notes: SectionNotes object to populate.
        citations: Pre-parsed citations from XML structure. If provided,
            these are used instead of regex-parsing the notes text.
    """
    # Citations: use pre-parsed if available, otherwise fall back to regex
    if citations is not None:
        notes.citations = citations
    else:
        notes.citations = parse_citations(raw_notes)

    # Check for section status
    if re.search(r"\bTransferred\b", raw_notes[:100], re.IGNORECASE):
        transfer_match = re.search(
            r"reclassified as section (\d+[a-z]?) of Title (\d+)",
            raw_notes,
            re.IGNORECASE,
        )
        if transfer_match:
            notes.transferred_to = (
                f"{transfer_match.group(2)} U.S.C. § {transfer_match.group(1)}"
            )
        else:
            notes.transferred_to = "another location"

    if re.search(r"\bOmitted\b", raw_notes[:100], re.IGNORECASE):
        notes.omitted = True

    # Parse the three main sections and extract notes from each
    _parse_historical_notes(raw_notes, notes)
    _parse_editorial_notes(raw_notes, notes)
    _parse_statutory_notes(raw_notes, notes)


def _parse_historical_notes(raw_notes: str, notes: SectionNotes) -> None:
    """Parse Historical and Revision Notes section."""
    # Match until next major section (with optional [H1] prefix)
    hist_match = re.search(
        r"Historical and Revision Notes\s*(.*?)(?=\[H1\]Editorial Notes|\[H1\]Statutory Notes|Editorial Notes|Statutory Notes|$)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if not hist_match:
        return

    hist_text = hist_match.group(1).strip()
    if not hist_text:
        return

    # Look for report headers (e.g., "House Report No. 94-1476")
    # These are the primary sub-divisions in historical notes
    report_pattern = re.compile(
        r"((?:House|Senate)\s+Report\s+No\.\s*[\d–-]+)",
        re.IGNORECASE,
    )

    matches = list(report_pattern.finditer(hist_text))
    if not matches:
        # No sub-headers, treat the whole section as one note
        notes.notes.append(
            SectionNote(
                header="Historical and Revision Notes",
                content=hist_text,
                lines=normalize_note_content(hist_text),
                category=NoteCategory.HISTORICAL,
            )
        )
        return

    # Extract unique report sections
    seen_headers: set[str] = set()
    for i, match in enumerate(matches):
        header = match.group(1).strip().title()
        if header in seen_headers:
            continue
        seen_headers.add(header)

        # Content runs from end of this header to start of next header (or end)
        content_start = match.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(hist_text)
        content = hist_text[content_start:content_end].strip()

        if content:
            notes.notes.append(
                SectionNote(
                    header=header,
                    content=content,
                    lines=normalize_note_content(content),
                    category=NoteCategory.HISTORICAL,
                )
            )


def _parse_editorial_notes(raw_notes: str, notes: SectionNotes) -> None:
    """Parse Editorial Notes section."""
    # Match "Editorial Notes" and capture until "Statutory Notes" (with optional [H1] prefix)
    edit_match = re.search(
        r"Editorial Notes\s*(.*?)(?=\[H1\]Statutory Notes|\[H1\]Editorial Notes|Statutory Notes|$)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if not edit_match:
        return

    editorial_text = edit_match.group(1).strip()
    if not editorial_text:
        return

    # Known editorial note headers in order they typically appear
    editorial_headers = [
        "Codification",
        "References in Text",
        "Amendments",
        "Prior ParsedLines",
    ]

    # Find positions of each header
    header_positions: list[tuple[int, str]] = []
    for header in editorial_headers:
        pattern = re.compile(rf"\b{re.escape(header)}\b", re.IGNORECASE)
        match = pattern.search(editorial_text)
        if match:
            header_positions.append((match.start(), header))

    # Sort by position
    header_positions.sort(key=lambda x: x[0])

    # Extract content for each header
    seen_headers: set[str] = set()
    for i, (pos, header) in enumerate(header_positions):
        if header in seen_headers:
            continue
        seen_headers.add(header)

        # Content starts after header, ends at next header or end
        # Find where header text ends
        header_match = re.search(
            rf"\b{re.escape(header)}\b", editorial_text[pos:], re.IGNORECASE
        )
        start = pos + header_match.end() if header_match else pos + len(header)

        # End at next header or end of text
        if i + 1 < len(header_positions):
            end = header_positions[i + 1][0]
        else:
            end = len(editorial_text)

        content = editorial_text[start:end].strip()
        if content:
            # Special handling for Amendments - also populate structured field
            if header == "Amendments":
                notes.amendments = _parse_amendments(content)

            notes.notes.append(
                SectionNote(
                    header=header,
                    content=content,
                    lines=normalize_note_content(content),
                    category=NoteCategory.EDITORIAL,
                )
            )


def _parse_statutory_notes(raw_notes: str, notes: SectionNotes) -> None:
    """Parse Statutory Notes section."""
    stat_match = re.search(
        r"Statutory Notes and Related Subsidiaries\s*(.*)",
        raw_notes,
        re.DOTALL | re.IGNORECASE,
    )
    if not stat_match:
        return

    statutory_text = stat_match.group(1).strip()
    if not statutory_text:
        return

    # Parse structured fields
    # Note: Effective dates are not parsed structurally - they're captured as
    # SectionNote objects because their content is free-form prose with complex
    # cross-references that don't lend themselves to structured extraction.
    notes.short_titles = _parse_short_titles(statutory_text)

    # Capture law-specific headers that appear in title case
    # Pattern: Title Case Words (at least 2 words, capitalized)
    # Include "YYYY Amendment" suffix for "Effective Date Of YYYY Amendment" patterns
    # The lookahead matches: newline, end, "Pub.", "Amendment by", or a capital letter
    # starting prose content (like "Effective Date Section applicable...")
    all_header_pattern = re.compile(
        r"(?:^|\n)\s*"
        r"([A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|[Oo]f|[Aa]nd|[Tt]he|[Ff]or))+"
        r"(?:\s+\d{4}\s+Amendment)?)"  # Include "YYYY Amendment" suffix (no leading "of")
        r"\s*(?=\n|$|Pub\.|Amendment\s+by\s|[A-Z][a-z])",  # Lookahead includes prose start
        re.MULTILINE,
    )

    # Find all headers and their positions
    header_positions: list[tuple[int, int, str]] = []
    for match in all_header_pattern.finditer(statutory_text):
        header = match.group(1).strip()
        # Skip if too short or a fragment
        if len(header.split()) < 2:
            continue
        # Skip common false positives
        skip_words = {
            "The",
            "And",
            "For",
            "With",
            "From",
            "That",
            "This",
            "Which",
            "Where",
        }
        if header.split()[0] in skip_words:
            continue
        header_positions.append((match.start(), match.end(), header.title()))

    # Deduplicate and extract content
    seen_headers: set[str] = set()
    for i, (_start, end, header) in enumerate(header_positions):
        if header in seen_headers:
            continue
        seen_headers.add(header)

        # Content runs to next header or end
        content_end = (
            header_positions[i + 1][0]
            if i + 1 < len(header_positions)
            else len(statutory_text)
        )
        content = statutory_text[end:content_end].strip()

        if content and len(content) > 30:
            notes.notes.append(
                SectionNote(
                    header=header,
                    content=content,
                    lines=normalize_note_content(content),
                    category=NoteCategory.STATUTORY,
                )
            )


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
        text_before_citation = text[: citation_match.start()].strip()
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
) -> ParsedSection:
    """Normalize a section of legal text into provisions using heuristics.

    This function is used when structured XML data is not available.
    It uses regex patterns to identify list item markers and sentence
    boundaries, then creates provisions with appropriate indentation.

    Args:
        text: The raw legal text to normalize.
        use_tabs: If True, use tab characters for indentation. If False, use spaces.
        indent_width: Number of spaces per indent level (only used if use_tabs=False).
        strip_notes: If True, separate historical/editorial notes from law text.

    Returns:
        ParsedSection with provision fields populated (other fields are empty/default).
    """
    from pipeline.olrc.parser import ParsedSection

    # Separate notes from law text if requested
    if strip_notes:
        law_text, notes = _separate_notes_from_text(text)
    else:
        law_text = text
        notes = SectionNotes()

    lines: list[ParsedLine] = []
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

            item_end = next_marker.start() if next_marker else len(law_text)

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
                    ParsedLine(
                        line_number=line_number,
                        content=f"{marker_text} {header}",
                        indent_level=indent_level,
                        marker=marker_text,
                        is_header=True,
                        start_char=pos,
                        end_char=marker_end + len(header),
                    )
                )

                # Content line: indented under the header
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content=remaining_content,
                        indent_level=indent_level + 1,  # Indent under header
                        marker=None,
                        is_header=False,
                        start_char=marker_end + len(header),
                        end_char=item_end,
                    )
                )
            else:
                # No header detected - keep as single line
                full_content = (
                    f"{marker_text} {item_content}" if item_content else marker_text
                )
                line_number += 1
                lines.append(
                    ParsedLine(
                        line_number=line_number,
                        content=full_content,
                        indent_level=indent_level,
                        marker=marker_text,
                        is_header=False,
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

            segment_end = next_marker.start() if next_marker else len(law_text)

            segment = law_text[pos:segment_end]

            # Split this segment into sentences
            sentences = _split_into_sentences(segment, start_offset=pos)

            for sentence_text, start_char, end_char in sentences:
                if sentence_text.strip():
                    line_number += 1
                    lines.append(
                        ParsedLine(
                            line_number=line_number,
                            content=sentence_text.strip(),
                            indent_level=current_indent,
                            marker=None,
                            is_header=False,
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
    normalized_lines = [
        line.to_display(use_tabs=use_tabs, indent_width=indent_width) for line in lines
    ]
    normalized_text = "\n".join(normalized_lines)

    return ParsedSection(
        section_number="",
        heading="",
        full_citation="",
        text_content=text,
        provisions=lines,
        normalized_text=normalized_text,
        section_notes=notes,
    )


def char_span_to_line_span(
    section: ParsedSection,
    start_char: int,
    end_char: int,
) -> tuple[int, int] | None:
    """Convert a character span to a line span.

    Args:
        section: The parsed section with provisions.
        start_char: Start character position in original text.
        end_char: End character position in original text.

    Returns:
        Tuple of (start_line, end_line) as 1-indexed line numbers,
        or None if the span doesn't map to any lines.
    """
    start_line = None
    end_line = None

    for line in section.provisions:
        # Check if this line overlaps with the character span
        if line.end_char > start_char and line.start_char < end_char:
            if start_line is None:
                start_line = line.line_number
            end_line = line.line_number

    if start_line is not None and end_line is not None:
        return (start_line, end_line)
    return None


def _add_blank_line(
    lines: list[ParsedLine],
    line_counter: list[int],
    char_pos: list[int],
) -> None:
    """Add a blank line for visual separation."""
    line_counter[0] += 1
    start_pos = char_pos[0]
    char_pos[0] += 1  # Just the newline
    lines.append(
        ParsedLine(
            line_number=line_counter[0],
            content="",
            indent_level=0,
            marker=None,
            is_header=False,
            start_char=start_pos,
            end_char=char_pos[0],
        )
    )


def _normalize_subsection_recursive(
    subsection: ParsedSubsection,
    lines: list[ParsedLine],
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
        # Add blank line before headers to separate logical blocks, but only when:
        # 1. The previous line has content (not a header-only line)
        # 2. This header is at the same or shallower level (sibling or moving up)
        #
        # Don't add blank lines when:
        # - Previous line is a header (consecutive headers)
        # - This header is deeper than previous content (subordinate relationship)
        #
        # Example 1 - consecutive headers (no blank line):
        #     L1 │ (a) Appropriation
        #     L2 │     (1) In general       <- deeper header, no blank
        #
        # Example 2 - introductory prose with subordinate list (no blank line):
        #     L1 │ (g) Definitions
        #     L2 │     In this section:     <- prose at level 1
        #     L3 │         (1) Term         <- level 2 header is subordinate, no blank
        #
        # Example 3 - sibling headers after content (blank line):
        #     L1 │         (1) First term
        #     L2 │             Definition of first term.
        #     L3 │                          <- blank line (siblings)
        #     L4 │         (2) Second term
        if lines:
            # Find the last non-blank line to check if it's a header
            last_content_line = None
            for line in reversed(lines):
                if line.content:  # Skip blank lines
                    last_content_line = line
                    break
            # Add blank line only if:
            # - Previous content was not a header, AND
            # - This header is at same or shallower level (sibling or moving up)
            if (
                last_content_line
                and not last_content_line.is_header
                and base_indent <= last_content_line.indent_level
            ):
                _add_blank_line(lines, line_counter, char_pos)

        line_counter[0] += 1
        header_content = f"{subsection.marker} {subsection.heading}"
        start_pos = char_pos[0]
        char_pos[0] += len(header_content) + 1  # +1 for newline
        lines.append(
            ParsedLine(
                line_number=line_counter[0],
                content=header_content,
                indent_level=base_indent,
                marker=subsection.marker,
                is_header=True,
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
                ParsedLine(
                    line_number=line_counter[0],
                    content=subsection.content,
                    indent_level=base_indent + 1,  # Indent under header
                    marker=None,
                    is_header=False,
                    start_char=start_pos,
                    end_char=char_pos[0],
                )
            )

        # Children are indented under the content
        # If there's content, children go at base + 2 (content is at base + 1)
        # If there's no content, children go at base + 1 (directly under header)
        child_indent = base_indent + 2 if subsection.content else base_indent + 1
    else:
        # No heading - marker and content on one line
        if subsection.content:
            line_counter[0] += 1
            content = (
                f"{subsection.marker} {subsection.content}"
                if subsection.marker
                else subsection.content
            )
            start_pos = char_pos[0]
            char_pos[0] += len(content) + 1
            lines.append(
                ParsedLine(
                    line_number=line_counter[0],
                    content=content,
                    indent_level=base_indent,
                    marker=subsection.marker if subsection.marker else None,
                    is_header=False,
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
                ParsedLine(
                    line_number=line_counter[0],
                    content=subsection.marker,
                    indent_level=base_indent,
                    marker=subsection.marker,
                    is_header=False,
                    start_char=start_pos,
                    end_char=char_pos[0],
                )
            )

        # Children are indented one level deeper
        child_indent = base_indent + 1

    # Process children recursively with increased indent
    for child in subsection.children:
        _normalize_subsection_recursive(
            child, lines, line_counter, char_pos, child_indent
        )


def normalize_parsed_section(
    parsed_section: ParsedSection,
    use_tabs: bool = True,
    indent_width: int = 4,
) -> ParsedSection:
    """Normalize a ParsedSection using its structured subsection data.

    This function populates the provisions, normalized_text, and section_notes
    fields on the ParsedSection using the explicit heading/content structure
    from XML rather than heuristic-based header detection.

    Args:
        parsed_section: A ParsedSection with subsections populated.
        use_tabs: If True, use tab characters for indentation.
        indent_width: Number of spaces per indent level (if use_tabs=False).

    Returns:
        The same ParsedSection with provision fields populated.
    """
    lines: list[ParsedLine] = []
    line_counter = [0]  # Mutable counter
    char_pos = [0]  # Mutable position tracker

    # Process each top-level subsection
    for subsection in parsed_section.subsections:
        _normalize_subsection_recursive(subsection, lines, line_counter, char_pos)

    # Build normalized text
    normalized_lines = [
        line.to_display(use_tabs=use_tabs, indent_width=indent_width) for line in lines
    ]
    normalized_text = "\n".join(normalized_lines)

    # Parse notes/citations
    # Prefer structured refs from XML when available (avoids regex pitfalls)
    notes = SectionNotes()
    citations: list[SourceLaw] | None = None
    if parsed_section.source_credit_refs or parsed_section.act_refs:
        citations = citations_from_source_credit_refs(
            parsed_section.source_credit_refs,
            act_refs=parsed_section.act_refs,
        )

    if parsed_section.notes:
        notes.raw_notes = parsed_section.notes
        _parse_notes_structure(parsed_section.notes, notes, citations=citations)

    # Populate the section with normalized data
    parsed_section.provisions = lines
    parsed_section.normalized_text = normalized_text
    parsed_section.section_notes = notes

    return parsed_section
