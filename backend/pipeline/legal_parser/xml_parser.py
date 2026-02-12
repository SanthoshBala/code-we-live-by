"""XML-native amendment parser for USLM Public Laws.

Parses amendments from GovInfo USLM XML using semantic tags
(<amendingAction>, <quotedText>, <ref>) instead of regex on plain text.
Falls back gracefully when XML structure is incomplete.
"""

import logging
import re
import xml.etree.ElementTree as ET

from app.models.enums import ChangeType
from pipeline.legal_parser.amendment_parser import ParsedAmendment, SectionReference
from pipeline.legal_parser.patterns import PatternType

logger = logging.getLogger(__name__)

# USLM namespace
NS = "http://schemas.gpo.gov/xml/uslm"
NSMAP = {"uslm": NS}


def _tag(local_name: str) -> str:
    """Return a fully-qualified USLM tag name."""
    return f"{{{NS}}}{local_name}"


# Map sets of amendingAction/@type values to (PatternType, ChangeType).
# Order matters: first match wins, so more-specific combos come first.
_ACTION_MAP: list[tuple[frozenset[str], PatternType, ChangeType]] = [
    (frozenset({"delete", "insert"}), PatternType.STRIKE_INSERT, ChangeType.MODIFY),
    (frozenset({"substitute"}), PatternType.SUBSTITUTE, ChangeType.MODIFY),
    (frozenset({"delete"}), PatternType.STRIKE, ChangeType.DELETE),
    (frozenset({"insert"}), PatternType.INSERT_NEW_TEXT, ChangeType.ADD),
    (frozenset({"repeal"}), PatternType.REPEAL, ChangeType.REPEAL),
    (frozenset({"repealAndReserve"}), PatternType.REPEAL, ChangeType.REPEAL),
    (frozenset({"redesignate"}), PatternType.REDESIGNATE, ChangeType.REDESIGNATE),
    (frozenset({"add"}), PatternType.ADD_SECTION, ChangeType.ADD),
    (frozenset({"enact"}), PatternType.ADD_SECTION, ChangeType.ADD),
]


def _classify_actions(
    action_types: set[str],
) -> tuple[PatternType, ChangeType]:
    """Map a set of amendingAction/@type values to PatternType and ChangeType.

    The ``amend`` type is a wrapper (e.g., "is amended by striking...")
    and is ignored when more-specific sub-actions are present.
    """
    # Strip the wrapper 'amend' when specific sub-actions exist
    specific = action_types - {"amend", "noChange", "conform", "unknown"}
    if not specific:
        # Only 'amend' (or nothing) → general amendment
        return PatternType.AMEND_GENERAL, ChangeType.MODIFY

    for required, pattern_type, change_type in _ACTION_MAP:
        if required <= specific:
            return pattern_type, change_type

    # Fallback
    return PatternType.AMEND_GENERAL, ChangeType.MODIFY


def _element_text(elem: ET.Element) -> str:
    """Get all text content of an element (including children), stripped."""
    return "".join(elem.itertext()).strip()


def _parse_ref_href(href: str) -> SectionReference | None:
    """Parse a USLM ``<ref href="...">`` into a SectionReference.

    Handles:
    - ``/us/usc/t26/s219``        → title=26, section="219"
    - ``/us/usc/t26/s219/c``      → title=26, section="219", subsection="(c)"
    - ``/us/usc/t42/s1395w-101``   → title=42, section="1395w-101"
    """
    m = re.match(r"/us/usc/t(\d+)/s([A-Za-z0-9._-]+)(?:/(.+))?", href)
    if not m:
        return None
    title = int(m.group(1))
    section = m.group(2)
    subsection_raw = m.group(3)
    subsection_path = None
    if subsection_raw:
        # Convert slash-delimited path like "c/1/A" → "(c)(1)(A)"
        parts = subsection_raw.split("/")
        subsection_path = "".join(f"({p})" for p in parts)
    return SectionReference(
        title=title, section=section, subsection_path=subsection_path
    )


