"""Tests for legal language parser."""

from app.models.enums import ChangeType
from pipeline.legal_parser import AmendmentParser, SectionReference
from pipeline.legal_parser.patterns import PatternType


class TestSectionReference:
    """Tests for SectionReference dataclass."""

    def test_str_with_all_fields(self) -> None:
        """Test string representation with all fields."""
        ref = SectionReference(title=17, section="106", subsection_path="(a)(1)")
        assert str(ref) == "17 U.S.C. § 106 (a)(1)"

    def test_str_without_title(self) -> None:
        """Test string representation without title."""
        ref = SectionReference(title=None, section="106", subsection_path=None)
        assert str(ref) == "§ 106"

    def test_str_with_letter_section(self) -> None:
        """Test string representation with letter in section number."""
        ref = SectionReference(title=17, section="106A", subsection_path=None)
        assert str(ref) == "17 U.S.C. § 106A"

    def test_from_match(self) -> None:
        """Test creating from match groups."""
        ref = SectionReference.from_match("106", title=17, subsection_path="(a)")
        assert ref.section == "106"
        assert ref.title == 17
        assert ref.subsection_path == "(a)"


class TestAmendmentParserBasic:
    """Basic tests for AmendmentParser."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        parser = AmendmentParser()
        assert parser.default_title is None
        assert len(parser.patterns) > 0
        assert parser.min_confidence == 0.0

    def test_init_with_title(self) -> None:
        """Test initialization with default title."""
        parser = AmendmentParser(default_title=17)
        assert parser.default_title == 17

    def test_init_with_min_confidence(self) -> None:
        """Test initialization with minimum confidence."""
        parser = AmendmentParser(min_confidence=0.90)
        assert parser.min_confidence == 0.90


class TestSectionReferenceParsing:
    """Tests for section reference parsing."""

    def test_parse_simple_section(self) -> None:
        """Test parsing simple section reference."""
        parser = AmendmentParser(default_title=17)
        ref = parser.parse_section_reference("Section 106")
        assert ref is not None
        assert ref.section == "106"
        assert ref.title == 17

    def test_parse_section_with_title(self) -> None:
        """Test parsing section with title."""
        parser = AmendmentParser()
        ref = parser.parse_section_reference("Section 106 of Title 17")
        assert ref is not None
        assert ref.section == "106"
        assert ref.title == 17

    def test_parse_section_with_subsection(self) -> None:
        """Test parsing section with subsection."""
        parser = AmendmentParser(default_title=17)
        ref = parser.parse_section_reference("Section 106(a)(1)")
        assert ref is not None
        assert ref.section == "106"
        assert ref.subsection_path == "(a)(1)"

    def test_parse_section_letter_suffix(self) -> None:
        """Test parsing section with letter suffix."""
        parser = AmendmentParser(default_title=17)
        ref = parser.parse_section_reference("Section 106A")
        assert ref is not None
        assert ref.section == "106A"


class TestStrikeInsertPatterns:
    """Tests for strike and insert pattern matching."""

    def test_strike_insert_basic(self) -> None:
        """Test basic strike and insert pattern."""
        parser = AmendmentParser(default_title=17)
        text = 'Section 106 is amended by striking "old text" and inserting "new text".'

        amendments = parser.parse(text)
        assert len(amendments) >= 1

        # Find the strike_insert amendment
        strike_insert = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]
        assert len(strike_insert) >= 1

        amendment = strike_insert[0]
        assert amendment.old_text == "old text"
        assert amendment.new_text == "new text"
        assert amendment.change_type == ChangeType.MODIFY

    def test_strike_insert_with_title(self) -> None:
        """Test strike and insert with explicit title."""
        parser = AmendmentParser()
        text = 'Section 512 of title 17, United States Code, is amended by striking "120 days" and inserting "180 days".'

        amendments = parser.parse(text)
        strike_insert = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]
        assert len(strike_insert) >= 1

        amendment = strike_insert[0]
        assert amendment.old_text == "120 days"
        assert amendment.new_text == "180 days"

    def test_strike_insert_single_quotes(self) -> None:
        """Test strike and insert with single quotes."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is amended by striking 'old' and inserting 'new'."

        amendments = parser.parse(text)
        strike_insert = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]
        assert len(strike_insert) >= 1

    def test_strike_insert_backtick_quotes(self) -> None:
        """Test strike and insert with GovInfo backtick-style quotes (``text'').

        PL 113-22: The heading of subsection (c) of section 219 of the
        Internal Revenue Code of 1986 is amended by striking ``Special
        Rules for Certain Married Individuals'' and inserting ``Kay Bailey
        Hutchison Spousal IRA''.
        """
        parser = AmendmentParser(default_title=26)
        text = (
            "The heading of subsection (c) of section 219 of the Internal Revenue "
            "Code of 1986 is amended by striking ``Special Rules for Certain Married "
            "Individuals'' and inserting ``Kay Bailey Hutchison Spousal IRA''."
        )

        amendments = parser.parse(text)
        strike_insert = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]
        assert len(strike_insert) >= 1

        amendment = strike_insert[0]
        assert amendment.old_text == "Special Rules for Certain Married Individuals"
        assert amendment.new_text == "Kay Bailey Hutchison Spousal IRA"


