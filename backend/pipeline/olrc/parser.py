"""Parse USLM (United States Legislative Markup) XML files."""

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from pipeline.olrc.normalized_section import ParsedLine, SectionNotes

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
class ParsedSubsection:
    """A subsection, paragraph, or other subdivision within a section.

    Subsections can be nested (paragraphs within subsections, etc.).
    """

    marker: str  # e.g., "(a)", "(1)", "(A)"
    heading: str | None  # e.g., "Registration requirements"
    content: str  # The text content (may include chapeau for list intros)
    children: list[ParsedSubsection] = field(default_factory=list)
    level: str = "subsection"  # subsection, paragraph, subparagraph, clause, subclause


@dataclass
class SourceCreditRef:
    """A structured reference from the sourceCredit element.

    Extracted from <ref href="/us/pl/116/136/..."> elements in USLM XML.
    This provides reliable citation data without regex parsing.
    """

    congress: int  # e.g., 116
    law_number: int  # e.g., 136
    section: str | None = None  # e.g., "5001(a)"
    division: str | None = None  # e.g., "A"
    title: str | None = None  # e.g., "V"
    date: str | None = None  # e.g., "Mar. 27, 2020"
    stat_volume: int | None = None  # e.g., 134
    stat_page: int | None = None  # e.g., 501
    raw_text: str = ""  # The display text from the ref element
    is_framework: bool = False  # True if this is the "as added" parent reference


@dataclass
class ActRef:
    """A pre-1957 Act reference from the sourceCredit element.

    Extracted from <ref href="/us/act/1935-08-14/ch531/..."> elements in USLM XML.
    Before 1957, laws were cited by date + chapter number.
    """

    date: str  # e.g., "1935-08-14" or "Aug. 14, 1935"
    chapter: int  # e.g., 531
    section: str | None = None  # e.g., "601"
    title: str | None = None  # e.g., "VI"
    stat_volume: int | None = None
    stat_page: int | None = None
    raw_text: str = ""  # The display text from the ref element
    short_title: str | None = None  # e.g., "Social Security Act"


@dataclass
class ParsedSection:
    """Parsed US Code Section data.

    This class represents a section of the US Code, containing both the
    raw parsed data from XML and the normalized provisions for display.

    The provisions, normalized_text, and section_notes fields are populated
    by calling normalize() after parsing.
    """

    section_number: str
    heading: str
    full_citation: str
    text_content: str  # Flattened text (for backwards compatibility)
    chapter_number: str | None = None
    subchapter_number: str | None = None
    notes: str | None = None  # Raw notes from XML
    sort_order: int = 0
    subsections: list[ParsedSubsection] = field(
        default_factory=list
    )  # Structured content
    source_credit_refs: list[SourceCreditRef] = field(
        default_factory=list
    )  # Structured PL citations (post-1957)
    act_refs: list[ActRef] = field(
        default_factory=list
    )  # Structured Act citations (pre-1957)

    # ParsedLine fields (populated after normalization)
    provisions: list[ParsedLine] = field(default_factory=list)
    normalized_text: str = ""  # Display-ready text with indentation
    section_notes: SectionNotes | None = (
        None  # Parsed notes with citations, amendments, etc.
    )

    @property
    def provision_count(self) -> int:
        """Return the total number of provisions."""
        return len(self.provisions)

    @property
    def is_normalized(self) -> bool:
        """Return True if this section has been normalized."""
        return len(self.provisions) > 0

    def get_provision(self, line_number: int) -> ParsedLine | None:
        """Get a provision by its 1-indexed line number."""
        if 1 <= line_number <= len(self.provisions):
            return self.provisions[line_number - 1]
        return None

    def get_provisions(self, start: int, end: int) -> list[ParsedLine]:
        """Get provisions in a range (1-indexed, inclusive)."""
        return self.provisions[max(0, start - 1) : end]

    def char_to_line(self, char_pos: int) -> int | None:
        """Convert a character position to a line number."""
        for provision in self.provisions:
            if provision.start_char <= char_pos < provision.end_char:
                return provision.line_number
        return None


