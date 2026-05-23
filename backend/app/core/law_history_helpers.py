"""Pure helper functions for classifying and titling legislative history events.

Shared between app/crud/public_law.py (live API path) and
pipeline/congress/law_history_ingestion.py (DB seeding path).
"""

from __future__ import annotations

import re


def compose_sponsor_name(
    first_name: str | None,
    middle_name: str | None,
    last_name: str | None,
) -> str | None:
    """Build a clean 'First [Middle] Last' display name from structured parts.

    Returns None when all parts are absent. Normalises ALL-CAPS names that
    the Congress.gov API occasionally returns (e.g. "DON", "YOUNG").
    """
    parts = [p for p in (first_name, middle_name, last_name) if p]
    if not parts:
        return None
    name = " ".join(parts)
    # Normalise if every alphabetic character is uppercase.
    if name.replace(".", "").replace(" ", "").isupper():
        name = name.title()
    return name


# Matches vote tallies like "392 - 17 - 26" or "95 - 0" in action text.
VOTE_TALLY_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)(?:\s*[-–]\s*(\d+))?")

PASSAGE_KEYWORDS = frozenset(["passed", "agreed to", "adopted", "concurred in"])


def parse_vote_tally(text: str) -> tuple[int | None, int | None, int | None]:
    """Extract yeas, nays, not_voting from action text. Returns (None,None,None) on miss."""
    m = VOTE_TALLY_RE.search(text)
    if not m:
        return None, None, None
    yeas = int(m.group(1))
    nays = int(m.group(2))
    not_voting = int(m.group(3)) if m.group(3) is not None else None
    return yeas, nays, not_voting


def is_passage_text(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in PASSAGE_KEYWORDS)


def classify_action(
    action_type: str | None,
    text: str,
    chamber: str | None,
    seen_intro: bool,
    seen_committee: bool,
) -> tuple[str, bool]:
    """Map a Congress.gov action to (event_type, is_milestone)."""
    lower = text.lower()
    atype = (action_type or "").lower()

    if atype == "president":
        return "presidential_action", True

    if atype == "introreferral":
        if "introduced" in lower:
            return "introduced", not seen_intro
        if "referred" in lower:
            return "committee_referral", not seen_committee
        return "other", False

    if atype == "committee":
        return "committee_referral", not seen_committee

    if atype == "floor":
        if chamber == "House" and is_passage_text(lower):
            return "house_vote", True
        if chamber == "Senate" and is_passage_text(lower):
            return "senate_vote", True
        return "other", False

    return "other", False


def build_event_title(event_type: str, text: str, chamber: str | None) -> str:
    """Build a short human-readable title for a timeline event."""
    if event_type == "introduced":
        ch = f" in the {chamber}" if chamber else ""
        return f"Bill introduced{ch}"
    if event_type == "committee_referral":
        return "Referred to committee"
    if event_type == "house_vote":
        return "Passed the House"
    if event_type == "senate_vote":
        return "Passed the Senate"
    if event_type == "presidential_action":
        lower = text.lower()
        if "vetoed" in lower or "veto" in lower:
            return "Vetoed by the President"
        if "signed" in lower or "became" in lower:
            return "Signed into law"
        return "Presidential action"
    return text[:80] if text else "Legislative action"
