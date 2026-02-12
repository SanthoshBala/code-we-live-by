"""Tests for the XML-native amendment parser (USLM)."""

from pathlib import Path

import pytest

from app.models.enums import ChangeType
from pipeline.legal_parser.parsing_modes import _is_uslm_xml
from pipeline.legal_parser.patterns import PatternType
from pipeline.legal_parser.xml_parser import (
    XMLAmendmentParser,
    _classify_actions,
    _parse_ref_href,
)

# Path to the cached PL 113-22 XML fixture
_PL113_22_XML = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "govinfo"
    / "plaw"
    / "PLAW-113publ22.xml"
)

_skip_no_fixture = pytest.mark.skipif(
    not _PL113_22_XML.exists(),
    reason="Cached PL 113-22 XML not available (run seed-laws first)",
)


def _load_pl113_22() -> str:
    return _PL113_22_XML.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Full-law integration test
# ---------------------------------------------------------------------------


@_skip_no_fixture
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
