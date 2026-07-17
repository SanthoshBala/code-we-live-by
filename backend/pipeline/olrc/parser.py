"""Parse USLM (United States Legislative Markup) XML files."""

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from pipeline.olrc.normalized_section import ParsedLine, SectionNotes

logger = logging.getLogger(__name__)

# Minor words that should not be capitalized in title case (unless first/last).
# Covers articles, coordinating conjunctions, and short prepositions.
_TITLE_CASE_MINOR_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "if",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "so",
        "the",
        "to",
        "up",
        "with",
        "yet",
    }
)


def _capitalize_word(word: str) -> str:
    """Capitalize a single word, handling hyphenated compounds."""
    if "-" in word:
        return "-".join(part.capitalize() for part in word.split("-"))
    return word.capitalize()


def title_case_heading(text: str) -> str:
    """Convert an ALL-CAPS heading to Title Case.

    US Code XML source data uses ALL-CAPS for title, chapter, and subchapter
    headings (e.g. "DEPARTMENT OF DEFENSE"). This converts them to readable
    Title Case (e.g. "Department of Defense").

    Only applies conversion when the text is predominantly uppercase (>=80%
    uppercase letters). Mixed-case headings are returned unchanged.

    Follows standard English title-case rules:
    - First and last words are always capitalized.
    - Minor words (articles, conjunctions, short prepositions) are lowercase.
    - Hyphenated compounds are capitalized on each part.
    """
    if not text:
        return text

    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return text

    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    if upper_ratio < 0.8:
        return text

    words = text.split()
    last_idx = len(words) - 1
    result: list[str] = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i == 0 or i == last_idx or lower not in _TITLE_CASE_MINOR_WORDS:
            result.append(_capitalize_word(word))
        else:
            result.append(lower)

    return " ".join(result)


def _clean_bracket_heading(text: str) -> str:
    """Strip orphaned brackets from heading text.

    OLRC XML splits bracket-enclosed status markers across <num> and <heading>
    elements, e.g. ``<num>[CHAPTER 5—</num><heading>REPEALED]</heading>``.
    This produces headings like ``REPEALED]`` (trailing bracket, missing opening
    bracket) or ``[Reserved]`` (fully bracketed). Strip leading ``[`` and
    trailing ``]`` so downstream title-casing works on clean text.
    """
    text = text.strip()
    if text.startswith("["):
        text = text[1:]
    if text.endswith("]"):
        text = text[:-1]
    return text.strip()


# Alias for backward compatibility
to_title_case = title_case_heading


# USLM XML namespaces
NAMESPACES = {
    "uslm": "http://xml.house.gov/schemas/uslm/1.0",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

# Compiled once at module level — _get_text_content is called O(sections × subsections)
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r" ([;,.])")

# Mapping from camelCase USLM <note topic="..."> values to canonical display strings.
# str.title() works fine for single-word topics like "amendments" → "Amendments",
# but fails for camelCase multi-word topics: "historicalAndRevision".title() produces
# "Historicalandrevision" (only the first character is capitalised because there are no
# word-boundary characters).  Entries here override topic.title() for known topics.
_NOTE_TOPIC_DISPLAY: dict[str, str] = {
    "historicalAndRevision": "Historical and Revision Notes",
    "referencesInText": "References in Text",
    "effectiveDateOfAmendment": "Effective Date of Amendment",
    "effectiveDate": "Effective Date",
    "changeOfName": "Change of Name",
    "transferOfFunctions": "Transfer of Functions",
    "shortTitle": "Short Title",
    "priorProvisions": "Prior Provisions",
    "savingsProvision": "Savings Provision",
    "constructionOfAmendment": "Construction of Amendment",
}


