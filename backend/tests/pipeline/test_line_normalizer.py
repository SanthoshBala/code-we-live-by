"""Tests for legal text line normalization."""

import pytest

from pipeline.legal_parser.line_normalizer import (
    Citation,
    NormalizedLine,
    NormalizedSection,
    normalize_section,
    char_span_to_line_span,
    parse_citation,
    parse_citations,
    _detect_marker_level,
    _is_sentence_boundary,
)


class TestMarkerLevelDetection:
    """Tests for list item marker level detection."""

    def test_lowercase_letter_level_1(self) -> None:
        """Lowercase letters (a), (b), (c) are level 1."""
        assert _detect_marker_level("(a)") == 1
        assert _detect_marker_level("(b)") == 1
        assert _detect_marker_level("(z)") == 1

    def test_number_level_2(self) -> None:
        """Numbers (1), (2), (3) are level 2."""
        assert _detect_marker_level("(1)") == 2
        assert _detect_marker_level("(2)") == 2
        assert _detect_marker_level("(99)") == 2

    def test_uppercase_letter_level_3(self) -> None:
        """Uppercase letters (A), (B), (C) are level 3."""
        assert _detect_marker_level("(A)") == 3
        assert _detect_marker_level("(B)") == 3
        assert _detect_marker_level("(Z)") == 3

    def test_lowercase_roman_level_4(self) -> None:
        """Lowercase roman numerals (ii), (iii), etc. are level 4.

        Note: Single (i) is ambiguous and treated as lowercase letter (level 1).
        """
        assert _detect_marker_level("(i)") == 1  # Ambiguous, treated as letter
        assert _detect_marker_level("(ii)") == 4
        assert _detect_marker_level("(iii)") == 4
        assert _detect_marker_level("(iv)") == 4
        assert _detect_marker_level("(ix)") == 4

    def test_uppercase_roman_level_5(self) -> None:
        """Uppercase roman numerals (II), (III), etc. are level 5.

        Note: Single (I) is ambiguous and treated as uppercase letter (level 3).
        """
        assert _detect_marker_level("(I)") == 3  # Ambiguous, treated as letter
        assert _detect_marker_level("(II)") == 5
        assert _detect_marker_level("(III)") == 5
        assert _detect_marker_level("(IV)") == 5

    def test_compound_marker_uses_deepest(self) -> None:
        """Compound markers like (a)(1) use the deepest level."""
        assert _detect_marker_level("(a)(1)") == 2
        assert _detect_marker_level("(a)(1)(A)") == 3
        assert _detect_marker_level("(b)(2)(B)(ii)") == 4  # (ii) is unambiguous roman


class TestSentenceBoundaryDetection:
    """Tests for sentence boundary detection."""

    def test_simple_sentence_end(self) -> None:
        """Simple period followed by space and capital is a boundary."""
        text = "This is a sentence. This is another."
        assert _is_sentence_boundary(text, 18) is True

    def test_abbreviation_not_boundary(self) -> None:
        """Known abbreviations are not sentence boundaries."""
        text = "See 17 U.S.C. section 106 for details."
        # The periods in U.S.C. should not be boundaries
        assert _is_sentence_boundary(text, 9) is False  # U.
        assert _is_sentence_boundary(text, 11) is False  # S.
        assert _is_sentence_boundary(text, 13) is False  # C.

    def test_sec_abbreviation(self) -> None:
        """Sec. abbreviation is not a sentence boundary."""
        text = "Sec. 106 is amended."
        assert _is_sentence_boundary(text, 3) is False

    def test_end_of_text(self) -> None:
        """Period at end of text is a boundary."""
        text = "This is the end."
        assert _is_sentence_boundary(text, 15) is True

    def test_period_followed_by_lowercase(self) -> None:
        """Period followed by lowercase is not a boundary."""
        text = "The amount is $1.5 million."
        assert _is_sentence_boundary(text, 16) is False


