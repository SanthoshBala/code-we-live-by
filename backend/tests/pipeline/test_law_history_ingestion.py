"""Tests for LawHistoryIngestionService._resolve_bill_ref.

Covers the Congress.gov /law/{congress}/{type}/{number} response structure,
which returns {"bill": {"type": ..., "number": ...}} at the top level.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.congress.law_history_ingestion import LawHistoryIngestionService


def _make_service() -> LawHistoryIngestionService:
    session = MagicMock()
    return LawHistoryIngestionService(session=session)


def _make_law(*, law_number: str = "23", congress: int = 113, origin_bill=None):
    law = MagicMock()
    law.law_number = law_number
    law.congress = congress
    law.origin_bill = origin_bill
    return law


class TestResolveBillRef:
    @pytest.mark.asyncio
    async def test_resolves_from_origin_bill_fk(self) -> None:
        """When origin_bill FK is populated, skip the API call entirely."""
        bill = MagicMock()
        bill.bill_number = "667"
        bill.bill_type.value = "HR"
        law = _make_law(origin_bill=bill)

        client = AsyncMock()
        service = _make_service()

        result = await service._resolve_bill_ref(law, client)

        assert result == ("hr", 667)
        client.get_law_bill_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolves_from_congress_api_response(self) -> None:
        """Falls back to Congress.gov API and parses {"bill": {...}} correctly."""
        law = _make_law(origin_bill=None)
        client = AsyncMock()
        client.get_law_bill_info.return_value = {
            "bill": {
                "type": "HR",
                "number": "667",
                "originChamber": "House",
                "laws": [{"number": "113-23", "type": "Public Law"}],
            },
            "request": {},
        }

        service = _make_service()
        result = await service._resolve_bill_ref(law, client)

        assert result == ("hr", 667)

    @pytest.mark.asyncio
    async def test_returns_none_when_api_returns_none(self) -> None:
        law = _make_law(origin_bill=None)
        client = AsyncMock()
        client.get_law_bill_info.return_value = None

        service = _make_service()
        result = await service._resolve_bill_ref(law, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_bill_missing_from_response(self) -> None:
        """API response has no bill key."""
        law = _make_law(origin_bill=None)
        client = AsyncMock()
        client.get_law_bill_info.return_value = {"request": {}}

        service = _make_service()
        result = await service._resolve_bill_ref(law, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_api_raises(self) -> None:
        law = _make_law(origin_bill=None)
        client = AsyncMock()
        client.get_law_bill_info.side_effect = Exception("timeout")

        service = _make_service()
        result = await service._resolve_bill_ref(law, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_senate_bill_type_lowercased(self) -> None:
        law = _make_law(origin_bill=None)
        client = AsyncMock()
        client.get_law_bill_info.return_value = {
            "bill": {"type": "S", "number": "42"},
        }

        service = _make_service()
        result = await service._resolve_bill_ref(law, client)

        assert result == ("s", 42)
