"""Text extractor — extract "the following" content from law text.

For ADD_AT_END, INSERT_AFTER, INSERT_BEFORE, SUBSTITUTE, and ADD_SECTION
patterns, the parser matches the amendment instruction but the actual new
text follows after the instruction. This module extracts that content.
"""

import logging
import re
from dataclasses import dataclass

from pipeline.legal_parser.amendment_parser import ParsedAmendment
from pipeline.legal_parser.patterns import PatternType

logger = logging.getLogger(__name__)

# Patterns that typically need text extraction from following content
NEEDS_EXTRACTION = frozenset({
    PatternType.ADD_AT_END,
    PatternType.INSERT_AFTER,
    PatternType.INSERT_BEFORE,
    PatternType.SUBSTITUTE,
    PatternType.ADD_SECTION,
    PatternType.ADD_SUBSECTION,
    PatternType.INSERT_NEW_TEXT,
})

# Common delimiters that signal the start of quoted/inserted text
# In law text, new content is typically introduced with a colon followed by
# quoted text or indented paragraphs
TEXT_START_PATTERNS = [
    # Colon followed by quoted text (most common)
    r':\s*["\u201c]',
    # "the following" followed by colon
    r"the\s+following[^:]*:\s*",
    # "to read as follows:" pattern
    r"to\s+read\s+as\s+follows\s*:\s*",
    # "the following new" pattern
    r"the\s+following\s+new\s+\w+\s*:\s*",
]

# Patterns that signal the end of extracted text
TEXT_END_PATTERNS = [
    # Next section header (SEC. N.)
    r"\n\s*SEC\.\s+\d+",
    # Next subsection at the same or higher level
    r"\n\s*\([a-z]\)\s+[A-Z]",
    # Closing quote followed by period
    r'["\u201d]\.\s*$',
    # Closing quote followed by semicolon or period and newline
    r'["\u201d][.;]\s*\n',
]


@dataclass
class ExtractedText:
    """Text extracted from following content of an amendment instruction.

    Attributes:
        text: The extracted text content.
        start_pos: Start position in the source law text.
        end_pos: End position in the source law text.
        confidence: Confidence that extraction boundaries are correct.
        method: Description of how the text was extracted.
    """

    text: str
    start_pos: int
    end_pos: int
    confidence: float = 0.8
    method: str = "colon_delimited"


