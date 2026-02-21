"""XML-native amendment parser for USLM Public Laws.

Parses amendments from GovInfo USLM XML using semantic tags
(<amendingAction>, <quotedText>, <ref>) instead of regex on plain text.
Falls back gracefully when XML structure is incomplete.
"""

import logging
import re
import xml.etree.ElementTree as ET

from app.models.enums import ChangeType
from pipeline.legal_parser.amendment_parser import (
    ParsedAmendment,
    PositionQualifier,
    PositionType,
    SectionReference,
)
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


# Characters to strip from quoted content boundaries.
_QUOTE_CHARS = '"\u201c\u201d\u2018\u2019\u0060\u00b4'


def _quoted_element_text(elem: ET.Element) -> str:
    """Get text of a ``<quotedText>`` or ``<quotedContent>`` element.

    Strips typographic quote characters from every text fragment, not just
    the outer boundary.  USLM XML often has ``"(1) ...`` inside child
    elements of ``<quotedContent>`` blocks.
    """
    parts: list[str] = []
    for fragment in elem.itertext():
        parts.append(fragment.lstrip(_QUOTE_CHARS))
    return "".join(parts).strip().rstrip(_QUOTE_CHARS)


# Tags whose text content should be excluded when extracting instruction prose.
_QUOTED_TAGS = frozenset({_tag("quotedText"), _tag("quotedContent")})


def _instruction_text(elem: ET.Element) -> str:
    """Get instruction prose, excluding ``<quotedText>`` / ``<quotedContent>``.

    This prevents subsection/paragraph mentions inside inserted or struck
    text from being mistaken for the amendment's target reference.
    """
    parts: list[str] = []

    def _walk(el: ET.Element) -> None:
        if el.tag in _QUOTED_TAGS:
            return
        if el.text:
            parts.append(el.text)
        for child in el:
            _walk(child)
            if child.tail:
                parts.append(child.tail)

    _walk(elem)
    return "".join(parts).strip()


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


_ACTION_TAG = _tag("amendingAction")

# Structural USLM elements that can contain sub-instructions.
_STRUCTURAL_TAGS = frozenset(
    _tag(n)
    for n in ("paragraph", "subparagraph", "clause", "subclause", "item", "subitem")
)


def _has_amending_action(elem: ET.Element) -> bool:
    """Return True if *elem* or any descendant contains an ``<amendingAction>``."""
    return any(True for _ in elem.iter(_ACTION_TAG))


def _is_redesignation(elem: ET.Element) -> bool:
    """Return True if *elem* text matches a redesignation pattern."""
    text = _element_text(elem).lower()
    return bool(re.search(r"\bby\s+(re)?designating\b", text))


