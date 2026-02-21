"""Tests for law change service orchestrator."""

from unittest.mock import AsyncMock, MagicMock

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

    @pytest.mark.asyncio
    async def test_process_law_idempotent_skips_existing(self) -> None:
        """process_law returns early when LawChange records already exist."""
        from app.models.public_law import PublicLaw

        session = AsyncMock()
        law = PublicLaw(congress=113, law_number="22")
        law.law_id = 100

        # First execute: find the law
        # Second execute: count existing LawChange records (returns 3)
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=law)),
            MagicMock(scalar=MagicMock(return_value=3)),
        ]
        session.execute = AsyncMock(side_effect=execute_results)

        service = LawChangeService(session)
        result = await service.process_law(congress=113, law_number=22)

        # Should return early with no amendments/changes/errors
        assert result.amendments == []
        assert result.changes == []
        assert result.errors == []
