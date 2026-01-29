"""Legal language parser for extracting amendment patterns from Public Laws."""

from pipeline.legal_parser.amendment_parser import (
    AmendmentParser,
    ParsedAmendment,
    SectionReference,
)
from pipeline.legal_parser.patterns import AMENDMENT_PATTERNS, PatternType
from pipeline.legal_parser.text_accounting import (
    AMENDMENT_KEYWORDS,
    ClaimedSpan,
    CoverageReport,
    TextAccountant,
    UnclaimedSpan,
)

__all__ = [
    # Parser
    "AmendmentParser",
    "ParsedAmendment",
    "SectionReference",
    "AMENDMENT_PATTERNS",
    "PatternType",
    # Text Accounting (Task 1.11)
    "TextAccountant",
    "ClaimedSpan",
    "UnclaimedSpan",
    "CoverageReport",
    "AMENDMENT_KEYWORDS",
]