def _find_leaf_instructions(
    elem: ET.Element, ancestor_prose: str = ""
) -> list[tuple[ET.Element, str]]:
    """Decompose a multi-part instruction into its leaf amendment groups.

    A "leaf" is the deepest structural element that contains
    ``<amendingAction>`` tags without having structural children that also
    contain ``<amendingAction>`` tags.

    Returns ``(leaf_element, ancestor_prose)`` pairs.  *ancestor_prose*
    accumulates ``<chapeau>`` / ``<num>`` text from parent structural
    elements so the leaf can inherit subsection context like "in paragraph (3)".
    """
    # Accumulate this element's chapeau / heading text for context.
    local_prose = ""
    for child in elem:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local in ("chapeau", "heading", "num"):
            local_prose += _instruction_text(child) + " "

    combined = ancestor_prose + local_prose

    # Check for structural children that carry their own amending actions.
    structural_kids = [
        child
        for child in elem
        if child.tag in _STRUCTURAL_TAGS and _has_amending_action(child)
    ]
    if structural_kids:
        leaves: list[tuple[ET.Element, str]] = []
        for kid in structural_kids:
            leaves.extend(_find_leaf_instructions(kid, combined))

        # Also capture structural siblings that have no <amendingAction>
        # but contain redesignation prose (e.g. "by designating...").
        # These are emitted as leaves so _parse_leaf can tag them with
        # a synthetic redesignate action.
        for child in elem:
            if (
                child.tag in _STRUCTURAL_TAGS
                and not _has_amending_action(child)
                and _is_redesignation(child)
            ):
                leaves.append((child, combined))
        return leaves

    if _has_amending_action(elem):
        return [(elem, combined)]
    return []


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

        # Find ALL elements with role="instruction" (section, subsection,
        # paragraph, etc.).  USLM places the attribute on whichever
        # structural element contains the amending instruction.
        for elem in root.iter():
            if elem.get("role") != "instruction":
                continue

            # Extract the section reference from the top-level instruction
            # (the <ref> tag lives here, not in the leaf sub-instructions).
            parent_ref = self._extract_section_ref(elem)

            # Decompose multi-part instructions into leaf amendment groups.
            for leaf, ancestor_prose in _find_leaf_instructions(elem):
                amendment = self._parse_leaf(leaf, xml_text, parent_ref, ancestor_prose)
                if amendment is not None:
                    amendments.append(amendment)

        return amendments

    def _parse_leaf(
        self,
        leaf: ET.Element,
        xml_text: str,
        parent_ref: SectionReference | None,
        ancestor_prose: str = "",
    ) -> ParsedAmendment | None:
        """Parse a leaf instruction element into a ParsedAmendment.

        The *parent_ref* carries the section reference extracted from the
        top-level ``role="instruction"`` element.  *ancestor_prose* contains
        accumulated text from intermediate structural elements (e.g.
        "in paragraph (3)—") for refining the subsection path.
        """
        content_text = _element_text(leaf)

        # --- Section reference (inherit from parent, refine locally) ---
        section_ref = self._refine_section_ref(parent_ref, leaf, ancestor_prose)

        # --- Action types ---
        action_types: set[str] = set()
        for action_elem in leaf.iter(_ACTION_TAG):
            atype = action_elem.get("type")
            if atype:
                action_types.add(atype)

        if not action_types:
            # Synthetic redesignate action for paragraphs with no
            # <amendingAction> but redesignation prose.
            if _is_redesignation(leaf):
                action_types = {"redesignate"}
            else:
                return None

        pattern_type, change_type = _classify_actions(action_types)

        # --- Quoted text ---
        quoted_texts, old_text, new_text = self._extract_old_new(leaf)

        # --- Position qualifier ---
        position_qualifier = self._extract_position_qualifier(
            leaf, quoted_texts, old_text, new_text
        )

        # --- Position in source XML (byte-level approximation) ---
        start_pos, end_pos = self._find_section_positions(leaf, xml_text)

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
            position_qualifier=position_qualifier,
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
                    if ref.subsection_path is None:
                        ref = self._augment_subsection(ref, section)
                    return ref

        # Fallback: parse plain text content
        content_text = _element_text(section)
        return _parse_section_from_text(content_text, self.default_title)

    def _refine_section_ref(
        self,
        parent_ref: SectionReference | None,
        leaf: ET.Element,
        ancestor_prose: str = "",
    ) -> SectionReference | None:
        """Refine *parent_ref* using ancestor and leaf text.

        For a leaf like ``(A) in subparagraph (B), by striking...`` whose
        ancestor prose is ``in paragraph (3)—``, this produces § 1839(3)(B).
        """
        if parent_ref is None:
            return self._extract_section_ref(leaf)

        if parent_ref.subsection_path is not None:
            return parent_ref

        # Combine ancestor context ("in paragraph (3)—") with the leaf's
        # own prose ("in subparagraph (B), by striking...").
        leaf_prose = _instruction_text(leaf)
        combined = ancestor_prose + " " + leaf_prose

        path_parts = self._extract_subsection_parts(combined)
        if not path_parts:
            return parent_ref

        return SectionReference(
            title=parent_ref.title,
            section=parent_ref.section,
            subsection_path="".join(path_parts),
        )

    @staticmethod
    def _extract_subsection_parts(prose: str) -> list[str]:
        """Extract subsection path parts like ``(3)(B)`` from instruction prose.

        Looks for patterns like "in paragraph (3)", "in subparagraph (B)",
        "subsection (b)(1)".  Returns path components in order found.
        """
        parts: list[str] = []
        for m in re.finditer(
            r"(?:subsection|paragraph|subparagraph)" r"((?:\s*\([a-zA-Z0-9]+\))+)",
            prose,
        ):
            parts.append(m.group(1).strip())
        return parts

    @staticmethod
    def _augment_subsection(
        ref: SectionReference, section: ET.Element
    ) -> SectionReference:
        """Try to fill in ``subsection_path`` from the instruction text.

        Common legislative patterns:
        - "is amended by striking subsection (b)"
        - "in subsection (c)(1), by striking..."
        - "in paragraph (3)(A), by striking..."

        Searches only the instruction's own prose (excluding quoted content)
        to avoid picking up subsection mentions from inserted text.

        For multi-part amendments ("is amended— (1) ... (2) ..."), the
        individual sub-targets are too granular — the section-level
        reference is kept instead.
        """
        prose = _instruction_text(section)

        # Find "is amended" anchor
        amended_pos = prose.find("is amended")
        if amended_pos < 0:
            return ref

        # Text after "is amended" — stop at a list marker like "—(1)" or
        # em-dash + parenthetical which signals a multi-part amendment.
        after = prose[amended_pos:]
        list_marker = re.search(r"\u2014\s*\(\d+\)", after)
        if list_marker:
            after = after[: list_marker.start()]

        m = re.search(
            r"(?:subsection|paragraph|subparagraph)" r"((?:\s*\([a-zA-Z0-9]+\))+)",
            after,
        )
        if m:
            return SectionReference(
                title=ref.title,
                section=ref.section,
                subsection_path=m.group(1).strip(),
            )
        return ref

    def _extract_quoted_texts(self, section: ET.Element) -> list[str]:
        """Collect text from all ``<quotedText>`` and ``<quotedContent>`` elements.

        Strips leading/trailing typographic quote characters that appear as
        formatting artifacts inside the XML.  For ``<quotedContent>`` blocks,
        inner child elements may also carry leading quote characters (e.g.
        ``"(1) ...``), so all text within the block is cleaned.
        """
        texts: list[str] = []
        for tag_name in ("quotedText", "quotedContent"):
            for elem in section.iter(_tag(tag_name)):
                text = _quoted_element_text(elem)
                if text:
                    texts.append(text)
        return texts

    def _extract_old_new(
        self, section: ET.Element
    ) -> tuple[list[str], str | None, str | None]:
        """Walk the element tree in document order to pair quoted texts with
        the preceding ``<amendingAction>`` type.

        Returns ``(all_quoted_texts, old_text, new_text)``.
        """
        action_tag = _tag("amendingAction")
        quoted_tags = {_tag("quotedText"), _tag("quotedContent")}

        # Collect (action_context, text) pairs in document order.
        last_action: str | None = None
        pairs: list[tuple[str | None, str]] = []

        for elem in section.iter():
            if elem.tag == action_tag:
                atype = elem.get("type")
                if atype:
                    last_action = atype
            elif elem.tag in quoted_tags:
                text = _quoted_element_text(elem)
                if text:
                    pairs.append((last_action, text))

        all_texts = [text for _, text in pairs]
        if not pairs:
            return all_texts, None, None

        # Assign old/new based on action context of each quoted text.
        old_text: str | None = None
        new_text: str | None = None
        for action, text in pairs:
            if action in ("delete", "substitute") and old_text is None:
                old_text = text
            elif (
                action in ("insert", "add", "enact", "substitute") and new_text is None
            ):
                new_text = text

        # Fallback: if action context didn't resolve, use positional logic.
        if old_text is None and new_text is None:
            if len(pairs) >= 2:
                old_text = pairs[0][1]
                new_text = pairs[1][1]
            elif len(pairs) == 1:
                old_text = pairs[0][1]

        return all_texts, old_text, new_text

    def _extract_position_qualifier(
        self,
        leaf: ET.Element,
        all_quoted_texts: list[str],
        old_text: str | None,
        new_text: str | None,
    ) -> PositionQualifier | None:
        """Extract positional context from instruction prose.

        Detects patterns like "at the end", "after <quotedText>",
        "before <quotedText>", "each place", and unquoted targets
        like "striking the period at the end".

        Returns a PositionQualifier or None if no positional context found.
        """
        prose = _instruction_text(leaf)
        prose_lower = prose.lower()

        # 1. "each place" → EACH_PLACE
        if re.search(r"each place", prose_lower):
            return PositionQualifier(type=PositionType.EACH_PLACE)

        # 2/3. "after <quotedText>" or "before <quotedText>" → AFTER/BEFORE
        #   Walk the element tree to find "after"/"before" keywords preceding
        #   a <quotedText> whose content differs from old_text/new_text.
        anchor = self._find_anchor_text(leaf, all_quoted_texts, old_text, new_text)
        if anchor is not None:
            return anchor

        # 2b. Plain-text "after/before subsection (X)" without <quotedText>
        m = re.search(
            r"\b(after|before)\s+subsection\s+\(([a-zA-Z0-9]+)\)", prose_lower
        )
        if m:
            pos_type = (
                PositionType.AFTER if m.group(1) == "after" else PositionType.BEFORE
            )
            return PositionQualifier(type=pos_type, anchor_text=f"({m.group(2)})")

        # 4. Unquoted target: "striking the period at the end" (no quotedText for old)
        if old_text is None:
            m = re.search(r"striking\s+(the\s+\w+(?:\s+at the end)?)", prose_lower)
            if m:
                return PositionQualifier(
                    type=PositionType.UNQUOTED_TARGET,
                    target_text=m.group(1),
                )

        # 5. "at the end" (catch-all after ruling out above)
        if "at the end" in prose_lower:
            return PositionQualifier(type=PositionType.AT_END)

        return None

    @staticmethod
    def _find_anchor_text(
        leaf: ET.Element,
        all_quoted_texts: list[str],  # noqa: ARG004 - reserved for future heuristics
        old_text: str | None,
        new_text: str | None,
    ) -> PositionQualifier | None:
        """Find BEFORE/AFTER anchor by walking the element tree.

        Looks for "after" or "before" keywords in text preceding a
        <quotedText> element whose content is neither old_text nor new_text
        (i.e., it's an anchor reference, not the amendment payload).
        """
        action_tag = _tag("amendingAction")
        quoted_tag = _tag("quotedText")
        known_texts = {t for t in (old_text, new_text) if t}

        # Collect text fragments and quoted elements in document order.
        # We look for the pattern: ...keyword... <quotedText>anchor</quotedText>
        prev_text = ""
        for elem in leaf.iter():
            if elem.tag == quoted_tag:
                text = _quoted_element_text(elem)
                if text and text not in known_texts:
                    # Strip quote characters before checking for keywords
                    cleaned = prev_text.rstrip(_QUOTE_CHARS + " \t\n")
                    cleaned_lower = cleaned.lower()
                    if re.search(r"\bafter$", cleaned_lower):
                        return PositionQualifier(
                            type=PositionType.AFTER,
                            anchor_text=text,
                        )
                    if re.search(r"\bbefore$", cleaned_lower):
                        return PositionQualifier(
                            type=PositionType.BEFORE,
                            anchor_text=text,
                        )
                # Reset accumulated text after any quoted element
                prev_text = elem.tail or ""
            elif elem.tag == action_tag:
                # Action elements contribute their text + tail
                prev_text += (elem.text or "") + " " + (elem.tail or "")
            else:
                if elem.text and elem.tag != leaf.tag:
                    prev_text += elem.text
                if elem.tail:
                    prev_text += elem.tail

        return None

    def _find_section_positions(
        self, section: ET.Element, xml_text: str
    ) -> tuple[int, int]:
        """Approximate the start/end positions of an instruction element in the raw XML.

        Uses the element's ``identifier`` attribute to locate it.
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
                # Derive end tag from the element's actual tag name
                # (may be section, subsection, paragraph, etc.)
                local_name = (
                    section.tag.split("}")[-1] if "}" in section.tag else section.tag
                )
                end_marker = f"</{local_name}>"
                ns_end = f"</{section.tag}>"
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
