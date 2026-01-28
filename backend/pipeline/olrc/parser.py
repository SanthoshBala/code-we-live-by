"""Parse USLM (United States Legislative Markup) XML files."""

import contextlib
import hashlib
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

# USLM XML namespaces
NAMESPACES = {
    "uslm": "http://xml.house.gov/schemas/uslm/1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


@dataclass
class ParsedTitle:
    """Parsed US Code Title data."""

    title_number: int
    title_name: str
    is_positive_law: bool = False
    positive_law_date: str | None = None
    positive_law_citation: str | None = None


@dataclass
class ParsedChapter:
    """Parsed US Code Chapter data."""

    chapter_number: str
    chapter_name: str
    sort_order: int = 0


@dataclass
class ParsedSubchapter:
    """Parsed US Code Subchapter data."""

    subchapter_number: str
    subchapter_name: str
    chapter_number: str  # Parent chapter
    sort_order: int = 0


@dataclass
class ParsedSection:
    """Parsed US Code Section data."""

    section_number: str
    heading: str
    full_citation: str
    text_content: str
    chapter_number: str | None = None
    subchapter_number: str | None = None
    notes: str | None = None
    sort_order: int = 0


@dataclass
class USLMParseResult:
    """Result of parsing a USLM XML file."""

    title: ParsedTitle
    chapters: list[ParsedChapter] = field(default_factory=list)
    subchapters: list[ParsedSubchapter] = field(default_factory=list)
    sections: list[ParsedSection] = field(default_factory=list)


class USLMParser:
    """Parser for USLM (United States Legislative Markup) XML files."""

    # Positive law titles (enacted into positive law)
    POSITIVE_LAW_TITLES = {
        1,
        3,
        4,
        5,
        9,
        10,
        11,
        13,
        14,
        17,
        18,
        23,
        28,
        31,
        32,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        44,
        46,
        49,
        51,
        54,
    }

    def __init__(self):
        """Initialize the parser."""
        self._current_chapter: str | None = None
        self._current_subchapter: str | None = None
        self._chapter_order = 0
        self._subchapter_order = 0
        self._section_order = 0

    def parse_file(self, xml_path: Path | str) -> USLMParseResult:
        """Parse a USLM XML file.

        Args:
            xml_path: Path to the XML file.

        Returns:
            Parsed result containing title, chapters, subchapters, and sections.
        """
        xml_path = Path(xml_path)
        logger.info(f"Parsing USLM XML file: {xml_path}")

        # Reset state
        self._current_chapter = None
        self._current_subchapter = None
        self._chapter_order = 0
        self._subchapter_order = 0
        self._section_order = 0

        # Parse XML
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Extract title information
        title = self._parse_title(root)

        # Parse hierarchical structure
        chapters: list[ParsedChapter] = []
        subchapters: list[ParsedSubchapter] = []
        sections: list[ParsedSection] = []

        # Find main content - try different possible root structures
        main = self._find_main_content(root)
        if main is None:
            logger.warning("Could not find main content element")
            return USLMParseResult(title=title)

        # Parse all levels
        for chapter, subchs, sects in self._parse_levels(main, title.title_number):
            if chapter:
                chapters.append(chapter)
            subchapters.extend(subchs)
            sections.extend(sects)

        logger.info(
            f"Parsed Title {title.title_number}: "
            f"{len(chapters)} chapters, {len(subchapters)} subchapters, "
            f"{len(sections)} sections"
        )

        return USLMParseResult(
            title=title,
            chapters=chapters,
            subchapters=subchapters,
            sections=sections,
        )

    def _find_main_content(self, root: etree._Element) -> etree._Element | None:
        """Find the main content element in various USLM formats."""
        # Try namespaced elements first
        for ns_prefix in ["uslm:", ""]:
            for tag in ["main", "title", "body"]:
                elem = root.find(f".//{ns_prefix}{tag}", NAMESPACES)
                if elem is not None:
                    return elem

        # Try without namespace
        main = root.find(".//main")
        if main is not None:
            return main

        # Fall back to root if it contains levels directly
        if root.find(".//level") is not None or root.find(".//chapter") is not None:
            return root

        return root

    def _parse_title(self, root: etree._Element) -> ParsedTitle:
        """Extract title information from the root element."""
        # Try to find title number and name from various locations
        title_number = 0
        title_name = ""
        is_positive_law = False

        # Check for docNumber in meta (OLRC format)
        doc_number = root.find(".//{*}docNumber")
        if doc_number is not None and doc_number.text:
            with contextlib.suppress(ValueError):
                title_number = int(doc_number.text.strip())

        # Check root attributes
        if not title_number and "number" in root.attrib:
            with contextlib.suppress(ValueError):
                title_number = int(root.attrib["number"])

        # Check for title element with num child that has value attribute
        title_elem = root.find(".//{*}title")
        if title_elem is not None:
            num_elem = title_elem.find("{*}num") or title_elem.find("num")
            if num_elem is not None and "value" in num_elem.attrib:
                with contextlib.suppress(ValueError):
                    title_number = int(num_elem.attrib["value"])

        # Try to extract from identifier attribute on root or title
        if not title_number:
            identifier = root.get("identifier", "")
            if not identifier and title_elem is not None:
                identifier = title_elem.get("identifier", "")
            if identifier:
                # Parse "/us/usc/t17" pattern
                match = re.search(r"/t(\d+)", identifier)
                if match:
                    title_number = int(match.group(1))

        # Extract title name from heading
        heading = None
        if title_elem is not None:
            heading = title_elem.find("{*}heading") or title_elem.find("heading")
        if heading is None:
            heading = root.find(".//{*}heading")
        if heading is None:
            heading = root.find(".//heading")
        if heading is not None:
            title_name = self._get_text_content(heading)

        # Clean up title name
        title_name = title_name.strip()
        if not title_name:
            title_name = f"Title {title_number}"

        # Check for positive law property in meta (OLRC format)
        for prop in root.findall(".//{*}property"):
            if prop.get("role") == "is-positive-law":
                is_positive_law = prop.text and prop.text.strip().lower() == "yes"
                break

        # Fall back to hardcoded list if not found in XML
        if not is_positive_law:
            is_positive_law = title_number in self.POSITIVE_LAW_TITLES

        return ParsedTitle(
            title_number=title_number,
            title_name=title_name,
            is_positive_law=is_positive_law,
        )

    def _parse_levels(
        self, parent: etree._Element, title_number: int
    ) -> Iterator[
        tuple[ParsedChapter | None, list[ParsedSubchapter], list[ParsedSection]]
    ]:
        """Recursively parse hierarchical levels.

        Yields:
            Tuple of (chapter, subchapters, sections) for each top-level structure.
        """
        # Look for chapter elements
        chapters = parent.findall(".//chapter") + parent.findall(".//{*}chapter")
        if not chapters:
            # Try level elements with chapter identifier
            chapters = [
                lvl
                for lvl in parent.findall(".//level") + parent.findall(".//{*}level")
                if self._get_level_type(lvl) == "chapter"
            ]

        if chapters:
            for chapter_elem in chapters:
                yield self._parse_chapter(chapter_elem, title_number)
        else:
            # No chapters - parse sections directly
            sections = self._parse_sections_in_element(parent, title_number)
            yield (None, [], sections)

    def _parse_chapter(
        self, chapter_elem: etree._Element, title_number: int
    ) -> tuple[ParsedChapter, list[ParsedSubchapter], list[ParsedSection]]:
        """Parse a chapter element and its contents."""
        self._chapter_order += 1
        self._subchapter_order = 0
        self._section_order = 0

        # Extract chapter number and name
        chapter_number = self._get_number(chapter_elem)
        chapter_name = self._get_heading(chapter_elem)

        if not chapter_number:
            chapter_number = str(self._chapter_order)

        self._current_chapter = chapter_number
        self._current_subchapter = None

        chapter = ParsedChapter(
            chapter_number=chapter_number,
            chapter_name=chapter_name,
            sort_order=self._chapter_order,
        )

        # Parse subchapters and sections within chapter
        subchapters: list[ParsedSubchapter] = []
        sections: list[ParsedSection] = []

        # Look for subchapters
        subchapter_elems = chapter_elem.findall(".//subchapter") + chapter_elem.findall(
            ".//{*}subchapter"
        )
        if not subchapter_elems:
            subchapter_elems = [
                lvl
                for lvl in chapter_elem.findall(".//level")
                + chapter_elem.findall(".//{*}level")
                if self._get_level_type(lvl) == "subchapter"
            ]

        if subchapter_elems:
            for subch_elem in subchapter_elems:
                subch, subch_sections = self._parse_subchapter(
                    subch_elem, title_number, chapter_number
                )
                subchapters.append(subch)
                sections.extend(subch_sections)
        else:
            # No subchapters - parse sections directly in chapter
            sections = self._parse_sections_in_element(chapter_elem, title_number)

        return chapter, subchapters, sections

    def _parse_subchapter(
        self, subch_elem: etree._Element, title_number: int, chapter_number: str
    ) -> tuple[ParsedSubchapter, list[ParsedSection]]:
        """Parse a subchapter element and its sections."""
        self._subchapter_order += 1
        self._section_order = 0

        subch_number = self._get_number(subch_elem)
        subch_name = self._get_heading(subch_elem)

        if not subch_number:
            subch_number = str(self._subchapter_order)

        self._current_subchapter = subch_number

        subchapter = ParsedSubchapter(
            subchapter_number=subch_number,
            subchapter_name=subch_name,
            chapter_number=chapter_number,
            sort_order=self._subchapter_order,
        )

        sections = self._parse_sections_in_element(subch_elem, title_number)

        return subchapter, sections

    def _parse_sections_in_element(
        self, parent: etree._Element, title_number: int
    ) -> list[ParsedSection]:
        """Parse all section elements within a parent element."""
        sections: list[ParsedSection] = []

        # Find section elements
        section_elems = parent.findall(".//section") + parent.findall(".//{*}section")
        if not section_elems:
            section_elems = [
                lvl
                for lvl in parent.findall(".//level") + parent.findall(".//{*}level")
                if self._get_level_type(lvl) == "section"
            ]

        for section_elem in section_elems:
            section = self._parse_section(section_elem, title_number)
            if section:
                sections.append(section)

        return sections

    def _parse_section(
        self, section_elem: etree._Element, title_number: int
    ) -> ParsedSection | None:
        """Parse a single section element."""
        self._section_order += 1

        section_number = self._get_number(section_elem)
        heading = self._get_heading(section_elem)

        if not section_number:
            # Try to extract from identifier attribute
            identifier = section_elem.get("identifier", "")
            match = re.search(r"/s(\d+[a-zA-Z]*)$", identifier)
            section_number = match.group(1) if match else str(self._section_order)

        # Build full citation
        full_citation = f"{title_number} U.S.C. § {section_number}"

        # Extract text content
        text_content = self._extract_section_text(section_elem)

        # Extract notes if present
        notes = self._extract_notes(section_elem)

        return ParsedSection(
            section_number=section_number,
            heading=heading,
            full_citation=full_citation,
            text_content=text_content,
            chapter_number=self._current_chapter,
            subchapter_number=self._current_subchapter,
            notes=notes,
            sort_order=self._section_order,
        )

    def _get_level_type(self, elem: etree._Element) -> str | None:
        """Determine the type of a level element."""
        # Check identifier attribute
        identifier = elem.get("identifier", "")
        if "/ch" in identifier:
            return "chapter"
        elif "/sch" in identifier:
            return "subchapter"
        elif "/s" in identifier:
            return "section"

        # Check role attribute
        role = elem.get("role", "").lower()
        if role in ("chapter", "subchapter", "section"):
            return role

        return None

    def _get_number(self, elem: etree._Element) -> str:
        """Extract the number/identifier from an element."""
        # Check number attribute on element
        if "number" in elem.attrib:
            return elem.attrib["number"]

        # Look for <num> child element with value attribute (OLRC format)
        num_elem = elem.find("{*}num")
        if num_elem is None:
            num_elem = elem.find("num")
        if num_elem is not None:
            # Prefer value attribute (contains clean number)
            if "value" in num_elem.attrib:
                return num_elem.attrib["value"]
            # Fall back to text content
            if num_elem.text:
                # Clean up the number (remove "§", "Chapter", etc.)
                num_text = num_elem.text.strip()
                num_text = re.sub(r"^(§|Section|Chapter|Subchapter)\s*", "", num_text)
                # Remove trailing punctuation
                num_text = num_text.rstrip("—.-:")
                return num_text.strip()

        # Try identifier attribute
        identifier = elem.get("identifier", "")
        if identifier:
            # Extract last component
            parts = identifier.split("/")
            if parts:
                last = parts[-1]
                # Remove prefix (ch, sch, s)
                match = re.match(r"^(ch|sch|s)(\d+[a-zA-Z]*)$", last)
                if match:
                    return match.group(2)

        return ""

    def _get_heading(self, elem: etree._Element) -> str:
        """Extract the heading text from an element."""
        heading_elem = elem.find("heading") or elem.find("{*}heading")
        if heading_elem is not None:
            return self._get_text_content(heading_elem)

        # Fall back to title element
        title_elem = elem.find("title") or elem.find("{*}title")
        if title_elem is not None:
            return self._get_text_content(title_elem)

        return ""

    def _get_text_content(self, elem: etree._Element) -> str:
        """Get all text content from an element, including nested elements."""
        if elem is None:
            return ""

        # Use itertext to get all text including from child elements
        return " ".join(elem.itertext()).strip()

    def _extract_section_text(self, section_elem: etree._Element) -> str:
        """Extract the full text content of a section."""
        # Find content element
        content = section_elem.find("content") or section_elem.find("{*}content")
        if content is not None:
            return self._get_text_content(content)

        # Fall back to getting all text except heading
        parts = []
        for child in section_elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag not in ("heading", "num", "title"):
                parts.append(self._get_text_content(child))

        return " ".join(parts).strip()

    def _extract_notes(self, section_elem: etree._Element) -> str | None:
        """Extract notes/annotations from a section."""
        # Try various paths for notes elements
        notes_elem = section_elem.find(".//{*}notes")
        if notes_elem is None:
            notes_elem = section_elem.find(".//notes")
        if notes_elem is None:
            notes_elem = section_elem.find(".//{*}sourceCredit")
        if notes_elem is None:
            notes_elem = section_elem.find(".//sourceCredit")
        if notes_elem is not None:
            return self._get_text_content(notes_elem)
        return None


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of text content.

    Args:
        text: Text to hash.

    Returns:
        Hexadecimal hash string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
