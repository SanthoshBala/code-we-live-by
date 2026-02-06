"""Tests for USLM XML parser."""

from pathlib import Path

import pytest

from pipeline.olrc.parser import (
    USLMParser,
    compute_text_hash,
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
            result.chapters[0].chapter_name == "SUBJECT MATTER AND SCOPE OF COPYRIGHT"
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
