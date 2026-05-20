"""HTML parser for House Rules and Manual (HMAN) Rule X jurisdiction text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

# Maps the lowercased committee name as it appears in Rule X to the stable
# committee_code slug used in the Committee table. Includes historical name
# variants so the parser works across Congresses 106–119.
HOUSE_COMMITTEE_NAME_TO_CODE: dict[str, str] = {
    "agriculture": "house-agriculture",
    "appropriations": "house-appropriations",
    "armed services": "house-armed-services",
    "budget": "house-budget",
    "education and the workforce": "house-education-and-workforce",
    "education and labor": "house-education-and-workforce",
    "education and economic opportunities": "house-education-and-workforce",
    "energy and commerce": "house-energy-and-commerce",
    "ethics": "house-ethics",
    "standards of official conduct": "house-ethics",
    "financial services": "house-financial-services",
    "banking and financial services": "house-financial-services",
    "foreign affairs": "house-foreign-affairs",
    "international relations": "house-foreign-affairs",
    "homeland security": "house-homeland-security",
    "house administration": "house-administration",
    "intelligence (permanent select)": "house-intelligence",
    "permanent select committee on intelligence": "house-intelligence",
    "judiciary": "house-judiciary",
    "natural resources": "house-natural-resources",
    "resources": "house-natural-resources",
    "oversight and accountability": "house-oversight-and-accountability",
    "oversight and government reform": "house-oversight-and-accountability",
    "government reform": "house-oversight-and-accountability",
    "rules": "house-rules",
    "science, space, and technology": "house-science-space-technology",
    "science and technology": "house-science-space-technology",
    "science": "house-science-space-technology",
    "small business": "house-small-business",
    "transportation and infrastructure": "house-transportation-and-infrastructure",
    "public works and transportation": "house-transportation-and-infrastructure",
    "veterans' affairs": "house-veterans-affairs",
    "ways and means": "house-ways-and-means",
}


@dataclass
class CommitteeJurisdictionData:
    """Parsed jurisdiction data for a single committee from Rule X."""

    committee_name: str
    committee_code: str | None
    clause_letter: str
    rule_citation: str
    jurisdiction_items: list[str] = field(default_factory=list)

    @property
    def jurisdiction_text(self) -> str:
        """Numbered jurisdiction items joined as a single text block."""
        return "\n".join(
            f"({i + 1}) {item}" for i, item in enumerate(self.jurisdiction_items)
        )


def _normalize_committee_name(raw_name: str) -> str:
    """Normalize a committee name for lookup against HOUSE_COMMITTEE_NAME_TO_CODE."""
    # Strip "Committee on the", "Committee on", "Select Committee on", etc.
    name = raw_name.lower().strip()
    # Remove leading articles and qualifiers
    for prefix in (
        "permanent select committee on intelligence",
        "committee on the ",
        "committee on ",
        "select committee on ",
    ):
        if (
            name.startswith(prefix)
            and prefix != "permanent select committee on intelligence"
        ):
            name = name[len(prefix) :]
            break
    return name.strip().rstrip(".")


def _lookup_committee_code(raw_name: str) -> str | None:
    """Return the committee_code slug for a raw Rule X committee name, or None."""
    normalized = _normalize_committee_name(raw_name)
    # Try direct lookup first
    if normalized in HOUSE_COMMITTEE_NAME_TO_CODE:
        return HOUSE_COMMITTEE_NAME_TO_CODE[normalized]
    # Try full raw name lowercased (catches "Permanent Select Committee on Intelligence")
    raw_lower = raw_name.lower().strip().rstrip(".")
    if raw_lower in HOUSE_COMMITTEE_NAME_TO_CODE:
        return HOUSE_COMMITTEE_NAME_TO_CODE[raw_lower]
    return None


def parse_rule_x(html: str) -> list[CommitteeJurisdictionData]:
    """Parse Rule X committee jurisdiction text from a GovInfo HMAN HTM document.

    Args:
        html: Full HTML content of an HMAN-{congress}-houserules.htm page.

    Returns:
        List of CommitteeJurisdictionData, one per committee found in Rule X clause 1.
    """
    soup = BeautifulSoup(html, "lxml")

    # Locate the Rule X section. The HMAN HTM uses a <p> or <h2> element with
    # text like "RULE X" or "Rule X". We find it and then walk forward.
    rule_x_start: Tag | None = None
    for tag in soup.find_all(string=re.compile(r"^\s*RULE\s+X\.?\s*$", re.IGNORECASE)):
        parent = tag.parent
        if parent:
            rule_x_start = parent
            break

    if rule_x_start is None:
        return []

    results: list[CommitteeJurisdictionData] = []
    current: CommitteeJurisdictionData | None = None

    # Walk siblings after Rule X header until we hit Rule XI
    # Matches "(a) Committee on Agriculture." or "(a) Permanent Select Committee..."
    committee_header_pattern = re.compile(
        r"^\s*\(([a-z])\)\s+((?:Permanent\s+Select\s+)?(?:Committee\s+on\s+(?:the\s+)?)?.*?)\.?\s*$",
        re.IGNORECASE,
    )
    item_pattern = re.compile(r"^\s*\((\d+)\)\s+(.+)$", re.DOTALL)
    rule_xi_pattern = re.compile(r"^\s*RULE\s+XI\.?\s*$", re.IGNORECASE)

    for sibling in rule_x_start.next_siblings:
        if not isinstance(sibling, Tag):
            continue

        text = sibling.get_text(separator=" ", strip=True)

        # Stop at Rule XI
        if rule_xi_pattern.match(text):
            break

        # Check for a new committee clause like "(a) Committee on Agriculture."
        header_match = committee_header_pattern.match(text)
        if header_match and re.search(r"\bcommittee\b", text, re.IGNORECASE):
            if current is not None:
                results.append(current)

            letter = header_match.group(1)
            raw_name = header_match.group(2).strip().rstrip(".")
            code = _lookup_committee_code(raw_name)
            citation = f"House Rule X, Clause 1({letter})"
            current = CommitteeJurisdictionData(
                committee_name=raw_name,
                committee_code=code,
                clause_letter=letter,
                rule_citation=citation,
            )
            continue

        # Check for a numbered jurisdiction item "(1) Agriculture generally."
        if current is not None:
            item_match = item_pattern.match(text)
            if item_match:
                current.jurisdiction_items.append(item_match.group(2).strip())

    # Don't forget the last committee
    if current is not None:
        results.append(current)

    return results
