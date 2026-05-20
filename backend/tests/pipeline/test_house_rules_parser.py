"""Tests for the House Rules HMAN Rule X parser."""

from pipeline.house_rules.parser import (
    _lookup_committee_code,
    _normalize_committee_name,
    parse_rule_x,
)

# Minimal HMAN-style HTML fixture with two committees under Rule X.
_RULE_X_FIXTURE = """
<!DOCTYPE html>
<html>
<body>
<p>RULE IX</p>
<p>Some rule IX content.</p>
<p>RULE X</p>
<p>Committees and their legislative jurisdictions</p>
<p>(a) Committee on Agriculture.</p>
<p>(1) Adulteration of seeds, insect pests, and protection of birds and animals in forest reserves.</p>
<p>(2) Agriculture generally.</p>
<p>(3) Agricultural and industrial chemistry.</p>
<p>(b) Committee on the Judiciary.</p>
<p>(1) Bankruptcy, mutiny, espionage, and counterfeiting.</p>
<p>(2) Civil and criminal judicial proceedings in general.</p>
<p>(3) Federal courts and judges.</p>
<p>(4) Immigration policy and non-border enforcement.</p>
<p>(5) Patents, the Patent and Trademark Office, copyrights, and trademarks.</p>
<p>RULE XI</p>
<p>Some rule XI content — should not be parsed.</p>
<p>(c) Committee on Appropriations.</p>
</body>
</html>
"""

_PERMANENT_SELECT_FIXTURE = """
<!DOCTYPE html>
<html>
<body>
<p>RULE X</p>
<p>(a) Committee on Agriculture.</p>
<p>(1) Agriculture generally.</p>
<p>(k) Permanent Select Committee on Intelligence.</p>
<p>(1) Intelligence and intelligence-related activities of all departments and agencies of the Government.</p>
<p>(2) The Central Intelligence Agency, the Director of National Intelligence, and the National Intelligence Program.</p>
<p>RULE XI</p>
</body>
</html>
"""


class TestNormalizeCommitteeName:
    def test_strips_committee_on(self) -> None:
        assert _normalize_committee_name("Committee on Agriculture") == "agriculture"

    def test_strips_committee_on_the(self) -> None:
        assert _normalize_committee_name("Committee on the Judiciary") == "judiciary"

    def test_lowercase(self) -> None:
        assert (
            _normalize_committee_name("Committee on Ways and Means") == "ways and means"
        )

    def test_strips_trailing_period(self) -> None:
        assert _normalize_committee_name("Committee on Rules.") == "rules"


class TestLookupCommitteeCode:
    def test_agriculture(self) -> None:
        assert _lookup_committee_code("Agriculture") == "house-agriculture"

    def test_judiciary(self) -> None:
        assert _lookup_committee_code("Committee on the Judiciary") == "house-judiciary"

    def test_ways_and_means(self) -> None:
        assert _lookup_committee_code("Ways and Means") == "house-ways-and-means"

    def test_historical_name_oversight(self) -> None:
        assert (
            _lookup_committee_code("Oversight and Government Reform")
            == "house-oversight-and-accountability"
        )

    def test_historical_name_resources(self) -> None:
        assert _lookup_committee_code("Resources") == "house-natural-resources"

    def test_unknown_returns_none(self) -> None:
        assert _lookup_committee_code("Completely Unknown Committee Name") is None

    def test_permanent_select_intelligence(self) -> None:
        assert (
            _lookup_committee_code("Permanent Select Committee on Intelligence")
            == "house-intelligence"
        )


class TestParseRuleX:
    def test_returns_committees(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        assert (
            len(results) == 2
        )  # Agriculture and Judiciary (Appropriations is after Rule XI)

    def test_agriculture_committee(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        ag = results[0]
        assert "agriculture" in ag.committee_name.lower()
        assert ag.committee_code == "house-agriculture"
        assert ag.clause_letter == "a"
        assert ag.rule_citation == "House Rule X, Clause 1(a)"

    def test_agriculture_jurisdiction_items(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        ag = results[0]
        assert len(ag.jurisdiction_items) == 3
        assert "Agriculture generally" in ag.jurisdiction_items[1]

    def test_judiciary_committee(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        jud = results[1]
        assert jud.committee_code == "house-judiciary"
        assert jud.clause_letter == "b"

    def test_judiciary_has_five_items(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        jud = results[1]
        assert len(jud.jurisdiction_items) == 5

    def test_stops_at_rule_xi(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        codes = [r.committee_code for r in results]
        assert "house-appropriations" not in codes

    def test_no_rule_x_returns_empty(self) -> None:
        results = parse_rule_x("<html><body><p>No rules here.</p></body></html>")
        assert results == []

    def test_jurisdiction_text_property(self) -> None:
        results = parse_rule_x(_RULE_X_FIXTURE)
        ag = results[0]
        text = ag.jurisdiction_text
        assert "(1)" in text
        assert "Agriculture generally" in text

    def test_permanent_select_intelligence(self) -> None:
        results = parse_rule_x(_PERMANENT_SELECT_FIXTURE)
        intel = next(
            (r for r in results if r.committee_code == "house-intelligence"), None
        )
        assert intel is not None
        assert len(intel.jurisdiction_items) == 2

    def test_unknown_committee_name_code_is_none(self) -> None:
        html = """
        <html><body>
        <p>RULE X</p>
        <p>(z) Committee on Completely Unknown.</p>
        <p>(1) Some jurisdiction.</p>
        <p>RULE XI</p>
        </body></html>
        """
        results = parse_rule_x(html)
        assert len(results) == 1
        assert results[0].committee_code is None
        assert results[0].clause_letter == "z"