@dataclass
class ParsedGroup:
    """A unified structural node in the US Code hierarchy.

    Replaces ParsedTitle, ParsedChapterGroup, ParsedChapter, and
    ParsedSubchapter.  The ``group_type`` field discriminates level
    (title, subtitle, part, division, chapter, subchapter, etc.) and
    ``parent_key`` / ``key`` form the tree.
    """

    group_type: str  # "title", "subtitle", "part", "division", "chapter", "subchapter"
    number: str
    name: str
    sort_order: int = 0
    parent_key: str | None = None  # Key of parent group, None for root (title)
    key: str = ""  # Unique path key, e.g. "title:26/subtitle:A/chapter:1"

    # Title-specific (only set when group_type == "title")
    is_positive_law: bool = False
    positive_law_date: str | None = None
    positive_law_citation: str | None = None

    @property
    def title_number(self) -> int:
        """Extract title number from key (convenience for backward compat)."""
        root = self.key.split("/")[0]  # "title:26"
        return int(root.split(":")[1])


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
    continuation: list[str] = field(
        default_factory=list
    )  # Closing text after child list


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
class NoteRef:
    """A hyperlink reference extracted from notes sections.

    Extracted from <ref href="..."> elements within Historical, Editorial,
    or Statutory notes in USLM XML. These enable linking from notes to
    referenced laws and sections.

    Unlike SourceCreditRef (used for sourceCredit element), NoteRef can
    reference multiple target types: Public Laws, Acts, US Code sections,
    and Statutes at Large.
    """

    ref_type: str  # "public_law", "act", "usc_section", "statute"
    href: str  # The full href value
    display_text: str = ""  # The display text from the ref element

    # Parsed target fields (based on ref_type)
    congress: int | None = None  # For PUBLIC_LAW
    law_number: int | None = None  # For PUBLIC_LAW
    act_date: str | None = None  # For ACT (e.g., "1935-08-14")
    act_chapter: int | None = None  # For ACT
    usc_title: int | None = None  # For USC_SECTION
    usc_section: str | None = None  # For USC_SECTION (e.g., "106")
    stat_volume: int | None = None  # For STATUTE
    stat_page: int | None = None  # For STATUTE


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
    parent_group_key: str | None = None  # Key of immediate parent group
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
    notes_refs: list[NoteRef] = field(
        default_factory=list
    )  # Hyperlinks in notes sections (Task 1.17b)

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

    title: ParsedGroup  # Root group (group_type == "title")
    groups: list[ParsedGroup] = field(default_factory=list)  # All groups incl. title
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

    # Structural elements that can appear between title and chapter
    _GROUP_ELEMENTS = ("subtitle", "part", "division")

    def __init__(self) -> None:
        """Initialize the parser."""
        self._current_group_key: str | None = None
        self._section_order = 0
        self._group_order = 0
        self._groups: list[ParsedGroup] = []

    def parse_file(self, xml_path: Path | str) -> USLMParseResult:
        """Parse a USLM XML file.

        Args:
            xml_path: Path to the XML file.

        Returns:
            Parsed result containing groups and sections.
        """
        xml_path = Path(xml_path)
        logger.info(f"Parsing USLM XML file: {xml_path}")

        # Reset state
        self._current_group_key = None
        self._section_order = 0
        self._group_order = 0
        self._groups = []

        # Parse XML
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Extract title information and create root group
        title_group = self._parse_title(root)
        self._groups.append(title_group)
        self._current_group_key = title_group.key

        # Parse hierarchical structure
        sections: list[ParsedSection] = []

        # Find main content - try different possible root structures
        main = self._find_main_content(root)
        if main is None:
            logger.warning("Could not find main content element")
            return USLMParseResult(title=title_group, groups=self._groups)

        # Parse all levels
        for sects in self._parse_levels(main, title_group):
            sections.extend(sects)

        logger.info(
            f"Parsed Title {title_group.title_number}: "
            f"{len(self._groups)} groups, {len(sections)} sections"
        )

        return USLMParseResult(
            title=title_group,
            groups=self._groups,
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

    def _parse_title(self, root: etree._Element) -> ParsedGroup:
        """Extract title information from the root element and return as a ParsedGroup."""
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

        # Clean up title name and convert ALL-CAPS to Title Case
        title_name = title_name.strip()
        if not title_name:
            title_name = f"Title {title_number}"
        else:
            title_name = title_case_heading(title_name)

        # Check for positive law property in meta (OLRC format)
        for prop in root.findall(".//{*}property"):
            if prop.get("role") == "is-positive-law":
                is_positive_law = prop.text and prop.text.strip().lower() == "yes"
                break

        # Fall back to hardcoded list if not found in XML
        if not is_positive_law:
            is_positive_law = title_number in self.POSITIVE_LAW_TITLES

        return ParsedGroup(
            group_type="title",
            number=str(title_number),
            name=title_name,
            sort_order=0,
            parent_key=None,
            key=f"title:{title_number}",
            is_positive_law=is_positive_law,
        )

    def _find_group_elements(
        self, parent: etree._Element
    ) -> list[tuple[etree._Element, str]]:
        """Find direct structural children (subtitle, part, division).

        Checks direct children of *parent* first, then children of any
        <title> wrapper (since USLM often nests <subtitle>/<part> under
        <main>/<title> rather than directly under <main>).

        Returns a list of (element, group_type) tuples.
        """
        results: list[tuple[etree._Element, str]] = []
        ns = NAMESPACES["uslm"]

        # Build list of containers to search: parent itself, plus any <title> child
        containers = [parent]
        title_child = parent.find(f"./{{{ns}}}title")
        if title_child is None:
            title_child = parent.find("./title")
        if title_child is not None:
            containers.append(title_child)

        for container in containers:
            for tag in self._GROUP_ELEMENTS:
                for elem in container.findall(f"./{tag}"):
                    results.append((elem, tag))
                for elem in container.findall(f"./{{{ns}}}{tag}"):
                    results.append((elem, tag))
                # Also check <level> elements with matching type
                for lvl in container.findall("./level"):
                    if self._get_level_type(lvl) == tag:
                        results.append((lvl, tag))
                for lvl in container.findall(f"./{{{ns}}}level"):
                    if self._get_level_type(lvl) == tag:
                        results.append((lvl, tag))
        return results

    def _parse_group(
        self,
        elem: etree._Element,
        group_type: str,
        title_number: int,
        parent_key: str,
    ) -> Iterator[list[ParsedSection]]:
        """Parse a structural group element, recursing into nested groups."""
        self._group_order += 1
        number = self._get_number(elem)
        name = title_case_heading(_clean_bracket_heading(self._get_heading(elem)))
        key = f"{parent_key}/{group_type}:{number}"

        group = ParsedGroup(
            group_type=group_type,
            number=number,
            name=name,
            sort_order=self._group_order,
            parent_key=parent_key,
            key=key,
        )
        self._groups.append(group)

        # Look for nested structural children first
        nested_groups = self._find_group_elements(elem)
        if nested_groups:
            for child_elem, child_type in nested_groups:
                yield from self._parse_group(
                    child_elem, child_type, title_number, parent_key=key
                )
        else:
            # Look for chapters within this group
            chapters = elem.findall("./chapter") + elem.findall(
                f"./{{{NAMESPACES['uslm']}}}chapter"
            )
            if not chapters:
                chapters = [
                    lvl
                    for lvl in elem.findall("./level")
                    + elem.findall(f"./{{{NAMESPACES['uslm']}}}level")
                    if self._get_level_type(lvl) == "chapter"
                ]
            if chapters:
                for chapter_elem in chapters:
                    yield from self._parse_chapter(
                        chapter_elem, title_number, parent_key=key
                    )
            else:
                # No chapters found — parse sections directly under this group
                prev_key = self._current_group_key
                self._current_group_key = key
                sections = self._parse_sections_in_element(elem, title_number)
                self._current_group_key = prev_key
                yield sections

    def _parse_levels(
        self, parent: etree._Element, title_group: ParsedGroup
    ) -> Iterator[list[ParsedSection]]:
        """Recursively parse hierarchical levels.

        First checks for structural group elements (subtitle, part, division)
        between title and chapter level. If found, descends recursively.
        Otherwise falls through to direct chapter/section parsing.

        Yields:
            Lists of ParsedSection for each structural branch.
        """
        title_key = title_group.key
        title_number = title_group.title_number

        # Check for structural groups above chapter level
        groups = self._find_group_elements(parent)
        if groups:
            for group_elem, group_type in groups:
                yield from self._parse_group(
                    group_elem, group_type, title_number, parent_key=title_key
                )
            return

        # Look for chapter elements (check parent and any <title> child wrapper)
        ns = NAMESPACES["uslm"]
        containers = [parent]
        title_child = parent.find(f"./{{{ns}}}title")
        if title_child is None:
            title_child = parent.find("./title")
        if title_child is not None:
            containers.append(title_child)

        chapters: list[etree._Element] = []
        for container in containers:
            chapters.extend(container.findall("./chapter"))
            chapters.extend(container.findall(f"./{{{ns}}}chapter"))
            chapters.extend(
                lvl
                for lvl in container.findall("./level")
                + container.findall(f"./{{{ns}}}level")
                if self._get_level_type(lvl) == "chapter"
            )

        if chapters:
            for chapter_elem in chapters:
                yield from self._parse_chapter(
                    chapter_elem, title_number, parent_key=title_key
                )
        else:
            # No chapters - parse sections directly under title
            sections = self._parse_sections_in_element(parent, title_number)
            yield sections

    def _parse_chapter(
        self,
        chapter_elem: etree._Element,
        title_number: int,
        parent_key: str,
    ) -> Iterator[list[ParsedSection]]:
        """Parse a chapter element and its contents as a ParsedGroup."""
        self._group_order += 1
        self._section_order = 0

        # Extract chapter number and name (convert ALL-CAPS to Title Case)
        chapter_number = self._get_number(chapter_elem)
        chapter_name = title_case_heading(
            _clean_bracket_heading(self._get_heading(chapter_elem))
        )

        if not chapter_number:
            chapter_number = str(self._group_order)

        key = f"{parent_key}/chapter:{chapter_number}"

        chapter_group = ParsedGroup(
            group_type="chapter",
            number=chapter_number,
            name=chapter_name,
            sort_order=self._group_order,
            parent_key=parent_key,
            key=key,
        )
        self._groups.append(chapter_group)

        # Look for subchapters
        subchapter_elems = chapter_elem.findall("./subchapter") + chapter_elem.findall(
            "./{*}subchapter"
        )
        if not subchapter_elems:
            subchapter_elems = [
                lvl
                for lvl in chapter_elem.findall("./level")
                + chapter_elem.findall("./{*}level")
                if self._get_level_type(lvl) == "subchapter"
            ]

        if subchapter_elems:
            for subch_elem in subchapter_elems:
                yield from self._parse_subchapter(subch_elem, title_number, key)
        else:
            # No subchapters - parse sections directly in chapter
            prev_key = self._current_group_key
            self._current_group_key = key
            sections = self._parse_sections_in_element(chapter_elem, title_number)
            self._current_group_key = prev_key
            yield sections

    def _parse_subchapter(
        self,
        subch_elem: etree._Element,
        title_number: int,
        chapter_key: str,
    ) -> Iterator[list[ParsedSection]]:
        """Parse a subchapter element as a ParsedGroup.

        Also detects <part> children within the subchapter — this is the
        fix for issue #69 (parts within subchapters).
        """
        self._group_order += 1
        self._section_order = 0

        subch_number = self._get_number(subch_elem)
        subch_name = title_case_heading(
            _clean_bracket_heading(self._get_heading(subch_elem))
        )

        if not subch_number:
            subch_number = str(self._group_order)

        key = f"{chapter_key}/subchapter:{subch_number}"

        subchapter_group = ParsedGroup(
            group_type="subchapter",
            number=subch_number,
            name=subch_name,
            sort_order=self._group_order,
            parent_key=chapter_key,
            key=key,
        )
        self._groups.append(subchapter_group)

        # Check for parts within subchapter (issue #69)
        ns = NAMESPACES["uslm"]
        part_elems = subch_elem.findall(f"./{{{ns}}}part") + subch_elem.findall(
            "./part"
        )
        if not part_elems:
            part_elems = [
                lvl
                for lvl in subch_elem.findall(f"./{{{ns}}}level")
                + subch_elem.findall("./level")
                if self._get_level_type(lvl) == "part"
            ]

        if part_elems:
            for part_elem in part_elems:
                yield from self._parse_subchapter_part(part_elem, title_number, key)
        else:
            prev_key = self._current_group_key
            self._current_group_key = key
            sections = self._parse_sections_in_element(subch_elem, title_number)
            self._current_group_key = prev_key
            yield sections

    def _parse_subchapter_part(
        self,
        part_elem: etree._Element,
        title_number: int,
        subchapter_key: str,
    ) -> Iterator[list[ParsedSection]]:
        """Parse a part element nested within a subchapter."""
        self._group_order += 1
        self._section_order = 0

        part_number = self._get_number(part_elem)
        part_name = title_case_heading(
            _clean_bracket_heading(self._get_heading(part_elem))
        )

        if not part_number:
            part_number = str(self._group_order)

        key = f"{subchapter_key}/part:{part_number}"

        part_group = ParsedGroup(
            group_type="part",
            number=part_number,
            name=part_name,
            sort_order=self._group_order,
            parent_key=subchapter_key,
            key=key,
        )
        self._groups.append(part_group)

        prev_key = self._current_group_key
        self._current_group_key = key
        sections = self._parse_sections_in_element(part_elem, title_number)
        self._current_group_key = prev_key
        yield sections

    def _parse_sections_in_element(
        self, parent: etree._Element, title_number: int
    ) -> list[ParsedSection]:
        """Parse all section elements within a parent element."""
        sections: list[ParsedSection] = []

        # Find direct child section elements only (not nested in notes/quotedContent)
        section_elems = parent.findall("./section") + parent.findall("./{*}section")
        if not section_elems:
            section_elems = [
                lvl
                for lvl in parent.findall("./level") + parent.findall("./{*}level")
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

        # Extract hyperlink refs from notes sections (Task 1.17b)
        notes_refs = self._extract_notes_refs(section_elem)

        return ParsedSection(
            section_number=section_number,
            heading=heading,
            full_citation=full_citation,
            text_content=text_content,
            parent_group_key=self._current_group_key,
            notes=notes,
            sort_order=self._section_order,
            subsections=subsections,
            source_credit_refs=source_credit_refs,
            act_refs=act_refs,
            notes_refs=notes_refs,
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
        valid_types = {
            "chapter",
            "subchapter",
            "section",
            "subtitle",
            "part",
            "division",
        }
        if role in valid_types:
            return str(role)

        return None

    def _get_number(self, elem: etree._Element) -> str:
        """Extract the number/identifier from an element."""
        # Check number attribute on element
        if "number" in elem.attrib:
            return str(elem.attrib["number"])

        # Look for <num> child element with value attribute (OLRC format)
        num_elem = elem.find("{*}num")
        if num_elem is None:
            num_elem = elem.find("num")
        if num_elem is not None:
            # Prefer value attribute (contains clean number)
            if "value" in num_elem.attrib:
                return str(num_elem.attrib["value"])
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
        """Extract the heading text from an element, stripping footnotes.

        For repealed/renumbered sections the USLM XML wraps the num+heading
        in editorial brackets, e.g. ``[§ 4. Repealed. ... 90 Stat. 1558]``.
        The opening ``[`` lives on the ``<num>`` element, while the closing
        ``]`` lands on the ``<heading>``.  We strip the dangling ``]`` here.
        """
        heading_elem = elem.find("heading") or elem.find("{*}heading")
        if heading_elem is not None:
            text = self._get_text_content(heading_elem, strip_footnotes=True)
            return text.rstrip("]").rstrip()

        # Fall back to title element
        title_elem = elem.find("title") or elem.find("{*}title")
        if title_elem is not None:
            return self._get_text_content(title_elem, strip_footnotes=True)

        return ""

    def _get_text_content(
        self, elem: etree._Element, strip_footnotes: bool = False
    ) -> str:
        """Get all text content from an element, including nested elements.

        Args:
            elem: The XML element to extract text from.
            strip_footnotes: If True, skip <ref class="footnoteRef"> and
                <note type="footnote"> elements.  Useful for headings and
                provision text where footnote content should not appear inline.
        """
        if elem is None:
            return ""

        if strip_footnotes:
            parts = list(self._itertext_skip_footnotes(elem))
        else:
            parts = list(elem.itertext())

        # Concatenate text fragments preserving original whitespace, then
        # collapse runs of whitespace to a single space.  Using "".join
        # (instead of " ".join) avoids inserting extra spaces at inline
        # element boundaries like <date> or <ref>.
        text = _WS_RE.sub(" ", "".join(parts)).strip()
        # Remove stray spaces before punctuation that arise from inline
        # element boundaries (e.g. "<ref>Pub. L. 94–455</ref> ;")
        text = _PUNCT_RE.sub(r"\1", text)
        return text

    def _get_text_content_excluding(
        self,
        elem: etree._Element,
        excluded: list[etree._Element],
        strip_footnotes: bool = False,
    ) -> str:
        """Get text content from an element, skipping specified child elements.

        Used to extract content text from a <content> element while excluding
        embedded <continuation> children so their text can be captured at the
        correct semantic level (e.g. section level for 17 U.S.C. § 107).

        Args:
            elem: The XML element to extract text from.
            excluded: Child elements whose text (and their children's text) should
                be omitted from the result.
            strip_footnotes: If True, also skip footnote refs and notes.
        """
        excluded_set = {id(e) for e in excluded}

        def itertext_excluding(
            el: etree._Element,
        ) -> Generator[str, None, None]:
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if strip_footnotes:
                if tag == "ref" and el.get("class", "") == "footnoteRef":
                    return
                if tag == "note" and el.get("type", "") == "footnote":
                    return
            if el.text:
                yield el.text
            for child in el:
                if id(child) in excluded_set:
                    # Skip this child entirely; still yield its tail (text after
                    # the closing tag) so surrounding punctuation is preserved.
                    if child.tail:
                        yield child.tail
                    continue
                yield from itertext_excluding(child)
                if child.tail:
                    yield child.tail

        parts = list(itertext_excluding(elem))
        text = _WS_RE.sub(" ", "".join(parts)).strip()
        text = _PUNCT_RE.sub(r"\1", text)
        return text

    @staticmethod
    def _itertext_skip_footnotes(elem: etree._Element) -> Generator[str, None, None]:
        """Like elem.itertext() but skips footnote refs and notes."""
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        # Skip footnote reference links and footnote note bodies
        if tag == "ref" and elem.get("class", "") == "footnoteRef":
            return
        if tag == "note" and elem.get("type", "") == "footnote":
            return
        if elem.text:
            yield elem.text
        for child in elem:
            yield from USLMParser._itertext_skip_footnotes(child)
            if child.tail:
                yield child.tail

    def _extract_section_text(self, section_elem: etree._Element) -> str:
        """Extract the full text content of a section."""
        # Find content element
        content = section_elem.find("content") or section_elem.find("{*}content")
        if content is not None:
            return self._get_text_content(content, strip_footnotes=True)

        # Fall back to getting all text except heading and metadata
        parts = []
        for child in section_elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag not in ("heading", "num", "title", "sourceCredit", "notes"):
                parts.append(self._get_text_content(child, strip_footnotes=True))

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
            self._get_text_content(heading_elem, strip_footnotes=True)
            if heading_elem is not None
            else None
        )

        # Get content (may be in <content> or <chapeau> or directly in element)
        content_elem = elem.find("{*}content")
        if content_elem is None:
            content_elem = elem.find("content")
        chapeau_elem = elem.find("{*}chapeau")
        if chapeau_elem is None:
            chapeau_elem = elem.find("chapeau")

        content_parts = []
        # Collect continuation elements that appear inside <content> (not direct
        # children of the paragraph/subsection element).  These are semantically
        # "flush-left" continuations that apply at the parent (section) level —
        # e.g. 17 U.S.C. § 107 where "The fact that a work is unpublished…"
        # appears as <continuation> inside <content> inside the last <paragraph>.
        # We strip them from the content text and collect them separately so
        # callers can promote them to the correct indent level.
        #
        # <p> elements inside <content> represent separate paragraphs in USLM
        # (e.g. 9 U.S.C. § 13 where a trailing sentence follows the (c) item).
        # They are also excluded from content text and emitted as continuations
        # so they render as separate provisions (Issue #479).
        content_continuations: list[str] = []
        if chapeau_elem is not None:
            content_parts.append(
                self._get_text_content(chapeau_elem, strip_footnotes=True)
            )
        if content_elem is not None:
            # Collect child elements inside <content> that should be separated out:
            # <continuation> and <p> elements each represent distinct paragraphs.
            cont_in_content = content_elem.findall(
                "{*}continuation"
            ) or content_elem.findall("continuation")
            p_in_content = content_elem.findall("{*}p") or content_elem.findall("p")
            excluded_in_content = cont_in_content + p_in_content
            if excluded_in_content:
                # Get content text excluding the separated child elements.
                content_text = self._get_text_content_excluding(
                    content_elem, excluded_in_content, strip_footnotes=True
                )
                if content_text:
                    content_parts.append(content_text)
                # Emit separated children in document order as continuation entries.
                excluded_set = {id(e) for e in excluded_in_content}
                for child_elem in content_elem:
                    if id(child_elem) in excluded_set:
                        cont_text = self._get_text_content(
                            child_elem, strip_footnotes=True
                        )
                        if cont_text:
                            content_continuations.append(cont_text)
            else:
                content_parts.append(
                    self._get_text_content(content_elem, strip_footnotes=True)
                )

        content = " ".join(content_parts).strip()

        # Parse nested children.
        #
        # The standard USLM hierarchy is:
        #     subsection > paragraph > subparagraph > clause > subclause > item
        #
        # Normally each level's children use the immediate-next tag (e.g. a
        # <paragraph> contains <subparagraph> children). However, some sources
        # (e.g. 38 U.S.C. § 3702(a)(1)) skip a level — a <paragraph> may
        # directly contain <clause> elements with no intervening
        # <subparagraph>. If we only ever look for the immediate-next tag, we
        # silently drop these deeper-nested children and lose their content.
        #
        # To handle this, we search for whichever of the structurally-valid
        # descendant tags (in hierarchy order, from shallowest to deepest)
        # actually appears as a direct child, and use that tag both to find
        # the children AND to determine the correct `level` to assign so they
        # render with the appropriate marker/indentation (e.g. clauses render
        # as "(i)", "(ii)" regardless of whether they are reached via
        # <subparagraph> or directly).
        children = []
        hierarchy = [
            "subsection",
            "paragraph",
            "subparagraph",
            "clause",
            "subclause",
            "item",
        ]
        if level in hierarchy:
            level_index = hierarchy.index(level)
            for child_level in hierarchy[level_index + 1 :]:
                child_elems = elem.findall(f"{{*}}{child_level}") or elem.findall(
                    child_level
                )
                if child_elems:
                    for child_elem in child_elems:
                        children.append(self._parse_subsection(child_elem, child_level))
                    break

        # Collect continuation elements (closing text that follows a numbered list,
        # e.g. the penalty clause in 18 U.S.C. § 1001(a)).
        # Continuations extracted from within <content> above are prepended so
        # they appear in document order before any direct-child continuations.
        continuation: list[str] = list(content_continuations)
        continuation_elems = elem.findall("{*}continuation") or elem.findall(
            "continuation"
        )
        for cont_elem in continuation_elems:
            cont_text = self._get_text_content(cont_elem, strip_footnotes=True)
            if cont_text:
                continuation.append(cont_text)

        return ParsedSubsection(
            marker=marker,
            heading=heading,
            content=content,
            children=children,
            level=level,
            continuation=continuation,
        )

    def _extract_subsections(
        self, section_elem: etree._Element
    ) -> list[ParsedSubsection]:
        """Extract structured subsections from a section element.

        Handles two XML patterns:
        1. Standard: <section> > <subsection> > <paragraph> > ...
        2. Direct paragraphs: <section> > <chapeau>? > <paragraph> > ...
           (e.g. 20 U.S.C. § 5204 which has no <subsection> wrapper)
        """
        subsections = []

        # Try namespaced first, then non-namespaced
        subsec_elems = section_elem.findall("{*}subsection")
        if not subsec_elems:
            subsec_elems = section_elem.findall("subsection")

        for subsec_elem in subsec_elems:
            subsections.append(self._parse_subsection(subsec_elem, "subsection"))

        # If no <subsection> elements, check for <paragraph> directly under section
        if not subsections:
            para_elems = section_elem.findall("{*}paragraph")
            if not para_elems:
                para_elems = section_elem.findall("paragraph")

            if para_elems:
                # Determine the document-order position of the first and last paragraph
                # to classify sibling <p> elements as intro text or trailing text.
                all_children = list(section_elem)
                first_para_idx = all_children.index(para_elems[0])
                last_para_idx = all_children.index(para_elems[-1])

                # Collect introductory text: explicit <chapeau> OR <p> siblings that
                # appear before the first <paragraph> in document order (Issue #478).
                chapeau_elem = section_elem.find("{*}chapeau")
                if chapeau_elem is None:
                    chapeau_elem = section_elem.find("chapeau")
                chapeau_parts: list[str] = []
                if chapeau_elem is not None:
                    text = self._get_text_content(chapeau_elem)
                    if text:
                        chapeau_parts.append(text)
                for child in all_children[:first_para_idx]:
                    child_tag = (
                        child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    )
                    if child_tag == "p":
                        text = self._get_text_content(child)
                        if text:
                            chapeau_parts.append(text)
                chapeau_text = " ".join(chapeau_parts)

                # Collect trailing text: explicit <continuation> OR <p> siblings that
                # appear after the last <paragraph> in document order (Issue #479).
                section_continuation: list[str] = []
                cont_elems = section_elem.findall(
                    "{*}continuation"
                ) or section_elem.findall("continuation")
                for cont_elem in cont_elems:
                    cont_text = self._get_text_content(cont_elem, strip_footnotes=True)
                    if cont_text:
                        section_continuation.append(cont_text)
                for child in all_children[last_para_idx + 1 :]:
                    child_tag = (
                        child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    )
                    if child_tag == "p":
                        text = self._get_text_content(child, strip_footnotes=True)
                        if text:
                            section_continuation.append(text)

                # Parse each paragraph, then bubble up any <continuation> elements
                # that were nested inside a paragraph's <content>.  In OLRC XML
                # (e.g. 17 U.S.C. § 107) these represent flush-left closing text
                # that applies to the entire section — semantically equivalent to
                # indent_level=0 — not a sub-clause of the individual paragraph.
                # We promote them to the synthetic section-wrapper's continuation
                # so they render at indent_level=0.  The paragraph's own
                # continuation list is cleared after promotion to avoid duplication.
                children = []
                for para_elem in para_elems:
                    parsed_para = self._parse_subsection(para_elem, "paragraph")
                    # Detect which continuation items originated inside <content>
                    # (captured by _parse_subsection via content_continuations).
                    # This includes both <continuation> elements (17 U.S.C. § 107)
                    # and <p> elements (9 U.S.C. § 13, Issue #479) — both represent
                    # section-level paragraphs, not sub-clauses of the list item.
                    para_content_elem = para_elem.find("{*}content")
                    if para_content_elem is None:
                        para_content_elem = para_elem.find("content")
                    if para_content_elem is not None:
                        in_content_separated_texts = {
                            self._get_text_content(ce, strip_footnotes=True)
                            for ce in (
                                para_content_elem.findall("{*}continuation")
                                or para_content_elem.findall("continuation")
                            )
                        } | {
                            self._get_text_content(pe, strip_footnotes=True)
                            for pe in (
                                para_content_elem.findall("{*}p")
                                or para_content_elem.findall("p")
                            )
                        }
                        if in_content_separated_texts:
                            # Bubble these up to section level and remove from
                            # the paragraph so they don't render at indent_level=1.
                            promoted: list[str] = []
                            kept: list[str] = []
                            for ct in parsed_para.continuation:
                                if ct in in_content_separated_texts:
                                    promoted.append(ct)
                                else:
                                    kept.append(ct)
                            section_continuation.extend(promoted)
                            parsed_para.continuation = kept
                    children.append(parsed_para)

                # Wrap in a synthetic subsection so normalization handles it
                subsections.append(
                    ParsedSubsection(
                        marker="",
                        heading=None,
                        content=chapeau_text,
                        children=children,
                        level="subsection",
                        continuation=section_continuation,
                    )
                )

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

        Parses the structured sections, subsections, paragraphs, etc. within
        quoted content and formats them with [QC:level] markers the normalizer
        uses to create properly indented lines.

        Patterns handled:
        - Anonymous inline: <section class="inline"> with chapeau + paragraphs
          + continuation (no section header emitted for empty <num>)
        - Full named sections: <section> with real <num> and <heading>
        - Subsection-only: <subsection> children at top level (legacy pattern)
        - Paragraph-only: <paragraph> children directly under quotedContent
          with no enclosing <section>/<subsection> wrapper, optionally
          preceded by a bare <inline> intro line (e.g. the 21 U.S.C. 822
          "Findings" note; see issue #536)
        """
        parts = []

        def format_item(item_elem: etree._Element, level: int) -> None:
            """Recursively format a structural element."""
            num_elem = item_elem.find("{*}num")
            if num_elem is None:
                num_elem = item_elem.find("num")
            marker = self._get_text_content(num_elem) if num_elem is not None else ""

            heading_elem = item_elem.find("{*}heading")
            if heading_elem is None:
                heading_elem = item_elem.find("heading")
            heading = (
                self._get_text_content(heading_elem).strip()
                if heading_elem is not None
                else ""
            )

            chapeau_elem = item_elem.find("{*}chapeau")
            if chapeau_elem is None:
                chapeau_elem = item_elem.find("chapeau")

            content_elem = item_elem.find("{*}content")
            if content_elem is None:
                content_elem = item_elem.find("content")

            # Emit the header line: marker + heading + direct content (if no chapeau)
            line_parts: list[str] = []
            if marker:
                line_parts.append(marker)
            if heading:
                line_parts.append(heading)
            if chapeau_elem is None and content_elem is not None:
                content_text = self._get_text_content(content_elem).strip()
                if content_text:
                    line_parts.append(content_text)

            if line_parts:
                parts.append(f"[QC:{level}]{' '.join(line_parts)}[/QC]")

            # Chapeau is the intro sentence before enumerated children
            if chapeau_elem is not None:
                chapeau_text = self._get_text_content(chapeau_elem).strip()
                if chapeau_text:
                    child_level = level + 1 if line_parts else level
                    parts.append(f"[QC:{child_level}]{chapeau_text}[/QC]")

            # Recurse into structural children (subsection added for section→subsection)
            child_tags = [
                "subsection",
                "paragraph",
                "subparagraph",
                "clause",
                "subclause",
                "item",
            ]
            for child_tag in child_tags:
                for child in item_elem.findall(f"{{*}}{child_tag}"):
                    format_item(child, level + 1)
                for child in item_elem.findall(child_tag):
                    format_item(child, level + 1)

            # Continuation is the closing sentence after enumerated children
            cont_elem = item_elem.find("{*}continuation")
            if cont_elem is None:
                cont_elem = item_elem.find("continuation")
            if cont_elem is not None:
                cont_text = self._get_text_content(cont_elem).strip()
                if cont_text:
                    child_level = level + 1 if line_parts else level
                    parts.append(f"[QC:{child_level}]{cont_text}[/QC]")

        # Process top-level sections (both anonymous inline and named)
        for section in elem.findall("{*}section"):
            format_item(section, 1)
        for section in elem.findall("section"):
            format_item(section, 1)

        # Process top-level subsections when no sections are present
        if not parts:
            for subsection in elem.findall("{*}subsection"):
                format_item(subsection, 1)
            for subsection in elem.findall("subsection"):
                format_item(subsection, 1)

        # Process top-level paragraphs when neither sections nor subsections
        # wrap them directly under quotedContent (e.g. a flat enumeration
        # like "(1)", "(2)" with "(A)", "(B)" sub-items but no enclosing
        # <section>/<subsection>). A bare <inline> intro line, if present,
        # is emitted first at the same level so it precedes the enumeration.
        if not parts:
            inline_elem = elem.find("{*}inline")
            if inline_elem is None:
                inline_elem = elem.find("inline")
            if inline_elem is not None:
                inline_text = self._get_text_content(inline_elem).strip()
                if inline_text:
                    parts.append(f"[QC:1]{inline_text}[/QC]")

            for paragraph in elem.findall("{*}paragraph"):
                format_item(paragraph, 1)
            for paragraph in elem.findall("paragraph"):
                format_item(paragraph, 1)

        # Fallback: extract plain text for simple inline quotedContent
        if not parts:
            text = self._get_text_content(elem).strip()
            if text:
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

        def process_element(
            el: etree._Element, in_bold: bool = False, in_italic: bool = False
        ) -> None:
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

            # Handle signature blocks (presidential/official signatures).
            # When <signature> has structured child elements (<name>, <role>),
            # emit each child as a separate [SIG] line to avoid embedding \n
            # in a single content string.  When there are no child elements,
            # fall back to the simple single-line form.
            if tag == "signature":
                child_tags_in_sig = [
                    c
                    for c in el
                    if (c.tag.split("}")[-1] if "}" in c.tag else c.tag)
                    in ("name", "role")
                ]
                if child_tags_in_sig:
                    # Emit each <name>/<role> child as its own [SIG] line
                    for child in child_tags_in_sig:
                        child_text = "".join(child.itertext()).strip().rstrip(".")
                        if child_text:
                            parts.append(f"[PARA][SIG]\u2014 {child_text}[/SIG]")
                else:
                    # No structured children — collapse the whole element as before
                    sig_text = "".join(el.itertext()).strip()
                    if sig_text:
                        sig_text = sig_text.rstrip(".")
                        parts.append(f"[PARA][SIG]\u2014 {sig_text}[/SIG]")
                if el.tail:
                    parts.append(el.tail)
                return

            # Handle <role> elements that appear as siblings to <signature>
            # in USLM notes (e.g. the signature blocks in 17 U.S.C. § 107).
            # These carry the signer's title/role and must be rendered as
            # their own [SIG] line — consistent with how <role> children
            # inside <signature> are handled — so that no raw \n ends up
            # embedded in a single content string.
            if tag == "role":
                role_text = "".join(el.itertext()).strip().rstrip(".")
                if role_text:
                    parts.append(f"[PARA][SIG]— {role_text}[/SIG]")
                if el.tail:
                    parts.append(el.tail)
                return

            # <note topic="..."> without a <heading> child: synthesize [NH] from topic.
            # Some USLM releases omit the heading element and rely solely on the
            # topic attribute (e.g. <note topic="amendments"><p>...</p>).
            if tag == "note":
                topic = el.get("topic", "")
                if topic:
                    child_tags = {
                        (c.tag.split("}")[-1] if "}" in c.tag else c.tag) for c in el
                    }
                    if "heading" not in child_tags:
                        # Use the canonical display string for known camelCase topics;
                        # fall back to topic.title() for simple single-word topics like
                        # "amendments" → "Amendments".
                        #
                        # Some OLRC releases capitalise the first character of the topic
                        # attribute (e.g. "HistoricalAndRevision" instead of the standard
                        # "historicalAndRevision").  Normalise to lowercase-first camelCase
                        # before the dict lookup so the canonical display string is always
                        # found (issue #542).
                        normalized_topic = topic[0].lower() + topic[1:]
                        display = _NOTE_TOPIC_DISPLAY.get(
                            normalized_topic, topic.title()
                        )
                        nh_marker = f"[NH]{display}[/NH]"
                        # Skip the [NH] marker if an immediately-preceding cross-heading
                        # (a <heading> child of the parent <notes> element) already
                        # emitted the equivalent header.  Both markers refer to the same
                        # note; emitting both causes _parse_historical_notes to capture
                        # empty content and _parse_flat_notes to add a duplicate note
                        # (issue #542).  Compare case-insensitively to handle the
                        # .title() capitalisation difference ("And" vs "and").
                        last_non_ws = next(
                            (p for p in reversed(parts) if p and p.strip()), ""
                        )
                        if last_non_ws.upper() != nh_marker.upper():
                            parts.append(nh_marker)

            # Preserve paragraph boundaries with a special marker
            # We use [PARA] marker instead of \n\n because tail text often contains \n
            if tag == "p" and parts:
                # Add paragraph break marker before this <p> element
                parts.append("[PARA]")

            # Check if this is a heading element — always emit [NH] markers regardless
            # of whether it has class="smallCaps".  Some USLM releases use
            # <note topic="amendments"><heading>Amendments</heading> without the
            # smallCaps class, but the element is still a structural note header.
            if tag == "heading":
                text = "".join(el.itertext()).strip()
                if text:
                    # Preserve verbatim text from OLRC source — do NOT apply
                    # .title() here because that mangles lowercase connective
                    # words ("of" → "Of", "in" → "In", etc.).  See issue #509.
                    parts.append(f"[NH]{text}[/NH]")
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
                    # Italic text is a sub-header only when it is followed
                    # immediately by ".—" (an em-dash introducer), e.g.:
                    #   <i>Reproduction</i>.—The right to reproduce.
                    # If the tail does NOT start with ".—" the element is
                    # inline formatting (case name, date, emphasis) and must
                    # be kept as plain text so the surrounding sentence is
                    # not fragmented. Also exclude known case-citation
                    # patterns (" v. ") and common Latin phrases.
                    inline_latin = {"et seq", "et al", "supra", "infra", "id"}
                    stripped_text = text.strip().rstrip(".")
                    tail = el.tail or ""
                    is_subheader_tail = bool(re.match(r"^\s*\.?\s*—", tail))
                    if (
                        " v. " in text
                        or stripped_text.lower() in inline_latin
                        or not is_subheader_tail
                    ):
                        # Inline text (case citation, date, Latin phrase, or
                        # mid-sentence emphasis) — keep as plain text
                        parts.append(text)
                    else:
                        # Standalone italic introducer followed by ".—":
                        # mark as sub-header for the normalizer
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
        # Join parts, converting [PARA] markers to double newlines.
        # Always strip whitespace from each part and join with a single
        # space so that inconsistent leading/trailing spaces in XML
        # text/tail never produce double-spaces or missing separators.
        result: list[str] = []
        for part in parts:
            if part == "[PARA]":
                result.append("\n\n")
                continue
            stripped = part.strip()
            if not stripped:
                continue
            if not result or result[-1] == "\n\n" or stripped[0] in ";,.":
                result.append(stripped)
            else:
                result.append(" " + stripped)
        return "".join(result).strip()

    @staticmethod
    def _collect_ref_subdivision_suffix(ref_elem: etree._Element) -> str:
        """Collect subdivision text that follows a <ref> element's closing tag.

        In OLRC XML, italic letters in subdivision specifiers (e.g., the 'l' in
        '(l)(3)(F)') are encoded as <i>l</i> elements immediately after the
        closing </ref> tag. The surrounding parentheses and alphanumeric identifiers
        appear as tail text of the <ref> or <i> elements. This method collects
        that trailing text and returns it as a suffix to append to the ref's
        display text.

        The collection stops at the first structural delimiter (a comma) encountered
        at the same parenthetical depth as the end of the ref element's own text, or
        at a structural sibling element (e.g., <date>, <ref>, <statuteRef>).

        Args:
            ref_elem: The <ref> element whose tail/siblings to inspect.

        Returns:
            Suffix string (e.g., '(l)(3)(F)') to append to the ref's text content,
            or an empty string if no subdivision suffix is found.
        """
        # Structural element local names that signal a new citation component
        _STOP_TAGS = {"date", "ref", "statuteRef", "sourceCredit"}

        def _paren_depth(s: str) -> int:
            """Return the net paren depth change for string s."""
            depth = 0
            for ch in s:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            return depth

        def _take_until_comma_at_depth(s: str, start_depth: int) -> tuple[str, int]:
            """Return (leading chars of s before a comma at depth <= 0, final depth).

            Scanning begins with paren depth = start_depth, and stops when a comma
            is encountered while depth <= 0.
            """
            depth = start_depth
            for i, ch in enumerate(s):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                elif ch == "," and depth <= 0:
                    return s[:i], depth
            return s, depth

        parent = ref_elem.getparent()
        if parent is None:
            return ""

        children = list(parent)
        try:
            ref_idx = children.index(ref_elem)
        except ValueError:
            return ""

        # Compute the paren depth at the end of the ref element's own text content.
        # If the ref text ends with an open paren (e.g., '§ 1103('), we start at
        # depth 1 so that a comma inside the subdivision does not act as a delimiter.
        ref_text = "".join(ref_elem.itertext())
        current_depth = _paren_depth(ref_text)

        parts: list[str] = []

        # 1. Collect from ref_elem.tail (text immediately after </ref>)
        tail = ref_elem.tail or ""
        chunk, current_depth = _take_until_comma_at_depth(tail, current_depth)
        parts.append(chunk)
        # If the tail contained a delimiter (chunk shorter than tail), stop here.
        if len(chunk) < len(tail):
            return "".join(parts)

        # 2. Collect from subsequent sibling elements until we hit a delimiter
        for sibling in children[ref_idx + 1 :]:
            tag = sibling.tag
            local = etree.QName(tag).localname if not callable(tag) else None
            if local in _STOP_TAGS:
                break
            # Collect all text inside the sibling (e.g., 'l' inside <i>l</i>)
            sib_text = "".join(sibling.itertext())
            current_depth += _paren_depth(sib_text)
            parts.append(sib_text)
            # Then collect from the sibling's tail
            sib_tail = sibling.tail or ""
            chunk, current_depth = _take_until_comma_at_depth(sib_tail, current_depth)
            parts.append(chunk)
            if len(chunk) < len(sib_tail):
                break  # Hit a structural delimiter in sibling tail

        return "".join(parts)

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

        # Process all significant elements within sourceCredit in document order.
        # We traverse the element tree once, handling <ref> and <date> elements
        # together so that each <date> is attributed to the most recently seen
        # PL ref rather than the positionally-matching one.
        #
        # This correctly handles "as added" credits, e.g.:
        #   (Pub. L. 87–195, ..., as added Pub. L. 104–132, ..., Apr. 24, 1996, ...)
        # where the single <date> belongs to PL 104-132 (the adding law), not
        # to PL 87-195 (the framework law that has no date in the credit).
        #
        # We use iter() to visit all descendants in document order, which gives
        # the correct interleaving of <ref> and <date> elements.

        # Track the most recent ref (either PL or Act) for stat/date association
        last_ref_type: str | None = None

        for elem in source_credit.iter():
            local_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if local_tag == "ref":
                href = elem.get("href", "")
                text = "".join(elem.itertext()).strip()

                # Collect any subdivision text following the </ref> closing tag.
                # In OLRC XML, italic letters in subdivision specifiers (e.g., the 'l'
                # in '§ 1103(l)(3)(F)') are encoded as sibling <i> elements after </ref>.
                subdivision_suffix = self._collect_ref_subdivision_suffix(elem)
                full_text = (text + subdivision_suffix).strip()

                # Compute the "bridge": trailing '(' chars in ref text that open the
                # subdivision but are not encoded in the href (e.g., '/s1103' href while
                # ref text ends with '§ 1103(').
                bridge = ""
                if subdivision_suffix:
                    trail = "".join(elem.itertext()).rstrip()
                    i = len(trail)
                    while i > 0 and trail[i - 1] == "(":
                        i -= 1
                    bridge = trail[i:]

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
                        href_section = match.group(5)
                        section_value: str | None = (
                            href_section + bridge + subdivision_suffix
                            if subdivision_suffix and href_section
                            else href_section
                        )
                        ref = SourceCreditRef(
                            congress=int(match.group(1)),
                            law_number=int(match.group(2)),
                            division=match.group(3),
                            title=match.group(4),
                            section=section_value,
                            raw_text=full_text,
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
                        href_section = match.group(4)
                        section_value = (
                            href_section + bridge + subdivision_suffix
                            if subdivision_suffix and href_section
                            else href_section
                        )
                        act_ref = ActRef(
                            date=match.group(1),  # e.g., "1935-08-14"
                            chapter=int(match.group(2)),
                            title=match.group(3),
                            section=section_value,
                            raw_text=full_text,
                        )
                        act_refs.append(act_ref)
                        last_ref_type = "act"

                # Parse /us/stat/VOLUME/PAGE hrefs to capture Stat references
                elif "/us/stat/" in href:
                    match = re.match(r"/us/stat/(\d+)/(\d+)", href)
                    if match:
                        stat_volume = int(match.group(1))
                        stat_page = int(match.group(2))
                        # Apply to the most recent ref
                        if last_ref_type == "pl" and pl_refs:
                            pl_refs[-1].stat_volume = stat_volume
                            pl_refs[-1].stat_page = stat_page
                        elif last_ref_type == "act" and act_refs:
                            act_refs[-1].stat_volume = stat_volume
                            act_refs[-1].stat_page = stat_page

            elif local_tag == "date":
                # Act refs already have dates in the href; <date> elements belong to
                # PL refs only. Attribute each date to the most recently seen PL ref
                # so that "as added" credits assign the date to the adding law, not
                # the framework law that precedes the "as added" clause.
                date_text = "".join(elem.itertext()).strip()
                if last_ref_type == "pl" and pl_refs:
                    pl_refs[-1].date = date_text

        return pl_refs, act_refs

    def _extract_notes_refs(self, section_elem: etree._Element) -> list[NoteRef]:
        """Extract hyperlink references from notes sections.

        Parses <ref href="..."> elements from Historical, Editorial, and
        Statutory notes (not sourceCredit). These provide hyperlinks to:
        - Public Laws: /us/pl/CONGRESS/LAW_NUMBER/...
        - Acts: /us/act/DATE/ch/CHAPTER/...
        - US Code sections: /us/usc/tTITLE/sSECTION
        - Statutes at Large: /us/stat/VOLUME/PAGE

        Args:
            section_elem: The section XML element to extract refs from.

        Returns:
            List of NoteRef objects in document order.
        """
        refs: list[NoteRef] = []

        # Find the notes element (not sourceCredit - that's handled separately)
        notes_elem = section_elem.find(".//{*}notes")
        if notes_elem is None:
            notes_elem = section_elem.find(".//notes")
        if notes_elem is None:
            return refs

        # Find all ref elements within notes
        ref_elems = notes_elem.findall(".//{*}ref")
        if not ref_elems:
            ref_elems = notes_elem.findall(".//ref")

        for ref_elem in ref_elems:
            href = ref_elem.get("href", "")
            if not href:
                continue

            text = "".join(ref_elem.itertext()).strip()

            # Parse /us/pl/CONGRESS/LAW/... hrefs (Public Laws, post-1957)
            if "/us/pl/" in href:
                match = re.match(
                    r"/us/pl/(\d+)/(\d+)",  # Congress and law number
                    href,
                )
                if match:
                    refs.append(
                        NoteRef(
                            ref_type="public_law",
                            href=href,
                            display_text=text,
                            congress=int(match.group(1)),
                            law_number=int(match.group(2)),
                        )
                    )

            # Parse /us/act/YYYY-MM-DD/chNNN/... hrefs (Acts, pre-1957)
            elif "/us/act/" in href:
                match = re.match(
                    r"/us/act/(\d{4}-\d{2}-\d{2})/ch(\d+)",  # Date and chapter
                    href,
                )
                if match:
                    refs.append(
                        NoteRef(
                            ref_type="act",
                            href=href,
                            display_text=text,
                            act_date=match.group(1),
                            act_chapter=int(match.group(2)),
                        )
                    )

            # Parse /us/usc/tTITLE/sSECTION hrefs (US Code sections)
            elif "/us/usc/" in href:
                match = re.match(
                    r"/us/usc/t(\d+)/s([\w-]+)",  # Title and section
                    href,
                )
                if match:
                    refs.append(
                        NoteRef(
                            ref_type="usc_section",
                            href=href,
                            display_text=text,
                            usc_title=int(match.group(1)),
                            usc_section=match.group(2),
                        )
                    )

            # Parse /us/stat/VOLUME/PAGE hrefs (Statutes at Large)
            elif "/us/stat/" in href:
                match = re.match(r"/us/stat/(\d+)/(\d+)", href)
                if match:
                    refs.append(
                        NoteRef(
                            ref_type="statute",
                            href=href,
                            display_text=text,
                            stat_volume=int(match.group(1)),
                            stat_page=int(match.group(2)),
                        )
                    )

        return refs


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of text content.

    Args:
        text: Text to hash.

    Returns:
        Hexadecimal hash string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
