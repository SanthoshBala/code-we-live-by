"""Tests for the XML-native amendment parser (USLM)."""

from pathlib import Path

import pytest

from app.models.enums import ChangeType
from pipeline.legal_parser.amendment_parser import PositionType
from pipeline.legal_parser.parsing_modes import _is_uslm_xml
from pipeline.legal_parser.patterns import PatternType
from pipeline.legal_parser.xml_parser import (
    XMLAmendmentParser,
    _classify_actions,
    _parse_ref_href,
)

# Path to cached XML fixtures
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "govinfo" / "plaw"

_PL113_22_XML = _DATA_DIR / "PLAW-113publ22.xml"
_PL114_153_XML = _DATA_DIR / "PLAW-114publ153.xml"

_skip_no_113_22 = pytest.mark.skipif(
    not _PL113_22_XML.exists(),
    reason="Cached PL 113-22 XML not available (run seed-laws first)",
)

_skip_no_114_153 = pytest.mark.skipif(
    not _PL114_153_XML.exists(),
    reason="Cached PL 114-153 XML not available (run seed-laws first)",
)


def _load_pl113_22() -> str:
    return _PL113_22_XML.read_text(encoding="utf-8")


def _load_pl114_153() -> str:
    return _PL114_153_XML.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Full-law integration test
# ---------------------------------------------------------------------------


