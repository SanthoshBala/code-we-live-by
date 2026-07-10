"""Tests for USLM XML parser."""

from pathlib import Path

import pytest
from lxml import etree

from pipeline.olrc.parser import (
    NoteRef,
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

    def test_parse_subsection_continuation_element(self, parser: USLMParser) -> None:
        """_parse_subsection collects <continuation> elements into the continuation field.

        Regression test for Issue #251: continuation text (e.g. penalty clauses
        closing a list of items) was silently dropped by the parser.
        """
        xml = """<subsection xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t18/s1001/a">
          <num value="a">(a)</num>
          <chapeau>Except as otherwise provided in this section, whoever, in any matter
          within the jurisdiction of the executive, legislative, or judicial branch of
          the Government of the United States, knowingly and willfully—</chapeau>
          <paragraph identifier="/us/usc/t18/s1001/a/1">
            <num value="1">(1)</num>
            <content>falsifies, conceals, or covers up by any trick, scheme, or device
            a material fact;</content>
          </paragraph>
          <paragraph identifier="/us/usc/t18/s1001/a/2">
            <num value="2">(2)</num>
            <content>makes any materially false, fictitious, or fraudulent statement
            or representation; or</content>
          </paragraph>
          <paragraph identifier="/us/usc/t18/s1001/a/3">
            <num value="3">(3)</num>
            <content>makes or uses any false writing or document knowing the same to
            contain any materially false, fictitious, or fraudulent statement or
            entry;</content>
          </paragraph>
          <continuation>shall be fined under this title, imprisoned not more than 5
          years or, if the offense involves international or domestic terrorism, not
          more than 8 years, or both.</continuation>
        </subsection>"""
        elem = etree.fromstring(xml)
        result = parser._parse_subsection(elem, "subsection")

        assert result.marker == "(a)"
        assert "knowingly and willfully" in result.content
        assert len(result.children) == 3
        assert len(result.continuation) == 1
        assert "shall be fined" in result.continuation[0]
        assert "imprisoned not more than 5" in result.continuation[0]

    def test_parse_subsection_no_continuation(self, parser: USLMParser) -> None:
        """_parse_subsection produces an empty continuation list when there is none."""
        xml = """<subsection xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t17/s101/a">
          <num value="a">(a)</num>
          <content>A work is created when fixed in a tangible medium.</content>
        </subsection>"""
        elem = etree.fromstring(xml)
        result = parser._parse_subsection(elem, "subsection")

        assert result.continuation == []

    def test_parse_subsection_clause_skipping_subparagraph_level(
        self, parser: USLMParser
    ) -> None:
        """_parse_subsection captures <clause> children nested directly in a
        <paragraph>, skipping the <subparagraph> level.

        Regression test for Issue #506: 38 U.S.C. § 3702(a)(1) encodes its
        paragraph as a <chapeau> followed directly by two <clause> elements
        (no intervening <subparagraph>). The parser previously only searched
        for the immediate-next level in the standard hierarchy
        (paragraph -> subparagraph), so it found nothing and silently dropped
        clauses (i) and (ii) along with their text.
        """
        xml = """<paragraph xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t38/s3702/a/1">
          <num value="1">(1)</num>
          <chapeau>The veterans described in paragraph (2) of this subsection are
          eligible for the housing loan benefits of this chapter. Entitlement
          derived from service during the most recent such period shall be
          reduced by the amount by which entitlement from service during any
          earlier such period has been used to obtain a direct, guaranteed, or
          insured housing loan&#8212;</chapeau>
          <clause identifier="/us/usc/t38/s3702/a/1/i">
            <num value="i">(i)</num>
            <content>on real property which the veteran owns at the time of
            application; or</content>
          </clause>
          <clause identifier="/us/usc/t38/s3702/a/1/ii">
            <num value="ii">(ii)</num>
            <content>as to which the Secretary has incurred actual liability or
            loss, unless in the event of loss or the incurrence and payment of
            such liability by the Secretary the resulting indebtedness of the
            veteran to the United States has been paid in full.</content>
          </clause>
        </paragraph>"""
        elem = etree.fromstring(xml)
        result = parser._parse_subsection(elem, "paragraph")

        assert result.marker == "(1)"
        assert "housing loan" in result.content

        assert len(result.children) == 2
        clause_i, clause_ii = result.children

        assert clause_i.marker == "(i)"
        assert clause_i.level == "clause"
        assert "on real property which the veteran owns" in clause_i.content

        assert clause_ii.marker == "(ii)"
        assert clause_ii.level == "clause"
        assert "incurred actual liability or loss" in clause_ii.content

    def test_extract_subsections_continuation_in_subsection(
        self, parser: USLMParser
    ) -> None:
        """Continuation text inside a <subsection> element is captured and accessible.

        Regression test for Issue #251: models 18 U.S.C. § 1001(a) where the
        penalty clause follows three numbered paragraphs inside subsection (a).
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t18/s1001">
          <num value="1001">§ 1001.</num>
          <heading>Statements or entries generally</heading>
          <subsection identifier="/us/usc/t18/s1001/a">
            <num value="a">(a)</num>
            <chapeau>Whoever knowingly and willfully—</chapeau>
            <paragraph identifier="/us/usc/t18/s1001/a/1">
              <num value="1">(1)</num>
              <content>falsifies a material fact;</content>
            </paragraph>
            <paragraph identifier="/us/usc/t18/s1001/a/2">
              <num value="2">(2)</num>
              <content>makes any false statement; or</content>
            </paragraph>
            <continuation>shall be fined under this title or imprisoned not more
            than 5 years, or both.</continuation>
          </subsection>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        assert len(subsections) == 1
        sub_a = subsections[0]
        assert sub_a.marker == "(a)"
        assert len(sub_a.children) == 2
        assert len(sub_a.continuation) == 1
        assert "shall be fined" in sub_a.continuation[0]

    def test_extract_subsections_continuation_inside_content_bubbled_to_section_level(
        self, parser: USLMParser
    ) -> None:
        """A <continuation> nested inside a paragraph's <content> is promoted to
        the section-level synthetic wrapper, not left on the paragraph.

        Regression test for Issue #447: 17 U.S.C. § 107 has a flush-left closing
        sentence ("The fact that a work is unpublished...") encoded as a
        <continuation> inside the <content> of the last <paragraph>.  OLRC
        semantics treat this as a section-level statement (indent_level=0), but
        the parser was previously including it as part of the paragraph's text,
        causing it to render at indent_level=2 instead of 0.
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t17/s107">
          <num value="107">§ 107.</num>
          <heading>Limitations on exclusive rights: Fair use</heading>
          <chapeau>Notwithstanding the provisions of sections 106 and 106A, the fair
          use of a copyrighted work, including such use by reproduction in copies or
          phonorecords or by any other means specified by that section, for purposes
          such as criticism, comment, news reporting, teaching (including multiple
          copies for classroom use), scholarship, or research, is not an infringement
          of copyright. In determining whether the use made of a work in any
          particular case is a fair use the factors to be considered shall include—
          </chapeau>
          <paragraph identifier="/us/usc/t17/s107/1">
            <num value="1">(1)</num>
            <content>the purpose and character of the use, including whether such
            use is of a commercial nature or is for nonprofit educational
            purposes;</content>
          </paragraph>
          <paragraph identifier="/us/usc/t17/s107/2">
            <num value="2">(2)</num>
            <content>the nature of the copyrighted work;</content>
          </paragraph>
          <paragraph identifier="/us/usc/t17/s107/3">
            <num value="3">(3)</num>
            <content>the amount and substantiality of the portion used in relation
            to the copyrighted work as a whole; and</content>
          </paragraph>
          <paragraph identifier="/us/usc/t17/s107/4">
            <num value="4">(4)</num>
            <content>the effect of the use upon the potential market for or value
            of the copyrighted work.
            <continuation>The fact that a work is unpublished shall not itself bar
            a finding of fair use if such finding is made upon consideration of all
            the above factors.</continuation>
            </content>
          </paragraph>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        # Should produce one synthetic wrapper subsection
        assert len(subsections) == 1
        wrapper = subsections[0]
        assert wrapper.marker == ""

        # The wrapper should have 4 paragraph children
        assert len(wrapper.children) == 4

        # Paragraph (4) should NOT include the continuation text in its content
        para4 = wrapper.children[3]
        assert para4.marker == "(4)"
        assert "effect of the use" in para4.content
        assert "unpublished" not in para4.content, (
            "Continuation text must not appear in paragraph (4) content"
        )
        # Paragraph (4) should have no continuation of its own
        assert para4.continuation == [], (
            "Continuation from <content> must be promoted to section level"
        )

        # The wrapper (section-level) should carry the continuation
        assert len(wrapper.continuation) == 1
        assert "unpublished" in wrapper.continuation[0], (
            "Continuation text must be promoted to the section-level wrapper"
        )

    def test_intro_p_sibling_captured_as_chapeau(self, parser: USLMParser) -> None:
        """A <p> element appearing before the first <paragraph> in a section is
        captured as introductory (chapeau) text rather than silently dropped.

        Regression test for Issue #478: 9 U.S.C. § 13 has an intro sentence
        ("The party moving for an order confirming...") encoded as a <p> sibling
        of the (a)/(b)/(c) <paragraph> elements.  The parser was previously
        looking only for <chapeau>, so the intro was absent from text_content
        and provisions.
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t9/s13">
          <num value="13">§ 13.</num>
          <heading>Application for order confirming, modifying, or correcting award</heading>
          <p>The party moving for an order confirming, modifying, or correcting an
          award shall, at the time such order is filed with the clerk for the entry of
          judgment thereon, also file the following papers with the clerk:</p>
          <paragraph identifier="/us/usc/t9/s13/a">
            <num value="a">(a)</num>
            <content>The agreement; the selection or appointment, if any, of an
            additional arbitrator or umpire.</content>
          </paragraph>
          <paragraph identifier="/us/usc/t9/s13/b">
            <num value="b">(b)</num>
            <content>The award.</content>
          </paragraph>
          <paragraph identifier="/us/usc/t9/s13/c">
            <num value="c">(c)</num>
            <content>Each notice, affidavit, or other paper used upon an application
            to confirm, modify, or correct the award.</content>
          </paragraph>
          <sourceCredit>(June 12, 1939, ch. 237.)</sourceCredit>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        assert len(subsections) == 1
        wrapper = subsections[0]

        # Intro sentence must appear as the wrapper's content (chapeau equivalent)
        assert "party moving" in wrapper.content, (
            "Introductory <p> before paragraphs must be captured as chapeau text"
        )
        assert len(wrapper.children) == 3
        assert wrapper.children[0].marker == "(a)"
        assert wrapper.children[1].marker == "(b)"
        assert wrapper.children[2].marker == "(c)"

    def test_trailing_p_sibling_captured_as_continuation(
        self, parser: USLMParser
    ) -> None:
        """A <p> element appearing after the last <paragraph> in a section is
        captured as a section-level continuation rather than silently dropped.

        Regression test for Issue #479: 9 U.S.C. § 13 has a trailing sentence
        ("The judgment shall be docketed...") encoded as a <p> sibling after the
        (a)/(b)/(c) <paragraph> elements.  This sentence was either dropped or
        merged into the (c) item — it must appear as a distinct provision.
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t9/s13">
          <num value="13">§ 13.</num>
          <heading>Application for order confirming, modifying, or correcting award</heading>
          <p>The party moving for an order confirming, modifying, or correcting an
          award shall, at the time such order is filed with the clerk for the entry of
          judgment thereon, also file the following papers with the clerk:</p>
          <paragraph identifier="/us/usc/t9/s13/a">
            <num value="a">(a)</num>
            <content>The agreement; the selection or appointment, if any, of an
            additional arbitrator or umpire.</content>
          </paragraph>
          <paragraph identifier="/us/usc/t9/s13/b">
            <num value="b">(b)</num>
            <content>The award.</content>
          </paragraph>
          <paragraph identifier="/us/usc/t9/s13/c">
            <num value="c">(c)</num>
            <content>Each notice, affidavit, or other paper used upon an application
            to confirm, modify, or correct the award.</content>
          </paragraph>
          <p>The judgment shall be docketed as if it was rendered in an action.</p>
          <sourceCredit>(June 12, 1939, ch. 237.)</sourceCredit>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        assert len(subsections) == 1
        wrapper = subsections[0]

        # Trailing <p> must appear as a section-level continuation
        assert len(wrapper.continuation) >= 1, (
            "Trailing <p> after paragraphs must be captured as section continuation"
        )
        assert any("docketed" in ct for ct in wrapper.continuation), (
            "Docketing sentence must appear in section-level continuation"
        )

        # (c) content must NOT include the docketing sentence
        para_c = wrapper.children[2]
        assert para_c.marker == "(c)"
        assert "docketed" not in para_c.content, (
            "Docketing sentence must not be merged into paragraph (c) content"
        )

    def test_p_inside_content_separated_as_continuation(
        self, parser: USLMParser
    ) -> None:
        """A <p> element inside a <content> element is excluded from the content
        text and emitted as a separate continuation entry.

        Regression test for Issue #479 (merged-paragraph variant): when OLRC XML
        encodes a trailing sentence as <p> inside <content> of the last paragraph,
        the itertext() merge caused the two sentences to concatenate without a
        space — e.g. '...application.The judgment shall be docketed...'
        """
        xml = """<section xmlns="http://xml.house.gov/schemas/uslm/1.0"
            identifier="/us/usc/t9/s13">
          <num value="13">§ 13.</num>
          <heading>Application for order confirming, modifying, or correcting award</heading>
          <p>The party moving for an order confirming, modifying, or correcting an
          award shall, at the time such order is filed with the clerk for the entry of
          judgment thereon, also file the following papers with the clerk:</p>
          <paragraph identifier="/us/usc/t9/s13/a">
            <num value="a">(a)</num>
            <content>The agreement.</content>
          </paragraph>
          <paragraph identifier="/us/usc/t9/s13/c">
            <num value="c">(c)</num>
            <content>Each notice, affidavit, or other paper used upon an application
            to confirm, modify, or correct the award.<p>The judgment shall be docketed
            as if it was rendered in an action.</p></content>
          </paragraph>
          <sourceCredit>(June 12, 1939, ch. 237.)</sourceCredit>
        </section>"""
        elem = etree.fromstring(xml)
        subsections = parser._extract_subsections(elem)

        assert len(subsections) == 1
        wrapper = subsections[0]
        para_c = wrapper.children[1]
        assert para_c.marker == "(c)"

        # The (c) content must NOT contain the docketing sentence
        assert "docketed" not in para_c.content, (
            "<p> inside <content> must not be merged into the list item text"
        )
        # The merged no-space artifact must not appear either
        assert "application.The" not in para_c.content, (
            "<p> inside <content> must not be concatenated without a space"
        )

        # The docketing sentence must appear separately at section level
        all_continuation = wrapper.continuation
        assert any("docketed" in ct for ct in all_continuation), (
            "<p> inside <content> must be promoted to section-level continuation"
        )


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


class TestExtractNotesRefs:
    """Tests for _extract_notes_refs method (Task 1.17b)."""

    @pytest.fixture
    def parser(self) -> USLMParser:
        """Create a parser instance."""
        return USLMParser()

    @pytest.fixture
    def xml_with_public_law_refs(self, tmp_path: Path) -> Path:
        """Create XML with Public Law references in notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>Test Chapter</heading>
        <section identifier="/us/usc/t17/s106" number="106">
          <heading>Exclusive rights</heading>
          <content><p>Test content.</p></content>
          <notes>
            <note>
              <heading>References in Text</heading>
              <p>The Music Modernization Act, referred to in subsec. (a),
              is <ref href="/us/pl/115/264">Pub. L. 115–264</ref>,
              Oct. 11, 2018, 132 Stat. 3676.</p>
              <p>See also <ref href="/us/pl/94/553">Pub. L. 94–553</ref>,
              the Copyright Act of 1976.</p>
            </note>
          </notes>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_pl_refs.xml"
        xml_path.write_text(xml_content)
        return xml_path

    @pytest.fixture
    def xml_with_usc_section_refs(self, tmp_path: Path) -> Path:
        """Create XML with US Code section references in notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>Test Chapter</heading>
        <section identifier="/us/usc/t17/s107" number="107">
          <heading>Limitations</heading>
          <content><p>Test content.</p></content>
          <notes>
            <note>
              <heading>References in Text</heading>
              <p>For the definition of "work made for hire",
              see <ref href="/us/usc/t17/s101">17 U.S.C. 101</ref>.</p>
              <p>The exclusive rights are defined in
              <ref href="/us/usc/t17/s106">section 106 of this title</ref>.</p>
            </note>
          </notes>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_usc_refs.xml"
        xml_path.write_text(xml_content)
        return xml_path

    @pytest.fixture
    def xml_with_statute_refs(self, tmp_path: Path) -> Path:
        """Create XML with Statutes at Large references in notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>Test Chapter</heading>
        <section identifier="/us/usc/t17/s108" number="108">
          <heading>Reproduction</heading>
          <content><p>Test content.</p></content>
          <notes>
            <note>
              <heading>Amendment History</heading>
              <p>For the original enactment, see
              <ref href="/us/stat/90/2546">90 Stat. 2546</ref>.</p>
            </note>
          </notes>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_stat_refs.xml"
        xml_path.write_text(xml_content)
        return xml_path

    @pytest.fixture
    def xml_with_act_refs(self, tmp_path: Path) -> Path:
        """Create XML with pre-1957 Act references in notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/42</identifier></meta>
  <main>
    <title identifier="/us/usc/t42" number="42">
      <heading>PUBLIC HEALTH</heading>
      <chapter identifier="/us/usc/t42/ch7" number="7">
        <heading>SOCIAL SECURITY</heading>
        <section identifier="/us/usc/t42/s401" number="401">
          <heading>Trust Funds</heading>
          <content><p>Test content.</p></content>
          <notes>
            <note>
              <heading>References in Text</heading>
              <p>The Social Security Act, referred to in text, is
              <ref href="/us/act/1935-08-14/ch531">act Aug. 14, 1935, ch. 531</ref>,
              49 Stat. 620.</p>
            </note>
          </notes>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_act_refs.xml"
        xml_path.write_text(xml_content)
        return xml_path

    @pytest.fixture
    def xml_with_mixed_refs(self, tmp_path: Path) -> Path:
        """Create XML with multiple types of references in notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>Test Chapter</heading>
        <section identifier="/us/usc/t17/s109" number="109">
          <heading>Distribution</heading>
          <content><p>Test content.</p></content>
          <notes>
            <note>
              <heading>References in Text</heading>
              <p>The Copyright Act, <ref href="/us/pl/94/553">Pub. L. 94–553</ref>,
              amended <ref href="/us/usc/t17/s106">section 106</ref>.
              See <ref href="/us/stat/90/2546">90 Stat. 2546</ref> for details.</p>
            </note>
          </notes>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_mixed_refs.xml"
        xml_path.write_text(xml_content)
        return xml_path

    def test_extract_public_law_refs(
        self, parser: USLMParser, xml_with_public_law_refs: Path
    ) -> None:
        """Test extraction of Public Law references from notes."""
        result = parser.parse_file(xml_with_public_law_refs)

        assert len(result.sections) == 1
        section = result.sections[0]

        # Should have extracted 2 Public Law refs
        assert len(section.notes_refs) == 2

        # Check first ref (Pub. L. 115-264)
        ref1 = section.notes_refs[0]
        assert ref1.ref_type == "public_law"
        assert ref1.congress == 115
        assert ref1.law_number == 264
        assert "Pub. L. 115–264" in ref1.display_text

        # Check second ref (Pub. L. 94-553)
        ref2 = section.notes_refs[1]
        assert ref2.ref_type == "public_law"
        assert ref2.congress == 94
        assert ref2.law_number == 553

    def test_extract_usc_section_refs(
        self, parser: USLMParser, xml_with_usc_section_refs: Path
    ) -> None:
        """Test extraction of US Code section references from notes."""
        result = parser.parse_file(xml_with_usc_section_refs)

        section = result.sections[0]
        assert len(section.notes_refs) == 2

        # Check first ref (17 U.S.C. 101)
        ref1 = section.notes_refs[0]
        assert ref1.ref_type == "usc_section"
        assert ref1.usc_title == 17
        assert ref1.usc_section == "101"

        # Check second ref (section 106)
        ref2 = section.notes_refs[1]
        assert ref2.ref_type == "usc_section"
        assert ref2.usc_title == 17
        assert ref2.usc_section == "106"

    def test_extract_statute_refs(
        self, parser: USLMParser, xml_with_statute_refs: Path
    ) -> None:
        """Test extraction of Statutes at Large references from notes."""
        result = parser.parse_file(xml_with_statute_refs)

        section = result.sections[0]
        assert len(section.notes_refs) == 1

        ref = section.notes_refs[0]
        assert ref.ref_type == "statute"
        assert ref.stat_volume == 90
        assert ref.stat_page == 2546

    def test_extract_act_refs(
        self, parser: USLMParser, xml_with_act_refs: Path
    ) -> None:
        """Test extraction of pre-1957 Act references from notes."""
        result = parser.parse_file(xml_with_act_refs)

        section = result.sections[0]
        assert len(section.notes_refs) == 1

        ref = section.notes_refs[0]
        assert ref.ref_type == "act"
        assert ref.act_date == "1935-08-14"
        assert ref.act_chapter == 531

    def test_extract_mixed_refs(
        self, parser: USLMParser, xml_with_mixed_refs: Path
    ) -> None:
        """Test extraction of multiple types of references from notes."""
        result = parser.parse_file(xml_with_mixed_refs)

        section = result.sections[0]
        assert len(section.notes_refs) == 3

        # Check types are correctly identified
        ref_types = [ref.ref_type for ref in section.notes_refs]
        assert "public_law" in ref_types
        assert "usc_section" in ref_types
        assert "statute" in ref_types

    def test_no_refs_when_no_notes(self, parser: USLMParser, tmp_path: Path) -> None:
        """Test that no refs are extracted when section has no notes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>Test</heading>
        <section identifier="/us/usc/t17/s101" number="101">
          <heading>Test</heading>
          <content><p>No notes here.</p></content>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_no_notes.xml"
        xml_path.write_text(xml_content)

        result = parser.parse_file(xml_path)
        section = result.sections[0]
        assert len(section.notes_refs) == 0


class TestNoteRefDataclass:
    """Tests for NoteRef dataclass."""

    def test_public_law_ref(self) -> None:
        """Test creating a Public Law reference."""
        ref = NoteRef(
            ref_type="public_law",
            href="/us/pl/115/264",
            display_text="Pub. L. 115–264",
            congress=115,
            law_number=264,
        )
        assert ref.ref_type == "public_law"
        assert ref.congress == 115
        assert ref.law_number == 264
        assert ref.usc_title is None

    def test_usc_section_ref(self) -> None:
        """Test creating a US Code section reference."""
        ref = NoteRef(
            ref_type="usc_section",
            href="/us/usc/t17/s106",
            display_text="section 106",
            usc_title=17,
            usc_section="106",
        )
        assert ref.ref_type == "usc_section"
        assert ref.usc_title == 17
        assert ref.usc_section == "106"
        assert ref.congress is None

    def test_statute_ref(self) -> None:
        """Test creating a Statutes at Large reference."""
        ref = NoteRef(
            ref_type="statute",
            href="/us/stat/90/2546",
            display_text="90 Stat. 2546",
            stat_volume=90,
            stat_page=2546,
        )
        assert ref.ref_type == "statute"
        assert ref.stat_volume == 90
        assert ref.stat_page == 2546

    def test_act_ref(self) -> None:
        """Test creating a pre-1957 Act reference."""
        ref = NoteRef(
            ref_type="act",
            href="/us/act/1935-08-14/ch531",
            display_text="act Aug. 14, 1935, ch. 531",
            act_date="1935-08-14",
            act_chapter=531,
        )
        assert ref.ref_type == "act"
        assert ref.act_date == "1935-08-14"
        assert ref.act_chapter == 531


class TestExtractSourceCreditRefs:
    """Tests for _extract_source_credit_refs — specifically the as-added date bug (Issue #480)."""

    @pytest.fixture
    def parser(self) -> USLMParser:
        """Create a parser instance."""
        return USLMParser()

    def test_as_added_date_attributed_to_adding_law_not_framework(
        self, parser: USLMParser, tmp_path: Path
    ) -> None:
        """Date after an 'as added' clause must go to the adding law, not the framework law.

        Regression test for Issue #480:
            (Pub. L. 87–195, pt. III, § 620G, as added Pub. L. 104–132,
             title III, § 325, Apr. 24, 1996, 110 Stat. 1256.)

        PL 87-195 has no date in this credit; the date belongs to PL 104-132.
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/22</identifier></meta>
  <main>
    <title identifier="/us/usc/t22" number="22">
      <heading>FOREIGN RELATIONS AND INTERCOURSE</heading>
      <chapter identifier="/us/usc/t22/ch32" number="32">
        <heading>FOREIGN ASSISTANCE</heading>
        <section identifier="/us/usc/t22/s2377" number="2377">
          <heading>Prohibition on assistance to countries that aid terrorist states</heading>
          <content><p>Test content.</p></content>
          <sourceCredit>(<ref href="/us/pl/87/195/tIII/s620G">Pub. L. 87–195</ref>, pt. III, § 620G, as added <ref href="/us/pl/104/132/tIII/s325">Pub. L. 104–132</ref>, title III, § 325, <date>Apr. 24, 1996</date>, <ref href="/us/stat/110/1256">110 Stat. 1256</ref>.)</sourceCredit>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_as_added.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        assert len(result.sections) == 1
        section = result.sections[0]

        pl_refs = section.source_credit_refs
        assert len(pl_refs) == 2, f"Expected 2 PL refs, got {len(pl_refs)}"

        # PL 87-195 is the framework law — no date should be attributed to it
        framework = pl_refs[0]
        assert framework.congress == 87
        assert framework.law_number == 195
        assert framework.date is None, (
            f"Framework law PL 87-195 should have date=None, got {framework.date!r}"
        )

        # PL 104-132 is the adding law — it gets the date "Apr. 24, 1996"
        adding = pl_refs[1]
        assert adding.congress == 104
        assert adding.law_number == 132
        assert adding.date == "Apr. 24, 1996", (
            f"Adding law PL 104-132 should have date='Apr. 24, 1996', got {adding.date!r}"
        )
        assert adding.stat_volume == 110
        assert adding.stat_page == 1256

    def test_simple_single_law_date_attributed_correctly(
        self, parser: USLMParser, tmp_path: Path
    ) -> None:
        """A single PL ref should still get its date when there is no 'as added' clause."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<usc xmlns="http://xml.house.gov/schemas/uslm/1.0">
  <meta><identifier>usc/17</identifier></meta>
  <main>
    <title identifier="/us/usc/t17" number="17">
      <heading>COPYRIGHTS</heading>
      <chapter identifier="/us/usc/t17/ch1" number="1">
        <heading>SUBJECT MATTER</heading>
        <section identifier="/us/usc/t17/s101" number="101">
          <heading>Definitions</heading>
          <content><p>Test content.</p></content>
          <sourceCredit>(<ref href="/us/pl/94/553">Pub. L. 94–553</ref>, <date>Oct. 19, 1976</date>, <ref href="/us/stat/90/2541">90 Stat. 2541</ref>.)</sourceCredit>
        </section>
      </chapter>
    </title>
  </main>
</usc>
"""
        xml_path = tmp_path / "test_simple_credit.xml"
        xml_path.write_text(xml_content)
        result = parser.parse_file(xml_path)

        assert len(result.sections) == 1
        section = result.sections[0]

        pl_refs = section.source_credit_refs
        assert len(pl_refs) == 1

        ref = pl_refs[0]
        assert ref.congress == 94
        assert ref.law_number == 553
        assert ref.date == "Oct. 19, 1976"
        assert ref.stat_volume == 90
        assert ref.stat_page == 2541
