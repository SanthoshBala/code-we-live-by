"""Tests for text accounting system (Task 1.11)."""

import pytest

from pipeline.legal_parser.text_accounting import (
    AMENDMENT_KEYWORDS,
    ClaimedSpan,
    TextAccountant,
    UnclaimedSpan,
)


class TestClaimedSpan:
    """Tests for ClaimedSpan dataclass."""

    def test_create_claimed_span(self) -> None:
        """Test creating a claimed span."""
        span = ClaimedSpan(
            start_pos=0,
            end_pos=100,
            amendment_id=1,
            pattern_name="strike_insert_quoted",
        )
        assert span.start_pos == 0
        assert span.end_pos == 100
        assert span.amendment_id == 1
        assert span.pattern_name == "strike_insert_quoted"


class TestUnclaimedSpan:
    """Tests for UnclaimedSpan dataclass."""

    def test_create_unclaimed_span(self) -> None:
        """Test creating an unclaimed span."""
        span = UnclaimedSpan(
            start_pos=100,
            end_pos=200,
            text="some unclaimed text",
        )
        assert span.start_pos == 100
        assert span.end_pos == 200
        assert span.text == "some unclaimed text"
        assert span.contains_keywords is False
        assert span.detected_keywords == []

    def test_unclaimed_span_with_keywords(self) -> None:
        """Test unclaimed span with detected keywords."""
        span = UnclaimedSpan(
            start_pos=100,
            end_pos=200,
            text="amended by striking",
            contains_keywords=True,
            detected_keywords=["amended", "striking"],
        )
        assert span.contains_keywords is True
        assert len(span.detected_keywords) == 2


class TestTextAccountant:
    """Tests for TextAccountant class."""

    def test_init(self) -> None:
        """Test initialization."""
        text = "This is a test text for the accountant."
        accountant = TextAccountant(text)
        assert accountant.total_length == len(text)
        assert accountant.text == text

    def test_claim_span(self) -> None:
        """Test claiming a span."""
        text = "This is a test text for the accountant."
        accountant = TextAccountant(text)
        accountant.claim_span(0, 10, amendment_id=1, pattern_name="test_pattern")

        spans = accountant.get_claimed_spans()
        assert len(spans) == 1
        assert spans[0].start_pos == 0
        assert spans[0].end_pos == 10
        assert spans[0].amendment_id == 1
        assert spans[0].pattern_name == "test_pattern"

    def test_claim_span_invalid_positions(self) -> None:
        """Test that invalid positions raise errors."""
        text = "Short text"
        accountant = TextAccountant(text)

        # End before start
        with pytest.raises(ValueError, match="Invalid span"):
            accountant.claim_span(10, 5, amendment_id=1, pattern_name="test")

        # Out of bounds
        with pytest.raises(ValueError, match="out of bounds"):
            accountant.claim_span(0, 1000, amendment_id=1, pattern_name="test")

        # Negative start
        with pytest.raises(ValueError, match="out of bounds"):
            accountant.claim_span(-1, 5, amendment_id=1, pattern_name="test")

    def test_multiple_claims(self) -> None:
        """Test claiming multiple spans."""
        text = "0123456789" * 10  # 100 chars
        accountant = TextAccountant(text)

        accountant.claim_span(0, 20, amendment_id=1, pattern_name="p1")
        accountant.claim_span(30, 50, amendment_id=2, pattern_name="p2")
        accountant.claim_span(70, 90, amendment_id=3, pattern_name="p3")

        spans = accountant.get_claimed_spans()
        assert len(spans) == 3
        # Should be sorted by position
        assert spans[0].start_pos == 0
        assert spans[1].start_pos == 30
        assert spans[2].start_pos == 70

    def test_get_unclaimed_spans_no_claims(self) -> None:
        """Test getting unclaimed spans with no claims."""
        text = "This is a test text with no claimed spans at all."
        accountant = TextAccountant(text)

        unclaimed = accountant.get_unclaimed_spans()
        assert len(unclaimed) == 1
        assert unclaimed[0].start_pos == 0
        assert unclaimed[0].end_pos == len(text)
        assert unclaimed[0].text == text

    def test_get_unclaimed_spans_full_coverage(self) -> None:
        """Test getting unclaimed spans with full coverage."""
        text = "0123456789"
        accountant = TextAccountant(text)
        accountant.claim_span(0, 10, amendment_id=1, pattern_name="full")

        unclaimed = accountant.get_unclaimed_spans()
        assert len(unclaimed) == 0

    def test_get_unclaimed_spans_gaps(self) -> None:
        """Test getting unclaimed spans between claimed spans."""
        text = "0" * 100
        accountant = TextAccountant(text)

        accountant.claim_span(0, 20, amendment_id=1, pattern_name="p1")
        accountant.claim_span(40, 60, amendment_id=2, pattern_name="p2")
        accountant.claim_span(80, 100, amendment_id=3, pattern_name="p3")

        unclaimed = accountant.get_unclaimed_spans(min_length=5)
        assert len(unclaimed) == 2
        assert unclaimed[0].start_pos == 20
        assert unclaimed[0].end_pos == 40
        assert unclaimed[1].start_pos == 60
        assert unclaimed[1].end_pos == 80

    def test_get_unclaimed_spans_min_length(self) -> None:
        """Test minimum length filter for unclaimed spans."""
        text = "0" * 100
        accountant = TextAccountant(text)

        # Leave a small gap (5 chars) and a large gap (25 chars)
        accountant.claim_span(0, 20, amendment_id=1, pattern_name="p1")
        accountant.claim_span(25, 50, amendment_id=2, pattern_name="p2")  # 5 char gap
        accountant.claim_span(75, 100, amendment_id=3, pattern_name="p3")  # 25 char gap

        # With min_length=10, should only return the large gap
        unclaimed = accountant.get_unclaimed_spans(min_length=10)
        assert len(unclaimed) == 1
        assert unclaimed[0].start_pos == 50
        assert unclaimed[0].end_pos == 75

    def test_overlapping_claims_merged(self) -> None:
        """Test that overlapping claims are merged when calculating coverage."""
        text = "0" * 100
        accountant = TextAccountant(text)

        # Overlapping spans
        accountant.claim_span(0, 30, amendment_id=1, pattern_name="p1")
        accountant.claim_span(20, 50, amendment_id=2, pattern_name="p2")

        report = accountant.generate_coverage_report()
        # Should count as 50 chars claimed (merged), not 60
        assert report.claimed_length == 50
        assert report.coverage_percentage == 50.0


