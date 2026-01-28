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
