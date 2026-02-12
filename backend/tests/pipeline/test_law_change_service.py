"""Tests for law change service orchestrator."""

import pytest

from pipeline.legal_parser.law_change_service import LawChangeResult, LawChangeService


class TestLawChangeResult:
    """Tests for LawChangeResult dataclass."""

    def test_default_result(self) -> None:
        from app.models.public_law import PublicLaw

        law = PublicLaw(congress=113, law_number="22")
        result = LawChangeResult(law=law)
        assert result.amendments == []
        assert result.diffs == []
        assert result.changes == []
        assert result.errors == []
        assert result.dry_run is False

    def test_dry_run_result(self) -> None:
        from app.models.public_law import PublicLaw

        law = PublicLaw(congress=113, law_number="22")
        result = LawChangeResult(law=law, dry_run=True)
        assert result.dry_run is True


class TestLawChangeService:
    """Tests for LawChangeService."""

    def test_service_importable(self) -> None:
        """Verify the service class is importable."""
        assert LawChangeService is not None