class TestNormalizeSectionBasic:
    """Basic tests for section normalization."""

    def test_simple_sentences(self) -> None:
        """Test splitting simple sentences."""
        text = "This is the first sentence. This is the second sentence."
        result = normalize_section(text)

        assert result.line_count == 2
        assert result.lines[0].content == "This is the first sentence."
        assert result.lines[1].content == "This is the second sentence."

    def test_single_list_item(self) -> None:
        """Test a single list item."""
        text = "(a) This is subsection a."
        result = normalize_section(text)

        assert result.line_count == 1
        assert result.lines[0].marker == "(a)"
        assert result.lines[0].indent_level == 1
        assert "(a)" in result.lines[0].content

    def test_multiple_list_items(self) -> None:
        """Test multiple list items at same level."""
        text = "(a) First item. (b) Second item. (c) Third item."
        result = normalize_section(text)

        assert result.line_count == 3
        assert result.lines[0].marker == "(a)"
        assert result.lines[1].marker == "(b)"
        assert result.lines[2].marker == "(c)"

    def test_nested_list_items(self) -> None:
        """Test nested list items with different levels."""
        text = "(a) Main item. (1) Sub-item one. (2) Sub-item two."
        result = normalize_section(text)

        assert result.line_count == 3
        assert result.lines[0].indent_level == 1  # (a)
        assert result.lines[1].indent_level == 2  # (1)
        assert result.lines[2].indent_level == 2  # (2)

    def test_line_numbers_are_one_indexed(self) -> None:
        """Line numbers should start at 1."""
        text = "(a) First. (b) Second."
        result = normalize_section(text)

        assert result.lines[0].line_number == 1
        assert result.lines[1].line_number == 2


class TestNormalizeSectionIndentation:
    """Tests for indentation in normalized output."""

    def test_display_with_tabs_default(self) -> None:
        """Test that display output uses tabs by default."""
        text = "(a) Main item. (1) Sub-item."
        result = normalize_section(text)

        lines = result.normalized_text.split("\n")
        # (a) at level 1 = 1 tab
        assert lines[0].startswith("\t")
        assert not lines[0].startswith("\t\t")
        # (1) at level 2 = 2 tabs
        assert lines[1].startswith("\t\t")
        assert not lines[1].startswith("\t\t\t")

    def test_display_with_spaces(self) -> None:
        """Test that display output can use spaces instead of tabs."""
        text = "(a) Main item. (1) Sub-item."
        result = normalize_section(text, use_tabs=False, indent_width=4)

        lines = result.normalized_text.split("\n")
        # (a) at level 1 = 4 spaces
        assert lines[0].startswith("    ")
        assert not lines[0].startswith("        ")
        # (1) at level 2 = 8 spaces
        assert lines[1].startswith("        ")

    def test_custom_indent_width(self) -> None:
        """Test custom indent width with spaces."""
        text = "(a) Item."
        result = normalize_section(text, use_tabs=False, indent_width=2)

        line = result.lines[0]
        display = line.to_display(use_tabs=False, indent_width=2)
        assert display.startswith("  ")  # 2 spaces for level 1

    def test_to_display_tabs(self) -> None:
        """Test to_display with tabs."""
        text = "(a) Item."
        result = normalize_section(text)

        line = result.lines[0]
        display = line.to_display(use_tabs=True)
        assert display.startswith("\t")
        assert display == "\t(a) Item."


class TestNormalizeSectionRealExamples:
    """Tests with realistic legal text from US Code."""

    def test_copyright_section_106(self) -> None:
        """Test with text similar to 17 U.S.C. § 106."""
        text = """Subject to sections 107 through 122, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following: (1) to reproduce the copyrighted work in copies or phonorecords; (2) to prepare derivative works based upon the copyrighted work; (3) to distribute copies or phonorecords of the copyrighted work to the public by sale or other transfer of ownership, or by rental, lease, or lending."""

        result = normalize_section(text)

        # Should have the intro sentence plus 3 list items
        assert result.line_count >= 4

        # First line should be the intro (no marker)
        assert result.lines[0].marker is None
        assert "exclusive rights" in result.lines[0].content

        # Subsequent lines should be numbered items
        numbered_items = [line for line in result.lines if line.marker is not None]
        assert len(numbered_items) == 3

    def test_nested_structure(self) -> None:
        """Test deeply nested legal structure."""
        text = """(a) General Rule.—The term "covered work" means— (1) a work that is— (A) created by an author who is a natural person; and (B) protected under section 102; or (2) a compilation of such works. (b) Exception.—Subsection (a) does not apply to works made for hire."""

        result = normalize_section(text)

        # Check we have the expected structure
        markers = [line.marker for line in result.lines if line.marker]
        assert "(a)" in markers
        assert "(1)" in markers
        assert "(A)" in markers
        assert "(B)" in markers
        assert "(2)" in markers
        assert "(b)" in markers

    def test_preserves_legal_abbreviations(self) -> None:
        """Test that legal abbreviations don't cause spurious splits."""
        text = "Section 512 of title 17, U.S.C., is amended by striking the phrase."

        result = normalize_section(text)

        # Should be one line (or two if there's a sentence after)
        # The key is that "U.S.C." doesn't split the sentence
        full_text = " ".join(line.content for line in result.lines)
        assert "U.S.C." in full_text


