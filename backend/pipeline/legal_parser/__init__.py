"""Legal language parser for extracting amendment patterns from Public Laws."""

from pipeline.legal_parser.amendment_parser import (
    AmendmentParser,
    ParsedAmendment,
    SectionReference,
)
from pipeline.legal_parser.patterns import AMENDMENT_PATTERNS, PatternType
from pipeline.legal_parser.text_accounting import (
    ClaimedSpan,
    CoverageReport,
    TextAccountant,
    UnclaimedSpan,
)

__all__ = [
    # Parser
    "AmendmentParser",
    "XMLAmendmentParser",
    "ParsedAmendment",
    "SectionReference",
    "AMENDMENT_PATTERNS",
    "PatternType",
    # Text Accounting (Task 1.11)
    "TextAccountant",
    "ClaimedSpan",
    "UnclaimedSpan",
    "CoverageReport",
    # Law Change Pipeline (Task 1.12-1.13)
    "SectionResolver",
    "TextExtractor",
    "DiffGenerator",
    "LawChangeService",
]


# Lazy imports for Task 1.12-1.13 modules (avoid circular imports)
def __getattr__(name: str):
    if name == "SectionResolver":
        from pipeline.legal_parser.section_resolver import SectionResolver

        return SectionResolver
    elif name == "TextExtractor":
        from pipeline.legal_parser.text_extractor import TextExtractor

        return TextExtractor
    elif name == "DiffGenerator":
        from pipeline.legal_parser.diff_generator import DiffGenerator

        return DiffGenerator
    elif name == "LawChangeService":
        from pipeline.legal_parser.law_change_service import LawChangeService

        return LawChangeService
    elif name == "XMLAmendmentParser":
        from pipeline.legal_parser.xml_parser import XMLAmendmentParser

        return XMLAmendmentParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