class TestKeywordDetection:
    """Tests for amendment keyword detection."""

    def test_keywords_defined(self) -> None:
        """Test that keywords are defined."""
        assert len(AMENDMENT_KEYWORDS) > 0
        assert "amended" in AMENDMENT_KEYWORDS
        assert "striking" in AMENDMENT_KEYWORDS
        assert "inserting" in AMENDMENT_KEYWORDS

    def test_check_unclaimed_for_keywords_found(self) -> None:
        """Test keyword detection when keywords present."""
        text = "Section 106 is amended by striking the old text."
        accountant = TextAccountant(text)

        span = UnclaimedSpan(start_pos=0, end_pos=len(text), text=text)
        result = accountant.check_unclaimed_for_keywords(span)

        assert result.contains_keywords is True
        assert "amended" in result.detected_keywords
        assert "striking" in result.detected_keywords

    def test_check_unclaimed_for_keywords_not_found(self) -> None:
        """Test keyword detection when no keywords present."""
        text = "This is just regular text with no special terms."
        accountant = TextAccountant(text)

        span = UnclaimedSpan(start_pos=0, end_pos=len(text), text=text)
        result = accountant.check_unclaimed_for_keywords(span)

        assert result.contains_keywords is False
        assert len(result.detected_keywords) == 0

    def test_keyword_detection_case_insensitive(self) -> None:
        """Test that keyword detection is case insensitive."""
        text = "AMENDED BY STRIKING and INSERTING"
        accountant = TextAccountant(text)

        span = UnclaimedSpan(start_pos=0, end_pos=len(text), text=text)
        result = accountant.check_unclaimed_for_keywords(span)

        assert result.contains_keywords is True
        # Keywords should be lowercased
        assert all(kw.islower() for kw in result.detected_keywords)