class TestCharacterToLineMapping:
    """Tests for character position to line number mapping."""

    def test_char_to_line_simple(self) -> None:
        """Test basic character to line mapping."""
        text = "(a) First item. (b) Second item."
        result = normalize_section(text)

        # Character 0 should be in line 1
        assert result.char_to_line(0) == 1

        # Find where (b) starts and check it maps to line 2
        b_pos = text.index("(b)")
        assert result.char_to_line(b_pos) == 2

    def test_char_span_to_line_span(self) -> None:
        """Test converting character span to line span."""
        text = "(a) First. (b) Second. (c) Third."
        result = normalize_section(text)

        # A span covering just "(b)" marker should map to line 2
        b_start = text.index("(b)")
        b_marker_end = b_start + 3  # Just "(b)"
        line_span = char_span_to_line_span(result, b_start, b_marker_end)

        assert line_span == (2, 2)

        # A span covering "(b) Second." exactly should also be line 2
        b_content_end = text.index("(c)") - 1  # Before the space before (c)
        line_span2 = char_span_to_line_span(result, b_start, b_content_end)
        assert line_span2 == (2, 2)

    def test_char_span_multiple_lines(self) -> None:
        """Test span covering multiple lines."""
        text = "(a) First. (b) Second. (c) Third."
        result = normalize_section(text)

        # A span from (a) to (c) should cover lines 1-3
        a_start = 0
        end = len(text)
        line_span = char_span_to_line_span(result, a_start, end)

        assert line_span == (1, 3)


class TestNormalizedSectionMethods:
    """Tests for NormalizedSection helper methods."""

    def test_get_line(self) -> None:
        """Test getting a specific line by number."""
        text = "(a) First. (b) Second."
        result = normalize_section(text)

        line1 = result.get_line(1)
        assert line1 is not None
        assert line1.marker == "(a)"

        line2 = result.get_line(2)
        assert line2 is not None
        assert line2.marker == "(b)"

        # Out of range
        assert result.get_line(0) is None
        assert result.get_line(100) is None

    def test_get_lines_range(self) -> None:
        """Test getting a range of lines."""
        text = "(a) First. (b) Second. (c) Third."
        result = normalize_section(text)

        lines = result.get_lines(1, 2)
        assert len(lines) == 2
        assert lines[0].marker == "(a)"
        assert lines[1].marker == "(b)"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text(self) -> None:
        """Test with empty text."""
        result = normalize_section("")
        assert result.line_count == 0
        assert result.normalized_text == ""

    def test_whitespace_only(self) -> None:
        """Test with whitespace-only text."""
        result = normalize_section("   \n\t  ")
        assert result.line_count == 0

    def test_no_markers_no_sentences(self) -> None:
        """Test text with no markers and no sentence-ending periods."""
        text = "Just a fragment without punctuation"
        result = normalize_section(text)

        assert result.line_count == 1
        assert result.lines[0].content == text

    def test_consecutive_markers(self) -> None:
        """Test markers without content between them."""
        text = "(a) (1) Nested content."
        result = normalize_section(text)

        # The (a) might be empty or combined with (1)
        # Main thing is we don't crash
        assert result.line_count >= 1

    def test_quoted_text_with_periods(self) -> None:
        """Test that periods inside quotes don't always split."""
        text = 'The term means "a work. Or works." as defined.'
        result = normalize_section(text)

        # This is tricky - we might split or not depending on implementation
        # The key is we handle it gracefully
        assert result.line_count >= 1


