"""SQLAlchemy models for The Code We Live By."""

from app.models.base import Base, TimestampMixin, async_session_maker, get_async_session
from app.models.enums import (
    AmendmentReviewStatus,
    BillStatus,
    BillType,
    Chamber,
    ChangeType,
    LawType,
    ParsingMode,
    ParsingSessionStatus,
    PatternDiscoveryStatus,
    PoliticalParty,
    ReferenceType,
    SpanType,
    SponsorshipRole,
    VerificationMethod,
    VerificationResult,
    VoteType,
)
from app.models.history import LineHistory, SectionHistory
from app.models.release_point import OLRCReleasePoint
from app.models.legislator import (
    IndividualVote,
    Legislator,
    LegislatorTerm,
    Sponsorship,
    Vote,
)
from app.models.public_law import Bill, LawChange, ProposedChange, PublicLaw
from app.models.supporting import (
    Amendment,
    BillCommitteeAssignment,
    Committee,
    DataCorrection,
    DataIngestionLog,
    SectionReference,
)
from app.models.us_code import (
    SectionGroup,
    USCodeLine,
    USCodeSection,
)
from app.models.validation import (
    IngestionReport,
    ParsedAmendmentRecord,
    ParsingSession,
    ParsingVerification,
    PatternDiscovery,
    TextSpan,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "async_session_maker",
    "get_async_session",
    # Enums
    "AmendmentReviewStatus",
    "BillStatus",
    "BillType",
    "Chamber",
    "ChangeType",
    "LawType",
    "ParsingMode",
    "ParsingSessionStatus",
    "PatternDiscoveryStatus",
    "PoliticalParty",
    "ReferenceType",
    "SpanType",
    "SponsorshipRole",
    "VoteType",
    # US Code
    "SectionGroup",
    "USCodeSection",
    "USCodeLine",
    # Public Law
    "PublicLaw",
    "Bill",
    "LawChange",
    "ProposedChange",
    # Legislator
    "Legislator",
    "LegislatorTerm",
    "Sponsorship",
    "Vote",
    "IndividualVote",
    # History
    "SectionHistory",
    "LineHistory",
    # Release Points (Task 1.12)
    "OLRCReleasePoint",
    # Supporting
    "SectionReference",
    "Committee",
    "BillCommitteeAssignment",
    "Amendment",
    "DataIngestionLog",
    "DataCorrection",
    # Validation (Task 1.11)
    "ParsingSession",
    "ParsingVerification",
    "TextSpan",
    "ParsedAmendmentRecord",
    "IngestionReport",
    "PatternDiscovery",
    "VerificationMethod",
    "VerificationResult",
]
