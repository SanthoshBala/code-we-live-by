"""Tests for legal text line normalization."""

import re

from app.models.enums import NoteRefType
from app.schemas import NoteReferenceSchema
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
    note_refs_to_schemas,
    parse_citation,
    parse_citations,
)
from pipeline.olrc.parser import NoteRef


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

    def test_hr_abbreviation_not_boundary(self) -> None:
        """H.R. (House Resolution/Report) is not a sentence boundary."""
        text = "summarized at pp. 30-31 of this report (H.R. Rep. No. 83, 90th Cong., 1st Sess.)"
        # Period at end of "H.R." should NOT be a boundary — next word is "Rep."
        pos = text.index("H.R.") + len("H.R.") - 1
        assert _is_sentence_boundary(text, pos) is False

    def test_senate_bill_abbreviation_not_boundary(self) -> None:
        """S. (Senate bill/report) is not a sentence boundary."""
        text = "retained in the Senate report on S. 22 (S. Rep. No. 94-473, pp. 63-65)."
        # Period at "S. 22" — the "S." should not be a boundary
        pos = text.index("S. 22") + 1
        assert _is_sentence_boundary(text, pos) is False

    def test_note_line_not_split_at_hr(self) -> None:
        """A legislative note citation with H.R. should produce a single line, not two."""
        text = (
            "The arguments are summarized at pp. 30-31 of this Committee's 1967 report "
            "(H.R. Rep. No. 83, 90th Cong., 1st Sess.), and have not changed materially."
        )
        sentences = _split_into_sentences(text)
        # The whole text should be ONE sentence — not split at H.R.
        plain = [s for s, _, _ in sentences if s != PARAGRAPH_BREAK_MARKER]
        assert len(plain) == 1, f"Expected 1 sentence, got {len(plain)}: {plain}"
        assert "H.R." in plain[0]
        assert "Rep. No. 83" in plain[0]


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

    def test_naval_asylum_regulations_not_treated_as_notes_header_issue_522(
        self,
    ) -> None:
        """Regression test for 24 U.S.C. § 17 (issue #522).

        The word "regulations" appearing mid-sentence must not be mistaken
        for the "Regulations" notes-section header, which would truncate the
        law text right before it.
        """
        text = (
            "The asylum for disabled and decrepit Navy officers, seamen, "
            "and marines shall be governed in accordance with the rules "
            "and regulations prescribed by the Secretary of the Navy."
        )

        result = normalize_section(text)

        full_text = " ".join(line.content for line in result.provisions)
        assert full_text == text
        assert "regulations prescribed by the Secretary of the Navy" in full_text

    def test_army_navy_hospital_regulations_not_truncated_issue_522(self) -> None:
        """Regression test for 24 U.S.C. § 18 (issue #522).

        Same pattern as § 17: "regulations" appears mid-sentence (after
        "such rules,") and must not be treated as a notes header.
        """
        text = (
            "The Army and Navy General Hospital at Hot Springs, Arkansas, "
            "shall be subject to such rules, regulations, and restrictions "
            "as shall be provided by the President of the United States "
            "and shall remain under the jurisdiction and control of the "
            "Department of the Army."
        )

        result = normalize_section(text)

        full_text = " ".join(line.content for line in result.provisions)
        assert full_text == text
        assert "regulations, and restrictions" in full_text
        assert "Department of the Army" in full_text


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

    def test_multi_sentence_no_marker_all_at_same_indent(self) -> None:
        """Multiple sentences in a no-marker subsection all render at base_indent.

        Regression test for Issue #450: 17 U.S.C. § 107's synthetic wrapper has
        no marker, so "In determining whether..." must not be bumped to indent_level=1.
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="107",
            heading="Fair use",
            full_citation="17 U.S.C. § 107",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="",
                    heading=None,
                    content=(
                        "Notwithstanding the provisions of sections 106 and 106A, "
                        "fair use is not infringement. "
                        "In determining whether the use is a fair use the factors shall include—"
                    ),
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="the purpose of the use;",
                            level="paragraph",
                        ),
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        sentence_lines = [
            p for p in result.provisions if p.content and not p.content.startswith("(")
        ]
        # Both section-level sentences must be at indent_level=0
        for line in sentence_lines:
            if "Notwithstanding" in line.content or "In determining" in line.content:
                assert line.indent_level == 0, (
                    f"Expected indent_level=0 for '{line.content[:40]}...', "
                    f"got {line.indent_level}"
                )


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


class TestNormalizeParsedSectionContinuationInsideContent:
    """End-to-end tests for <continuation> inside <content> in enumerated lists.

    Regression tests for Issue #447: 17 U.S.C. § 107's closing sentence
    ("The fact that a work is unpublished...") appears as a <continuation>
    element inside the <content> of the last <paragraph>.  The parser
    must promote it to section level so it renders at indent_level=0.
    """

    def test_continuation_inside_content_renders_at_indent_level_0(self) -> None:
        """A <continuation> inside a paragraph's <content> is promoted to
        section level and renders at indent_level=0.

        Models 17 U.S.C. § 107: four numbered factors followed by a flush-left
        closing sentence that applies to the entire section, not just factor (4).
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        # Simulate what the parser produces AFTER the fix: the continuation
        # has been promoted out of para4 and into the synthetic wrapper.
        section = ParsedSection(
            section_number="107",
            heading="Limitations on exclusive rights: Fair use",
            full_citation="17 U.S.C. § 107",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="",
                    heading=None,
                    content=(
                        "Notwithstanding the provisions of sections 106 and 106A, "
                        "in determining whether the use made of a work in any "
                        "particular case is a fair use the factors to be considered "
                        "shall include—"
                    ),
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="the purpose and character of the use;",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(2)",
                            heading=None,
                            content="the nature of the copyrighted work;",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(3)",
                            heading=None,
                            content=(
                                "the amount and substantiality of the portion used;"
                            ),
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(4)",
                            heading=None,
                            content=(
                                "the effect of the use upon the potential market for "
                                "or value of the copyrighted work."
                            ),
                            level="paragraph",
                            continuation=[],  # NOT here — promoted to wrapper
                        ),
                    ],
                    continuation=[
                        "The fact that a work is unpublished shall not itself bar "
                        "a finding of fair use if such finding is made upon "
                        "consideration of all the above factors."
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Find the continuation line
        continuation_lines = [
            p for p in result.provisions if "unpublished" in p.content
        ]
        assert len(continuation_lines) == 1, (
            "Expected exactly one line containing the continuation text"
        )
        cont_line = continuation_lines[0]

        # The continuation must be at indent_level=0 (flush-left, section level)
        assert cont_line.indent_level == 0, (
            f"Expected indent_level=0 for continuation, got {cont_line.indent_level}"
        )
        assert cont_line.marker is None

        # The numbered factors should be at indent_level=1
        factor_lines = [
            p for p in result.provisions if p.marker in {"(1)", "(2)", "(3)", "(4)"}
        ]
        assert len(factor_lines) == 4
        for fl in factor_lines:
            assert fl.indent_level == 1, (
                f"Factor {fl.marker} expected indent_level=1, got {fl.indent_level}"
            )

        # The continuation must appear after all four factors
        cont_line_num = cont_line.line_number
        for fl in factor_lines:
            assert fl.line_number < cont_line_num, (
                f"Factor {fl.marker} (line {fl.line_number}) must come before "
                f"continuation (line {cont_line_num})"
            )


class TestNormalizeParsedSectionContinuation:
    """Tests for <continuation> elements in parsed sections.

    Regression tests for Issue #251: continuation text (closing statutory
    clauses that follow a numbered list, e.g. penalty clauses) was silently
    dropped from the normalized output.
    """

    def test_continuation_appended_after_children(self) -> None:
        """Continuation text appears after child items at the same indent as the chapeau.

        Models 18 U.S.C. § 1001(a): chapeau + three paragraphs + penalty clause.
        The penalty clause (continuation) must appear at indent_level == 0,
        matching the chapeau's indent level.
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="1001",
            heading="Statements or entries generally",
            full_citation="18 U.S.C. § 1001",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content="Whoever knowingly and willfully—",
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="falsifies a material fact;",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(2)",
                            heading=None,
                            content="makes any false statement; or",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(3)",
                            heading=None,
                            content="makes or uses any false writing;",
                            level="paragraph",
                        ),
                    ],
                    continuation=[
                        "shall be fined under this title or imprisoned not more than 5 years, or both."
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Expected lines:
        #   0: "(a) Whoever knowingly and willfully—"  indent 0
        #   1: "(1) falsifies a material fact;"         indent 1
        #   2: "(2) makes any false statement; or"      indent 1
        #   3: "(3) makes or uses any false writing;"   indent 1
        #   4: "shall be fined under this title..."     indent 0  (continuation)
        assert result.provision_count == 5

        chapeau_line = result.provisions[0]
        assert "(a)" in chapeau_line.content
        assert "knowingly" in chapeau_line.content
        assert chapeau_line.indent_level == 0

        assert result.provisions[1].indent_level == 1
        assert "(1)" in result.provisions[1].content

        assert result.provisions[2].indent_level == 1
        assert "(2)" in result.provisions[2].content

        assert result.provisions[3].indent_level == 1
        assert "(3)" in result.provisions[3].content

        continuation_line = result.provisions[4]
        assert "shall be fined" in continuation_line.content
        assert continuation_line.indent_level == 0
        assert continuation_line.marker is None

    def test_continuation_indent_matches_chapeau_not_children(self) -> None:
        """Continuation is at the same indent as the enclosing chapeau, not the children."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="1001",
            heading="Test",
            full_citation="18 U.S.C. § 1001",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content="Intro text—",
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="item one;",
                            level="paragraph",
                        ),
                    ],
                    continuation=["closing clause."],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Lines: chapeau (indent 0), child (indent 1), continuation (indent 0)
        assert result.provision_count == 3
        chapeau_indent = result.provisions[0].indent_level
        child_indent = result.provisions[1].indent_level
        continuation_indent = result.provisions[2].indent_level

        assert child_indent > chapeau_indent
        assert continuation_indent == chapeau_indent

    def test_no_continuation_when_absent(self) -> None:
        """Sections without continuation produce no extra lines at the end."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="102",
            heading="Test",
            full_citation="17 U.S.C. § 102",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content="Single item.",
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)
        assert result.provision_count == 1
        assert result.provisions[0].content == "(a) Single item."


class TestNormalizeParsedSection9USC13:
    """End-to-end normalization tests for 9 U.S.C. § 13.

    Regression tests for Issues #478 and #479: the statutory body parser was
    silently dropping the introductory <p> element that precedes the (a)/(b)/(c)
    list, and merging a trailing <p> into the (c) item without a separator.
    """

    def test_intro_p_renders_as_first_provision(self) -> None:
        """The introductory <p> before the first list item must appear as the
        first provision at indent_level=0, not be dropped entirely.

        Regression test for Issue #478.
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        # Simulate what the parser produces AFTER the fix: intro <p> captured
        # as the synthetic wrapper's content (chapeau), trailing <p> in continuation.
        section = ParsedSection(
            section_number="13",
            heading="Application for order confirming, modifying, or correcting award",
            full_citation="9 U.S.C. § 13",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="",
                    heading=None,
                    content=(
                        "The party moving for an order confirming, modifying, or"
                        " correcting an award shall, at the time such order is filed"
                        " with the clerk for the entry of judgment thereon, also file"
                        " the following papers with the clerk:"
                    ),
                    children=[
                        ParsedSubsection(
                            marker="(a)",
                            heading=None,
                            content=(
                                "The agreement; the selection or appointment, if any,"
                                " of an additional arbitrator or umpire; and each"
                                " written extension of the time, if any, within which"
                                " to make the award."
                            ),
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(b)",
                            heading=None,
                            content="The award.",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(c)",
                            heading=None,
                            content=(
                                "Each notice, affidavit, or other paper used upon an"
                                " application to confirm, modify, or correct the award,"
                                " and a copy of each order of the court upon such an"
                                " application."
                            ),
                            level="paragraph",
                        ),
                    ],
                    level="subsection",
                    continuation=[
                        "The judgment shall be docketed as if it was rendered in an action."
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Must have 5 provisions: intro + (a) + (b) + (c) + docketing sentence
        assert result.provision_count == 5, (
            f"Expected 5 provisions (intro + 3 items + docketing), got"
            f" {result.provision_count}: {[p.content for p in result.provisions]}"
        )

        # First provision: intro sentence at indent 0 (Issue #478)
        intro = result.provisions[0]
        assert "party moving" in intro.content, (
            "Introductory sentence must appear as the first provision"
        )
        assert intro.indent_level == 0
        assert intro.marker is None

        # (a), (b), (c) at indent 1
        assert "(a)" in result.provisions[1].content
        assert result.provisions[1].indent_level == 1
        assert "(b)" in result.provisions[2].content
        assert result.provisions[2].indent_level == 1
        assert "(c)" in result.provisions[3].content
        assert result.provisions[3].indent_level == 1

        # Docketing sentence as a separate provision at indent 0 (Issue #479)
        docketing = result.provisions[4]
        assert "docketed" in docketing.content, (
            "Docketing sentence must appear as a distinct final provision"
        )
        assert docketing.indent_level == 0
        assert docketing.marker is None

    def test_docketing_sentence_not_merged_with_c_item(self) -> None:
        """The docketing sentence must NOT be concatenated into the (c) content.

        Regression test for Issue #479: the merged content was
        '(c) ...application.The judgment shall be docketed...' (no space).
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="13",
            heading="Application for order confirming, modifying, or correcting award",
            full_citation="9 U.S.C. § 13",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="",
                    heading=None,
                    content="The party moving for an order:",
                    children=[
                        ParsedSubsection(
                            marker="(a)",
                            heading=None,
                            content="The agreement.",
                            level="paragraph",
                        ),
                        ParsedSubsection(
                            marker="(c)",
                            heading=None,
                            content=(
                                "Each notice, affidavit, or other paper used upon an"
                                " application to confirm, modify, or correct the award,"
                                " and a copy of each order of the court upon such an"
                                " application."
                            ),
                            level="paragraph",
                        ),
                    ],
                    level="subsection",
                    continuation=[
                        "The judgment shall be docketed as if it was rendered in an action."
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Find the (c) provision
        c_provision = next(
            (p for p in result.provisions if p.content.startswith("(c)")), None
        )
        assert c_provision is not None, "Provision (c) must be present"

        # (c) content must NOT include the docketing sentence
        assert "docketed" not in c_provision.content, (
            "Docketing sentence must NOT be merged into provision (c)"
        )
        # The no-space artifact must not appear
        assert "application.The" not in c_provision.content, (
            "Sentences must not be concatenated without a space"
        )

        # The docketing sentence must be a separate provision
        docketing = next(
            (p for p in result.provisions if "docketed" in p.content), None
        )
        assert docketing is not None, (
            "Docketing sentence must appear as a distinct provision"
        )
        assert docketing.line_number > c_provision.line_number, (
            "Docketing sentence must appear after provision (c)"
        )


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

    def test_sig_single_line_no_embedded_newline(self) -> None:
        """Each [SIG] token produces exactly one line with no embedded newline."""
        # Simulates parser output when <signature> has separate <name> and <role>
        # children that were emitted as two distinct [SIG] tokens (issue #511).
        text = "[PARA][SIG]— By Irwin Karp,[/SIG][PARA][SIG]— Counsel[/SIG]"
        lines = normalize_note_content(text)

        sig_lines = [ln for ln in lines if ln.is_signature]
        # Must produce two separate signature lines, not one with an embedded \n
        assert len(sig_lines) == 2
        for ln in sig_lines:
            assert "\n" not in ln.content, (
                f"Embedded newline found in signature line: {ln.content!r}"
            )
        assert sig_lines[0].content == "— By Irwin Karp,"
        assert sig_lines[1].content == "— Counsel"


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

    def test_section_with_chapeau_and_continuation(self) -> None:
        """quotedContent with anonymous section: chapeau + paragraphs + continuation."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <quotedContent>
                <section class="inline">
                    <num value=""/>
                    <chapeau>"Notwithstanding any provision&#8212;</chapeau>
                    <paragraph>
                        <num value="1">"(1)"</num>
                        <content>imposes any tax, or</content>
                    </paragraph>
                    <paragraph>
                        <num value="2">"(2)"</num>
                        <content>establishes any trust fund,</content>
                    </paragraph>
                    <continuation>shall have no force or effect."</continuation>
                </section>
            </quotedContent>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Chapeau should be at level 1, paragraphs at level 2
        assert "[QC:1]" in content
        assert "[QC:2]" in content
        assert "Notwithstanding" in content
        assert '"(1)"' in content
        assert "imposes any tax" in content
        assert "shall have no force or effect" in content

    def test_named_sections_in_quoted_content(self) -> None:
        """quotedContent with named sections (section + subsection nesting)."""
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <quotedContent>
                <section>
                    <num value="1">"SEC. 1."</num>
                    <heading>SHORT TITLE.</heading>
                    <content>This Act may be cited as the 'Test Act'.</content>
                </section>
                <section>
                    <num value="2">"SEC. 2."</num>
                    <heading>DEFINITIONS.</heading>
                    <subsection>
                        <num value="a">"(a)"</num>
                        <content>For purposes of this Act&#8212;</content>
                    </subsection>
                </section>
            </quotedContent>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # Section headers at level 1, subsection at level 2
        assert '"SEC. 1."' in content
        assert "SHORT TITLE" in content
        assert '"SEC. 2."' in content
        assert "[QC:1]" in content
        assert "[QC:2]" in content

    def test_paragraphs_direct_children_of_quoted_content(self) -> None:
        """quotedContent whose direct children are <paragraph> (no enclosing
        <section>/<subsection>), optionally preceded by a bare <inline> intro.

        This mirrors the real OLRC structure for the 21 U.S.C. 822 "Findings"
        statutory note (Pub. L. 111-273, Sec. 2), where <quotedContent> wraps
        an <inline> intro line followed directly by sibling <paragraph>
        elements -- some of which have nested <subparagraph> children -- with
        no <section> or <subsection> wrapper at the top level (issue #536).
        """
        from lxml import etree

        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        xml = """<notes>
            <quotedContent>
                <inline>"Congress finds the following:</inline>
                <paragraph>
                    <num value="1">"(1)"</num>
                    <content>The nonmedical use of prescription drugs is a growing problem.</content>
                </paragraph>
                <paragraph>
                    <num value="2">"(2)"</num>
                    <chapeau>According to the Department of Justice&#8212;</chapeau>
                    <subparagraph>
                        <num value="A">"(A)"</num>
                        <content>the number of deaths has increased significantly; and</content>
                    </subparagraph>
                    <subparagraph>
                        <num value="B">"(B)"</num>
                        <content>treatment admissions increased.</content>
                    </subparagraph>
                </paragraph>
            </quotedContent>
        </notes>"""
        elem = etree.fromstring(xml)

        content = parser._get_notes_text_content(elem)

        # The bare intro line and each enumerated paragraph/subparagraph
        # must become its own [QC:level] marker rather than being flattened
        # into a single block of concatenated text.
        assert "Congress finds the following" in content
        assert '"(1)"' in content
        assert '"(2)"' in content
        assert '"(A)"' in content
        assert '"(B)"' in content
        assert "[QC:1]" in content
        assert "[QC:2]" in content

        # The intro and each paragraph/subparagraph must be distinct QC
        # blocks -- not one giant block containing all of the text below.
        qc_blocks = re.findall(r"\[QC:\d+\](.*?)\[/QC\]", content, flags=re.DOTALL)
        assert len(qc_blocks) >= 5
        assert not any('"(1)"' in block and '"(2)"' in block for block in qc_blocks), (
            "paragraphs (1) and (2) must not be merged into a single QC block"
        )
        assert not any('"(A)"' in block and '"(B)"' in block for block in qc_blocks), (
            "subparagraphs (A) and (B) must not be merged into a single QC block"
        )

    def test_is_quoted_flag_set_on_qc_lines(self) -> None:
        """Lines derived from quotedContent blocks have is_quoted=True."""
        from pipeline.olrc.normalized_section import normalize_note_content

        raw = 'Provided that:\n[QC:1]"(a)" First item.[/QC]\n[QC:1]"(b)" Second item.[/QC]'
        lines = normalize_note_content(raw)

        prose_lines = [ln for ln in lines if not ln.is_quoted]
        quoted_lines = [ln for ln in lines if ln.is_quoted]

        assert any("Provided" in ln.content for ln in prose_lines)
        assert len(quoted_lines) == 2
        assert all(ln.is_quoted for ln in quoted_lines)

    def test_smallcaps_heading_marked_with_nh(self) -> None:
        """Test that smallCaps headings are marked with [NH]...[/NH].

        The heading text must be preserved verbatim from the XML — no
        title-casing applied (see issue #509).  Paragraph content must
        NOT be wrapped in [NH] markers regardless of its capitalisation.
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

        # Heading must be wrapped in [NH]...[/NH] with verbatim text (issue #509)
        assert "[NH]Delegation of Functions[/NH]" in content
        # Title-cased variant must NOT appear
        assert "[NH]Delegation Of Functions[/NH]" not in content
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

    def test_signature_with_name_and_role_emits_separate_sig_tokens(self) -> None:
        """<signature> with <name> and <role> children emits two separate [SIG] tokens.

        Regression test for issue #511: when <signature> contains both <name>
        and <role> child elements, the parser must not collapse them into a
        single string with an embedded \\n. Each child element should become
        its own [SIG] token so that normalize_note_content can turn them into
        distinct line objects.
        """
        from lxml import etree

        from pipeline.olrc.normalized_section import normalize_note_content
        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        # Mirrors the OLRC source for 17 U.S.C. § 107 Guidelines note
        xml = """<notes>
            <p>Agreed upon in principle March 19, 1976.</p>
            <signature>
                <name>By Irwin Karp,</name>
                <role>Counsel.</role>
            </signature>
            <signature>
                <name>By Alexander C. Hoffman</name>
            </signature>
        </notes>"""
        elem = etree.fromstring(xml)

        raw = parser._get_notes_text_content(elem)

        # Should have three separate [SIG]...[/SIG] blocks: Irwin Karp name,
        # Counsel role, and Alexander C. Hoffman (no role child).
        assert raw.count("[SIG]") == 3, (
            f"Expected 3 [SIG] tokens, got {raw.count('[SIG]')}: {raw!r}"
        )

        # No embedded newline must appear inside any single [SIG] span
        import re

        for m in re.finditer(r"\[SIG\](.*?)\[/SIG\]", raw, re.DOTALL):
            assert "\n" not in m.group(1), (
                f"Embedded newline inside [SIG]: {m.group(1)!r}"
            )

        # Now verify normalize_note_content produces two separate line objects
        lines = normalize_note_content(raw)
        sig_lines = [ln for ln in lines if ln.is_signature]
        assert len(sig_lines) == 3
        for ln in sig_lines:
            assert "\n" not in ln.content, (
                f"Embedded newline in rendered signature line: {ln.content!r}"
            )

    def test_sibling_role_after_signature_emits_separate_sig_line(self) -> None:
        """Adjacent <signature> + <role> siblings each emit their own [SIG] line.

        Regression test for issue #555: when a <role> element appears as a
        sibling (not a child) of <signature> in a USLM note — as in
        17 U.S.C. § 107, release point 113-21 — the parser must not collapse
        them into a single content string with an embedded raw newline, nor
        silently drop the role text.  Both elements must become distinct
        is_signature=True lines with no \\n in their content.
        """
        from lxml import etree

        from pipeline.olrc.normalized_section import normalize_note_content
        from pipeline.olrc.parser import USLMParser

        parser = USLMParser()

        # Mirrors the actual OLRC USLM structure for the classroom-copying
        # agreement note in 17 U.S.C. § 107 (release point 113-21).
        xml = """<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">
            <note>
                <heading>House Report No. 94-1476</heading>
                <p>Agreed upon in principle March 19, 1976.</p>
                <p>Authors League of America:</p>
                <signature>By Irwin Karp,</signature>
                <role>Counsel.</role>
            </note>
        </notes>"""
        elem = etree.fromstring(xml)

        raw = parser._get_notes_text_content(elem)

        # Both the <signature> and the sibling <role> must produce separate
        # [SIG] tokens — no embedded \n between them.
        import re

        sig_spans = re.findall(r"\[SIG\](.*?)\[/SIG\]", raw, re.DOTALL)
        assert len(sig_spans) == 2, (
            f"Expected 2 [SIG] tokens for sibling signature+role, "
            f"got {len(sig_spans)}: {raw!r}"
        )
        for span in sig_spans:
            assert "\n" not in span, f"Embedded newline inside [SIG] span: {span!r}"

        # normalize_note_content must produce two is_signature=True lines
        lines = normalize_note_content(raw)
        sig_lines = [ln for ln in lines if ln.is_signature]
        assert len(sig_lines) == 2, (
            f"Expected 2 signature lines, got {len(sig_lines)}: "
            + str([(ln.is_signature, ln.content) for ln in lines])
        )
        for ln in sig_lines:
            assert "\n" not in ln.content, (
                f"Embedded newline in rendered signature line: {ln.content!r}"
            )

        # The <role> line must have the same is_signature flag as the <signature>
        # line — no role text should appear as a plain non-signature line.
        non_sig_contents = [ln.content for ln in lines if not ln.is_signature]
        for content in non_sig_contents:
            assert "Counsel" not in content, (
                f"Role text 'Counsel' ended up in a non-signature line: {content!r}"
            )


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

    def test_strip_h2_markers_keeps_text(self) -> None:
        """[H2]...[/H2] wrappers are removed but the inner text is preserved."""
        text = "provided that: [H2]Brevity[/H2] (i) Poetry: ..."
        result = _strip_note_markers(text)
        assert "[H2]" not in result
        assert "[/H2]" not in result
        assert "Brevity" in result

    def test_strip_qc_markers_keeps_text(self) -> None:
        """[QC:N]...[/QC] wrappers are removed but the inner text is preserved."""
        text = 'provided that: [QC:1]"The amendments made by subsection (a) shall apply."[/QC] No Requirement'
        result = _strip_note_markers(text)
        assert "[QC:1]" not in result
        assert "[/QC]" not in result
        assert "amendments made by subsection" in result
        assert "No Requirement" in result

    def test_strip_qc_multilevel(self) -> None:
        """[QC:N] with any level number is stripped."""
        text = "[QC:1]First level.[/QC] [QC:2]Second level.[/QC]"
        result = _strip_note_markers(text)
        assert "[QC:" not in result
        assert "First level." in result
        assert "Second level." in result


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

        # Lines should include the Memorandum paragraphs
        all_text = " ".join(line.content for line in statutory_notes[0].lines)
        assert "Memorandum of President" in all_text
        assert "Secretary of State" in all_text

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

        # First note should be "Congressional Committees Defined" and contain the key text
        first_note = notes.notes[0]
        assert first_note.header == "Congressional Committees Defined"
        first_text = " ".join(line.content for line in first_note.lines)
        assert "congressional defense committees" in first_text

    def test_single_statutory_note_h1_header(self) -> None:
        """Regression for Issue #534: lone note encoded with [H1] heading marker.

        When a USLM section uses <b>Effective Date</b> as the sub-heading for
        a statutory note (producing [H1]...[/H1] rather than [NH]...[/NH]),
        _parse_statutory_notes must still capture the note via the [H1] fallback.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_statutory_notes,
        )

        raw_notes = (
            "[H1]Statutory Notes and Related Subsidiaries[/H1] "
            "[H1]Effective Date[/H1]\n\n"
            "For effective date of this section, see section 29 of Pub. L. 91-597, "
            "set out as a note under section 1031 of this title."
        )
        notes = SectionNotes()
        _parse_statutory_notes(raw_notes, notes)
        assert len(notes.notes) == 1
        assert notes.notes[0].header == "Effective Date"
        assert notes.notes[0].category.value == "statutory"
        all_text = " ".join(line.content for line in notes.notes[0].lines)
        assert "Pub. L. 91-597" in all_text

    def test_single_statutory_note_plain_text_header(self) -> None:
        """Regression for Issue #534: lone note with header as plain tail text.

        21 U.S.C. ss 1054's XML has "Effective Date" as tail text of the
        <b>Statutory Notes and Related Subsidiaries</b> element with no marker.
        The plain-text fallback must capture it when no [NH] or [H1] markers exist.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_statutory_notes,
        )

        raw_notes = (
            "[H1]Statutory Notes and Related Subsidiaries[/H1] "
            "Effective Date\n\n"
            "For effective date of this section, see section 29 of Pub. L. 91-597, "
            "set out as a note under section 1031 of this title."
        )
        notes = SectionNotes()
        _parse_statutory_notes(raw_notes, notes)
        assert len(notes.notes) == 1
        assert notes.notes[0].header == "Effective Date"
        assert notes.notes[0].category.value == "statutory"
        all_text = " ".join(line.content for line in notes.notes[0].lines)
        assert "Pub. L. 91-597" in all_text

    def test_full_xml_pipeline_issue_534(self) -> None:
        """End-to-end regression for Issue #534: full XML to parsed notes pipeline.

        Confirms that the complete pipeline (XML parsing -> raw text ->
        _parse_notes_structure) correctly captures the lone Effective Date
        statutory note that immediately follows the cross-heading in the USLM
        XML for 21 U.S.C. ss 1054.
        """
        from lxml import etree

        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )
        from pipeline.olrc.parser import USLMParser

        # Mirrors the USLM XML structure for 21 U.S.C. ss 1054 as described in Issue #534.
        xml = (
            "<notes>"
            "<b>Statutory Notes and Related Subsidiaries</b>"
            "Effective Date"
            "<p>For effective date of this section, see section 29 of "
            "Pub. L. 91-597, set out as a note under section 1031 of this title.</p>"
            "</notes>"
        )
        notes_elem = etree.fromstring(xml)
        raw = USLMParser()._get_notes_text_content(notes_elem)
        notes = SectionNotes()
        _parse_notes_structure(raw, notes)
        statutory = [n for n in notes.notes if n.category.value == "statutory"]
        assert len(statutory) == 1, f"Expected 1 statutory note, got {len(statutory)}"
        assert statutory[0].header == "Effective Date"
        body = " ".join(line.content for line in statutory[0].lines)
        assert "Pub. L. 91-597" in body


class TestFlatNotesParser:
    """Tests for _parse_flat_notes — fallback for sections without category wrappers.

    Real-world example: 16 U.S.C. § 797 has individual <note> elements directly
    under <notes> with no "Editorial Notes" or "Statutory Notes" wrapper heading,
    so the three category-aware parsers all fail and notes.notes ends up empty.
    """

    def test_flat_amendments_note_is_editorial(self) -> None:
        """Flat 'Amendments' note is categorised as EDITORIAL."""
        from pipeline.olrc.normalized_section import SectionNotes, _parse_flat_notes

        raw_notes = (
            "[NH]Amendments[/NH] "
            "2005—Subsec. (e). Pub. L. 109–58, inserted text after first proviso. "
            "1986—Subsec. (e). Pub. L. 99–495 inserted additional provisions."
        )
        notes = SectionNotes()
        _parse_flat_notes(raw_notes, notes)

        assert len(notes.notes) == 1
        assert notes.notes[0].header == "Amendments"
        assert notes.notes[0].category.value == "editorial"

    def test_flat_statutory_note_is_statutory(self) -> None:
        """Flat notes with non-editorial headers are categorised as STATUTORY."""
        from pipeline.olrc.normalized_section import SectionNotes, _parse_flat_notes

        raw_notes = (
            "[NH]Effective Date Of 1986 Amendment[/NH] "
            "Pub. L. 99–495, § 18, Oct. 16, 1986, 100 Stat. 1259, provided that "
            "the amendments shall take effect with respect to each license issued after enactment."
        )
        notes = SectionNotes()
        _parse_flat_notes(raw_notes, notes)

        assert len(notes.notes) == 1
        assert notes.notes[0].header == "Effective Date Of 1986 Amendment"
        assert notes.notes[0].category.value == "statutory"

    def test_flat_notes_multiple_headers(self) -> None:
        """Multiple flat notes are all parsed with correct categories."""
        from pipeline.olrc.normalized_section import SectionNotes, _parse_flat_notes

        raw_notes = (
            "[NH]Amendments[/NH] "
            "2005—Subsec. (e). Pub. L. 109–58, inserted text after first proviso. "
            "1986—Subsec. (e). Pub. L. 99–495 inserted additional provisions. "
            "[NH]Change Of Name[/NH] "
            "Department of War designated Department of the Army by act July 26, 1947. "
            "[NH]Savings Provision[/NH] "
            "Pub. L. 99–495, § 17(a), Oct. 16, 1986, 100 Stat. 1259, provided that "
            "nothing in the Act shall be construed as authorizing the appropriation of water."
        )
        notes = SectionNotes()
        _parse_flat_notes(raw_notes, notes)

        assert len(notes.notes) == 3
        headers = [n.header for n in notes.notes]
        assert "Amendments" in headers
        assert "Change Of Name" in headers
        assert "Savings Provision" in headers

        editorial = [n for n in notes.notes if n.category.value == "editorial"]
        statutory = [n for n in notes.notes if n.category.value == "statutory"]
        assert len(editorial) == 2  # Amendments + Change Of Name
        assert len(statutory) == 1  # Savings Provision

    def test_flat_notes_fallback_in_parse_notes_structure(self) -> None:
        """_parse_notes_structure triggers the flat fallback when no category headers exist.

        This is the actual bug from 16 U.S.C. § 797: notes text contains [NH] markers
        but no 'Editorial Notes' / 'Statutory Notes' wrapper.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        raw_notes = (
            "[NH]Amendments[/NH] "
            "2005—Subsec. (e). Pub. L. 109–58, inserted text after first proviso. "
            "1986—Subsec. (e). Pub. L. 99–495 inserted additional provisions. "
            "[NH]Savings Provision[/NH] "
            "Pub. L. 99–495, § 17(a), Oct. 16, 1986, 100 Stat. 1259, provided that "
            "nothing in the Act shall be construed as authorizing the appropriation of water."
        )
        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        assert len(notes.notes) >= 2
        headers = [n.header for n in notes.notes]
        assert "Amendments" in headers
        assert "Savings Provision" in headers

    def test_flat_notes_short_content_skipped(self) -> None:
        """Notes with content <= 30 characters are skipped."""
        from pipeline.olrc.normalized_section import SectionNotes, _parse_flat_notes

        raw_notes = "[NH]Amendments[/NH] Too short."
        notes = SectionNotes()
        _parse_flat_notes(raw_notes, notes)

        assert len(notes.notes) == 0

    def test_flat_notes_after_historical_note_issue_283(self) -> None:
        """Regression: flat notes after 'Historical and Revision Notes' must not be swallowed.

        13 U.S.C. § 141 has 11 flat notes. The first is 'Historical and Revision
        Notes'; prior to the fix _parse_historical_notes greedily consumed all
        content (since there was no 'Editorial Notes' terminator), leaving notes
        2–11 unprocessed.  Closes #283.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        raw_notes = (
            "[NH]Historical And Revision Notes[/NH] "
            "Based on title 13, U.S.C., 1952 ed., § 201 (part). "
            "[NH]Amendments[/NH] "
            "1957—Pub. L. 85–207, § 9, substituted heading; added housing census. "
            "1975—Pub. L. 94–171, §§ 1, 2(a), inserted apportionment tabulation. "
            "1976—Pub. L. 94–521, § 7(a), updated heading and subsections. "
            "[NH]Effective Date Of 1976 Amendment[/NH] "
            "Amendment by Pub. L. 94–521 effective Oct. 1, 1976. "
            "[NH]Statistical Sampling Or Adjustment In Decennial Enumeration[/NH] "
            "Pub. L. 105–119, title II, § 209(a), Nov. 26, 1997, 111 Stat. 2482, provided."
        )
        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        headers = [n.header for n in notes.notes]
        # _parse_historical_notes hardcodes "Historical and Revision Notes" (lowercase "and")
        assert "Historical and Revision Notes" in headers
        assert "Amendments" in headers
        assert "Effective Date Of 1976 Amendment" in headers
        assert "Statistical Sampling Or Adjustment In Decennial Enumeration" in headers
        assert len(notes.notes) >= 4

    def test_references_in_text_not_captured_in_historical_note_issue_504(
        self,
    ) -> None:
        """Regression: References in Text content must not bleed into Historical note.

        For positive-law sections (e.g. 41 U.S.C. § 4706) the OLRC XML places
        multiple <note> children inside a single <notes> wrapper:

            <notes>
              <note topic="historicalAndRevision"><heading>Historical and Revision Notes</heading>
                ...table and paragraphs...
              </note>
              <note topic="referencesInText"><heading>References In Text</heading>
                <p>The Inspector General Act of 1978...</p>
              </note>
            </notes>

        _get_notes_text_content processes all children and produces a raw_notes
        string where both note headers appear as [NH] markers:

            [NH]Historical And Revision Notes[/NH] ... [NH]References In Text[/NH] ...

        Prior to the fix _parse_historical_notes used a regex that stopped only
        at "Editorial Notes" / "Statutory Notes" or end-of-string.  It greedily
        consumed the References in Text paragraph as the last line of the
        Historical note, while _parse_flat_notes also created a correct
        "References In Text" note — resulting in the Inspector General Act
        sentence appearing twice.  Closes #504.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        # This mirrors what _get_notes_text_content produces for the XML
        # described above (one <notes> wrapper, two <note> children).
        # The historical note refers to IG Act generically; the References
        # note gives the full citation — "set out in the Appendix to Title 5"
        # is unique to the References In Text note and must not appear in the
        # Historical note's lines.
        raw_notes = (
            "[NH]Historical And Revision Notes[/NH] "
            "In subsection (a), the reference is for clarity. "
            "In subsection (c)(1), the reference to the Inspector General Act "
            "of 1978 is added for clarity. "
            "[NH]References In Text[/NH] "
            "The Inspector General Act of 1978, referred to in subsec. (c)(1), "
            "is Pub. L. 95-452, Oct. 12, 1978, 92 Stat. 1101, which is set out "
            "in the Appendix to Title 5, Government Organization and Employees."
        )
        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        headers = [n.header for n in notes.notes]
        assert "Historical and Revision Notes" in headers
        assert "References In Text" in headers

        # The Historical note must NOT contain the References in Text sentence.
        # "set out in the Appendix to Title 5" is unique to the References note.
        hist_note = next(n for n in notes.notes if "Historical" in n.header)
        hist_content = " ".join(line.content for line in hist_note.lines)
        assert "set out in the Appendix to Title 5" not in hist_content, (
            "References in Text content must not bleed into Historical note lines"
        )

        # The References In Text note must contain the correct sentence.
        ref_note = next(n for n in notes.notes if "References" in n.header)
        ref_content = " ".join(line.content for line in ref_note.lines)
        assert "set out in the Appendix to Title 5" in ref_content

    def test_amendments_populated_from_flat_notes_issue_284(self) -> None:
        """Regression: notes.amendments must be populated when 'Amendments' is a flat note.

        For 13 U.S.C. § 141 the 'Amendments' note is flat (no 'Editorial Notes'
        wrapper). Prior to the fix _parse_flat_notes was not called because
        _parse_historical_notes had already added a note.  Closes #284.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        raw_notes = (
            "[NH]Historical And Revision Notes[/NH] "
            "Based on title 13, U.S.C., 1952 ed., § 201 (part). "
            "[NH]Amendments[/NH] "
            "1957—Pub. L. 85–207, § 9, substituted the heading for prior heading. "
            "1975—Pub. L. 94–171, §§ 1, 2(a), inserted apportionment language. "
        )
        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        # amendments array must be populated from the flat Amendments note
        assert len(notes.amendments) > 0
        years = [a.year for a in notes.amendments]
        assert 1957 in years
        assert 1975 in years

    def test_house_report_note_does_not_absorb_siblings_issue_498(self) -> None:
        """Regression: House Report note must not bleed into Amendments/Effective Date.

        11 U.S.C. § 1163 (release 113-21): the Historical and Revision Notes contain
        a House Report No. 95-595 note, followed by flat [NH]-delimited sibling notes
        for Amendments and Effective Date of 1986 Amendment.  Because there is no
        'Editorial Notes' / 'Statutory Notes' wrapper, the hist_text regex captured
        everything to end-of-string.  The House Report note's content_end was then set
        to len(hist_text), absorbing the Amendments and Effective Date text.  Closes #498.
        """
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        # Minimal reproduction of the 11 USC § 1163 flat-notes structure:
        # Historical notes header + House Report + sibling flat notes
        raw_notes = (
            "Historical and Revision Notes "
            "[NH]House Report No. 95-595[/NH] "
            "[Section 1162] This section [enacted as section 1163] requires the appointment "
            "of an independent trustee in a railroad reorganization case. "
            "The court may appoint one or more disinterested persons to serve as trustee "
            "in the case. "
            "[NH]Amendments[/NH] "
            "1986— Pub. L. 99–554 amended section generally, substituting provisions "
            "relating to appointment of trustee for provisions relating to qualification "
            "of trustee. "
            "[NH]Effective Date Of 1986 Amendment[/NH] "
            "Effective date and applicability of amendment by Pub. L. 99–554 are "
            "as provided in section 302(a) of Pub. L. 99–554."
        )

        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        # All four notes must be present
        headers = [n.header for n in notes.notes]
        assert "House Report No. 95-595" in headers, f"Notes: {headers}"
        assert "Amendments" in headers, f"Notes: {headers}"
        assert "Effective Date Of 1986 Amendment" in headers, f"Notes: {headers}"

        # The House Report note must contain ONLY its own content —
        # no Amendments text and no Effective Date text.
        house_report = next(
            n for n in notes.notes if n.header == "House Report No. 95-595"
        )
        house_text = " ".join(line.content for line in house_report.lines)
        assert "independent trustee" in house_text, (
            "House Report should contain its own text"
        )
        assert "1986" not in house_text, (
            "House Report note must not contain Amendments year text"
        )
        assert "Pub. L. 99–554" not in house_text, (
            "House Report note must not contain Amendments Pub. L. reference"
        )
        assert "Effective date and applicability" not in house_text, (
            "House Report note must not contain Effective Date text"
        )

        # Amendments note must have its own content
        amendments = next(n for n in notes.notes if n.header == "Amendments")
        amend_text = " ".join(line.content for line in amendments.lines)
        assert "Pub. L. 99–554" in amend_text, (
            "Amendments note should contain Pub. L. ref"
        )

        # Effective Date note must have its own content
        eff_date = next(
            n for n in notes.notes if n.header == "Effective Date Of 1986 Amendment"
        )
        eff_text = " ".join(line.content for line in eff_date.lines)
        assert "Effective date and applicability" in eff_text, (
            "Effective Date note should contain its own text"
        )


class TestNoteTopicAmendmentParsing:
    """Regression tests for issue #216: <note topic="amendments"> not parsed.

    Two patterns appear in USLM XML for amendment notes that previously broke:
    - Editorial wrapper + inner <note topic="amendments"><heading>Amendments</heading>
    - Flat <note topic="amendments"> without a <heading> child at all
    """

    def _parse_xml_notes(self, xml_snippet: str) -> object:
        from lxml import etree

        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )
        from pipeline.olrc.parser import USLMParser

        notes_elem = etree.fromstring(xml_snippet)
        raw = USLMParser()._get_notes_text_content(notes_elem)
        notes = SectionNotes()
        _parse_notes_structure(raw, notes)
        return notes

    def test_editorial_wrapper_with_plain_heading(self) -> None:
        """17 USC 403 pattern: <note class="editorial"> + inner <heading>Amendments</heading>.

        The inner heading has no class="smallCaps" but must still emit [NH] so
        _parse_editorial_notes can find and categorise it.
        """
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note class="editorial">'
            '<heading class="smallCaps">Editorial Notes</heading>'
            '<note topic="amendments">'
            "<heading>Amendments</heading>"
            "<p>1988—Pub. L. 100–568 amended section generally.</p>"
            "</note>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        assert any(n.header == "Amendments" for n in notes.notes)
        assert len(notes.amendments) == 1
        assert notes.amendments[0].year == 1988

    def test_flat_topic_note_without_heading(self) -> None:
        """17 USC 1005 pattern: <note topic="amendments"> with no <heading> child.

        The topic attribute alone must synthesise the [NH] header so the fallback
        flat-notes parser can categorise the content.
        """
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="amendments">'
            "<p>1993—Pub. L. 103–198 struck out at end"
            ' "The Register shall submit a report."</p>'
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        assert any(n.header == "Amendments" for n in notes.notes)
        assert len(notes.amendments) == 1
        assert notes.amendments[0].year == 1993

    def test_flat_topic_note_with_heading(self) -> None:
        """<note topic="amendments"><heading>Amendments</heading>: heading takes precedence."""
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="amendments">'
            "<heading>Amendments</heading>"
            "<p>1993—Pub. L. 103–198 struck out at end"
            ' "The Register shall submit a report."</p>'
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        # Should not produce duplicate Amendments notes
        amendment_notes = [n for n in notes.notes if n.header == "Amendments"]
        assert len(amendment_notes) == 1
        assert len(notes.amendments) >= 1

    def test_multiple_flat_notes_mixed_categories_issue_222(self) -> None:
        """33 USC §2215 pattern: multiple flat <note topic="..."><heading>...</heading> elements.

        The section has 4 flat notes with no 'Editorial Notes'/'Statutory Notes' wrapper.
        All notes must be parsed with correct categories. Closes #222.
        """
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="referencesInText">'
            "<heading>References in Text</heading>"
            "<p>The Water Resources Development Act of 2000, referred to in subsec. (d)(2),"
            " is Pub. L. 106–541, Dec. 11, 2000, 114 Stat. 2572."
            " Title VI of the Act is not classified to the Code.</p>"
            "</note>"
            '<note topic="amendments">'
            "<heading>Amendments</heading>"
            "<p>2007—Subsec. (a)(3). Pub. L. 110–114, added par. (3).</p>"
            "<p>1990—Subsec. (b). Pub. L. 101–640 inserted text at end.</p>"
            "</note>"
            '<note topic="effectiveDateOfAmendment">'
            "<heading>Effective Date of 1996 Amendment</heading>"
            "<p>Pub. L. 104–303, title II, § 203(b), Oct. 12, 1996,"
            " 110 Stat. 3678, provided that the amendments shall apply"
            " notwithstanding any prior feasibility cost-sharing agreement.</p>"
            "</note>"
            '<note topic="miscellaneous">'
            "<heading>No Requirement of Reimbursement</heading>"
            "<p>Pub. L. 104–303, title II, § 203(c), Oct. 12, 1996,"
            " 110 Stat. 3678, provided that nothing in this section requires"
            " reimbursement for funds previously contributed for a study.</p>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        assert len(notes.notes) == 4

        # Headers must be verbatim from the OLRC source XML <heading> elements —
        # no title-casing applied (see issue #509).
        headers = [n.header for n in notes.notes]
        assert "References in Text" in headers
        assert "Amendments" in headers
        assert "Effective Date of 1996 Amendment" in headers
        assert "No Requirement of Reimbursement" in headers

        editorial = [n for n in notes.notes if n.category.value == "editorial"]
        statutory = [n for n in notes.notes if n.category.value == "statutory"]
        assert len(editorial) == 2  # References in Text + Amendments
        assert len(statutory) == 2  # Effective Date + No Requirement

        assert len(notes.amendments) >= 2
        years = [a.year for a in notes.amendments]
        assert 1990 in years
        assert 2007 in years

    def test_historical_and_revision_camelcase_topic_no_duplicate_issue_503(
        self,
    ) -> None:
        """Regression: <note topic="historicalAndRevision"> must not produce a duplicate note.

        Positive-law sections (e.g. 41 U.S.C. § 4706) use
        <note topic="historicalAndRevision"> without a <heading> child.  Prior to
        the fix, topic.title() produced the garbled header "Historicalandrevision"
        (camelCase is treated as a single word by str.title()), which did not match
        the already-processed "historical and revision notes" header.  The flat-notes
        fallback then added a second, malformed SectionNote.

        After the fix, the canonical display string "Historical and Revision Notes"
        is used for this topic, so the fallback recognises it as already processed
        and no duplicate is created.  Closes #503.
        """
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="historicalAndRevision">'
            "<p>Based on 41:252(a)(1), (c)."
            " Source Credit: Pub. L. 111-350, Jan. 4, 2011, 124 Stat. 3677.</p>"
            "<p>The words 'agency' and 'executive agency' are coextensive"
            " and synonymous in the revised title.</p>"
            "</note>"
            '<note topic="amendments">'
            "<heading>Amendments</heading>"
            "<p>2012—Subsec. (a). Pub. L. 112-239, § 801(b)(1),"
            " substituted 'executive agency' for 'agency'.</p>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        headers = [n.header for n in notes.notes]
        # Only one Historical and Revision Notes entry — no duplicate
        hist_notes = [n for n in notes.notes if "historical" in n.header.lower()]
        assert len(hist_notes) == 1, (
            f"Expected exactly 1 historical note, got {len(hist_notes)}: {headers}"
        )
        assert hist_notes[0].header == "Historical and Revision Notes"
        assert hist_notes[0].category.value == "historical"
        # No garbled "Historicalandrevision" header
        assert not any("historicalandrevision" in h.lower() for h in headers), (
            f"Garbled camelCase header found in: {headers}"
        )
        # Amendments note is also present and correct
        assert "Amendments" in headers


class TestAmendmentsIndentLevel:
    """Regression tests for issue #573: Amendments note lines must use indent_level=1.

    The _amendment_lines fast-path previously hardcoded indent_level=0, causing
    Amendments content to render flush-left while peer notes (Derivation,
    References In Text) correctly used indent_level=1 from normalize_note_content.
    All editorial note content lines must have the same base indent level.
    """

    def test_amendment_lines_indent_level_is_one(self) -> None:
        """_amendment_lines returns lines with indent_level=1, matching peer notes."""
        from pipeline.olrc.normalized_section import _amendment_lines

        raw = (
            "[NH]Amendments[/NH] "
            "1954—Act Sept. 3, 1954, brought section into conformity with arbitration "
            "rules of the Federal Rules of Civil Procedure."
        )
        lines = _amendment_lines(raw)

        assert len(lines) > 0
        for line in lines:
            assert line.indent_level == 1, (
                f"Expected indent_level=1 for Amendments line, got {line.indent_level}: "
                f"{line.content!r}"
            )

    def test_amendments_indent_matches_peer_notes_issue_573(self) -> None:
        """9 U.S.C. § 4 pattern: Amendments indent_level equals Derivation/References indent.

        Amendments, Derivation, and References In Text are peer notes in the OLRC
        XML. All three must produce lines with the same indent_level so the rendered
        notes section is visually consistent. Closes #573.
        """
        from lxml import etree

        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )
        from pipeline.olrc.parser import USLMParser

        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note class="editorial">'
            '<heading class="smallCaps">Editorial Notes</heading>'
            '<note topic="derivation">'
            "<heading>Derivation</heading>"
            "<p>Act Feb. 12, 1925, ch. 213, § 4, 43 Stat. 883.</p>"
            "</note>"
            '<note topic="referencesInText">'
            "<heading>References In Text</heading>"
            "<p>Federal Rules of Civil Procedure, referred to in text,"
            " are set out in the Appendix to Title 28.</p>"
            "</note>"
            '<note topic="amendments">'
            "<heading>Amendments</heading>"
            "<p>1954—Act Sept. 3, 1954, brought section into conformity"
            " with arbitration rules of the Federal Rules of Civil Procedure.</p>"
            "</note>"
            "</note>"
            "</notes>"
        )
        notes_elem = etree.fromstring(xml)
        raw = USLMParser()._get_notes_text_content(notes_elem)
        notes = SectionNotes()
        _parse_notes_structure(raw, notes)

        # Collect all content lines (non-empty, non-header) by note header
        content_lines_by_header: dict[str, list[int]] = {}
        for note in notes.notes:
            content_lines = [
                line.indent_level
                for line in note.lines
                if line.content and not line.is_header
            ]
            if content_lines:
                content_lines_by_header[note.header] = content_lines

        assert "Derivation" in content_lines_by_header, "Derivation note not found"
        assert "References In Text" in content_lines_by_header, (
            "References In Text note not found"
        )
        assert "Amendments" in content_lines_by_header, "Amendments note not found"

        derivation_indent = content_lines_by_header["Derivation"][0]
        references_indent = content_lines_by_header["References In Text"][0]
        amendments_indent = content_lines_by_header["Amendments"][0]

        assert amendments_indent == derivation_indent, (
            f"Amendments indent_level ({amendments_indent}) != "
            f"Derivation indent_level ({derivation_indent})"
        )
        assert amendments_indent == references_indent, (
            f"Amendments indent_level ({amendments_indent}) != "
            f"References In Text indent_level ({references_indent})"
        )
        # Explicit check: all note content must be at indent_level=1
        assert amendments_indent == 1, (
            f"Expected indent_level=1 for all editorial note content, "
            f"got {amendments_indent} for Amendments"
        )


class TestNoteHeadersVerbatim:
    """Regression tests for issue #509: note headers must not be title-cased.

    The OLRC XML <heading> element inside <note> contains verbatim headings
    (e.g. "Effective Date of 1984 Amendment") that must be preserved exactly.
    Applying .title() mangles lowercase connective words ("of" → "Of").
    """

    def _parse_xml_notes(self, xml_snippet: str) -> object:
        from lxml import etree

        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )
        from pipeline.olrc.parser import USLMParser

        notes_elem = etree.fromstring(xml_snippet)
        raw = USLMParser()._get_notes_text_content(notes_elem)
        notes = SectionNotes()
        _parse_notes_structure(raw, notes)
        return notes

    def test_of_in_note_header_preserved_verbatim(self) -> None:
        """'of' in a note <heading> must not become 'Of' (issue #509).

        Mirrors the failing example from Title 3 § 6 of release 113-21:
        OLRC XML: <heading>Effective Date of 1984 Amendment</heading>
        Bug:      notes[].header == "Effective Date Of 1984 Amendment"
        Fix:      notes[].header == "Effective Date of 1984 Amendment"
        """
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="effectiveDateOfAmendment">'
            "<heading>Effective Date of 1984 Amendment</heading>"
            "<p>Pub. L. 98–497 effective Apr. 1, 1985, see section 301 of Pub. L. 98–497.</p>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        headers = [n.header for n in notes.notes]
        # Verbatim — lowercase "of" must be preserved
        assert "Effective Date of 1984 Amendment" in headers
        # Title-cased form must NOT appear
        assert "Effective Date Of 1984 Amendment" not in headers

    def test_connectives_in_note_headers_preserved(self) -> None:
        """All common lowercase connectives must survive verbatim (issue #509)."""
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="miscellaneous">'
            "<heading>Termination of Reporting Requirements</heading>"
            "<p>Pub. L. 104–66 provided that the reporting requirement is terminated.</p>"
            "</note>"
            '<note topic="miscellaneous">'
            "<heading>Applicability of Future Employment Laws</heading>"
            "<p>Pub. L. 104–331 extended laws to Presidential offices.</p>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        headers = [n.header for n in notes.notes]
        assert "Termination of Reporting Requirements" in headers, (
            "lowercase 'of' must be preserved in note headers"
        )
        assert "Applicability of Future Employment Laws" in headers, (
            "lowercase 'of' must be preserved in note headers"
        )
        # Title-cased variants must NOT appear
        assert "Termination Of Reporting Requirements" not in headers
        assert "Applicability Of Future Employment Laws" not in headers

    def test_note_header_exactly_matches_xml_heading(self) -> None:
        """note.header must equal the verbatim XML <heading> text, character-for-character."""
        xml = (
            '<notes xmlns="http://xml.house.gov/schemas/uslm/1.0">'
            '<note topic="referencesInText">'
            "<heading>References in Text</heading>"
            "<p>The Higher Education Act of 1965, referred to in text, is Pub. L. 89–329.</p>"
            "</note>"
            "</notes>"
        )
        notes = self._parse_xml_notes(xml)

        assert len(notes.notes) == 1
        assert notes.notes[0].header == "References in Text", (
            f"Expected 'References in Text' but got {notes.notes[0].header!r}"
        )


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


class TestMultiSentenceSplitting:
    """Tests for splitting multi-sentence paragraphs onto separate provision lines.

    Covers both the XML-based path (normalize_parsed_section) and the
    fallback heuristic path (normalize_section).
    """

    # -- XML-based path (normalize_parsed_section) --

    def test_xml_heading_multi_sentence_content(self) -> None:
        """Multi-sentence content under a heading produces one line per sentence."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="2705",
            heading="Exemptions",
            full_citation="16 U.S.C. § 2705",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(d)",
                    heading="Exemptions",
                    content=(
                        "The Commission may in its discretion grant an exemption. "
                        "Except as specifically provided in this subsection, "
                        "no exemption shall apply."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Header + 2 content sentences = 3 lines
        assert result.provision_count == 3
        assert result.provisions[0].content == "(d) Exemptions"
        assert result.provisions[0].is_header is True
        assert result.provisions[1].content == (
            "The Commission may in its discretion grant an exemption."
        )
        assert result.provisions[1].indent_level == 1
        assert result.provisions[2].content == (
            "Except as specifically provided in this subsection, "
            "no exemption shall apply."
        )
        assert result.provisions[2].indent_level == 1

    def test_xml_no_heading_multi_sentence_content(self) -> None:
        """Multi-sentence content without a heading splits after the marker."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="100",
            heading="Test",
            full_citation="42 U.S.C. § 100",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content=(
                        "First sentence of provision. Second sentence continues here."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # 2 lines: marker + first sentence, then second sentence
        assert result.provision_count == 2
        assert result.provisions[0].content == ("(a) First sentence of provision.")
        assert result.provisions[0].marker == "(a)"
        assert result.provisions[1].content == "Second sentence continues here."
        assert result.provisions[1].marker is None
        # Continuation line is indented one level deeper, flush with the text
        # portion of line 0 (not the marker). Fixes: github.com/SanthoshBala/code-we-live-by/issues/122
        assert (
            result.provisions[1].indent_level == result.provisions[0].indent_level + 1
        )

    def test_xml_single_sentence_unchanged(self) -> None:
        """Single-sentence content still produces exactly one line."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="101",
            heading="Test",
            full_citation="17 U.S.C. § 101",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content="Only one sentence here.",
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 1
        assert result.provisions[0].content == "(a) Only one sentence here."

    def test_xml_abbreviations_not_split(self) -> None:
        """Legal abbreviations like U.S.C. are not treated as sentence boundaries."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="200",
            heading="Test",
            full_citation="42 U.S.C. § 200",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content=(
                        "As defined under title 42, U.S.C. The term applies broadly. "
                        "Additional provisions may apply."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # "U.S.C." should NOT be a sentence boundary, so the first two
        # sentences merge.  Only the period after "broadly." triggers a real
        # split, producing 2 lines total (not 3).
        assert result.provision_count == 2
        first = result.provisions[0].content
        assert "U.S.C." in first
        assert "applies broadly." in first

    def test_xml_pub_l_abbreviation_not_split(self) -> None:
        """Pub. L. abbreviation does not cause a false sentence split."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="300",
            heading="Test",
            full_citation="50 U.S.C. § 300",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(b)",
                    heading=None,
                    content=(
                        "As amended by Pub. L. 116–136, this section provides relief."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # "Pub." and "L." should not cause splits
        assert result.provision_count == 1
        assert "Pub. L. 116–136" in result.provisions[0].content

    def test_xml_three_sentences(self) -> None:
        """Three sentences in one paragraph produce three lines."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="400",
            heading="Test",
            full_citation="26 U.S.C. § 400",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(c)",
                    heading=None,
                    content=(
                        "The Secretary shall promulgate regulations. "
                        "Such regulations shall take effect on the date of enactment. "
                        "Nothing in this paragraph limits the authority of the Secretary."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 3
        assert result.provisions[0].content.startswith("(c) The Secretary")
        assert result.provisions[0].marker == "(c)"
        assert result.provisions[1].content.startswith("Such regulations")
        assert result.provisions[1].marker is None
        assert result.provisions[2].content.startswith("Nothing in this paragraph")
        assert result.provisions[2].marker is None

    def test_xml_chapeau_not_split_on_colon(self) -> None:
        """Chapeau text ending with a colon stays on one line."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="500",
            heading="Test",
            full_citation="22 U.S.C. § 500",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content="The following conditions apply:",
                    level="subsection",
                    children=[
                        ParsedSubsection(
                            marker="(1)",
                            heading=None,
                            content="Condition one.",
                            level="paragraph",
                        ),
                    ],
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # Chapeau on one line, child on next
        assert result.provisions[0].content == "(a) The following conditions apply:"
        assert result.provisions[1].content == "(1) Condition one."

    # -- Fallback heuristic path (normalize_section) --

    def test_fallback_multi_sentence_list_item(self) -> None:
        """Fallback normalize_section splits multi-sentence list items."""
        text = (
            "(a) The Commission may grant an exemption in its discretion. "
            "No exemption shall be granted without notice."
        )

        result = normalize_section(text)

        assert result.provision_count == 2
        assert result.provisions[0].content.startswith("(a) The Commission")
        assert result.provisions[0].marker == "(a)"
        assert result.provisions[1].content.startswith("No exemption")
        assert result.provisions[1].marker is None
        # Continuation line must be one level deeper (flush with text, not marker).
        assert (
            result.provisions[1].indent_level == result.provisions[0].indent_level + 1
        )

    def test_fallback_single_sentence_unchanged(self) -> None:
        """Fallback single-sentence list items remain on one line."""
        text = "(a) The Commission may grant an exemption."

        result = normalize_section(text)

        assert result.provision_count == 1
        assert (
            result.provisions[0].content == "(a) The Commission may grant an exemption."
        )

    def test_fallback_abbreviation_not_split(self) -> None:
        """Fallback path respects legal abbreviations."""
        text = "(a) Pursuant to Pub. L. 116–136, the Secretary shall act."

        result = normalize_section(text)

        assert result.provision_count == 1
        assert "Pub. L. 116–136" in result.provisions[0].content

    def test_xml_et_seq_abbreviation_not_split(self) -> None:
        """'et seq.' abbreviation does not trigger a false split."""
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        section = ParsedSection(
            section_number="600",
            heading="Test",
            full_citation="42 U.S.C. § 600",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content=(
                        "As defined in section 1396 et seq. "
                        "Additional requirements apply."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        # "et seq." ends with a period but should not trigger a split
        # because "seq." is in LEGAL_ABBREVIATIONS (via "et." check)
        # The "Additional" starts a new sentence after "seq. "
        # This should produce 2 lines
        assert result.provision_count == 2
        assert "et seq." in result.provisions[0].content

    def test_xml_no_heading_continuation_indent_2usc31_2(self) -> None:
        """Continuation lines of a no-heading provision are indented one level
        deeper than the marker line (flush with the text portion).

        Regression test for 2 U.S.C. § 31-2 L18-19 being flush with the marker
        instead of the text. See: github.com/SanthoshBala/code-we-live-by/issues/122
        """
        from pipeline.olrc.normalized_section import normalize_parsed_section
        from pipeline.olrc.parser import ParsedSection, ParsedSubsection

        # Mimics the structure of 2 U.S.C. § 31-2 where (a) has multiple sentences
        section = ParsedSection(
            section_number="31-2",
            heading="Lump-sum payments",
            full_citation="2 U.S.C. § 31-2",
            text_content="",
            subsections=[
                ParsedSubsection(
                    marker="(a)",
                    heading=None,
                    content=(
                        "Each Member of the House of Representatives may receive a lump-sum payment. "
                        "Such payment shall be in lieu of any other payment. "
                        "The amount shall be determined by the Committee."
                    ),
                    level="subsection",
                ),
            ],
        )

        result = normalize_parsed_section(section)

        assert result.provision_count == 3
        # First line: marker + first sentence at base indent
        assert result.provisions[0].marker == "(a)"
        marker_indent = result.provisions[0].indent_level
        # Continuation lines (L18-19 equivalent) must be one level deeper
        assert result.provisions[1].indent_level == marker_indent + 1
        assert result.provisions[2].indent_level == marker_indent + 1


class TestNoteRefsToSchemas:
    """Tests for note_refs_to_schemas function (Task 1.17b)."""

    def test_convert_public_law_ref(self) -> None:
        """Test converting a Public Law NoteRef to NoteReferenceSchema."""
        note_ref = NoteRef(
            ref_type="public_law",
            href="/us/pl/115/264",
            display_text="Pub. L. 115–264",
            congress=115,
            law_number=264,
        )
        schemas = note_refs_to_schemas([note_ref])

        assert len(schemas) == 1
        schema = schemas[0]
        assert schema.ref_type == NoteRefType.PUBLIC_LAW
        assert schema.href == "/us/pl/115/264"
        assert schema.display_text == "Pub. L. 115–264"
        assert schema.congress == 115
        assert schema.law_number == 264
        assert schema.target_id == "PL 115-264"

    def test_convert_usc_section_ref(self) -> None:
        """Test converting a US Code section NoteRef to NoteReferenceSchema."""
        note_ref = NoteRef(
            ref_type="usc_section",
            href="/us/usc/t17/s106",
            display_text="section 106",
            usc_title=17,
            usc_section="106",
        )
        schemas = note_refs_to_schemas([note_ref])

        assert len(schemas) == 1
        schema = schemas[0]
        assert schema.ref_type == NoteRefType.USC_SECTION
        assert schema.usc_title == 17
        assert schema.usc_section == "106"
        assert schema.target_id == "17 USC 106"

    def test_convert_statute_ref(self) -> None:
        """Test converting a Statute NoteRef to NoteReferenceSchema."""
        note_ref = NoteRef(
            ref_type="statute",
            href="/us/stat/90/2546",
            display_text="90 Stat. 2546",
            stat_volume=90,
            stat_page=2546,
        )
        schemas = note_refs_to_schemas([note_ref])

        assert len(schemas) == 1
        schema = schemas[0]
        assert schema.ref_type == NoteRefType.STATUTE
        assert schema.stat_volume == 90
        assert schema.stat_page == 2546
        assert schema.target_id == "90 Stat. 2546"

    def test_convert_act_ref(self) -> None:
        """Test converting an Act NoteRef to NoteReferenceSchema."""
        note_ref = NoteRef(
            ref_type="act",
            href="/us/act/1935-08-14/ch531",
            display_text="act Aug. 14, 1935, ch. 531",
            act_date="1935-08-14",
            act_chapter=531,
        )
        schemas = note_refs_to_schemas([note_ref])

        assert len(schemas) == 1
        schema = schemas[0]
        assert schema.ref_type == NoteRefType.ACT
        assert schema.act_date == "1935-08-14"
        assert schema.act_chapter == 531
        assert schema.target_id == "Act of 1935-08-14 ch. 531"

    def test_convert_multiple_refs(self) -> None:
        """Test converting multiple NoteRefs to schemas."""
        note_refs = [
            NoteRef(
                ref_type="public_law",
                href="/us/pl/94/553",
                display_text="Pub. L. 94–553",
                congress=94,
                law_number=553,
            ),
            NoteRef(
                ref_type="usc_section",
                href="/us/usc/t17/s101",
                display_text="17 U.S.C. 101",
                usc_title=17,
                usc_section="101",
            ),
            NoteRef(
                ref_type="statute",
                href="/us/stat/90/2546",
                display_text="90 Stat. 2546",
                stat_volume=90,
                stat_page=2546,
            ),
        ]
        schemas = note_refs_to_schemas(note_refs)

        assert len(schemas) == 3
        assert schemas[0].ref_type == NoteRefType.PUBLIC_LAW
        assert schemas[1].ref_type == NoteRefType.USC_SECTION
        assert schemas[2].ref_type == NoteRefType.STATUTE

    def test_empty_list(self) -> None:
        """Test converting an empty list returns empty list."""
        schemas = note_refs_to_schemas([])
        assert schemas == []


class TestNoteReferenceSchema:
    """Tests for NoteReferenceSchema model (Task 1.17b)."""

    def test_target_id_public_law(self) -> None:
        """Test target_id computed property for Public Law."""
        schema = NoteReferenceSchema(
            ref_type=NoteRefType.PUBLIC_LAW,
            href="/us/pl/115/264",
            congress=115,
            law_number=264,
        )
        assert schema.target_id == "PL 115-264"

    def test_target_id_usc_section(self) -> None:
        """Test target_id computed property for US Code section."""
        schema = NoteReferenceSchema(
            ref_type=NoteRefType.USC_SECTION,
            href="/us/usc/t17/s106",
            usc_title=17,
            usc_section="106",
        )
        assert schema.target_id == "17 USC 106"

    def test_target_id_statute(self) -> None:
        """Test target_id computed property for Statute."""
        schema = NoteReferenceSchema(
            ref_type=NoteRefType.STATUTE,
            href="/us/stat/90/2546",
            stat_volume=90,
            stat_page=2546,
        )
        assert schema.target_id == "90 Stat. 2546"

    def test_target_id_act(self) -> None:
        """Test target_id computed property for Act."""
        schema = NoteReferenceSchema(
            ref_type=NoteRefType.ACT,
            href="/us/act/1935-08-14/ch531",
            act_date="1935-08-14",
            act_chapter=531,
        )
        assert schema.target_id == "Act of 1935-08-14 ch. 531"

    def test_target_id_fallback_to_href(self) -> None:
        """Test target_id falls back to href when fields missing."""
        schema = NoteReferenceSchema(
            ref_type=NoteRefType.PUBLIC_LAW,
            href="/us/pl/unknown",
            # Missing congress and law_number
        )
        assert schema.target_id == "/us/pl/unknown"


class TestPrePLAmendmentCitations:
    """Regression tests for issues #566 and #567.

    Pre-1957 chapter-style amendment citations (e.g. "Act Oct. 31, 1951, ch. 655")
    must populate notes.amendments and contribute to last_amendment_year even though
    they have no modern Pub. L. number.
    """

    def test_pre_pl_amendment_appears_in_amendments(self) -> None:
        """A section with only a chapter-style amendment has a non-empty notes.amendments."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = (
            '1951—Act Oct. 31, 1951, substituted "United States district court for"'
            ' for "United States court in and for", and "by law for" for'
            ' "on February 12, 1925, for".'
        )
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        assert amendments[0].year == 1951
        assert amendments[0].law is None
        assert "Act Oct. 31, 1951" in amendments[0].description

    def test_pre_pl_amendment_year_from_year_prefix(self) -> None:
        """last_amendment_year is derived from the year prefix in a chapter-style note."""
        from pipeline.olrc.normalized_section import (
            SectionNotes,
            _parse_notes_structure,
        )

        raw_notes = (
            "[NH]Amendments[/NH] "
            '1951—Act Oct. 31, 1951, ch. 655, substituted "United States district court for"'
            ' for "United States court in and for".'
        )
        notes = SectionNotes()
        _parse_notes_structure(raw_notes, notes)

        assert len(notes.amendments) == 1
        assert notes.amendments[0].year == 1951
        assert notes.amendments[0].law is None

    def test_modern_pl_amendments_unaffected(self) -> None:
        """Sections with modern Pub. L. amendments are parsed as before."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = "2013—Pub. L. 112–239, § 1033(b)(2)(B), made technical amendments."
        amendments = _parse_amendments(text)

        assert len(amendments) == 1
        assert amendments[0].year == 2013
        assert amendments[0].law is not None
        assert amendments[0].law.congress == 112
        assert amendments[0].law.law_number == 239

    def test_pre_pl_and_modern_amendments_coexist(self) -> None:
        """A section amended by both an Act and a Pub. L. returns both entries."""
        from pipeline.olrc.normalized_section import _parse_amendments

        text = (
            "2000—Pub. L. 106–518 made a change.\n"
            '1951—Act Oct. 31, 1951, ch. 655, substituted "district court for" for "court in and for".'
        )
        amendments = _parse_amendments(text)

        assert len(amendments) == 2
        years = {a.year for a in amendments}
        assert years == {2000, 1951}
        modern = next(a for a in amendments if a.year == 2000)
        pre_pl = next(a for a in amendments if a.year == 1951)
        assert modern.law is not None
        assert modern.law.congress == 106
        assert pre_pl.law is None


class TestAmendmentMidSentencePubLFix:
    """Regression tests for issue #558: amendment parser splits mid-sentence on
    Pub. L. cross-references, producing spurious and truncated entries.

    Root cause: the old _PUB_L_PATTERN lookahead fired on any 'Pub. L.' string,
    including cross-references inside sentences.  The fix splits each year-block
    into paragraphs at double-newlines (one <p> element → one entry) and uses a
    per-paragraph anchored pattern (_PUB_L_PARA_PATTERN) instead.
    """

    def test_bug_a_no_split_on_mid_sentence_pub_l_crossref(self) -> None:
        """Bug A: Pub. L. cross-reference mid-sentence must NOT create a spurious entry.

        13 USC §141 first 1976 paragraph:
          "Pub. L. 94–521 substituted catchline … without reference to
           amendment of catchline by Pub. L. 94–171."

        Must produce exactly ONE entry (for Pub. L. 94–521) with the full
        sentence.  Previously produced two: a truncated entry ending at "by"
        and a spurious entry for Pub. L. 94–171.
        """
        from pipeline.olrc.normalized_section import _parse_amendments

        text = (
            "1976—Pub. L. 94–521 substituted “Population and other "
            "census information” for “Population, unemployment, and housing” "
            "in section catchline, without reference to amendment of catchline "
            "by Pub. L. 94–171."
        )
        amendments = _parse_amendments(text)

        assert len(amendments) == 1, (
            f"Expected 1 amendment but got {len(amendments)}: "
            + str([a.description for a in amendments])
        )
        a = amendments[0]
        assert a.year == 1976
        assert a.law.congress == 94
        assert a.law.law_number == 521
        # Full sentence must be preserved, including the cross-reference law
        assert "by Pub. L. 94–171" in a.description

    def test_bug_b_subsecs_plural_prefix_captured(self) -> None:
        """Bug B: 'Subsecs.' (plural) prefix must be captured, not lost.

        13 USC §141 fifth 1976 paragraph:
          "Subsecs. (d) to (g). Pub. L. 94–521 added subsecs. (d) to (g)."

        Must produce ONE entry with the prefix included in the description.
        Previously the 'Subsecs.' form was not recognised as a prefix, so the
        subsection range bled into the *previous* entry and this entry lost it.
        """
        from pipeline.olrc.normalized_section import _parse_amendments

        text = "1976—Subsecs. (d) to (g). Pub. L. 94–521 added subsecs. (d) to (g)."
        amendments = _parse_amendments(text)

        assert len(amendments) == 1, (
            f"Expected 1 amendment but got {len(amendments)}: "
            + str([a.description for a in amendments])
        )
        a = amendments[0]
        assert a.year == 1976
        assert a.law.congress == 94
        assert a.law.law_number == 521
        assert "Subsecs. (d) to (g)." in a.description
        assert "added subsecs. (d) to (g)." in a.description

    def test_13_usc_141_full_1976_block_produces_eight_entries(self) -> None:
        """Regression: 13 USC §141 must produce exactly 8 amendment entries.

        OLRC shows 5 PL 94-521 entries + 2 PL 94-171 entries + 1 PL 85-207
        entry = 8 total.  Previously produced 9 entries due to Bugs A and B.
        """
        from pipeline.olrc.normalized_section import _parse_amendments

        # Paragraphs separated by \n\n (as produced from separate <p> elements)
        text = (
            "1976—"
            "Pub. L. 94–521 substituted “Population and other census "
            "information” for “Population, unemployment, and housing” "
            "in section catchline, without reference to amendment of catchline "
            "by Pub. L. 94–171.\n\n"
            "Subsec. (a). Pub. L. 94–521 substituted provisions in subsec. (a).\n\n"
            "Subsec. (b). Pub. L. 94–521 substituted provisions in subsec. (b).\n\n"
            "Subsec. (c). Pub. L. 94–521 substituted “the decennial census "
            "date” for “the census date” wherever appearing.\n\n"
            "Subsecs. (d) to (g). Pub. L. 94–521 added subsecs. (d) to (g).\n\n"
            "1975—"
            "Pub. L. 94–171, §§ 1, 2(a), inserted “;tabulation "
            "for legislative apportionment” in catchline.\n\n"
            "Subsec. (c). Pub. L. 94–171, § 1, added subsec. (c).\n\n"
            "1957—"
            "Pub. L. 85–207, § 9, substituted catchline and added "
            "housing provisions."
        )
        amendments = _parse_amendments(text)

        assert len(amendments) == 8, (
            f"Expected 8 amendments but got {len(amendments)}: "
            + str([(a.year, a.law.congress, a.law.law_number) for a in amendments])
        )

        years = [a.year for a in amendments]
        assert years.count(1976) == 5
        assert years.count(1975) == 2
        assert years.count(1957) == 1

        # All 1976 entries must be attributed to PL 94-521
        for a in amendments:
            if a.year == 1976:
                assert a.law.congress == 94
                assert a.law.law_number == 521

        # The first 1976 entry must contain the full cross-reference sentence
        first_1976 = next(a for a in amendments if a.year == 1976)
        assert "by Pub. L. 94–171" in first_1976.description

        # The fifth 1976 entry must have the Subsecs. plural prefix
        fifth_1976 = [a for a in amendments if a.year == 1976][4]
        assert "Subsecs. (d) to (g)." in fifth_1976.description


class TestReferencesInTextLines:
    """Tests for _references_in_text_lines function.

    Regression tests for Issue #601: a single <p> element in a References in
    Text note must not be split into multiple lines by sentence-boundary
    detection.  Each <p> element (represented by [PARA] markers in the raw
    content) must produce exactly one ParsedLine.
    """

    def test_single_para_with_multiple_sentences_produces_one_line(self) -> None:
        """A single <p> element with multiple sentences stays as one line.

        Regression test for Issue #601: the sentence splitter was incorrectly
        breaking a References in Text note paragraph into multiple lines.
        The paragraph for 26 U.S.C. § 2504 contains three sentence-ending
        periods but should appear as a single display line.
        """
        from pipeline.olrc.normalized_section import _references_in_text_lines

        # One <p> element whose text contains three sentence-ending periods —
        # the exact structure that triggered Issue #601.
        raw = (
            " The Tax Reform Act of 1976, referred to in subsec. (b), "
            "is Pub. L. 94–455, Oct. 4, 1976, 90 Stat. 1520. "
            "Section 2521 of the Internal Revenue Code of 1954 was repealed "
            "by Pub. L. 94–455. "
            "For complete classification of this Act to the Code, "
            "see Tables."
        )

        lines = _references_in_text_lines(raw)

        assert len(lines) == 1, (
            f"Expected 1 line for single <p> with multiple sentences, "
            f"got {len(lines)}: {[ln.content for ln in lines]}"
        )
        assert "Tax Reform Act" in lines[0].content
        assert "Section 2521" in lines[0].content
        assert "see Tables" in lines[0].content

    def test_multiple_paras_produce_separate_lines(self) -> None:
        """Multiple <p> elements (separated by [PARA]) each become one line."""
        from pipeline.olrc.normalized_section import _references_in_text_lines

        raw = (
            " First paragraph text with multiple sentences. It continues here.[PARA]"
            " Second paragraph with different content. Also multiple sentences here."
        )

        lines = _references_in_text_lines(raw)

        assert len(lines) == 2, (
            f"Expected 2 lines (one per <p> element), got {len(lines)}: "
            f"{[ln.content for ln in lines]}"
        )
        assert "First paragraph" in lines[0].content
        assert "Second paragraph" in lines[1].content

    def test_nh_markers_stripped(self) -> None:
        """[NH]...[/NH] note-header markers are stripped from content."""
        from pipeline.olrc.normalized_section import _references_in_text_lines

        raw = (
            "[NH]References in Text[/NH]"
            " The relevant act, Pub. L. 94–455, applies here."
        )

        lines = _references_in_text_lines(raw)

        assert len(lines) == 1
        assert "[NH]" not in lines[0].content
        assert "Pub. L. 94–455" in lines[0].content

    def test_empty_content_returns_empty_list(self) -> None:
        """Empty or whitespace-only content returns an empty list."""
        from pipeline.olrc.normalized_section import _references_in_text_lines

        assert _references_in_text_lines("") == []
        assert _references_in_text_lines("   ") == []
        assert _references_in_text_lines("[NH]Header[/NH]") == []

    def test_lines_have_indent_level_one(self) -> None:
        """All parsed lines are at indent_level=1 (matching other note lines)."""
        from pipeline.olrc.normalized_section import _references_in_text_lines

        raw = "First reference paragraph.[PARA]Second reference paragraph."
        lines = _references_in_text_lines(raw)

        assert len(lines) == 2
        for ln in lines:
            assert ln.indent_level == 1
            assert ln.marker is None
            assert ln.is_header is False