@_skip_no_113_22
class TestParsePL113_22:
    """Integration tests using cached PL 113-22 XML."""

    def test_parse_finds_one_amendment(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        assert len(amendments) == 1

    def test_section_reference(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        ref = amendments[0].section_ref
        assert ref is not None
        assert ref.title == 26
        assert ref.section == "219"

    def test_action_types(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        a = amendments[0]
        assert a.pattern_type == PatternType.STRIKE_INSERT
        assert a.change_type == ChangeType.MODIFY

    def test_quoted_text(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        a = amendments[0]
        assert a.old_text is not None
        assert "Special Rules for Certain Married Individuals" in a.old_text
        assert a.new_text is not None
        assert "Kay Bailey Hutchison Spousal IRA" in a.new_text

    def test_confidence_high(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        # Has both <ref> and <quotedText> → 0.98
        assert amendments[0].confidence >= 0.95

    def test_pattern_name_prefix(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        assert amendments[0].pattern_name.startswith("xml_")

    def test_metadata_source(self) -> None:
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        assert amendments[0].metadata["source"] == "xml"
        assert "amend" in amendments[0].metadata["action_types"]

    def test_needs_review_false_for_strike_insert(self) -> None:
        """Strike-insert with both quoted texts should not need review."""
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        assert amendments[0].needs_review is False


@_skip_no_114_153
class TestParsePL114_153:
    """Integration tests using cached PL 114-153 XML.

    PL 114-153 (Defend Trade Secrets Act) uses ``role="instruction"`` on
    ``<subsection>`` and ``<paragraph>`` elements — not ``<section>``.
    """

    def test_parse_finds_amendments(self) -> None:
        parser = XMLAmendmentParser(default_title=18)
        amendments = parser.parse(_load_pl114_153())
        # Multi-part instructions are decomposed into leaf amendments.
        assert len(amendments) == 16

    def test_amendments_reference_title_18(self) -> None:
        parser = XMLAmendmentParser(default_title=18)
        amendments = parser.parse(_load_pl114_153())
        for a in amendments:
            assert a.section_ref is not None
            assert a.section_ref.title == 18

    def test_all_xml_source(self) -> None:
        parser = XMLAmendmentParser(default_title=18)
        amendments = parser.parse(_load_pl114_153())
        for a in amendments:
            assert a.metadata["source"] == "xml"
            assert a.pattern_name.startswith("xml_")

    def test_high_confidence(self) -> None:
        parser = XMLAmendmentParser(default_title=18)
        amendments = parser.parse(_load_pl114_153())
        for a in amendments:
            assert a.confidence >= 0.95


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


class TestParseRefHref:
    def test_basic_title_section(self) -> None:
        ref = _parse_ref_href("/us/usc/t26/s219")
        assert ref is not None
        assert ref.title == 26
        assert ref.section == "219"
        assert ref.subsection_path is None

    def test_with_subsection(self) -> None:
        ref = _parse_ref_href("/us/usc/t26/s219/c")
        assert ref is not None
        assert ref.title == 26
        assert ref.section == "219"
        assert ref.subsection_path == "(c)"

    def test_deep_subsection(self) -> None:
        ref = _parse_ref_href("/us/usc/t42/s1395w-101/a/1/A")
        assert ref is not None
        assert ref.title == 42
        assert ref.section == "1395w-101"
        assert ref.subsection_path == "(a)(1)(A)"

    def test_non_usc_href(self) -> None:
        ref = _parse_ref_href("/us/bill/113/hr/2289")
        assert ref is None


class TestClassifyActions:
    def test_delete_insert(self) -> None:
        pt, ct = _classify_actions({"amend", "delete", "insert"})
        assert pt == PatternType.STRIKE_INSERT
        assert ct == ChangeType.MODIFY

    def test_delete_only(self) -> None:
        pt, ct = _classify_actions({"delete"})
        assert pt == PatternType.STRIKE
        assert ct == ChangeType.DELETE

    def test_insert_only(self) -> None:
        pt, ct = _classify_actions({"insert"})
        assert pt == PatternType.INSERT_NEW_TEXT
        assert ct == ChangeType.ADD

    def test_repeal(self) -> None:
        pt, ct = _classify_actions({"repeal"})
        assert pt == PatternType.REPEAL
        assert ct == ChangeType.REPEAL

    def test_redesignate(self) -> None:
        pt, ct = _classify_actions({"redesignate"})
        assert pt == PatternType.REDESIGNATE
        assert ct == ChangeType.REDESIGNATE

    def test_substitute(self) -> None:
        pt, ct = _classify_actions({"substitute"})
        assert pt == PatternType.SUBSTITUTE
        assert ct == ChangeType.MODIFY

    def test_add(self) -> None:
        pt, ct = _classify_actions({"add"})
        assert pt == PatternType.ADD_SECTION
        assert ct == ChangeType.ADD

    def test_amend_only(self) -> None:
        pt, ct = _classify_actions({"amend"})
        assert pt == PatternType.AMEND_GENERAL
        assert ct == ChangeType.MODIFY

    def test_empty(self) -> None:
        pt, ct = _classify_actions(set())
        assert pt == PatternType.AMEND_GENERAL
        assert ct == ChangeType.MODIFY


class TestIsUslmXml:
    def test_uslm_xml(self) -> None:
        text = '<?xml version="1.0"?><pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
        assert _is_uslm_xml(text) is True

    def test_plain_text(self) -> None:
        assert _is_uslm_xml("Section 1. This act may be cited...") is False

    def test_non_uslm_xml(self) -> None:
        text = '<?xml version="1.0"?><html><body>Not USLM</body></html>'
        assert _is_uslm_xml(text) is False

    def test_whitespace_prefix(self) -> None:
        text = (
            '  \n <?xml version="1.0"?><pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
        )
        assert _is_uslm_xml(text) is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_non_xml_returns_empty(self) -> None:
        parser = XMLAmendmentParser()
        result = parser.parse("This is plain text, not XML.")
        assert result == []

    def test_empty_xml_no_instructions(self) -> None:
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            "<main><section><num>1</num></section></main>"
            "</pLaw>"
        )
        parser = XMLAmendmentParser()
        result = parser.parse(xml)
        assert result == []

    def test_instruction_without_amending_action(self) -> None:
        """Section with role=instruction but no amendingAction tags."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num><content>Some text</content>"
            "</section></main></pLaw>"
        )
        parser = XMLAmendmentParser()
        result = parser.parse(xml)
        assert result == []

    def test_subsection_role_instruction(self) -> None:
        """role=instruction on <subsection> should be found."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            "<main><section><num>2</num>"
            '<subsection role="instruction">'
            "<num>(a)</num>"
            "<content>Section 101 of title 42 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>old phrase</quotedText>" and '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new phrase</quotedText>".'
            "</content></subsection>"
            "</section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=42)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].old_text == "old phrase"
        assert result[0].new_text == "new phrase"
        assert result[0].pattern_type == PatternType.STRIKE_INSERT

    def test_subsection_augmented_from_text(self) -> None:
        """When <ref> has no subsection, text like 'subsection (b)' fills it in."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>"
            '<ref href="/us/usc/t18/s1836">Section 1836 of title 18</ref>, '
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            "subsection (b) and "
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new subsection text</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        ref = result[0].section_ref
        assert ref is not None
        assert ref.section == "1836"
        assert ref.subsection_path == "(b)"

    def test_multipart_decomposed_into_leaves(self) -> None:
        """Multi-part amendment with structural <paragraph> children is decomposed."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><subsection role="instruction">'
            "<num>(b)</num>"
            "<chapeau>"
            '<ref href="/us/usc/t18/s1839">Section 1839 of title 18</ref>, '
            '<amendingAction type="amend">is amended</amendingAction>'
            "\u2014</chapeau>"
            "<paragraph><num>(1)</num>"
            "<content>in paragraph (3), by "
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>old</quotedText>" and '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new</quotedText>".'
            "</content></paragraph>"
            "<paragraph><num>(2)</num>"
            "<content>by "
            '<amendingAction type="add">adding</amendingAction> '
            "at the end the following:"
            '<quotedContent>"(5) new definition.</quotedContent>.'
            "</content></paragraph>"
            "</subsection></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 2
        # First leaf: "in paragraph (3), by striking..."
        assert result[0].section_ref is not None
        assert result[0].section_ref.section == "1839"
        assert result[0].section_ref.subsection_path == "(3)"
        assert result[0].old_text == "old"
        assert result[0].new_text == "new"
        # Second leaf: "by adding..."
        assert result[1].section_ref is not None
        assert result[1].section_ref.section == "1839"
        assert result[1].new_text is not None
        assert result[1].new_text.startswith("(5)")

    def test_paragraph_role_instruction(self) -> None:
        """role=instruction on <paragraph> should be found."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            "<main><section><num>2</num>"
            "<subsection><num>(d)</num>"
            '<paragraph role="instruction">'
            "<num>(1)</num>"
            "<content>Section 200 of title 18 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>added text</quotedText>".'
            "</content></paragraph>"
            "</subsection></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].new_text == "added text"
        assert result[0].pattern_type == PatternType.INSERT_NEW_TEXT
        assert result[0].change_type == ChangeType.ADD

    def test_insert_only_quoted_text_assigned_as_new(self) -> None:
        """When strike-and-insert has only one quotedContent after 'insert',
        it should be new_text, not old_text."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>"
            '<ref href="/us/usc/t18/s1836">Section 1836 of title 18</ref>, '
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            "subsection (b) and "
            '<amendingAction type="insert">inserting</amendingAction> '
            "the following:"
            '<quotedContent>"(b) New subsection text.</quotedContent>.'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].old_text is None
        assert result[0].new_text is not None
        assert "New subsection text" in result[0].new_text

    def test_inner_quotes_stripped_from_quoted_content(self) -> None:
        """Typographic quotes inside child elements of quotedContent are stripped."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>"
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="insert">inserting</amendingAction> '
            "the following:"
            "<quotedContent>"
            '<paragraph>"(1) First paragraph.</paragraph>'
            '<paragraph>"(2) Second paragraph.</paragraph>'
            "</quotedContent>."
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].new_text is not None
        assert result[0].new_text.startswith("(1)")
        assert '"' not in result[0].new_text

    def test_default_title_used_as_fallback(self) -> None:
        """When no <ref> tag is present, fallback uses default_title."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>old</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=42)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].section_ref is not None
        assert result[0].section_ref.title == 42
        assert result[0].section_ref.section == "101"


# ---------------------------------------------------------------------------
# Position qualifier tests — unit tests with minimal XML snippets
# ---------------------------------------------------------------------------


class TestPositionQualifierUnit:
    """Unit tests for position qualifier extraction using minimal XML."""

    def test_at_end_strike(self) -> None:
        """'striking "X" at the end' → AT_END."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>and</quotedText>" at the end.'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].old_text == "and"
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.AT_END

    def test_at_end_add(self) -> None:
        """'adding at the end the following' → AT_END."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="add">adding</amendingAction> '
            "at the end the following:"
            '<quotedContent>"(5) new paragraph.</quotedContent>.'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].new_text is not None
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.AT_END

    def test_after_anchor(self) -> None:
        """'inserting "X" after "Y"' → AFTER with anchor_text."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new words</quotedText>" '
            'after "<quotedText>prohibit</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].new_text == "new words"
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.AFTER
        assert pq.anchor_text == "prohibit"

    def test_before_anchor(self) -> None:
        """'inserting "X" before "Y"' → BEFORE with anchor_text."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new clause,</quotedText>" '
            'before "<quotedText>section 1951</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].new_text == "new clause,"
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.BEFORE
        assert pq.anchor_text == "section 1951"

    def test_each_place(self) -> None:
        """'striking "X" each place such term appears' → EACH_PLACE."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>old term</quotedText>" each place such term '
            "appears and "
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new term</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].old_text == "old term"
        assert result[0].new_text == "new term"
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.EACH_PLACE

    def test_unquoted_target(self) -> None:
        """'striking the period at the end' (no quotedText) → UNQUOTED_TARGET."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            "the period at the end and "
            '<amendingAction type="insert">inserting</amendingAction> '
            "a semicolon."
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].old_text is None
        pq = result[0].position_qualifier
        assert pq is not None
        assert pq.type == PositionType.UNQUOTED_TARGET
        assert "the period" in pq.target_text

    def test_no_qualifier_for_simple_strike_insert(self) -> None:
        """Simple strike-and-insert with no positional context → None."""
        xml = (
            '<?xml version="1.0"?>'
            '<pLaw xmlns="http://schemas.gpo.gov/xml/uslm">'
            '<main><section role="instruction">'
            "<num>1</num>"
            "<content>Section 101 "
            '<amendingAction type="amend">is amended</amendingAction> by '
            '<amendingAction type="delete">striking</amendingAction> '
            '"<quotedText>old phrase</quotedText>" and '
            '<amendingAction type="insert">inserting</amendingAction> '
            '"<quotedText>new phrase</quotedText>".'
            "</content></section></main></pLaw>"
        )
        parser = XMLAmendmentParser(default_title=18)
        result = parser.parse(xml)
        assert len(result) == 1
        assert result[0].position_qualifier is None


# ---------------------------------------------------------------------------
# Position qualifier tests — integration with cached PL XML
# ---------------------------------------------------------------------------


@_skip_no_114_153
class TestPositionQualifierPL114_153:
    """Integration tests for position qualifiers using PL 114-153."""

    def _parse(self) -> list:
        parser = XMLAmendmentParser(default_title=18)
        return parser.parse(_load_pl114_153())

    def test_at_end_qualifier_strike_and(self) -> None:
        """§ 2(b)(1)(B): striking 'and' at the end → AT_END."""
        amendments = self._parse()
        # Find the amendment that strikes "and"
        matches = [
            a
            for a in amendments
            if a.old_text == "and" and a.position_qualifier is not None
        ]
        assert len(matches) >= 1
        pq = matches[0].position_qualifier
        assert pq.type == PositionType.AT_END

    def test_unquoted_target_period(self) -> None:
        """§ 2(b)(2): striking the period at the end → UNQUOTED_TARGET."""
        amendments = self._parse()
        matches = [
            a
            for a in amendments
            if a.position_qualifier is not None
            and a.position_qualifier.type == PositionType.UNQUOTED_TARGET
        ]
        assert len(matches) >= 1
        assert "the period" in matches[0].position_qualifier.target_text

    def test_add_at_end_qualifier(self) -> None:
        """§ 2(b)(3): adding at the end the following → AT_END."""
        amendments = self._parse()
        matches = [
            a
            for a in amendments
            if a.position_qualifier is not None
            and a.position_qualifier.type == PositionType.AT_END
            and a.new_text is not None
        ]
        assert len(matches) >= 1

    def test_after_anchor_prohibit(self) -> None:
        """§ 2(c): inserting ... after 'prohibit' → AFTER."""
        amendments = self._parse()
        matches = [
            a
            for a in amendments
            if a.position_qualifier is not None
            and a.position_qualifier.type == PositionType.AFTER
            and a.position_qualifier.anchor_text == "prohibit"
        ]
        assert len(matches) == 1
        assert "private right of action" in matches[0].new_text

    def test_before_anchor_section_1951(self) -> None:
        """§ 3(b): inserting ... before 'section 1951' → BEFORE."""
        amendments = self._parse()
        matches = [
            a
            for a in amendments
            if a.position_qualifier is not None
            and a.position_qualifier.type == PositionType.BEFORE
            and a.position_qualifier.anchor_text is not None
            and "section 1951" in a.position_qualifier.anchor_text
        ]
        assert len(matches) == 1
        assert "1831" in matches[0].new_text

    def test_no_qualifier_for_simple_strike_insert(self) -> None:
        """PL 113-22 has a simple strike/insert with no positional context."""
        parser = XMLAmendmentParser(default_title=26)
        amendments = parser.parse(_load_pl113_22())
        assert len(amendments) == 1
        assert amendments[0].position_qualifier is None