class TestRepealPatterns:
    """Tests for repeal pattern matching."""

    def test_section_repealed(self) -> None:
        """Test simple section repeal."""
        parser = AmendmentParser(default_title=17)
        text = "Section 115 is hereby repealed."

        amendments = parser.parse(text)
        repeals = [a for a in amendments if a.pattern_type == PatternType.REPEAL]
        assert len(repeals) >= 1

        amendment = repeals[0]
        assert amendment.change_type == ChangeType.REPEAL
        assert amendment.section_ref is not None
        assert amendment.section_ref.section == "115"

    def test_section_repealed_without_hereby(self) -> None:
        """Test section repeal without 'hereby'."""
        parser = AmendmentParser(default_title=17)
        text = "Section 115 is repealed."

        amendments = parser.parse(text)
        repeals = [a for a in amendments if a.pattern_type == PatternType.REPEAL]
        assert len(repeals) >= 1

    def test_paragraph_repealed(self) -> None:
        """Test paragraph repeal."""
        parser = AmendmentParser(default_title=17)
        text = "paragraph (3) is hereby repealed"

        amendments = parser.parse(text)
        repeals = [a for a in amendments if a.pattern_type == PatternType.REPEAL]
        assert len(repeals) >= 1


class TestAddPatterns:
    """Tests for add/insert pattern matching."""

    def test_add_at_end(self) -> None:
        """Test add at end pattern."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is amended by adding at the end the following:"

        amendments = parser.parse(text)
        adds = [a for a in amendments if a.pattern_type == PatternType.ADD_AT_END]
        assert len(adds) >= 1

        amendment = adds[0]
        assert amendment.change_type == ChangeType.ADD
        assert amendment.needs_review  # Text extraction needs review

    def test_insert_after_paragraph(self) -> None:
        """Test insert after paragraph pattern."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is amended by inserting after paragraph (2) the following:"

        amendments = parser.parse(text)
        inserts = [a for a in amendments if a.pattern_type == PatternType.INSERT_AFTER]
        assert len(inserts) >= 1

    def test_insert_after_section(self) -> None:
        """Test insert after section pattern."""
        parser = AmendmentParser(default_title=17)
        text = "Title 17 is amended by inserting after section 106 the following new section:"

        amendments = parser.parse(text)
        inserts = [a for a in amendments if a.pattern_type == PatternType.INSERT_AFTER]
        assert len(inserts) >= 1


class TestRedesignatePatterns:
    """Tests for redesignate pattern matching."""

    def test_redesignate_section(self) -> None:
        """Test redesignate section pattern."""
        parser = AmendmentParser(default_title=17)
        text = "by redesignating section 107 as section 108"

        amendments = parser.parse(text)
        redesignates = [
            a for a in amendments if a.pattern_type == PatternType.REDESIGNATE
        ]
        assert len(redesignates) >= 1

        amendment = redesignates[0]
        assert amendment.change_type == ChangeType.REDESIGNATE

    def test_redesignate_paragraphs(self) -> None:
        """Test redesignate paragraphs pattern."""
        parser = AmendmentParser(default_title=17)
        text = "by redesignating paragraphs (3) and (4) as paragraphs (4) and (5)"

        amendments = parser.parse(text)
        redesignates = [
            a for a in amendments if a.pattern_type == PatternType.REDESIGNATE
        ]
        assert len(redesignates) >= 1


