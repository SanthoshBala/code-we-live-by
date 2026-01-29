"""SQLAlchemy ENUM types for the database schema."""

import enum


class LawType(str, enum.Enum):
    """Type of law (Public or Private)."""

    PUBLIC = "Public"
    PRIVATE = "Private"


class BillType(str, enum.Enum):
    """Type of congressional bill."""

    HR = "HR"  # House Bill
    S = "S"  # Senate Bill
    HJRES = "HJRES"  # House Joint Resolution
    SJRES = "SJRES"  # Senate Joint Resolution
    HCONRES = "HCONRES"  # House Concurrent Resolution
    SCONRES = "SCONRES"  # Senate Concurrent Resolution
    HRES = "HRES"  # House Simple Resolution
    SRES = "SRES"  # Senate Simple Resolution


class BillStatus(str, enum.Enum):
    """Status of a bill in Congress."""

    INTRODUCED = "Introduced"
    IN_COMMITTEE = "In_Committee"
    REPORTED_BY_COMMITTEE = "Reported_by_Committee"
    PASSED_HOUSE = "Passed_House"
    PASSED_SENATE = "Passed_Senate"
    RESOLVING_DIFFERENCES = "Resolving_Differences"
    TO_PRESIDENT = "To_President"
    BECAME_LAW = "Became_Law"
    FAILED = "Failed"
    VETOED = "Vetoed"
    VETO_OVERRIDDEN = "Veto_Overridden"
    POCKET_VETOED = "Pocket_Vetoed"
    DIED_IN_COMMITTEE = "Died_in_Committee"
    WITHDRAWN = "Withdrawn"


class ChangeType(str, enum.Enum):
    """Type of change made to a section of law."""

    ADD = "Add"
    DELETE = "Delete"
    MODIFY = "Modify"
    REPEAL = "Repeal"
    REDESIGNATE = "Redesignate"
    TRANSFER = "Transfer"


class LineType(str, enum.Enum):
    """Type of line in a section."""

    HEADING = "Heading"
    PROSE = "Prose"
    LIST_ITEM = "ListItem"


class Chamber(str, enum.Enum):
    """Congressional chamber."""

    HOUSE = "House"
    SENATE = "Senate"


class VoteType(str, enum.Enum):
    """Type of vote cast."""

    YEA = "Yea"
    NAY = "Nay"
    PRESENT = "Present"
    NOT_VOTING = "Not_Voting"
    PAIRED_YEA = "Paired_Yea"
    PAIRED_NAY = "Paired_Nay"


class SponsorshipRole(str, enum.Enum):
    """Role in sponsoring legislation."""

    SPONSOR = "Sponsor"
    COSPONSOR = "Cosponsor"


class ReferenceType(str, enum.Enum):
    """Type of cross-reference between sections."""

    EXPLICIT_CITATION = "Explicit_Citation"
    CROSS_REFERENCE = "Cross_Reference"
    SUBJECT_TO = "Subject_To"
    CONDITIONAL = "Conditional"
    EXCEPTION = "Exception"
    INCORPORATION = "Incorporation"


class PoliticalParty(str, enum.Enum):
    """Political party affiliation."""

    DEMOCRAT = "Democrat"
    REPUBLICAN = "Republican"
    INDEPENDENT = "Independent"
    LIBERTARIAN = "Libertarian"
    GREEN = "Green"
    OTHER = "Other"


# =============================================================================
# Validation and Parsing Enums (Task 1.11)
# =============================================================================


class ParsingMode(str, enum.Enum):
    """Mode of parsing for legal text.

    Defines the level of automation and human oversight for parsing operations.
    """

    HUMAN_PLUS_LLM = "Human_Plus_LLM"  # Human + Claude review together
    LLM = "LLM"  # Claude autonomous with parser tools
    REGEX = "RegEx"  # Pure programmatic parsing


class ParsingSessionStatus(str, enum.Enum):
    """Status of a parsing session."""

    IN_PROGRESS = "In_Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ESCALATED = "Escalated"


class SpanType(str, enum.Enum):
    """Type of text span in coverage tracking."""

    CLAIMED = "Claimed"  # Matched by a pattern
    UNCLAIMED_FLAGGED = "Unclaimed_Flagged"  # Contains amendment keywords
    UNCLAIMED_IGNORED = "Unclaimed_Ignored"  # Boilerplate, no keywords


class AmendmentReviewStatus(str, enum.Enum):
    """Review status for parsed amendments."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CORRECTED = "Corrected"


class PatternDiscoveryStatus(str, enum.Enum):
    """Status of a discovered pattern in the learning loop."""

    NEW = "New"
    UNDER_REVIEW = "Under_Review"
    PROMOTED = "Promoted"
    REJECTED = "Rejected"