class TestCitationParsing:
    """Tests for Public Law citation parsing."""

    def test_parse_simple_citation(self) -> None:
        """Test parsing a simple Pub. L. citation."""
        text = "Pub. L. 94–553"
        citation = parse_citation(text)

        assert citation is not None
        assert citation.congress == 94
        assert citation.law_number == 553
        assert citation.public_law_id == "PL 94-553"

    def test_parse_full_citation(self) -> None:
        """Test parsing a complete citation with all components."""
        text = "Pub. L. 94–553, title I, § 101, Oct. 19, 1976, 90 Stat. 2546"
        citation = parse_citation(text)

        assert citation is not None
        assert citation.congress == 94
        assert citation.law_number == 553
        assert citation.title == "I"
        assert citation.section == "101"
        assert citation.date == "Oct. 19, 1976"
        assert citation.stat_volume == 90
        assert citation.stat_page == 2546
        assert citation.stat_reference == "90 Stat. 2546"

    def test_parse_citation_with_hyphen(self) -> None:
        """Test parsing citation with regular hyphen instead of en-dash."""
        text = "Pub. L. 111-295, § 6(f)(2), Dec. 9, 2010, 124 Stat. 3181"
        citation = parse_citation(text)

        assert citation is not None
        assert citation.congress == 111
        assert citation.law_number == 295
        assert citation.section == "6(f)(2)"
        assert citation.date == "Dec. 9, 2010"

    def test_parse_citation_without_title(self) -> None:
        """Test parsing citation without a title component."""
        text = "Pub. L. 105-304, § 102, Oct. 28, 1998, 112 Stat. 2861"
        citation = parse_citation(text)

        assert citation is not None
        assert citation.congress == 105
        assert citation.law_number == 304
        assert citation.title is None
        assert citation.section == "102"

    def test_parse_invalid_citation(self) -> None:
        """Test that invalid text returns None."""
        assert parse_citation("Not a citation") is None
        assert parse_citation("Section 106") is None

    def test_parse_multiple_citations(self) -> None:
        """Test parsing multiple citations from a block."""
        text = """( Pub. L. 94–553, title I, § 106, Oct. 19, 1976, 90 Stat. 2546;
        Pub. L. 101–650, title VII, § 703, Dec. 1, 1990, 104 Stat. 5133;
        Pub. L. 106–44, § 2, Aug. 5, 1999, 113 Stat. 221 )"""

        citations = parse_citations(text)

        assert len(citations) == 3
        assert citations[0].congress == 94
        assert citations[0].law_number == 553
        assert citations[1].congress == 101
        assert citations[1].law_number == 650
        assert citations[2].congress == 106
        assert citations[2].law_number == 44

    def test_citation_in_section_notes(self) -> None:
        """Test that citations are extracted from section notes."""
        text = """(a) The owner has exclusive rights.
        ( Pub. L. 94–553, title I, § 106, Oct. 19, 1976, 90 Stat. 2546 )
        Editorial Notes
        Some editorial content here."""

        result = normalize_section(text)

        assert result.notes.has_citations
        assert len(result.notes.citations) == 1
        assert result.notes.citations[0].congress == 94
        assert result.notes.citations[0].public_law_id == "PL 94-553"

    def test_citation_public_law_id_property(self) -> None:
        """Test the public_law_id property format."""
        citation = Citation(congress=118, law_number=60)
        assert citation.public_law_id == "PL 118-60"

    def test_citation_stat_reference_property(self) -> None:
        """Test the stat_reference property."""
        citation = Citation(
            congress=94, law_number=553, stat_volume=90, stat_page=2546
        )
        assert citation.stat_reference == "90 Stat. 2546"

        # Without stat info, should return None
        citation_no_stat = Citation(congress=94, law_number=553)
        assert citation_no_stat.stat_reference is None

    def test_citation_order_and_is_original(self) -> None:
        """Test that citations have order set and is_original works."""
        text = """( Pub. L. 94–553, title I, § 106, Oct. 19, 1976, 90 Stat. 2546;
        Pub. L. 101–650, title VII, § 703, Dec. 1, 1990, 104 Stat. 5133;
        Pub. L. 106–44, § 2, Aug. 5, 1999, 113 Stat. 221 )"""

        citations = parse_citations(text)

        assert len(citations) == 3

        # First citation is the original (order=0)
        assert citations[0].order == 0
        assert citations[0].is_original is True

        # Subsequent citations are amendments
        assert citations[1].order == 1
        assert citations[1].is_original is False

        assert citations[2].order == 2
        assert citations[2].is_original is False

    def test_citation_sort_key(self) -> None:
        """Test that sort_key provides chronological ordering."""
        # Create citations out of order
        c1 = Citation(congress=106, law_number=44)
        c2 = Citation(congress=94, law_number=553)
        c3 = Citation(congress=101, law_number=650)

        # Sort by sort_key should give chronological order
        citations = sorted([c1, c2, c3], key=lambda c: c.sort_key)

        assert citations[0].congress == 94  # Oldest
        assert citations[1].congress == 101
        assert citations[2].congress == 106  # Newest