class TestSubstitutePatterns:
    """Tests for substitute pattern matching."""

    def test_section_to_read_as_follows(self) -> None:
        """Test section to read as follows pattern."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is amended to read as follows:"

        amendments = parser.parse(text)
        substitutes = [
            a for a in amendments if a.pattern_type == PatternType.SUBSTITUTE
        ]
        assert len(substitutes) >= 1

        amendment = substitutes[0]
        assert amendment.change_type == ChangeType.MODIFY
        assert amendment.needs_review  # Text extraction needs review

    def test_subsection_to_read_as_follows(self) -> None:
        """Test subsection to read as follows pattern."""
        parser = AmendmentParser(default_title=17)
        text = "subsection (a) is amended to read as follows:"

        amendments = parser.parse(text)
        substitutes = [
            a for a in amendments if a.pattern_type == PatternType.SUBSTITUTE
        ]
        assert len(substitutes) >= 1


class TestGeneralAmendmentPatterns:
    """Tests for general amendment pattern matching."""

    def test_section_amended_general(self) -> None:
        """Test general section amended pattern."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 of title 17, United States Code, is amended"

        amendments = parser.parse(text)
        assert len(amendments) >= 1

    def test_title_amended(self) -> None:
        """Test title amended pattern."""
        parser = AmendmentParser()
        text = "Title 17, United States Code, is amended by adding the following:"

        amendments = parser.parse(text)
        assert len(amendments) >= 1


class TestComplexScenarios:
    """Tests for complex amendment scenarios."""

    def test_multiple_amendments_in_text(self) -> None:
        """Test parsing text with multiple amendments."""
        parser = AmendmentParser(default_title=17)
        text = """
        Section 106 is amended by striking "old" and inserting "new".
        Section 107 is hereby repealed.
        Section 108 is amended to read as follows:
        """

        amendments = parser.parse(text)
        assert len(amendments) >= 3

        # Check we have different types
        types = {a.pattern_type for a in amendments}
        assert PatternType.STRIKE_INSERT in types or PatternType.AMEND_GENERAL in types
        assert PatternType.REPEAL in types

    def test_nested_amendments(self) -> None:
        """Test parsing nested amendment structure."""
        parser = AmendmentParser(default_title=17)
        text = """
        Section 106 is amended—
            (1) by striking "foo" and inserting "bar"; and
            (2) by adding at the end the following:
        """

        amendments = parser.parse(text)
        # Should find at least the strike/insert and add at end
        assert len(amendments) >= 2

    def test_amendment_with_full_context(self) -> None:
        """Test that context is captured."""
        parser = AmendmentParser(default_title=17)
        text = (
            "Some preamble text. Section 106 is hereby repealed. Some following text."
        )

        amendments = parser.parse(text, context_chars=50)
        assert len(amendments) >= 1

        amendment = amendments[0]
        assert len(amendment.context) > len(amendment.full_match)
        assert "preamble" in amendment.context or "following" in amendment.context