def _parse_section_from_text(
    text: str, default_title: int | None
) -> SectionReference | None:
    """Fallback: extract a section reference from plain text content.

    Handles patterns like "section 219 of title 26" or "section 219 of the
    Internal Revenue Code".
    """
    m = re.search(
        r"[Ss]ection\s+(\d+[A-Za-z]?)"
        r"((?:\s*\([a-zA-Z0-9]+\))+)?"
        r"(?:\s+of\s+[Tt]itle\s+(\d+))?",
        text,
    )
    if not m:
        return None
    section = m.group(1)
    subsection = m.group(2)
    title_str = m.group(3)
    title = int(title_str) if title_str else default_title
    return SectionReference(
        title=title,
        section=section,
        subsection_path=subsection.strip() if subsection else None,
    )


class XMLAmendmentParser:
    """Parse amendments from USLM XML using semantic tags.

    Usage::

        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(xml_string)
    """

    def __init__(self, default_title: int | None = None):
        self.default_title = default_title

    def parse(self, xml_text: str) -> list[ParsedAmendment]:
        """Parse all amendments from a USLM XML string."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Failed to parse USLM XML: %s", exc)
            return []

        amendments: list[ParsedAmendment] = []

        # Find all <section role="instruction"> elements (recursive)
        for section_elem in root.iter(_tag("section")):
            if section_elem.get("role") != "instruction":
                continue

            amendment = self._parse_section(section_elem, xml_text)
            if amendment is not None:
                amendments.append(amendment)

        return amendments

    def _parse_section(
        self, section: ET.Element, xml_text: str
    ) -> ParsedAmendment | None:
        """Parse a single ``<section role="instruction">`` into a ParsedAmendment."""
        # Collect all text for full_match / context
        content_text = _element_text(section)

        # --- Section reference ---
        section_ref = self._extract_section_ref(section)

        # --- Action types ---
        action_types: set[str] = set()
        for action_elem in section.iter(_tag("amendingAction")):
            atype = action_elem.get("type")
            if atype:
                action_types.add(atype)

        if not action_types:
            # Not an amending instruction we can classify
            return None

        pattern_type, change_type = _classify_actions(action_types)

        # --- Quoted text ---
        quoted_texts = self._extract_quoted_texts(section)
        old_text, new_text = self._assign_old_new(quoted_texts, action_types)

        # --- Position in source XML (byte-level approximation) ---
        # Use the section's identifier or find its position in the raw XML
        start_pos, end_pos = self._find_section_positions(section, xml_text)

        # --- Confidence ---
        has_ref = section_ref is not None
        has_quotes = len(quoted_texts) > 0
        if has_ref and has_quotes:
            confidence = 0.98
        elif has_ref or has_quotes:
            confidence = 0.95
        else:
            confidence = 0.90

        # --- Needs review ---
        needs_review = self._needs_review(pattern_type, section_ref, old_text, new_text)

        # Pattern name reflects XML source
        pattern_name = f"xml_{pattern_type.value}"

        return ParsedAmendment(
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            change_type=change_type,
            section_ref=section_ref,
            old_text=old_text,
            new_text=new_text,
            full_match=content_text,
            confidence=confidence,
            start_pos=start_pos,
            end_pos=end_pos,
            needs_review=needs_review,
            context=content_text[:200],
            metadata={"source": "xml", "action_types": sorted(action_types)},
        )

    def _extract_section_ref(self, section: ET.Element) -> SectionReference | None:
        """Extract a SectionReference from ``<ref>`` tags or text fallback."""
        # Look for <ref href="/us/usc/t{title}/s{section}">
        for ref_elem in section.iter(_tag("ref")):
            href = ref_elem.get("href", "")
            if "/us/usc/" in href:
                ref = _parse_ref_href(href)
                if ref is not None:
                    return ref

        # Fallback: parse plain text content
        content_text = _element_text(section)
        return _parse_section_from_text(content_text, self.default_title)

    def _extract_quoted_texts(self, section: ET.Element) -> list[str]:
        """Collect text from all ``<quotedText>`` and ``<quotedContent>`` elements."""
        texts: list[str] = []
        for tag_name in ("quotedText", "quotedContent"):
            for elem in section.iter(_tag(tag_name)):
                text = _element_text(elem)
                if text:
                    texts.append(text)
        return texts

    def _assign_old_new(
        self, quoted_texts: list[str], action_types: set[str]
    ) -> tuple[str | None, str | None]:
        """Assign quoted texts to old_text / new_text based on action types.

        For strike-and-insert (delete + insert), the first quoted text is
        the old text and the second is the new text.
        """
        old_text: str | None = None
        new_text: str | None = None

        specific = action_types - {"amend"}
        if {"delete", "insert"} <= specific:
            # Strike and insert: first = old, second = new
            if len(quoted_texts) >= 2:
                old_text = quoted_texts[0]
                new_text = quoted_texts[1]
            elif len(quoted_texts) == 1:
                old_text = quoted_texts[0]
        elif "delete" in specific:
            if quoted_texts:
                old_text = quoted_texts[0]
        elif "insert" in specific or "add" in specific or "enact" in specific:
            if quoted_texts:
                new_text = quoted_texts[0]
        elif "substitute" in specific:
            if len(quoted_texts) >= 2:
                old_text = quoted_texts[0]
                new_text = quoted_texts[1]
            elif len(quoted_texts) == 1:
                new_text = quoted_texts[0]
        else:
            # Generic: best guess
            if len(quoted_texts) >= 2:
                old_text = quoted_texts[0]
                new_text = quoted_texts[1]
            elif len(quoted_texts) == 1:
                old_text = quoted_texts[0]

        return old_text, new_text

    def _find_section_positions(
        self, section: ET.Element, xml_text: str
    ) -> tuple[int, int]:
        """Approximate the start/end positions of a section in the raw XML.

        Uses the section's ``identifier`` attribute to locate it.
        Falls back to 0-based positions if not found.
        """
        identifier = section.get("identifier", "")
        if identifier:
            marker = f'identifier="{identifier}"'
            idx = xml_text.find(marker)
            if idx >= 0:
                # Walk backwards to find the opening '<'
                start = xml_text.rfind("<", 0, idx)
                if start < 0:
                    start = idx
                # Walk forward to find the closing '</section>'
                end_marker = "</section>"
                # Use namespace-qualified end tag as well
                ns_end = f"</{_tag('section')}"
                end = xml_text.find(end_marker, idx)
                if end < 0:
                    end = xml_text.find(ns_end, idx)
                if end >= 0:
                    end += len(end_marker)
                else:
                    end = min(idx + 500, len(xml_text))
                return start, end

        # Fallback: use the section's text to find approximate position
        content_text = _element_text(section)
        if content_text:
            snippet = content_text[:80]
            idx = xml_text.find(snippet)
            if idx >= 0:
                return idx, idx + len(content_text)

        return 0, 0

    def _needs_review(
        self,
        pattern_type: PatternType,
        section_ref: SectionReference | None,
        old_text: str | None,
        new_text: str | None,
    ) -> bool:
        """Determine if this amendment needs manual review."""
        if section_ref is None:
            return True

        # Strike-insert with both texts is high confidence
        if pattern_type == PatternType.STRIKE_INSERT and old_text and new_text:
            return False

        # Patterns that require downstream text extraction
        if pattern_type in (
            PatternType.ADD_SECTION,
            PatternType.ADD_SUBSECTION,
            PatternType.INSERT_NEW_TEXT,
            PatternType.INSERT_AFTER,
            PatternType.INSERT_BEFORE,
            PatternType.SUBSTITUTE,
        ):
            return True

        # General amendments without specific text
        return pattern_type == PatternType.AMEND_GENERAL