@dataclass
class USLMParseResult:
    """Result of parsing a USLM XML file."""

    title: ParsedTitle
    chapters: list[ParsedChapter] = field(default_factory=list)
    subchapters: list[ParsedSubchapter] = field(default_factory=list)
    sections: list[ParsedSection] = field(default_factory=list)


class USLMParser:
    """Parser for USLM (United States Legislative Markup) XML files."""

    # =========================================================================
    # HARDCODED ASSUMPTION: Positive law titles (fallback only)
    # Source: https://uscode.house.gov/codification/legislation.shtml
    # See also: Titles marked with asterisk at https://uscode.house.gov/browse.xhtml
    # Last verified: January 2026
    # Update cadence: Rarely changes. New titles are enacted into positive law
    #   infrequently (typically 0-2 per Congress). Check the source URL when a
    #   new title is enacted.
    #
    # NOTE: The parser first checks the XML metadata for positive law status
    # via <property role="is-positive-law">yes/no</property>. This set is only
    # used as a fallback if the XML doesn't contain the metadata.
    #
    # Current positive law titles (27 total):
    #   1 (General Provisions), 3 (The President), 4 (Flag and Seal),
    #   5 (Govt Organization), 9 (Arbitration), 10 (Armed Forces),
    #   11 (Bankruptcy), 13 (Census), 14 (Coast Guard), 17 (Copyrights),
    #   18 (Crimes), 23 (Highways), 28 (Judiciary), 31 (Money and Finance),
    #   32 (National Guard), 35 (Patents), 36 (Patriotic Societies),
    #   37 (Pay and Allowances), 38 (Veterans' Benefits), 39 (Postal Service),
    #   40 (Public Buildings), 41 (Public Contracts), 44 (Public Printing),
    #   46 (Shipping), 49 (Transportation), 51 (Space Programs), 54 (NPS)
    # =========================================================================
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
            heading = title_elem.find("{*}heading")
            if heading is None:
                heading = title_elem.find("heading")
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

        # Extract text content (flattened for backwards compatibility)
        text_content = self._extract_section_text(section_elem)

        # Extract structured subsections from XML
        subsections = self._extract_subsections(section_elem)

        # Extract notes if present
        notes = self._extract_notes(section_elem)

        # Extract structured citation refs from sourceCredit
        source_credit_refs, act_refs = self._extract_source_credit_refs(section_elem)

        return ParsedSection(
            section_number=section_number,
            heading=heading,
            full_citation=full_citation,
            text_content=text_content,
            chapter_number=self._current_chapter,
            subchapter_number=self._current_subchapter,
            notes=notes,
            sort_order=self._section_order,
            subsections=subsections,
            source_credit_refs=source_credit_refs,
            act_refs=act_refs,
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

    def _parse_subsection(
        self, elem: etree._Element, level: str = "subsection"
    ) -> ParsedSubsection:
        """Parse a subsection/paragraph/etc. element into structured data."""
        # Get marker (num)
        num_elem = elem.find("{*}num")
        if num_elem is None:
            num_elem = elem.find("num")
        marker = self._get_text_content(num_elem) if num_elem is not None else ""

        # Get heading
        heading_elem = elem.find("{*}heading")
        if heading_elem is None:
            heading_elem = elem.find("heading")
        heading = (
            self._get_text_content(heading_elem) if heading_elem is not None else None
        )

        # Get content (may be in <content> or <chapeau> or directly in element)
        content_elem = elem.find("{*}content")
        if content_elem is None:
            content_elem = elem.find("content")
        chapeau_elem = elem.find("{*}chapeau")
        if chapeau_elem is None:
            chapeau_elem = elem.find("chapeau")

        content_parts = []
        if chapeau_elem is not None:
            content_parts.append(self._get_text_content(chapeau_elem))
        if content_elem is not None:
            content_parts.append(self._get_text_content(content_elem))

        content = " ".join(content_parts).strip()

        # Parse nested children
        children = []
        child_levels = {
            "subsection": ("paragraph", "paragraph"),
            "paragraph": ("subparagraph", "subparagraph"),
            "subparagraph": ("clause", "clause"),
            "clause": ("subclause", "subclause"),
            "subclause": ("item", "item"),
        }

        if level in child_levels:
            child_tag, child_level = child_levels[level]
            for child_elem in elem.findall(f"{{*}}{child_tag}") or elem.findall(
                child_tag
            ):
                children.append(self._parse_subsection(child_elem, child_level))

        return ParsedSubsection(
            marker=marker,
            heading=heading,
            content=content,
            children=children,
            level=level,
        )

    def _extract_subsections(
        self, section_elem: etree._Element
    ) -> list[ParsedSubsection]:
        """Extract structured subsections from a section element."""
        subsections = []

        # Try namespaced first, then non-namespaced
        subsec_elems = section_elem.findall("{*}subsection")
        if not subsec_elems:
            subsec_elems = section_elem.findall("subsection")

        for subsec_elem in subsec_elems:
            subsections.append(self._parse_subsection(subsec_elem, "subsection"))

        return subsections

    def _extract_notes(self, section_elem: etree._Element) -> str | None:
        """Extract notes/annotations from a section.

        USLM XML has two relevant elements:
        - <sourceCredit>: Contains the citation block (Pub. L. references)
        - <notes>: Contains Historical/Editorial/Statutory notes

        We extract both and combine them so citation parsing works correctly.
        """
        parts = []

        # Extract sourceCredit (citation block) first
        source_credit = section_elem.find(".//{*}sourceCredit")
        if source_credit is None:
            source_credit = section_elem.find(".//sourceCredit")
        if source_credit is not None:
            parts.append(self._get_text_content(source_credit))

        # Extract notes (Historical/Editorial/Statutory)
        notes_elem = section_elem.find(".//{*}notes")
        if notes_elem is None:
            notes_elem = section_elem.find(".//notes")
        if notes_elem is not None:
            parts.append(self._get_notes_text_content(notes_elem))

        if parts:
            return " ".join(parts)
        return None

    def _format_quoted_content(self, elem: etree._Element) -> str:
        """Format quotedContent element with proper structure markers.

        Parses the structured subsections, paragraphs, etc. within quoted content
        and formats them with markers that the normalizer can use to create
        properly indented lines.

        Markers: [QC:level:marker]content where level is indent depth (1-5).
        """
        parts = []

        def format_item(item_elem: etree._Element, level: int) -> None:
            """Format a subsection/paragraph/clause/etc. element."""
            # Get marker (num)
            num_elem = item_elem.find("{*}num")
            if num_elem is None:
                num_elem = item_elem.find("num")
            marker = self._get_text_content(num_elem) if num_elem is not None else ""

            # Get heading
            heading_elem = item_elem.find("{*}heading")
            if heading_elem is None:
                heading_elem = item_elem.find("heading")
            heading = ""
            if heading_elem is not None:
                heading = self._get_text_content(heading_elem).strip()

            # Get content
            content_elem = item_elem.find("{*}content")
            if content_elem is None:
                content_elem = item_elem.find("content")
            chapeau_elem = item_elem.find("{*}chapeau")
            if chapeau_elem is None:
                chapeau_elem = item_elem.find("chapeau")

            content = ""
            if chapeau_elem is not None:
                content = self._get_text_content(chapeau_elem).strip()
            elif content_elem is not None:
                content = self._get_text_content(content_elem).strip()

            # Build the formatted line
            line_parts = []
            if marker:
                line_parts.append(marker)
            if heading:
                line_parts.append(heading)
            if content:
                line_parts.append(content)

            if line_parts:
                text = " ".join(line_parts)
                parts.append(f"[QC:{level}]{text}[/QC]")

            # Process nested children
            child_tags = ["paragraph", "subparagraph", "clause", "subclause", "item"]
            for child_tag in child_tags:
                for child in item_elem.findall(f"{{*}}{child_tag}"):
                    format_item(child, level + 1)
                for child in item_elem.findall(child_tag):
                    format_item(child, level + 1)

        # Process top-level subsections in quoted content
        for subsection in elem.findall("{*}subsection"):
            format_item(subsection, 1)
        for subsection in elem.findall("subsection"):
            format_item(subsection, 1)

        # If no structured content, extract plain text (for inline quotedContent)
        if not parts:
            text = self._get_text_content(elem).strip()
            if text:
                # Inline quoted content at level 1
                parts.append(f"[QC:1]{text}[/QC]")

        return "\n".join(parts)

    def _get_notes_text_content(self, elem: etree._Element) -> str:
        """Get text content from notes, preserving header formatting.

        In USLM XML:
        - Headings with class="smallCaps" are section headers (stored lowercase)
        - <b> tags indicate inline headers (e.g., "General Scope of Copyright.")
        - <i> tags followed by ".—" indicate sub-headers (e.g., "Reproduction.—")
        - <quotedContent> contains structured law text with subsections

        We insert markers to preserve this structure:
        - [H1] prefix for bold headers
        - [H2] prefix for italic sub-headers
        - [QC:level]...[/QC] for quoted content items

        These markers are processed by normalize_note_content() to create
        properly indented ParsedLine structures.
        """
        parts = []

        def process_element(el, in_bold=False, in_italic=False):
            """Recursively process element and its children."""
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag

            # Handle quotedContent specially - parse its structure
            if tag == "quotedContent":
                quoted_text = self._format_quoted_content(el)
                if quoted_text:
                    parts.append("\n" + quoted_text)
                # Add tail text and return - don't process children normally
                if el.tail:
                    parts.append(el.tail)
                return

            # Preserve paragraph boundaries with a special marker
            # We use [PARA] marker instead of \n\n because tail text often contains \n
            if tag == "p" and parts:
                # Add paragraph break marker before this <p> element
                parts.append("[PARA]")

            # Check if this is a heading with smallCaps class
            if tag == "heading":
                css_class = el.get("class", "")
                if "smallCaps" in css_class:
                    # Apply title case to smallCaps headings
                    text = "".join(el.itertext()).strip()
                    if text:
                        parts.append(text.title())
                    return  # Don't process children

            # Track bold/italic state
            new_in_bold = in_bold or tag == "b"
            new_in_italic = in_italic or tag == "i"

            # Add text before children
            if el.text:
                text = el.text
                if tag == "b":
                    # Bold text is a header - strip trailing period
                    header_text = text.rstrip(".")
                    parts.append(f"[H1]{header_text}[/H1]")
                elif tag == "i":
                    # Italic text might be a sub-header if followed by ".—"
                    # But NOT if it's a case citation (contains " v. ")
                    # or other inline emphasis (Latin terms, etc.)
                    if " v. " in text:
                        # Case citation - keep as inline italic text
                        parts.append(text)
                    else:
                        # Mark as potential sub-header for normalizer
                        parts.append(f"[H2]{text}[/H2]")
                else:
                    parts.append(text)

            # Process children
            for child in el:
                process_element(child, new_in_bold, new_in_italic)

            # Add tail text (text after closing tag)
            if el.tail:
                parts.append(el.tail)

        process_element(elem)
        # Join parts, converting [PARA] markers to double newlines
        result = []
        for part in parts:
            if part == "[PARA]":
                # Convert to double newline for paragraph break
                result.append("\n\n")
            elif result and result[-1] != "\n\n":
                result.append(" " + part)
            else:
                result.append(part)
        return "".join(result).strip()

    def _extract_source_credit_refs(
        self, section_elem: etree._Element
    ) -> tuple[list[SourceCreditRef], list[ActRef]]:
        """Extract structured citation refs from sourceCredit element.

        Parses <ref href="/us/pl/116/136/..."> elements for Public Laws (post-1957)
        and <ref href="/us/act/1935-08-14/ch531/..."> elements for Acts (pre-1957).

        Returns:
            Tuple of (SourceCreditRef list, ActRef list) in document order.
        """
        pl_refs: list[SourceCreditRef] = []
        act_refs: list[ActRef] = []

        source_credit = section_elem.find(".//{*}sourceCredit")
        if source_credit is None:
            source_credit = section_elem.find(".//sourceCredit")
        if source_credit is None:
            return pl_refs, act_refs

        # Find all ref elements within sourceCredit
        ref_elems = source_credit.findall(".//{*}ref")
        if not ref_elems:
            ref_elems = source_credit.findall(".//ref")

        # Track current stat volume/page for associating with refs
        current_stat_volume: int | None = None
        current_stat_page: int | None = None
        # Track the most recent ref (either PL or Act) for stat association
        last_ref_type: str | None = None

        for ref_elem in ref_elems:
            href = ref_elem.get("href", "")
            text = "".join(ref_elem.itertext()).strip()

            # Parse /us/pl/CONGRESS/LAW/... hrefs (Public Laws, post-1957)
            if "/us/pl/" in href:
                match = re.match(
                    r"/us/pl/(\d+)/(\d+)"  # Congress and law number
                    r"(?:/d([A-Z]+))?"  # Optional division (can be multi-letter: LL, FF)
                    r"(?:/t([IVXLCDM]+))?"  # Optional title
                    r"(?:/s([\w()]+))?",  # Optional section
                    href,
                )
                if match:
                    ref = SourceCreditRef(
                        congress=int(match.group(1)),
                        law_number=int(match.group(2)),
                        division=match.group(3),
                        title=match.group(4),
                        section=match.group(5),
                        raw_text=text,
                    )
                    pl_refs.append(ref)
                    last_ref_type = "pl"

            # Parse /us/act/YYYY-MM-DD/chNNN/... hrefs (Acts, pre-1957)
            elif "/us/act/" in href:
                match = re.match(
                    r"/us/act/(\d{4}-\d{2}-\d{2})/ch(\d+)"  # Date and chapter
                    r"(?:/t([IVXLCDM]+))?"  # Optional title
                    r"(?:/s([\w()]+))?",  # Optional section
                    href,
                )
                if match:
                    ref = ActRef(
                        date=match.group(1),  # e.g., "1935-08-14"
                        chapter=int(match.group(2)),
                        title=match.group(3),
                        section=match.group(4),
                        raw_text=text,
                    )
                    act_refs.append(ref)
                    last_ref_type = "act"

            # Parse /us/stat/VOLUME/PAGE hrefs to capture Stat references
            elif "/us/stat/" in href:
                match = re.match(r"/us/stat/(\d+)/(\d+)", href)
                if match:
                    current_stat_volume = int(match.group(1))
                    current_stat_page = int(match.group(2))
                    # Apply to the most recent ref
                    if last_ref_type == "pl" and pl_refs:
                        pl_refs[-1].stat_volume = current_stat_volume
                        pl_refs[-1].stat_page = current_stat_page
                    elif last_ref_type == "act" and act_refs:
                        act_refs[-1].stat_volume = current_stat_volume
                        act_refs[-1].stat_page = current_stat_page

        # Extract dates from <date> elements and associate with PL refs
        # Act refs already have dates in the href, so all <date> elements belong to PL refs
        date_elems = source_credit.findall(".//{*}date")
        if not date_elems:
            date_elems = source_credit.findall(".//date")

        # Simple heuristic: dates appear after their associated PL ref, in order
        for i, date_elem in enumerate(date_elems):
            date_text = "".join(date_elem.itertext()).strip()
            if i < len(pl_refs):
                pl_refs[i].date = date_text

        return pl_refs, act_refs


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of text content.

    Args:
        text: Text to hash.

    Returns:
        Hexadecimal hash string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