class TextExtractor:
    """Extract text content that follows amendment instructions in law text.

    Many amendment patterns describe WHAT to do (e.g., "add at the end the
    following") but the actual text to be added follows the instruction.
    This class extracts that following text.
    """

    def __init__(self, law_text: str):
        """Initialize with the full law text.

        Args:
            law_text: The complete text of the Public Law.
        """
        self.law_text = law_text

    def extract_following_text(
        self, amendment: ParsedAmendment
    ) -> ExtractedText | None:
        """Extract text following an amendment instruction.

        Args:
            amendment: The parsed amendment whose following text to extract.

        Returns:
            ExtractedText or None if extraction fails.
        """
        if amendment.pattern_type not in NEEDS_EXTRACTION:
            return None

        # Start searching from the end of the amendment match
        search_start = amendment.end_pos

        # Try colon-delimited extraction first (most common pattern)
        result = self._extract_colon_delimited(search_start)
        if result:
            return result

        # Try quoted text extraction
        result = self._extract_quoted_text(search_start)
        if result:
            return result

        # Fall back to paragraph extraction
        result = self._extract_paragraph(search_start)
        if result:
            return result

        logger.debug(
            f"Could not extract following text for {amendment.pattern_name} "
            f"at position {amendment.start_pos}"
        )
        return None

    def extract_batch(
        self, amendments: list[ParsedAmendment]
    ) -> dict[int, ExtractedText]:
        """Extract following text for all amendments that need it.

        Args:
            amendments: List of parsed amendments.

        Returns:
            Dict mapping amendment index to ExtractedText.
        """
        results = {}
        for i, amendment in enumerate(amendments):
            if amendment.pattern_type in NEEDS_EXTRACTION:
                extracted = self.extract_following_text(amendment)
                if extracted:
                    results[i] = extracted
        return results

    def _extract_colon_delimited(self, start_pos: int) -> ExtractedText | None:
        """Extract text after a colon delimiter.

        Looks for the pattern: <instruction>: "<new text>".
        """
        # Look for colon within 200 chars of the amendment end
        window = self.law_text[start_pos : start_pos + 200]
        colon_match = re.search(r":\s*", window)

        if not colon_match:
            return None

        text_start = start_pos + colon_match.end()

        # Check if what follows is a quoted string
        remaining = self.law_text[text_start:]

        # Try to find quoted content
        quote_match = re.match(r'\s*["""\u201c]', remaining)
        if quote_match:
            return self._extract_between_quotes(
                text_start + quote_match.end() - 1
            )

        # Otherwise extract until next section marker or double newline
        end_match = re.search(r"\n\s*(?:SEC\.\s+\d+|\([a-z]\)\s+)", remaining)
        if end_match:
            text = remaining[: end_match.start()].strip()
            if text:
                return ExtractedText(
                    text=text,
                    start_pos=text_start,
                    end_pos=text_start + end_match.start(),
                    confidence=0.6,
                    method="colon_to_section",
                )

        return None

    def _extract_quoted_text(self, start_pos: int) -> ExtractedText | None:
        """Extract text enclosed in quotation marks."""
        window = self.law_text[start_pos : start_pos + 500]

        # Find opening quote
        quote_match = re.search(r'["""\u201c]', window)
        if not quote_match:
            return None

        abs_start = start_pos + quote_match.start()
        return self._extract_between_quotes(abs_start)

    def _extract_between_quotes(self, quote_start: int) -> ExtractedText | None:
        """Extract text between matching quotation marks.

        Handles nested quotes and multi-line quoted content.
        """
        remaining = self.law_text[quote_start:]

        # Track quote depth
        open_char = remaining[0] if remaining else ""
        close_chars = {'"': '"', "\u201c": "\u201d", '"': '"'}
        close_char = close_chars.get(open_char, '"')

        depth = 0
        i = 0
        for i, char in enumerate(remaining):
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    # Found matching close quote
                    text = remaining[1:i]  # Exclude outer quotes
                    return ExtractedText(
                        text=text.strip(),
                        start_pos=quote_start + 1,
                        end_pos=quote_start + i,
                        confidence=0.9,
                        method="quoted",
                    )

        # If no matching close found, try looking for period + quote
        close_match = re.search(
            rf'\.(?:\s*{re.escape(close_char)}|\s*")',
            remaining[1:5000],  # Search up to 5000 chars
        )
        if close_match:
            text = remaining[1 : 1 + close_match.end()]
            return ExtractedText(
                text=text.strip().rstrip('""\u201d'),
                start_pos=quote_start + 1,
                end_pos=quote_start + 1 + close_match.end(),
                confidence=0.7,
                method="quoted_heuristic",
            )

        return None

    def _extract_paragraph(self, start_pos: int) -> ExtractedText | None:
        """Extract a paragraph of text following the amendment instruction.

        Falls back to extracting until the next section header or double newline.
        """
        remaining = self.law_text[start_pos:]

        # Skip any leading whitespace/colon
        stripped = remaining.lstrip(": \t\n")
        offset = len(remaining) - len(stripped)

        # Find end: double newline or next SEC.
        end_match = re.search(r"\n\s*\n|\nSEC\.\s+\d+", stripped)
        if end_match:
            text = stripped[: end_match.start()].strip()
            if text and len(text) > 10:
                return ExtractedText(
                    text=text,
                    start_pos=start_pos + offset,
                    end_pos=start_pos + offset + end_match.start(),
                    confidence=0.5,
                    method="paragraph",
                )

        return None
