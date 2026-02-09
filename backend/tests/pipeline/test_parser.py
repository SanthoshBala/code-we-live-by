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
        assert result.title.name == "Copyrights"
        assert result.title.is_positive_law is True  # Title 17 is positive law

    def test_parse_groups_chapters(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test parsing of chapters as groups."""
        result = parser.parse_file(sample_xml)

        # Find chapter groups (not the title group itself)
        chapters = [g for g in result.groups if g.group_type == "chapter"]
        assert len(chapters) == 2
        assert chapters[0].number == "1"
        assert chapters[0].name == "Subject Matter and Scope of Copyright"
        assert chapters[1].number == "2"

    def test_parse_groups_subchapters(
        self, parser: USLMParser, sample_xml: Path
    ) -> None:
        """Test parsing of subchapters as groups."""
        result = parser.parse_file(sample_xml)

        subchapters = [g for g in result.groups if g.group_type == "subchapter"]
        assert len(subchapters) == 1
        assert subchapters[0].number == "I"
        assert subchapters[0].name == "Ownership"
        # Parent should be chapter 2
        assert "chapter:2" in subchapters[0].parent_key

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

    def test_section_parent_group_association(
        self, parser: USLMParser, sample_xml: Path
    ) -> None:
        """Test that sections are properly associated with parent groups."""
        result = parser.parse_file(sample_xml)

        # Sections 101, 102 should have chapter 1 as parent
        sec101 = next(s for s in result.sections if s.section_number == "101")
        sec102 = next(s for s in result.sections if s.section_number == "102")
        assert sec101.parent_group_key is not None
        assert "chapter:1" in sec101.parent_group_key
        assert sec102.parent_group_key is not None
        assert "chapter:1" in sec102.parent_group_key

        # Section 201 should have subchapter I as parent
        sec201 = next(s for s in result.sections if s.section_number == "201")
        assert sec201.parent_group_key is not None
        assert "subchapter:I" in sec201.parent_group_key

    def test_sort_order(self, parser: USLMParser, sample_xml: Path) -> None:
        """Test that sort orders are assigned correctly."""
        result = parser.parse_file(sample_xml)

        # Chapters should have sequential sort orders
        chapters = [g for g in result.groups if g.group_type == "chapter"]
        assert chapters[0].sort_order == 1
        assert chapters[1].sort_order == 2

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


class TestChapterGroups:
    """Tests for chapter group (subtitle, part, division) parsing."""

    @pytest.fixture
    def parser(self) -> USLMParser:
        """Create a parser instance."""
        return USLMParser()

    def test_subtitle_groups_t26_pattern(
        self, parser: USLMParser, tmp_path: Path
    ) -> None:
        """Title 26 pattern: subtitle → chapter (no intermediate part)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <main>
    <title identifier="/us/usc/t26" number="26">
      <heading>INTERNAL REVENUE CODE</heading>
      <subtitle identifier="/us/usc/t26/stA" number="A">
        <heading>INCOME TAXES</heading>
        <chapter identifier="/us/usc/t26/stA/ch1" number="1">
          <heading>NORMAL TAXES AND SURTAXES</heading>
          <section identifier="/us/usc/t26/s1" number="1">
            <heading>Tax imposed</heading>
            <content><p>There is imposed a tax.</p></content>
          </section>
        </chapter>
      </subtitle>
      <subtitle identifier="/us/usc/t26/stB" number="B">
        <heading>ESTATE AND GIFT TAXES</heading>
        <chapter identifier="/us/usc/t26/stB/ch11" number="11">
          <heading>ESTATE TAX</heading>
          <section identifier="/us/usc/t26/s2001" number="2001">
            <heading>Imposition and rate of tax</heading>
            <content><p>A tax is imposed.</p></content>
          </section>
        </chapter>
      </subtitle>
    </title>
  </main>
</usc>"""
        xml_path = tmp_path / "t26.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        # Non-title groups: 2 subtitles + 2 chapters = 4, plus the title = 5 total
        non_title_groups = [g for g in result.groups if g.group_type != "title"]
        subtitles = [g for g in non_title_groups if g.group_type == "subtitle"]
        chapters = [g for g in non_title_groups if g.group_type == "chapter"]

        assert len(subtitles) == 2
        assert subtitles[0].number == "A"
        assert subtitles[0].name == "Income Taxes"
        assert subtitles[0].parent_key is not None
        assert "title:26" in subtitles[0].parent_key
        assert subtitles[1].number == "B"

        assert len(chapters) == 2
        # Chapters should have subtitle as parent
        assert "subtitle:A" in chapters[0].parent_key
        assert "subtitle:B" in chapters[1].parent_key

        # Sections should still be parsed
        assert len(result.sections) == 2

    def test_nested_groups_t10_pattern(
        self, parser: USLMParser, tmp_path: Path
    ) -> None:
        """Title 10 pattern: subtitle → part → chapter."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <main>
    <title identifier="/us/usc/t10" number="10">
      <heading>ARMED FORCES</heading>
      <subtitle identifier="/us/usc/t10/stA" number="A">
        <heading>GENERAL MILITARY LAW</heading>
        <part identifier="/us/usc/t10/stA/ptI" number="I">
          <heading>ORGANIZATION AND GENERAL MILITARY POWERS</heading>
          <chapter identifier="/us/usc/t10/stA/ptI/ch1" number="1">
            <heading>DEFINITIONS</heading>
            <section identifier="/us/usc/t10/s101" number="101">
              <heading>Definitions</heading>
              <content><p>In this title.</p></content>
            </section>
          </chapter>
        </part>
        <part identifier="/us/usc/t10/stA/ptII" number="II">
          <heading>PERSONNEL</heading>
          <chapter identifier="/us/usc/t10/stA/ptII/ch31" number="31">
            <heading>ENLISTMENTS</heading>
            <section identifier="/us/usc/t10/s501" number="501">
              <heading>Enlistment oath</heading>
              <content><p>Each person enlisted.</p></content>
            </section>
          </chapter>
        </part>
      </subtitle>
    </title>
  </main>
</usc>"""
        xml_path = tmp_path / "t10.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        non_title_groups = [g for g in result.groups if g.group_type != "title"]
        subtitles = [g for g in non_title_groups if g.group_type == "subtitle"]
        parts = [g for g in non_title_groups if g.group_type == "part"]
        chapters = [g for g in non_title_groups if g.group_type == "chapter"]

        # 1 subtitle + 2 parts + 2 chapters = 5 non-title groups
        assert len(subtitles) == 1
        assert subtitles[0].number == "A"

        assert len(parts) == 2
        assert parts[0].number == "I"
        assert "subtitle:A" in parts[0].parent_key
        assert parts[1].number == "II"
        assert "subtitle:A" in parts[1].parent_key

        assert len(chapters) == 2
        assert "part:I" in chapters[0].parent_key
        assert "part:II" in chapters[1].parent_key

    def test_part_only_t18_pattern(self, parser: USLMParser, tmp_path: Path) -> None:
        """Title 18 pattern: part → chapter (no subtitle)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <main>
    <title identifier="/us/usc/t18" number="18">
      <heading>CRIMES AND CRIMINAL PROCEDURE</heading>
      <part identifier="/us/usc/t18/ptI" number="I">
        <heading>CRIMES</heading>
        <chapter identifier="/us/usc/t18/ptI/ch1" number="1">
          <heading>GENERAL PROVISIONS</heading>
          <section identifier="/us/usc/t18/s1" number="1">
            <heading>Applicability</heading>
            <content><p>This title applies.</p></content>
          </section>
        </chapter>
      </part>
    </title>
  </main>
</usc>"""
        xml_path = tmp_path / "t18.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        non_title_groups = [g for g in result.groups if g.group_type != "title"]
        parts = [g for g in non_title_groups if g.group_type == "part"]
        chapters = [g for g in non_title_groups if g.group_type == "chapter"]

        assert len(parts) == 1
        assert parts[0].number == "I"
        assert "title:18" in parts[0].parent_key

        assert len(chapters) == 1
        assert "part:I" in chapters[0].parent_key

    def test_no_groups_t17_pattern(self, parser: USLMParser, tmp_path: Path) -> None:
        """Title 17 pattern: chapters directly under title (no groups)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>SUBJECT MATTER</heading>
        <section identifier="/us/usc/t17/s101" number="101">
          <heading>Definitions</heading>
          <content><p>As used in this title.</p></content>
        </section>
      </chapter>
    </title>
  </main>
</usc>"""
        xml_path = tmp_path / "t17.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        non_title_groups = [g for g in result.groups if g.group_type != "title"]
        # Only 1 chapter, no subtitles/parts
        assert len(non_title_groups) == 1
        assert non_title_groups[0].group_type == "chapter"
        # Chapter's parent should be the title
        assert "title:17" in non_title_groups[0].parent_key
