"""Tests for legal text line normalization."""

from pipeline.olrc.normalized_section import (
    PARAGRAPH_BREAK_MARKER,
    ParsedPublicLaw,
    SourceLaw,
    _detect_marker_level,
    _is_sentence_boundary,
    _split_into_sentences,
    _strip_note_markers,
    char_span_to_line_span,
    normalize_note_content,
    normalize_section,
    parse_citation,
    parse_citations,
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

    def test_ex_ord_abbreviation(self) -> None:
        """Ex. and Ord. in 'Ex. Ord. No.' are not sentence boundaries."""
        text = "Ex. Ord. No. 12504, Jan. 31, 1985."
        assert _is_sentence_boundary(text, 2) is False  # Ex.
        assert _is_sentence_boundary(text, 7) is False  # Ord.

    def test_period_after_paren_ref_before_pub_l(self) -> None:
        """Period after (a)(2) before Pub. L. is not a sentence boundary."""
        text = "Subsec. (a)(2). Pub. L. 100-159 inserted provision."
        pos = text.index("). P") + 1  # period after )
        assert _is_sentence_boundary(text, pos) is False


class TestNormalizeSectionBasic:
    """Basic tests for section normalization."""

    def test_simple_sentences(self) -> None:
        """Test splitting simple sentences."""
        text = "This is the first sentence. This is the second sentence."
        result = normalize_section(text)

        assert result.provision_count == 2
        assert result.provisions[0].content == "This is the first sentence."
        assert result.provisions[1].content == "This is the second sentence."

    def test_single_list_item(self) -> None:
        """Test a single list item."""
        text = "(a) This is subsection a."
        result = normalize_section(text)

        assert result.provision_count == 1
        assert result.provisions[0].marker == "(a)"
        assert result.provisions[0].indent_level == 1
        assert "(a)" in result.provisions[0].content

    def test_multiple_list_items(self) -> None:
        """Test multiple list items at same level."""
        text = "(a) First item. (b) Second item. (c) Third item."
        result = normalize_section(text)

        assert result.provision_count == 3
        assert result.provisions[0].marker == "(a)"
        assert result.provisions[1].marker == "(b)"
        assert result.provisions[2].marker == "(c)"

    def test_nested_list_items(self) -> None:
        """Test nested list items with different levels."""
        text = "(a) Main item. (1) Sub-item one. (2) Sub-item two."
        result = normalize_section(text)

        assert result.provision_count == 3
        assert result.provisions[0].indent_level == 1  # (a)
        assert result.provisions[1].indent_level == 2  # (1)
        assert result.provisions[2].indent_level == 2  # (2)

    def test_line_numbers_are_one_indexed(self) -> None:
        """Line numbers should start at 1."""
        text = "(a) First. (b) Second."
        result = normalize_section(text)

        assert result.provisions[0].line_number == 1
        assert result.provisions[1].line_number == 2


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

        line = result.provisions[0]
        display = line.to_display(use_tabs=False, indent_width=2)
        assert display.startswith("  ")  # 2 spaces for level 1

    def test_to_display_tabs(self) -> None:
        """Test to_display with tabs."""
        text = "(a) Item."
        result = normalize_section(text)

        line = result.provisions[0]
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
        assert result.provision_count >= 4

        # First line should be the intro (no marker)
        assert result.provisions[0].marker is None
        assert "exclusive rights" in result.provisions[0].content

        # Subsequent lines should be numbered items
        numbered_items = [line for line in result.provisions if line.marker is not None]
        assert len(numbered_items) == 3

    def test_nested_structure(self) -> None:
        """Test deeply nested legal structure."""
        text = """(a) General Rule.—The term "covered work" means— (1) a work that is— (A) created by an author who is a natural person; and (B) protected under section 102; or (2) a compilation of such works. (b) Exception.—Subsection (a) does not apply to works made for hire."""

        result = normalize_section(text)

        # Check we have the expected structure
        markers = [line.marker for line in result.provisions if line.marker]
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
        full_text = " ".join(line.content for line in result.provisions)
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

    def test_get_provision(self) -> None:
        """Test getting a specific provision by line number."""
        text = "(a) First. (b) Second."
        result = normalize_section(text)

        line1 = result.get_provision(1)
        assert line1 is not None
        assert line1.marker == "(a)"

        line2 = result.get_provision(2)
        assert line2 is not None
        assert line2.marker == "(b)"

        # Out of range
        assert result.get_provision(0) is None
        assert result.get_provision(100) is None

    def test_get_provisions_range(self) -> None:
        """Test getting a range of provisions."""
        text = "(a) First. (b) Second. (c) Third."
        result = normalize_section(text)

        lines = result.get_provisions(1, 2)
        assert len(lines) == 2
        assert lines[0].marker == "(a)"
        assert lines[1].marker == "(b)"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text(self) -> None:
        """Test with empty text."""
        result = normalize_section("")
        assert result.provision_count == 0
        assert result.normalized_text == ""

    def test_whitespace_only(self) -> None:
        """Test with whitespace-only text."""
        result = normalize_section("   \n\t  ")
        assert result.provision_count == 0

    def test_no_markers_no_sentences(self) -> None:
        """Test text with no markers and no sentence-ending periods."""
        text = "Just a fragment without punctuation"
        result = normalize_section(text)

        assert result.provision_count == 1
        assert result.provisions[0].content == text

    def test_consecutive_markers(self) -> None:
        """Test markers without content between them."""
        text = "(a) (1) Nested content."
        result = normalize_section(text)

        # The (a) might be empty or combined with (1)
        # Main thing is we don't crash
        assert result.provision_count >= 1

    def test_quoted_text_with_periods(self) -> None:
        """Test that periods inside quotes don't always split."""
        text = 'The term means "a work. Or works." as defined.'
        result = normalize_section(text)

        # This is tricky - we might split or not depending on implementation
        # The key is we handle it gracefully
        assert result.provision_count >= 1


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

        assert result.section_notes.has_citations
        assert len(result.section_notes.citations) == 1
        assert result.section_notes.citations[0].congress == 94
        assert result.section_notes.citations[0].public_law_id == "PL 94-553"

    def test_citation_public_law_id_property(self) -> None:
        """Test the public_law_id property format."""
        law = ParsedPublicLaw(congress=118, law_number=60)
        citation = SourceLaw(law=law)
        assert citation.public_law_id == "PL 118-60"

    def test_citation_stat_reference_property(self) -> None:
        """Test the stat_reference property."""
        law = ParsedPublicLaw(
            congress=94, law_number=553, stat_volume=90, stat_page=2546
        )
        citation = SourceLaw(law=law)
        assert citation.stat_reference == "90 Stat. 2546"

        # Without stat info, should return None
        law_no_stat = ParsedPublicLaw(congress=94, law_number=553)
        citation_no_stat = SourceLaw(law=law_no_stat)
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
        c1 = SourceLaw(law=ParsedPublicLaw(congress=106, law_number=44))
        c2 = SourceLaw(law=ParsedPublicLaw(congress=94, law_number=553))
        c3 = SourceLaw(law=ParsedPublicLaw(congress=101, law_number=650))

        # Sort by sort_key should give chronological order
        citations = sorted([c1, c2, c3], key=lambda c: c.sort_key)

        assert citations[0].congress == 94  # Oldest
        assert citations[1].congress == 101
        assert citations[2].congress == 106  # Newest


class TestNormalizeParsedSection:
    """Tests for normalizing ParsedSection with structured subsections."""

    def test_normalize_with_headings(self) -> None:
        """Subsections with headings create header + content lines with blank line separators."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="101",
            heading="Test Section",
            full_citation="17 U.S.C. § 101",
            text_content="Test content",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading="First Item",
                    content="This is the content.",
                    level="subsection",
                ),
                ParsedSubsection(
                    marker="(b)",
                    heading="Second Item",
                    content="More content here.",
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # 5 lines: header + content + blank + header + content
        assert result.provision_count == 5
        # First header at indent 0 (top-level, like a function)
        assert result.provisions[0].content == "(a) First Item"
        assert result.provisions[0].marker == "(a)"
        assert result.provisions[0].indent_level == 0
        # First content (indented under header)
        assert result.provisions[1].content == "This is the content."
        assert result.provisions[1].marker is None
        assert result.provisions[1].indent_level == 1
        # Blank line before second header
        assert result.provisions[2].content == ""
        assert result.provisions[2].indent_level == 0
        # Second header
        assert result.provisions[3].content == "(b) Second Item"
        # Second content
        assert result.provisions[4].content == "More content here."

    def test_normalize_without_headings(self) -> None:
        """Subsections without headings create single lines at base indent."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="102",
            heading="Test Section",
            full_citation="17 U.S.C. § 102",
            text_content="Test content",
            subsections=[
                ParsedSubsection(
                    marker="(1)",
                    heading=None,
                    content="Item without heading.",
                    level="paragraph",
                ),
                ParsedSubsection(
                    marker="(2)",
                    heading=None,
                    content="Another item.",
                    level="paragraph",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 2
        assert result.provisions[0].content == "(1) Item without heading."
        assert result.provisions[0].indent_level == 0  # top-level, like a function
        assert result.provisions[1].content == "(2) Another item."

    def test_normalize_with_nested_children(self) -> None:
        """Nested subsections are properly indented relative to parent."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="103",
            heading="Test Section",
            full_citation="17 U.S.C. § 103",
            text_content="Test content",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading="Parent",
                    content="Parent content.",
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="Child item.",
                            level="paragraph",
                        ),
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 3
        # Parent header at indent 0 (top-level)
        assert result.provisions[0].content == "(a) Parent"
        assert result.provisions[0].indent_level == 0
        # Parent content at indent 1
        assert result.provisions[1].content == "Parent content."
        assert result.provisions[1].indent_level == 1
        # Child at indent 2 (parent base + 2 because parent has heading)
        assert result.provisions[2].content == "(1) Child item."
        assert result.provisions[2].indent_level == 2

    def test_empty_subsections_falls_back_to_text(self) -> None:
        """Section with no subsections falls back to sentence-based normalization."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection

        section = ParsedSection(
            section_number="104",
            heading="Empty Section",
            full_citation="17 U.S.C. § 104",
            text_content="First sentence. Second sentence.",
            subsections=[],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 2
        assert result.provisions[0].content == "First sentence."
        assert result.provisions[1].content == "Second sentence."

    def test_empty_subsections_no_text(self) -> None:
        """Section with no subsections and no text returns empty lines."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection

        section = ParsedSection(
            section_number="104",
            heading="Empty Section",
            full_citation="17 U.S.C. § 104",
            text_content="",
            subsections=[],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 0
        assert result.provisions == []

    def test_no_blank_line_between_consecutive_headers(self) -> None:
        """No blank line between a header-only parent and its child header.

        When a parent header has no content, its child header should follow
        immediately without a blank line. Blank lines are only added to
        separate content blocks, not to separate "container" headers.

        Example - WRONG (awkward spacing):
            L1 │ (a) Appropriation
            L2 │
            L3 │     (1) In general
            L4 │         Content here...

        Example - RIGHT (natural spacing):
            L1 │ (a) Appropriation
            L2 │     (1) In general
            L3 │         Content here...
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="801",
            heading="Test Section",
            full_citation="42 U.S.C. § 801",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading="Appropriation",  # Header only, no content
                    content=None,
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading="In general",
                            content="Content here.",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(2)",
                            heading="Reservation",
                            content="More content.",
                            level="paragraph",
                        ),
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Expected: (a) header, (1) header, (1) content, blank, (2) header, (2) content
        # NO blank line between (a) and (1) since (a) has no content
        assert result.provision_count == 6
        assert result.provisions[0].content == "(a) Appropriation"
        assert result.provisions[0].is_header is True
        # (1) immediately follows (a) - no blank line
        assert result.provisions[1].content == "(1) In general"
        assert result.provisions[1].is_header is True
        assert result.provisions[2].content == "Content here."
        # Blank line before (2) because there's content before it
        assert result.provisions[3].content == ""
        assert result.provisions[4].content == "(2) Reservation"
        assert result.provisions[5].content == "More content."

    def test_blank_line_after_content_before_header(self) -> None:
        """Blank line IS added between content and the next header.

        When a subsection has content, a blank line should appear before
        the next sibling header to visually separate the logical blocks.
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="102",
            heading="Test Section",
            full_citation="17 U.S.C. § 102",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading="First",
                    content="First content.",  # Has content
                    level="subsection",
                ),
                ParsedSubsection(
                    marker="(b)",
                    heading="Second",
                    content="Second content.",
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Expected: (a) header, (a) content, blank, (b) header, (b) content
        assert result.provision_count == 5
        assert result.provisions[0].content == "(a) First"
        assert result.provisions[1].content == "First content."
        # Blank line after content, before next header
        assert result.provisions[2].content == ""
        assert result.provisions[3].content == "(b) Second"
        assert result.provisions[4].content == "Second content."

    def test_no_blank_line_when_header_subordinate_to_prose(self) -> None:
        """No blank line when a header is subordinate to introductory prose.

        When prose introduces a list (e.g., "In this section:"), the child
        headers should follow immediately without a blank line since they
        are subordinate to the prose, not siblings.

        Example - WRONG (awkward spacing):
            L1 │ (g) Definitions
            L2 │     In this section:
            L3 │
            L4 │         (1) Term

        Example - RIGHT (natural spacing):
            L1 │ (g) Definitions
            L2 │     In this section:
            L3 │         (1) Term
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="801",
            heading="Test Section",
            full_citation="42 U.S.C. § 801",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(g)",
                    heading="Definitions",
                    content="In this section:",  # Introductory prose
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading="First term",
                            content="The definition.",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(2)",
                            heading="Second term",
                            content="Another definition.",
                            level="paragraph",
                        ),
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Expected structure:
        # L1: (g) Definitions (header, level 0)
        # L2: In this section: (content, level 1)
        # L3: (1) First term (header, level 2) - NO blank before, subordinate to L2
        # L4: The definition. (content, level 3)
        # L5: blank - separates sibling definitions
        # L6: (2) Second term (header, level 2)
        # L7: Another definition. (content, level 3)
        assert result.provision_count == 7
        assert result.provisions[0].content == "(g) Definitions"
        assert result.provisions[0].indent_level == 0
        assert result.provisions[1].content == "In this section:"
        assert result.provisions[1].indent_level == 1
        # (1) immediately follows introductory prose - no blank line
        assert result.provisions[2].content == "(1) First term"
        assert result.provisions[2].indent_level == 2
        assert result.provisions[3].content == "The definition."
        assert result.provisions[3].indent_level == 3
        # Blank line before sibling (2)
        assert result.provisions[4].content == ""
        assert result.provisions[5].content == "(2) Second term"
        assert result.provisions[6].content == "Another definition."


class TestNormalizeParsedSectionDirectParagraphs:
    """Tests for sections with paragraphs directly under section (no subsection).

    Regression tests for 20 U.S.C. § 5204 which has <paragraph> elements as
    direct children of <section> with a section-level <chapeau>.
    """

    def test_chapeau_with_direct_paragraphs(self) -> None:
        """Chapeau + direct paragraphs produce indented lines."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="5204",
            heading="Authorization of appropriations",
            full_citation="20 U.S.C. § 5204",
            text_content="flat text fallback",
            subsections=[
                ParsedSubsection(
                    marker="",
                    heading=None,
                    content="To provide a permanent endowment—",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="$5,000,000; and",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(2)",
                            heading=None,
                            content="the lesser of—",
                            children=[
                                ParsedSubsection(
                                    marker="(A)",
                                    heading=None,
                                    content="$2,500,000, or",
                                    level="subparagraph",
                                ),
                                ParsedSubsection(
                                    marker="(B)",
                                    heading=None,
                                    content="an amount equal to contributions.",
                                    level="subparagraph",
                                ),
                            ],
                            level="paragraph",
                        ),
                    ],
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Should produce indented lines, not flat text fallback
        assert result.normalized_text != "flat text fallback"
        assert result.provision_count == 5

        # Chapeau at indent 0
        assert result.provisions[0].content == "To provide a permanent endowment—"
        assert result.provisions[0].indent_level == 0

        # (1) at indent 1
        assert result.provisions[1].content == "(1) $5,000,000; and"
        assert result.provisions[1].indent_level == 1

        # (2) at indent 1
        assert result.provisions[2].content == "(2) the lesser of—"
        assert result.provisions[2].indent_level == 1

        # (A) and (B) at indent 2
        assert result.provisions[3].content == "(A) $2,500,000, or"
        assert result.provisions[3].indent_level == 2
        assert result.provisions[4].content == "(B) an amount equal to contributions."
        assert result.provisions[4].indent_level == 2


class TestNormalizeNoteContent:
    """Tests for normalize_note_content function (notes parsing)."""

    def test_simple_text(self) -> None:
        """Test normalizing simple text without markers."""
        text = "This is a simple note. It has two sentences."
        lines = normalize_note_content(text)

        assert len(lines) == 2
        assert lines[0].content == "This is a simple note."
        assert lines[1].content == "It has two sentences."

    def test_h1_header_markers(self) -> None:
        """Test that [H1]...[/H1] markers create header lines."""
        text = "[H1]General Scope[/H1] The five fundamental rights."
        lines = normalize_note_content(text)

        assert len(lines) == 2
        assert lines[0].content == "General Scope"
        assert lines[0].is_header is True
        assert lines[0].indent_level == 1  # H1 at indent 1
        assert lines[1].content == "The five fundamental rights."
        assert lines[1].is_header is False
        assert lines[1].indent_level == 2  # Content after H1 at indent 2

    def test_h2_header_markers(self) -> None:
        """Test that [H2]...[/H2] markers create sub-header lines."""
        text = "[H2]Reproduction[/H2] The right to reproduce."
        lines = normalize_note_content(text)

        assert len(lines) == 2
        assert lines[0].content == "Reproduction"
        assert lines[0].is_header is True
        assert lines[0].indent_level == 2  # H2 at indent 2
        assert lines[1].content == "The right to reproduce."
        assert lines[1].indent_level == 3  # Content after H2 at indent 3

    def test_paragraph_breaks(self) -> None:
        """Test that double newlines create blank lines."""
        text = "First paragraph.\n\nSecond paragraph."
        lines = normalize_note_content(text)

        assert len(lines) == 3
        assert lines[0].content == "First paragraph."
        assert lines[1].content == ""  # Blank line
        assert lines[2].content == "Second paragraph."

    def test_block_quote_after_provided(self) -> None:
        """Block-quoted text after 'provided:' is indented without blank line."""
        text = (
            "Ex. Ord. No. 12504, Jan. 31, 1985, 50 F.R. 4849, provided:"
            "\n\n"
            "By the authority vested in me as President. Ronald Reagan."
        )
        lines = normalize_note_content(text)

        assert (
            lines[0].content
            == "Ex. Ord. No. 12504, Jan. 31, 1985, 50 F.R. 4849, provided:"
        )
        assert lines[0].indent_level == 1
        # No blank line — block quote follows directly
        assert lines[1].content == "By the authority vested in me as President."
        assert lines[1].indent_level == 2
        assert lines[2].content == "Ronald Reagan."
        assert lines[2].indent_level == 2

    def test_block_quote_after_as_follows(self) -> None:
        """Block-quoted text after 'as follows:' is indented without blank line."""
        text = "it is hereby ordered as follows:\n\nSection 1. The Secretary shall act."
        lines = normalize_note_content(text)

        assert lines[0].content == "it is hereby ordered as follows:"
        assert lines[0].indent_level == 1
        assert lines[1].content == "Section 1."
        assert lines[1].indent_level == 2

    def test_quoted_content_markers(self) -> None:
        """Test that [QC:level]...[/QC] markers create indented lines."""
        text = 'Provided that:\n[QC:1]"(a)" Definition.— The term means.[/QC]\n[QC:2]"(1)" In general.— More detail.[/QC]'
        lines = normalize_note_content(text)

        # Should have intro line, then two QC lines
        assert len(lines) >= 3
        # Find the QC lines
        qc_lines = [line for line in lines if line.marker is not None]
        assert len(qc_lines) == 2
        assert qc_lines[0].marker == '"(a)"'
        assert qc_lines[1].marker == '"(1)"'
        # QC level 2 should be more indented than level 1
        assert qc_lines[1].indent_level > qc_lines[0].indent_level

    def test_nested_headers_and_content(self) -> None:
        """Test complex structure with H1, H2, and content."""
        text = "[H1]Rights of Performance[/H1] The right of public performance. [H2]Performing Rights[/H2] The exclusive right."
        lines = normalize_note_content(text)

        # H1 header
        assert lines[0].content == "Rights of Performance"
        assert lines[0].is_header is True
        assert lines[0].indent_level == 1
        # Content after H1
        assert lines[1].content == "The right of public performance."
        assert lines[1].indent_level == 2
        # H2 header
        assert lines[2].content == "Performing Rights"
        assert lines[2].is_header is True
        assert lines[2].indent_level == 2
        # Content after H2
        assert lines[3].content == "The exclusive right."
        assert lines[3].indent_level == 3

    def test_ex_ord_not_split_into_sentences(self) -> None:
        """Test that 'Ex. Ord. No. 12504' is not split into separate lines."""
        text = "Ex. Ord. No. 12504, Jan. 31, 1985, 50 F.R. 4849, provided:"
        lines = normalize_note_content(text)

        assert len(lines) == 1
        assert "Ex. Ord. No. 12504" in lines[0].content

    def test_amendment_subsec_ref_not_split(self) -> None:
        """Test that 'Subsec. (a)(2). Pub. L.' stays on one line."""
        text = "1987—Subsec. (a)(2). Pub. L. 100–159 inserted provision."
        lines = normalize_note_content(text)

        assert len(lines) == 1
        assert "Subsec. (a)(2). Pub. L. 100–159" in lines[0].content


class TestSentenceSplittingWithParagraphs:
    """Tests for sentence splitting with paragraph break detection."""

    def test_paragraph_break_marker_emitted(self) -> None:
        """Test that PARAGRAPH_BREAK_MARKER is emitted for double newlines."""
        text = "First sentence.\n\nSecond sentence."
        sentences = _split_into_sentences(text)

        # Should have: sentence, marker, sentence
        assert len(sentences) == 3
        assert sentences[0][0] == "First sentence."
        assert sentences[1][0] == PARAGRAPH_BREAK_MARKER
        assert sentences[2][0] == "Second sentence."

    def test_paragraph_break_after_whitespace(self) -> None:
        """Test paragraph break detection with trailing whitespace."""
        # Simulates XML tail text: sentence, space, newline, newline, newline
        text = "First sentence. \n\n\nSecond sentence."
        sentences = _split_into_sentences(text)

        markers = [s for s in sentences if s[0] == PARAGRAPH_BREAK_MARKER]
        assert len(markers) == 1

    def test_no_paragraph_break_for_single_newline(self) -> None:
        """Test that single newlines don't create paragraph breaks."""
        text = "First sentence.\nSecond sentence."
        sentences = _split_into_sentences(text)

        markers = [s for s in sentences if s[0] == PARAGRAPH_BREAK_MARKER]
        assert len(markers) == 0


class TestParserNotesContent:
    """Tests for parser's notes content extraction."""

    def test_case_citation_not_marked_as_header(self) -> None:
        """Test that case citations with ' v. ' are not marked as H2 headers."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        # Create a mock element with italic case citation
        xml = (
            "<notes><p>contrary to <i>Smith v. Jones</i>, the rule applies.</p></notes>"
        )
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should NOT contain [H2] marker for case citation
        assert "[H2]" not in content
        assert "Smith v. Jones" in content

    def test_italic_subheader_marked_as_h2(self) -> None:
        """Test that italic sub-headers ARE marked as H2."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = "<notes><p><i>Reproduction</i>.—The right to reproduce.</p></notes>"
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should contain [H2] marker for sub-header
        assert "[H2]Reproduction" in content

    def test_paragraph_markers_inserted(self) -> None:
        """Test that [PARA] markers are inserted between <p> elements."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = "<notes><p>First paragraph.</p><p>Second paragraph.</p></notes>"
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should have double newline (converted from [PARA])
        assert "\n\n" in content

    def test_quoted_content_parsing(self) -> None:
        """Test that quotedContent elements are properly parsed."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <p>Provided that:</p>
            <quotedContent>
                <subsection>
                    <num value="a">"(a)"</num>
                    <heading>Definition</heading>
                    <content>The term means something.</content>
                </subsection>
                <subsection>
                    <num value="b">"(b)"</num>
                    <heading>Application</heading>
                    <content>This applies to cases.</content>
                </subsection>
            </quotedContent>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should contain QC markers for structured content
        assert "[QC:1]" in content
        assert '"(a)"' in content
        assert "Definition" in content
        assert '"(b)"' in content

    def test_nested_quoted_content_levels(self) -> None:
        """Test that nested quoted content has increasing indent levels."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <quotedContent>
                <subsection>
                    <num value="a">"(a)"</num>
                    <content>Main section.</content>
                    <paragraph>
                        <num value="1">"(1)"</num>
                        <content>Sub-item.</content>
                    </paragraph>
                </subsection>
            </quotedContent>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should have level 1 for subsection, level 2 for paragraph
        assert "[QC:1]" in content
        assert "[QC:2]" in content

    def test_smallcaps_heading_marked_with_nh(self) -> None:
        """Test that smallCaps headings are marked with [NH]...[/NH].

        This prevents title-cased paragraph content (like "Memorandum Of
        President...") from being incorrectly parsed as note headers.
        """
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <note>
                <heading class="centered smallCaps">Delegation of Functions</heading>
                <p>Memorandum of President of the United States, Mar. 16, 2012.</p>
                <p>By the authority vested in me as President.</p>
            </note>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # SmallCaps heading should be wrapped in [NH]...[/NH]
        assert "[NH]Delegation Of Functions[/NH]" in content
        # Paragraph content should NOT be wrapped in [NH]
        assert "[NH]Memorandum" not in content
        assert "Memorandum of President" in content

    def test_et_seq_italic_not_marked_as_header(self) -> None:
        """Test that 'et seq' in italic is kept inline, not marked as H2."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = "<notes><p>( 17 U.S.C. 901 <i>et seq</i>.)</p></notes>"
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Should NOT contain [H2] marker for "et seq"
        assert "[H2]" not in content
        assert "et seq" in content


class TestStripNoteMarkers:
    """Tests for _strip_note_markers function."""

    def test_strip_nh_markers(self) -> None:
        """Test stripping [NH]...[/NH] note header markers."""
        text = "[NH]References In Text[/NH] Some content here."
        result = _strip_note_markers(text)
        assert result == "Some content here."
        assert "[NH]" not in result
        assert "[/NH]" not in result

    def test_strip_h1_markers(self) -> None:
        """Test stripping [H1]...[/H1] bold header markers."""
        text = "Content before. [H1]Executive Documents[/H1] Content after."
        result = _strip_note_markers(text)
        assert "Executive Documents" not in result
        assert "Content before." in result
        assert "Content after." in result

    def test_strip_orphaned_closing_markers(self) -> None:
        """Test stripping orphaned [/NH] and [/H1] closing markers.

        These can appear at the start of content when the opening marker
        is in a preceding section header that was already captured.
        """
        text = "[/NH] Content after orphaned marker."
        result = _strip_note_markers(text)
        assert result == "Content after orphaned marker."
        assert "[/NH]" not in result

        text2 = "[/H1] Content after orphaned marker."
        result2 = _strip_note_markers(text2)
        assert result2 == "Content after orphaned marker."
        assert "[/H1]" not in result2

    def test_strip_multiple_markers(self) -> None:
        """Test stripping multiple different markers."""
        text = "[/NH] [NH]Header[/NH] Content. [H1]Bold[/H1] More content."
        result = _strip_note_markers(text)
        # Note: stripping leaves extra spaces which is fine for content processing
        assert "Content." in result
        assert "More content." in result
        assert "[NH]" not in result
        assert "[H1]" not in result
        assert "Header" not in result
        assert "Bold" not in result

    def test_strip_multiline_markers(self) -> None:
        """Test stripping markers that span multiple lines."""
        text = "[NH]Header\nWith Multiple\nLines[/NH] Content."
        result = _strip_note_markers(text)
        assert result == "Content."

    def test_empty_string(self) -> None:
        """Test with empty string."""
        assert _strip_note_markers("") == ""

    def test_no_markers(self) -> None:
        """Test with text containing no markers."""
        text = "Just regular content with no markers."
        assert _strip_note_markers(text) == text


class TestStatutoryNotesHeaderParsing:
    """Tests for statutory notes correctly distinguishing headers from content.

    Bug fixed: Title-cased paragraph content (like "Memorandum Of President...")
    was incorrectly being parsed as note headers. The fix uses [NH] markers.
    """

    def test_memorandum_not_parsed_as_header(self) -> None:
        """Test that 'Memorandum of President...' is parsed as content, not header.

        This was the original bug: paragraphs starting with title-case text
        were incorrectly identified as note headers.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_statutory_notes,
        )

        # Simulate notes text with [NH] markers from XML parser
        raw_notes = """Statutory Notes and Related Subsidiaries
        [NH]Delegation Of Reporting Functions[/NH]
        Memorandum of President of the United States, Mar. 16, 2012.
        Memorandum for the Secretary of State.
        By the authority vested in me as President.
        """

        notes = SectionNotes()
        _parse_statutory_notes(raw_notes, notes)

        # Should have exactly one note
        statutory_notes = [n for n in notes.notes if n.header]
        assert len(statutory_notes) == 1
        assert statutory_notes[0].header == "Delegation Of Reporting Functions"

        # Content should include the Memorandum paragraphs
        assert "Memorandum of President" in statutory_notes[0].content
        assert "Secretary of State" in statutory_notes[0].content

    def test_multiple_statutory_notes_with_nh_markers(self) -> None:
        """Test parsing multiple statutory notes using [NH] markers."""
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_statutory_notes,
        )

        raw_notes = """Statutory Notes and Related Subsidiaries
        [NH]Effective Date Of 2013 Amendment[/NH]
        Amendment effective Oct. 1, 2012.
        [NH]Termination Of Reporting Requirements[/NH]
        For termination, see section 1061.
        """

        notes = SectionNotes()
        _parse_statutory_notes(raw_notes, notes)

        headers = [n.header for n in notes.notes]
        assert "Effective Date Of 2013 Amendment" in headers
        assert "Termination Of Reporting Requirements" in headers
        assert len(notes.notes) == 2

    def test_cross_heading_stripped_from_content(self) -> None:
        """Test that [H1] cross-headings like 'Executive Documents' are stripped."""
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_statutory_notes,
        )

        # Content must be > 30 characters for notes to be created
        raw_notes = """Statutory Notes and Related Subsidiaries
        [NH]Congressional Committees Defined[/NH]
        The term 'congressional defense committees' means the committees on appropriations and armed services.
        [H1]Executive Documents[/H1]
        [NH]Delegation Of Functions[/NH]
        Memorandum of the President of the United States dated March 16, 2012, provided as follows.
        """

        notes = SectionNotes()
        _parse_statutory_notes(raw_notes, notes)

        # Should have two notes
        assert len(notes.notes) == 2

        # First note should not include "Executive Documents" in its content
        first_note = notes.notes[0]
        assert "Executive Documents" not in first_note.content
        assert "congressional defense committees" in first_note.content


class TestCleanHeading:
    """Tests for _clean_heading function."""

    def test_strip_trailing_em_dash(self) -> None:
        """Test stripping trailing '.—' from heading."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("Implementation.—") == "Implementation"
        assert _clean_heading("Sense of congress.—") == "Sense of congress"
        assert _clean_heading("Report .—") == "Report"  # Space before period

    def test_strip_trailing_period(self) -> None:
        """Test stripping trailing '.' from heading."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("PENALTIES.") == "Penalties"
        assert _clean_heading("Definitions.") == "Definitions"
        assert _clean_heading("Report. ") == "Report"  # Trailing space

    def test_all_caps_to_title_case(self) -> None:
        """Test ALL-CAPS headings are converted to Title Case."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("DEFINITIONS") == "Definitions"
        assert _clean_heading("PENALTIES") == "Penalties"
        assert _clean_heading("GENERAL PROVISIONS") == "General Provisions"
        assert (
            _clean_heading("SUBJECT MATTER AND SCOPE OF COPYRIGHT")
            == "Subject Matter And Scope Of Copyright"
        )

    def test_all_caps_with_trailing_period(self) -> None:
        """Test ALL-CAPS headings with trailing period."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("DEFINITIONS.") == "Definitions"
        assert _clean_heading("PENALTIES.") == "Penalties"
        assert _clean_heading("GENERAL PROVISIONS.") == "General Provisions"

    def test_mixed_case_unchanged(self) -> None:
        """Test mixed-case headings are not altered."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("Definitions") == "Definitions"
        assert _clean_heading("General provisions") == "General provisions"
        assert _clean_heading("Ownership of copyright") == "Ownership of copyright"

    def test_no_trailing_dash(self) -> None:
        """Test headings without trailing '.—' are unchanged."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("Implementation") == "Implementation"
        assert _clean_heading("Sense of congress") == "Sense of congress"

    def test_empty_heading(self) -> None:
        """Test empty headings."""
        from pipeline.olrc.normalized_section import _clean_heading

        assert _clean_heading("") == ""
        assert _clean_heading(None) is None


class TestAmendmentSubsectionPrefix:
    """Tests for amendment parsing with subsection prefix."""

    def test_subsection_prefix_captured(self) -> None:
        """Test that subsection prefix like 'Subsec. (c)(1).' is captured."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = """2021—Subsec. (c)(1), (2)(A). Pub. L. 117–81, § 1632(1), substituted text.
        """
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        assert "Subsec. (c)(1), (2)(A)." in amendments[0].description
        assert "Pub. L. 117–81" in amendments[0].description

    def test_amendment_without_subsection_prefix(self) -> None:
        """Test amendment without subsection prefix."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = """2013—Pub. L. 112–239, § 1033(b)(2)(B), made technical amendments.
        """
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        assert amendments[0].description.startswith("Pub. L. 112–239")
        assert "Subsec." not in amendments[0].description


class TestAmendmentDateSpacing:
    """Tests for fixing whitespace inside quotes in amendments."""

    def test_curly_quote_spacing_fixed(self) -> None:
        """Test that spaces inside curly quotes are removed."""
        from pipeline.olrc.normalized_section import _parse_amendments

        # Simulate text with curly quotes and extra spaces
        text = '2021—Pub. L. 117–81 substituted " December 31, 2021 " for " December 31, 2011 ".'
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        desc = amendments[0].description
        # Spaces inside curly quotes should be removed
        assert '" December' not in desc or '"December' in desc

    def test_straight_quote_spacing_fixed(self) -> None:
        """Test that spaces inside straight quotes are removed."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = '2021—Pub. L. 117–81 substituted " December 31, 2021 " for text.'
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        desc = amendments[0].description
        # Spaces inside quotes should be removed
        assert '" December' not in desc
