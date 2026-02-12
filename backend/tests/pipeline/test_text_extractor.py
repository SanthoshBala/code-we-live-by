"""Tests for text extractor."""

import pytest

from app.models.enums import ChangeType
from pipeline.legal_parser.amendment_parser import ParsedAmendment, SectionReference
from pipeline.legal_parser.patterns import PatternType
from pipeline.legal_parser.text_extractor import ExtractedText, TextExtractor


class TestTextExtractor:
    """Tests for TextExtractor."""

    def _make_amendment(
        self,
        pattern_type: PatternType,
        start_pos: int = 0,
        end_pos: int = 50,
    ) -> ParsedAmendment:
        """Create a test ParsedAmendment."""
        return ParsedAmendment(
            pattern_name="test_pattern",
            pattern_type=pattern_type,
            change_type=ChangeType.ADD,
            section_ref=SectionReference(title=17, section="106"),
            start_pos=start_pos,
            end_pos=end_pos,
        )

    def test_extract_colon_quoted(self) -> None:
        """Test extraction of colon + quoted text pattern."""
        law_text = (
            'Section 106 is amended by adding at the end the following: '
            '"(c) Special rules.—The provisions of this section shall apply.".'
        )
        extractor = TextExtractor(law_text)
        amendment = self._make_amendment(
            PatternType.ADD_AT_END,
            start_pos=0,
            end_pos=59,  # End of "the following"
        )

        result = extractor.extract_following_text(amendment)
        assert result is not None
        assert "(c) Special rules" in result.text

    def test_extract_batch(self) -> None:
        """Test batch extraction."""
        law_text = (
            'Section 106(a) is amended by striking "old text" and inserting '
            '"new text". Section 107 is amended by adding at the end: '
            '"New paragraph.".'
        )
        extractor = TextExtractor(law_text)

        amendments = [
            self._make_amendment(PatternType.STRIKE_INSERT, 0, 50),
            self._make_amendment(
                PatternType.ADD_AT_END, 70, 120
            ),
        ]

        results = extractor.extract_batch(amendments)
        # STRIKE_INSERT doesn't need extraction, ADD_AT_END does
        assert 0 not in results  # STRIKE_INSERT not in NEEDS_EXTRACTION
        assert 1 in results

    def test_no_extraction_for_strike(self) -> None:
        """Test that STRIKE pattern doesn't trigger extraction."""
        law_text = 'Section 106 is amended by striking "the old text".'
        extractor = TextExtractor(law_text)
        amendment = self._make_amendment(PatternType.STRIKE, 0, 50)

        result = extractor.extract_following_text(amendment)
        assert result is None

    def test_extract_paragraph(self) -> None:
        """Test paragraph extraction fallback."""
        law_text = (
            "Section 106 is amended by adding the following new subsection:\n"
            "(c) Any person who violates this section shall be subject "
            "to penalties as described in section 501.\n\n"
            "SEC. 3. EFFECTIVE DATE."
        )
        extractor = TextExtractor(law_text)
        amendment = self._make_amendment(
            PatternType.ADD_SUBSECTION,
            start_pos=0,
            end_pos=60,
        )

        result = extractor.extract_following_text(amendment)
        assert result is not None
        assert "violates" in result.text


class TestExtractedText:
    """Tests for ExtractedText dataclass."""

    def test_defaults(self) -> None:
        et = ExtractedText(text="hello", start_pos=0, end_pos=5)
        assert et.confidence == 0.8
        assert et.method == "colon_delimited"