class TestCoverageReport:
    """Tests for coverage report generation."""

    def test_generate_coverage_report_empty(self) -> None:
        """Test report for text with no claims."""
        text = "Some text without any claims."
        accountant = TextAccountant(text)

        report = accountant.generate_coverage_report()

        assert report.total_length == len(text)
        assert report.claimed_length == 0
        assert report.coverage_percentage == 0.0
        assert len(report.claimed_spans) == 0
        assert len(report.unclaimed_spans) == 1

    def test_generate_coverage_report_full(self) -> None:
        """Test report for fully claimed text."""
        text = "0123456789"
        accountant = TextAccountant(text)
        accountant.claim_span(0, 10, amendment_id=1, pattern_name="full")

        report = accountant.generate_coverage_report()

        assert report.total_length == 10
        assert report.claimed_length == 10
        assert report.coverage_percentage == 100.0
        assert len(report.claimed_spans) == 1
        assert len(report.unclaimed_spans) == 0

    def test_generate_coverage_report_partial(self) -> None:
        """Test report for partially claimed text."""
        text = "0" * 100
        accountant = TextAccountant(text)
        accountant.claim_span(0, 50, amendment_id=1, pattern_name="half")

        report = accountant.generate_coverage_report()

        assert report.total_length == 100
        assert report.claimed_length == 50
        assert report.coverage_percentage == 50.0

    def test_report_flagged_vs_ignored(self) -> None:
        """Test that unclaimed spans are classified correctly."""
        text = "Some text amended by striking and more normal text here."
        accountant = TextAccountant(text)
        # Claim just the "more normal text here" part at the end
        accountant.claim_span(35, 56, amendment_id=1, pattern_name="test")

        report = accountant.generate_coverage_report(min_unclaimed_length=5)

        # The first part has keywords, should be flagged
        assert len(report.flagged_unclaimed) >= 1
        # The ignored list should have less since we claimed the normal part

    def test_coverage_percentage_rounding(self) -> None:
        """Test that coverage percentage is properly rounded."""
        text = "0" * 33
        accountant = TextAccountant(text)
        accountant.claim_span(0, 10, amendment_id=1, pattern_name="test")

        report = accountant.generate_coverage_report()

        # 10/33 = 30.303030...
        assert report.coverage_percentage == 30.30


class TestJsonSerialization:
    """Tests for JSON serialization."""

    def test_to_json_basic(self) -> None:
        """Test basic JSON serialization."""
        text = "0123456789"
        accountant = TextAccountant(text)
        accountant.claim_span(0, 5, amendment_id=1, pattern_name="test")

        json_str = accountant.to_json()
        assert '"total_length": 10' in json_str
        assert '"claimed_spans"' in json_str
        assert '"start_pos": 0' in json_str

    def test_to_json_with_text(self) -> None:
        """Test JSON serialization with text included."""
        text = "0123456789"
        accountant = TextAccountant(text)
        accountant.claim_span(0, 5, amendment_id=1, pattern_name="test")

        json_str = accountant.to_json(include_text=True)
        assert '"text": "01234"' in json_str


class TestIntegration:
    """Integration tests with realistic legal text."""

    def test_parse_real_amendment_text(self) -> None:
        """Test with realistic amendment text."""
        text = """
        SEC. 101. AMENDMENT TO TITLE 17.

        Section 106 of title 17, United States Code, is amended by striking
        "reproduction" and inserting "reproduction or distribution".

        SEC. 102. EFFECTIVE DATE.

        This Act shall take effect on January 1, 2025.
        """

        accountant = TextAccountant(text)

        # Simulate claiming the amendment portion (lines 4-5)
        amendment_start = text.find('is amended by striking')
        amendment_end = text.find('distribution"') + len('distribution"')
        if amendment_end > 0:
            accountant.claim_span(
                amendment_start,
                amendment_end + 1,
                amendment_id=1,
                pattern_name="strike_insert_quoted",
            )

        report = accountant.generate_coverage_report()

        # Should have some coverage
        assert report.claimed_length > 0
        assert report.coverage_percentage > 0

        # Should flag the section title as containing "amended" keyword
        # (though it's not a real amendment instruction)
        # This is expected behavior - keyword detection finds "amended" in section headers too
        assert report.total_length > report.claimed_length

    def test_multiple_amendments_coverage(self) -> None:
        """Test coverage tracking with multiple amendments."""
        text = """
        (1) by striking "old1" and inserting "new1";
        (2) by striking "old2" and inserting "new2"; and
        (3) by adding at the end the following:
        """

        accountant = TextAccountant(text)

        # Claim each amendment instruction
        pos1 = text.find('by striking "old1"')
        end1 = text.find('new1";') + len('new1";')
        accountant.claim_span(pos1, end1, amendment_id=1, pattern_name="strike_insert")

        pos2 = text.find('by striking "old2"')
        end2 = text.find('new2";') + len('new2";')
        accountant.claim_span(pos2, end2, amendment_id=2, pattern_name="strike_insert")

        pos3 = text.find('by adding at the end')
        end3 = text.find('following:') + len('following:')
        accountant.claim_span(pos3, end3, amendment_id=3, pattern_name="add_at_end")

        report = accountant.generate_coverage_report()

        assert len(report.claimed_spans) == 3
        # Most of the text should be claimed
        assert report.coverage_percentage > 50
