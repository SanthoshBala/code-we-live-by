"""Text accounting for legal parser coverage tracking (Task 1.11).

This module provides the TextAccountant class that tracks which portions
of a law's text have been claimed by pattern matches, detects unclaimed
spans that may contain amendments, and generates coverage reports.
"""

import json
import re
from dataclasses import dataclass, field

# Keywords that suggest amendment content in unclaimed text
AMENDMENT_KEYWORDS = [
    "amended",
    "amending",
    "striking",
    "inserting",
    "adding",
    "repealed",
    "redesignated",
    "transferred",
    "substituting",
    "deleted",
    "removed",
    "modified",
    "replaced",
    "paragraph",
    "subsection",
    "section",
    "subparagraph",
    "clause",
]


@dataclass
class ClaimedSpan:
    """A span of text claimed by a pattern match."""

    start_pos: int
    end_pos: int
    amendment_id: int
    pattern_name: str


@dataclass
class UnclaimedSpan:
    """A span of text not claimed by any pattern."""

    start_pos: int
    end_pos: int
    text: str
    contains_keywords: bool = False
    detected_keywords: list[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Report on text coverage from parsing."""

    total_length: int
    claimed_length: int
    coverage_percentage: float
    claimed_spans: list[ClaimedSpan]
    unclaimed_spans: list[UnclaimedSpan]
    flagged_unclaimed: list[UnclaimedSpan]
    ignored_unclaimed: list[UnclaimedSpan]


class TextAccountant:
    """Tracks text coverage and detects unclaimed spans with potential amendments.

    The accountant maintains a list of claimed spans and can identify gaps
    that may contain unrecognized amendments based on keyword detection.

    Example usage:
        accountant = TextAccountant(law_text)
        for amendment in parsed_amendments:
            accountant.claim_span(amendment.start_pos, amendment.end_pos,
                                 amendment_id, amendment.pattern_name)
        report = accountant.generate_coverage_report()
    """

    def __init__(self, text: str):
        """Initialize the accountant with the full text to track.

        Args:
            text: The full text of the law to track coverage for.
        """
        self.text = text
        self.total_length = len(text)
        self._claimed_spans: list[ClaimedSpan] = []
        self._keyword_pattern = self._build_keyword_pattern()

    def _build_keyword_pattern(self) -> re.Pattern:
        """Build a compiled regex pattern for keyword detection."""
        # Create a pattern that matches any of the keywords (case insensitive)
        keywords_regex = "|".join(re.escape(kw) for kw in AMENDMENT_KEYWORDS)
        return re.compile(rf"\b({keywords_regex})\b", re.IGNORECASE)

    def claim_span(
        self, start_pos: int, end_pos: int, amendment_id: int, pattern_name: str
    ) -> None:
        """Mark a span of text as claimed by a pattern match.

        Args:
            start_pos: Start position in text.
            end_pos: End position in text.
            amendment_id: ID of the amendment that claimed this span.
            pattern_name: Name of the pattern that matched.

        Raises:
            ValueError: If positions are invalid.
        """
        if start_pos < 0 or end_pos > self.total_length:
            raise ValueError(
                f"Span positions out of bounds: {start_pos}-{end_pos} "
                f"(text length: {self.total_length})"
            )
        if end_pos <= start_pos:
            raise ValueError(
                f"Invalid span: end ({end_pos}) must be > start ({start_pos})"
            )

        self._claimed_spans.append(
            ClaimedSpan(
                start_pos=start_pos,
                end_pos=end_pos,
                amendment_id=amendment_id,
                pattern_name=pattern_name,
            )
        )

    def get_claimed_spans(self) -> list[ClaimedSpan]:
        """Get all claimed spans, sorted by position."""
        return sorted(self._claimed_spans, key=lambda s: s.start_pos)

    def get_unclaimed_spans(self, min_length: int = 10) -> list[UnclaimedSpan]:
        """Get spans of text not claimed by any pattern.

        Args:
            min_length: Minimum length of unclaimed span to return.
                       Shorter spans are likely just whitespace/punctuation.

        Returns:
            List of unclaimed spans, sorted by position.
        """
        if not self._claimed_spans:
            # Everything is unclaimed
            text = self.text
            if len(text) >= min_length:
                return [UnclaimedSpan(start_pos=0, end_pos=len(text), text=text)]
            return []

        # Sort claimed spans by start position
        sorted_claims = sorted(self._claimed_spans, key=lambda s: s.start_pos)

        # Merge overlapping claims
        merged_claims = self._merge_overlapping_spans(sorted_claims)

        unclaimed: list[UnclaimedSpan] = []
        current_pos = 0

        for claim in merged_claims:
            if claim.start_pos > current_pos:
                # Gap before this claim
                gap_text = self.text[current_pos : claim.start_pos]
                if len(gap_text.strip()) >= min_length:
                    unclaimed.append(
                        UnclaimedSpan(
                            start_pos=current_pos,
                            end_pos=claim.start_pos,
                            text=gap_text,
                        )
                    )
            current_pos = max(current_pos, claim.end_pos)

        # Check for gap at end
        if current_pos < self.total_length:
            gap_text = self.text[current_pos:]
            if len(gap_text.strip()) >= min_length:
                unclaimed.append(
                    UnclaimedSpan(
                        start_pos=current_pos,
                        end_pos=self.total_length,
                        text=gap_text,
                    )
                )

        return unclaimed

    def _merge_overlapping_spans(
        self, sorted_spans: list[ClaimedSpan]
    ) -> list[ClaimedSpan]:
        """Merge overlapping claimed spans."""
        if not sorted_spans:
            return []

        merged: list[ClaimedSpan] = [sorted_spans[0]]

        for span in sorted_spans[1:]:
            last = merged[-1]
            if span.start_pos <= last.end_pos:
                # Overlapping - extend the last span
                merged[-1] = ClaimedSpan(
                    start_pos=last.start_pos,
                    end_pos=max(last.end_pos, span.end_pos),
                    amendment_id=last.amendment_id,
                    pattern_name=last.pattern_name,
                )
            else:
                merged.append(span)

        return merged

    def check_unclaimed_for_keywords(self, span: UnclaimedSpan) -> UnclaimedSpan:
        """Check if an unclaimed span contains amendment keywords.

        Args:
            span: The unclaimed span to check.

        Returns:
            Updated span with keyword detection results.
        """
        matches = self._keyword_pattern.findall(span.text)
        if matches:
            span.contains_keywords = True
            # Normalize to lowercase and deduplicate
            span.detected_keywords = list({m.lower() for m in matches})
        return span

    def generate_coverage_report(
        self, min_unclaimed_length: int = 10
    ) -> CoverageReport:
        """Generate a comprehensive coverage report.

        Args:
            min_unclaimed_length: Minimum length for unclaimed spans.

        Returns:
            CoverageReport with all statistics.
        """
        claimed_spans = self.get_claimed_spans()

        # Calculate claimed length (accounting for overlaps)
        merged = self._merge_overlapping_spans(claimed_spans)
        claimed_length = sum(s.end_pos - s.start_pos for s in merged)

        # Calculate coverage percentage
        coverage_percentage = (
            (claimed_length / self.total_length * 100) if self.total_length > 0 else 0.0
        )

        # Get and classify unclaimed spans
        unclaimed_spans = self.get_unclaimed_spans(min_length=min_unclaimed_length)
        flagged: list[UnclaimedSpan] = []
        ignored: list[UnclaimedSpan] = []

        for span in unclaimed_spans:
            self.check_unclaimed_for_keywords(span)
            if span.contains_keywords:
                flagged.append(span)
            else:
                ignored.append(span)

        return CoverageReport(
            total_length=self.total_length,
            claimed_length=claimed_length,
            coverage_percentage=round(coverage_percentage, 2),
            claimed_spans=claimed_spans,
            unclaimed_spans=unclaimed_spans,
            flagged_unclaimed=flagged,
            ignored_unclaimed=ignored,
        )

    def to_json(self, include_text: bool = False) -> str:
        """Serialize claimed spans to JSON.

        Args:
            include_text: Whether to include the claimed text in output.

        Returns:
            JSON string of claimed spans.
        """
        data = {
            "total_length": self.total_length,
            "claimed_spans": [
                {
                    "start_pos": s.start_pos,
                    "end_pos": s.end_pos,
                    "amendment_id": s.amendment_id,
                    "pattern_name": s.pattern_name,
                    **(
                        {"text": self.text[s.start_pos : s.end_pos]}
                        if include_text
                        else {}
                    ),
                }
                for s in self.get_claimed_spans()
            ],
        }
        return json.dumps(data, indent=2)
