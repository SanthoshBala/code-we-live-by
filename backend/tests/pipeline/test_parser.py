"""Tests for USLM XML parser."""

from pathlib import Path

import pytest
from lxml import etree

from pipeline.olrc.parser import (
    USLMParser,
    _clean_bracket_heading,
    compute_text_hash,
    title_case_heading,
    to_title_case,
)


class TestUSLMParser:
    """Tests for USLMParser class."""

    @pytest.fixture
    def parser(self) -> USLMParser:
        """Create a parser instance."""
        return USLMParser()

    @pytest.fixture
    def sample_xml(self, tmp_path: Path) -> Path:
        """Create a sample USLM XML file for testing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta>
    <identifier>usc/17</identifier>
  </meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>SUBJECT MATTER AND SCOPE OF COPYRIGHT</heading>
        <section identifier="/us/usc/t17/s101" number="101">
          <heading>Definitions</heading>
          <content>
            <p>As used in this title, the following terms have the following meanings:</p>
            <p>An "architectural work" is the design of a building.</p>
          </content>
        </section>
        <section identifier="/us/usc/t17/s102" number="102">
          <heading>Subject matter of copyright</heading>
          <content>
            <p>Copyright protection subsists in original works of authorship.</p>
          </content>
        </section>
      </chapter>
      <chapter identifier="/us/usc/t17/ch2" number="2">
        <heading>COPYRIGHT OWNERSHIP AND TRANSFER</heading>
        <subchapter identifier="/us/usc/t17/ch2/schI" number="I">
          <heading>Ownership</heading>
          <section identifier="/us/usc/t17/s201" number="201">
            <heading>Ownership of copyright</heading>
            <content>
              <p>Copyright in a work protected under this title vests initially in the author.</p>
            </content>
          </section>
        </subchapter>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_title.xml"
        xml_path.write_text(xml_content)
        return xml_path

    def test_parse_file_basic(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test basic parsing of a USLM XML file."""
        result = parser.parse_file(sample_xml)

        assert result.title.title_number == 17
        assert result.title.title_name == "Copyrights"
        assert result.title.is_positive_law is True  # Title 17 is positive law

    def test_parse_chapters(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test parsing of chapters."""
        result = parser.parse_file(sample_xml)

        assert len(result.chapters) == 2
        assert result.chapters[0].chapter_number == "1"
        assert (
            result.chapters[0].chapter_name == "Subject Matter and Scope of Copyright"
        )
        assert result.chapters[1].chapter_number == "2"

    def test_parse_subchapters(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test parsing of subchapters."""
        result = parser.parse_file(sample_xml)

        assert len(result.subchapters) == 1
        assert result.subchapters[0].subchapter_number == "I"
        assert result.subchapters[0].subchapter_name == "Ownership"
        assert result.subchapters[0].chapter_number == "2"

    def test_parse_sections(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test parsing of sections."""
        result = parser.parse_file(sample_xml)

        assert len(result.sections) == 3

        # Check first section
        sec101 = result.sections[0]
        assert sec101.section_number == "101"
        assert sec101.heading == "Definitions"
        assert sec101.full_citation == "17 U.S.C. § 101"
        assert "architectural work" in sec101.text_content

    def test_section_chapter_association(
        self, parser: USLMParser, sample_xml: Path
    ) -> None:
        """Test that sections are properly associated with chapters."""
        result = parser.parse_file(sample_xml)

        # Sections 101, 102 should be in chapter 1
        sec101 = next(s for s in result.sections if s.section_number == "101")
        sec102 = next(s for s in result.sections if s.section_number == "102")
        assert sec101.chapter_number == "1"
        assert sec102.chapter_number == "1"

        # Section 201 should be in chapter 2
        sec201 = next(s for s in result.sections if s.section_number == "201")
        assert sec201.chapter_number == "2"

    def test_section_subchapter_association(
        self, parser: USLMParser, sample_xml: Path
    ) -> None:
        """Test that sections are properly associated with subchapters."""
        result = parser.parse_file(sample_xml)

        sec201 = next(s for s in result.sections if s.section_number == "201")
        assert sec201.subchapter_number == "I"

    def test_sort_order(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test that sort orders are assigned correctly."""
        result = parser.parse_file(sample_xml)

        # Chapters should have sequential sort orders
        assert result.chapters[0].sort_order == 1
        assert result.chapters[1].sort_order == 2

    def test_positive_law_detection(self, parser: USLMParser) -> None:
        """Test positive law title detection."""
        assert 17 in parser.POSITIVE_LAW_TITLES  # Copyrights
        assert 18 in parser.POSITIVE_LAW_TITLES  # Crimes
        assert 20 not in parser.POSITIVE_LAW_TITLES  # Education (not positive law)

    def test_get_text_content_no_extra_spaces_around_inline_elements(
        self, parser: USLMParser
    ) -> None:
        """Inline elements like <date> and <ref> should not introduce extra spaces.

        Regression test for 20 U.S.C. § 5204 where _get_text_content produced
        'beginning on  October 24, 1990 .' with double spaces.
        """
        xml = """<content xmlns="http://xml.house.gov/schemas/uslm/1.0">
          an amount during the 4-year period beginning on
          <date date="1990-10-24">October 24, 1990</date>.
        </content>"""
        elem = etree.fromstring(xml)
        text = parser._get_text_content(elem)
        assert "on October 24, 1990." in text
        assert "  " not in text  # No double spaces anywhere

    def test_extract_section_text_excludes_source_credit(
        self, parser: USLMParser
    ) -> None:
        """Source credit text should not appear in extracted section text.

        Regression test for 20 U.S.C. § 5204 where the source credit
        '(Pub. L. 101-454, § 5 ...)' was being included in text_content.
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t20/s5204">
          <num value="5204">§ 5204.</num>
          <heading>Authorization of appropriations</heading>
          <chapeau>To provide a permanent endowment—</chapeau>
          <paragraph identifier="/us/usc/t20/s5204/1">
            <num value="1">(1)</num>
            <content>$5,000,000; and</content>
          </paragraph>
          <sourceCredit>(Pub. L. 101–454, § 5, Oct. 24, 1990, 104 Stat. 1064.)</sourceCredit>
        </section>"""
        elem = etree.fromstring(xml)
        text = parser._extract_section_text(elem)
        assert "Pub. L." not in text
        assert "endowment" in text

    def test_extract_subsections_with_direct_paragraphs(
        self, parser: USLMParser
    ) -> None:
        """Sections with paragraphs directly under section (no subsection wrapper)
        should still produce structured subsections.

        Regression test for 20 U.S.C. § 5204 which has <paragraph> elements
        as direct children of <section> instead of nested inside <subsection>.
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t20/s5204">
          <num value="5204">§ 5204.</num>
          <heading>Authorization of appropriations</heading>
          <chapeau>To provide a permanent endowment—</chapeau>
          <paragraph identifier="/us/usc/t20/s5204/1">
            <num value="1">(1)</num>
            <content>$5,000,000; and</content>
          </paragraph>
          <paragraph identifier="/us/usc/t20/s5204/2">
            <num value="2">(2)</num>
            <chapeau>the lesser of—</chapeau>
            <subparagraph identifier="/us/usc/t20/s5204/2/A">
              <num value="A">(A)</num>
              <content>$2,500,000, or</content>
            </subparagraph>
            <subparagraph identifier="/us/usc/t20/s5204/2/B">
              <num value="B">(B)</num>
              <content>an amount equal to contributions.</content>
            </subparagraph>
          </paragraph>
          <sourceCredit>(Pub. L. 101–454, § 5, Oct. 24, 1990, 104 Stat. 1064.)</sourceCredit>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        # Should produce a synthetic subsection wrapping the chapeau + paragraphs
        assert len(subsections) == 1
        wrapper = subsections[0]
        assert "endowment" in wrapper.content
        assert len(wrapper.children) == 2

        # First paragraph: (1) $5,000,000; and
        para1 = wrapper.children[0]
        assert para1.marker == "(1)"
        assert "$5,000,000" in para1.content

        # Second paragraph: (2) the lesser of—, with 2 subparagraphs
        para2 = wrapper.children[1]
        assert para2.marker == "(2)"
        assert "lesser of" in para2.content
        assert len(para2.children) == 2
        assert para2.children[0].marker == "(A)"
        assert para2.children[1].marker == "(B)"


class TestToTitleCase:
    """Tests for to_title_case function."""

    def test_single_word(self) -> None:
        assert to_title_case("COPYRIGHTS") == "Copyrights"

    def test_two_words(self) -> None:
        assert to_title_case("ARMED FORCES") == "Armed Forces"

    def test_minor_word_lowercased(self) -> None:
        assert (
            to_title_case("CRIMES AND CRIMINAL PROCEDURE")
            == "Crimes and Criminal Procedure"
        )

    def test_first_word_always_capitalized(self) -> None:
        assert (
            to_title_case("THE PUBLIC HEALTH AND WELFARE")
            == "The Public Health and Welfare"
        )

    def test_last_word_always_capitalized(self) -> None:
        """Last word is capitalized even if it's a minor word."""
        assert to_title_case("SOMETHING TO") == "Something To"

    def test_multiple_minor_words(self) -> None:
        assert to_title_case("WAR AND NATIONAL DEFENSE") == "War and National Defense"

    def test_already_title_case(self) -> None:
        assert to_title_case("Armed Forces") == "Armed Forces"

    def test_empty_string(self) -> None:
        assert to_title_case("") == ""

    def test_internal_revenue_code(self) -> None:
        assert to_title_case("INTERNAL REVENUE CODE") == "Internal Revenue Code"

    def test_foreign_relations_and_intercourse(self) -> None:
        assert (
            to_title_case("FOREIGN RELATIONS AND INTERCOURSE")
            == "Foreign Relations and Intercourse"
        )


class TestComputeTextHash:
    """Tests for compute_text_hash function."""

    def test_compute_hash(self) -> None:
        """Test hash computation."""
        text = "Test content"
        hash_value = compute_text_hash(text)

        assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
        assert hash_value.isalnum()

    def test_hash_deterministic(self) -> None:
        """Test that hash is deterministic."""
        text = "Same content"
        hash1 = compute_text_hash(text)
        hash2 = compute_text_hash(text)

        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        hash1 = compute_text_hash("Content A")
        hash2 = compute_text_hash("Content B")

        assert hash1 != hash2


class TestTitleCaseHeading:
    """Tests for title_case_heading function."""

    def test_all_caps_basic(self) -> None:
        """Test basic ALL-CAPS to Title Case conversion."""
        assert title_case_heading("DEPARTMENT OF DEFENSE") == "Department of Defense"

    def test_all_caps_with_articles(self) -> None:
        """Test that articles and prepositions stay lowercase."""
        assert (
            title_case_heading("SUBJECT MATTER AND SCOPE OF COPYRIGHT")
            == "Subject Matter and Scope of Copyright"
        )

    def test_first_word_always_capitalized(self) -> None:
        """Test that the first word is always capitalized even if it's a small word."""
        assert (
            title_case_heading("THE JUDICIARY AND JUDICIAL PROCEDURE")
            == "The Judiciary and Judicial Procedure"
        )

    def test_single_word(self) -> None:
        """Test single-word ALL-CAPS heading."""
        assert title_case_heading("COPYRIGHTS") == "Copyrights"

    def test_mixed_case_unchanged(self) -> None:
        """Test that mixed-case headings are returned unchanged."""
        assert title_case_heading("General Provisions") == "General Provisions"

    def test_already_title_case(self) -> None:
        """Test that already Title Case text is returned unchanged."""
        assert (
            title_case_heading("Subject Matter and Scope of Copyright")
            == "Subject Matter and Scope of Copyright"
        )

    def test_empty_string(self) -> None:
        """Test empty string returns empty string."""
        assert title_case_heading("") == ""

    def test_hyphenated_words(self) -> None:
        """Test hyphenated compound words are capitalized on each part."""
        assert (
            title_case_heading("ANTI-TERRORISM AND DEATH PENALTY")
            == "Anti-Terrorism and Death Penalty"
        )

    def test_no_alpha_characters(self) -> None:
        """Test string with no alphabetic characters returns unchanged."""
        assert title_case_heading("123 - 456") == "123 - 456"

    def test_multiple_prepositions(self) -> None:
        """Test heading with multiple small words."""
        assert (
            title_case_heading("CRIMES AND CRIMINAL PROCEDURE")
            == "Crimes and Criminal Procedure"
        )

    def test_of_in_middle(self) -> None:
        """Test 'of' stays lowercase in the middle of a heading."""
        assert (
            title_case_heading("PROTECTION OF TRADING WITH ENEMIES")
            == "Protection of Trading with Enemies"
        )


class TestCleanBracketHeading:
    """Tests for _clean_bracket_heading()."""

    def test_trailing_bracket_allcaps(self) -> None:
        """Test trailing bracket from split-bracket REPEALED status."""
        assert _clean_bracket_heading("REPEALED]") == "REPEALED"

    def test_trailing_bracket_mixed_case(self) -> None:
        """Test trailing bracket from split-bracket Repealed status."""
        assert _clean_bracket_heading("Repealed]") == "Repealed"

    def test_trailing_bracket_transferred(self) -> None:
        """Test trailing bracket from split-bracket TRANSFERRED status."""
        assert _clean_bracket_heading("TRANSFERRED]") == "TRANSFERRED"

    def test_fully_bracketed_reserved(self) -> None:
        """Test fully bracketed [Reserved] heading."""
        assert _clean_bracket_heading("[Reserved]") == "Reserved"

    def test_fully_bracketed_allcaps_reserved(self) -> None:
        """Test fully bracketed [RESERVED] heading."""
        assert _clean_bracket_heading("[RESERVED]") == "RESERVED"

    def test_normal_heading_unchanged(self) -> None:
        """Test normal heading without brackets is unchanged."""
        assert _clean_bracket_heading("GENERAL PROVISIONS") == "GENERAL PROVISIONS"

    def test_empty_string(self) -> None:
        """Test empty string returns empty string."""
        assert _clean_bracket_heading("") == ""