class TestConfidenceScoring:
    """Tests for confidence scoring."""

    def test_high_confidence_with_section(self) -> None:
        """Test high confidence when section is found."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is hereby repealed."

        amendments = parser.parse(text)
        assert len(amendments) >= 1

        amendment = [a for a in amendments if a.pattern_type == PatternType.REPEAL][0]
        assert amendment.confidence >= 0.90

    def test_reduced_confidence_without_title(self) -> None:
        """Test reduced confidence without explicit title."""
        parser = AmendmentParser()  # No default title
        text = "Section 106 is hereby repealed."

        amendments = parser.parse(text)
        assert len(amendments) >= 1

        amendment = [a for a in amendments if a.pattern_type == PatternType.REPEAL][0]
        # Section found but no title = slightly reduced confidence
        assert 0.80 <= amendment.confidence <= 0.95

    def test_needs_review_for_text_extraction(self) -> None:
        """Test that patterns needing text extraction are flagged for review."""
        parser = AmendmentParser(default_title=17)
        text = "Section 106 is amended by adding at the end the following:"

        amendments = parser.parse(text)
        adds = [a for a in amendments if a.pattern_type == PatternType.ADD_AT_END]
        assert len(adds) >= 1

        amendment = adds[0]
        assert amendment.needs_review is True


class TestStatistics:
    """Tests for statistics generation."""

    def test_get_statistics_empty(self) -> None:
        """Test statistics with empty list."""
        parser = AmendmentParser()
        stats = parser.get_statistics([])

        assert stats["total"] == 0
        assert stats["needs_review"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_get_statistics_with_amendments(self) -> None:
        """Test statistics with amendments."""
        parser = AmendmentParser(default_title=17)
        text = """
        Section 106 is amended by striking "old" and inserting "new".
        Section 107 is hereby repealed.
        """

        amendments = parser.parse(text)
        stats = parser.get_statistics(amendments)

        assert stats["total"] >= 2
        assert "avg_confidence" in stats
        assert "by_change_type" in stats


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text(self) -> None:
        """Test parsing empty text."""
        parser = AmendmentParser(default_title=17)
        amendments = parser.parse("")
        assert amendments == []

    def test_no_amendments(self) -> None:
        """Test parsing text with no amendments."""
        parser = AmendmentParser(default_title=17)
        text = "This is just regular text with no legal amendments."
        amendments = parser.parse(text)
        assert amendments == []

    def test_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        parser = AmendmentParser(default_title=17)

        # Lowercase
        text1 = "section 106 is hereby repealed."
        amendments1 = parser.parse(text1)

        # Uppercase
        text2 = "SECTION 106 IS HEREBY REPEALED."
        amendments2 = parser.parse(text2)

        assert len(amendments1) >= 1
        assert len(amendments2) >= 1

    def test_whitespace_variations(self) -> None:
        """Test handling of whitespace variations."""
        parser = AmendmentParser(default_title=17)
        text = "Section   106   is   hereby   repealed."

        amendments = parser.parse(text)
        repeals = [a for a in amendments if a.pattern_type == PatternType.REPEAL]
        assert len(repeals) >= 1

    def test_multiline_pattern(self) -> None:
        """Test pattern matching across lines."""
        parser = AmendmentParser(default_title=17)
        text = """Section 106 is amended
        by striking "old"
        and inserting "new"."""

        amendments = parser.parse(text)
        # Should still find the amendment
        assert len(amendments) >= 1


class TestRealWorldExamples:
    """Tests using real amendment language from actual Public Laws.

    These examples are drawn from different Congressional eras and titles
    to ensure the parser handles stylistic variations over time.

    Sources:
    - 104th Congress (1995-1996): Older "striking out" / "in lieu thereof" style
    - 105th Congress (1997-1998): Copyright amendments
    - 110th Congress (2007-2008): FDA Amendments Act
    - 115th-118th Congress (2017-2024): Modern drafting style
    """

    def test_1996_striking_out_in_lieu_thereof(self) -> None:
        """Test older 'striking out' and 'in lieu thereof' phrasing.

        Source: S. Rept. 104-272 (Electronic FOIA Improvement Act of 1996)
        """
        parser = AmendmentParser(default_title=5)
        text = (
            'Section 552(a)(6)(A)(i) is amended by striking out "ten days" '
            'and inserting in lieu thereof "twenty days".'
        )

        amendments = parser.parse(text)
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]

        assert len(strike_inserts) >= 1
        amendment = strike_inserts[0]
        assert amendment.old_text == "ten days"
        assert amendment.new_text == "twenty days"

    def test_1995_strike_and_all_that_follows(self) -> None:
        """Test 'and all that follows through the period' pattern.

        Source: H.R.692 - 104th Congress (Rural Community Wastewater)
        """
        parser = AmendmentParser(default_title=33)
        text = (
            'Section 603(d)(7) is amended by striking "except that" '
            "and all that follows through the period."
        )

        amendments = parser.parse(text)
        strikes = [a for a in amendments if a.pattern_type == PatternType.STRIKE]

        assert len(strikes) >= 1
        amendment = strikes[0]
        assert amendment.old_text == "except that"
        assert amendment.change_type == ChangeType.DELETE

    def test_1995_copyright_title_17(self) -> None:
        """Test copyright law amendment with full title reference.

        Source: H.R.2441 - 104th Congress (NII Copyright Protection Act)
        """
        parser = AmendmentParser()
        text = (
            "Section 106(3) of title 17, United States Code, is amended by "
            'striking "or by rental, lease, or lending" and inserting '
            '"by rental, lease, or lending, or by transmission".'
        )

        amendments = parser.parse(text)
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]

        assert len(strike_inserts) >= 1
        amendment = strike_inserts[0]
        assert amendment.old_text == "or by rental, lease, or lending"
        assert amendment.new_text == "by rental, lease, or lending, or by transmission"

    def test_2007_each_place_appears(self) -> None:
        """Test 'each place such term appears' multi-location pattern.

        Source: FDAAA 2007 (Food and Drug Administration Amendments Act)
        """
        parser = AmendmentParser(default_title=21)
        text = (
            'Section 736(a) is amended by striking "(c)(4)" each place '
            'such term appears and inserting "(c)(5)".'
        )

        amendments = parser.parse(text)
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]

        assert len(strike_inserts) >= 1
        amendment = strike_inserts[0]
        assert amendment.old_text == "(c)(4)"
        assert amendment.new_text == "(c)(5)"

    def test_2007_redesignation_with_addition(self) -> None:
        """Test redesignation pattern from 2007 law.

        Source: FDAAA 2007
        """
        parser = AmendmentParser(default_title=21)
        text = "by redesignating subparagraph (C) as subparagraph (B)"

        amendments = parser.parse(text)
        redesignates = [
            a for a in amendments if a.pattern_type == PatternType.REDESIGNATE
        ]

        assert len(redesignates) >= 1
        assert redesignates[0].change_type == ChangeType.REDESIGNATE

    def test_multiple_titles_in_one_law(self) -> None:
        """Test parsing amendments affecting multiple USC titles.

        Modern laws often amend multiple titles in one section.
        """
        parser = AmendmentParser()
        text = """
        (a) Section 1007(b) of title 17, United States Code, is amended
            by striking "Within 30 days after" and inserting "After".
        (b) Section 7825 of title 26, United States Code, is amended
            by striking "Civil Service Commission" and inserting
            "Merit Systems Protection Board".
        """

        amendments = parser.parse(text)

        # Should find amendments in both titles
        assert len(amendments) >= 2

        # Check we detected amendments with different implied titles
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]
        assert len(strike_inserts) >= 2

    def test_subsection_with_complex_path(self) -> None:
        """Test subsection reference with deep nesting.

        Example from 1996 H.R.4095 (National Information Infrastructure Protection)
        """
        parser = AmendmentParser(default_title=18)
        text = (
            "Section 1030(a)(1) of title 18, United States Code, is amended "
            'by striking "knowingly accesses" and inserting '
            '"having knowingly accessed".'
        )

        amendments = parser.parse(text)
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]

        assert len(strike_inserts) >= 1
        amendment = strike_inserts[0]
        assert amendment.old_text == "knowingly accesses"
        assert amendment.new_text == "having knowingly accessed"

    def test_defense_authorization_style(self) -> None:
        """Test National Defense Authorization Act amendment style.

        Defense bills have distinctive amendment patterns.
        """
        parser = AmendmentParser(default_title=10)
        text = (
            "Section 2302(5) of title 10, United States Code, is amended "
            "to read as follows:"
        )

        amendments = parser.parse(text)
        substitutes = [
            a for a in amendments if a.pattern_type == PatternType.SUBSTITUTE
        ]

        assert len(substitutes) >= 1
        assert substitutes[0].needs_review  # Needs text extraction

    def test_tax_code_amendment_title_26(self) -> None:
        """Test Internal Revenue Code (Title 26) amendment.

        Tax amendments often use precise numerical substitutions.
        """
        parser = AmendmentParser(default_title=26)
        text = (
            'Section 401(a)(9)(C)(ii)(I) is amended by striking "$160,000" '
            'and inserting "$170,000".'
        )

        amendments = parser.parse(text)
        strike_inserts = [
            a for a in amendments if a.pattern_type == PatternType.STRIKE_INSERT
        ]

        assert len(strike_inserts) >= 1
        amendment = strike_inserts[0]
        assert amendment.old_text == "$160,000"
        assert amendment.new_text == "$170,000"
