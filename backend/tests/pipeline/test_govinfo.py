"""Tests for GovInfo API client."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.govinfo.client import (
    GovInfoClient,
    PLAWPackageDetail,
    PLAWPackageInfo,
)


class TestPLAWPackageInfo:
    """Tests for PLAWPackageInfo dataclass."""

    def test_from_api_response_public_law(self) -> None:
        """Test parsing a public law from API response."""
        data = {
            "packageId": "PLAW-119publ60",
            "lastModified": "2025-12-18T10:00:00Z",
            "title": "National Defense Authorization Act for Fiscal Year 2026",
        }

        info = PLAWPackageInfo.from_api_response(data)

        assert info.package_id == "PLAW-119publ60"
        assert info.congress == 119
        assert info.law_number == 60
        assert info.law_type == "public"
        assert info.title == "National Defense Authorization Act for Fiscal Year 2026"

    def test_from_api_response_private_law(self) -> None:
        """Test parsing a private law from API response."""
        data = {
            "packageId": "PLAW-118pvt5",
            "lastModified": "2024-06-15T10:00:00Z",
            "title": "For the relief of John Doe",
        }

        info = PLAWPackageInfo.from_api_response(data)

        assert info.package_id == "PLAW-118pvt5"
        assert info.congress == 118
        assert info.law_number == 5
        assert info.law_type == "private"

    def test_from_api_response_handles_missing_fields(self) -> None:
        """Test that missing fields are handled gracefully."""
        data = {"packageId": "PLAW-117publ1"}

        info = PLAWPackageInfo.from_api_response(data)

        assert info.package_id == "PLAW-117publ1"
        assert info.congress == 117
        assert info.law_number == 1
        assert info.title == ""


class TestPLAWPackageDetail:
    """Tests for PLAWPackageDetail dataclass."""

    def test_from_api_response_full(self) -> None:
        """Test parsing full package detail from API response."""
        data = {
            "packageId": "PLAW-119publ60",
            "title": "An act to authorize appropriations for fiscal year 2026.",
            "shortTitle": [
                {"title": "National Defense Authorization Act for Fiscal Year 2026"}
            ],
            "dateIssued": "2025-12-18",
            "governmentAuthor1": "Congress",
            "publisher": "Government Publishing Office",
            "collectionCode": "PLAW",
            "docClass": "publ",
            "download": {
                "pdfLink": "https://govinfo.gov/pkg/PLAW-119publ60/pdf/PLAW-119publ60.pdf",
                "xmlLink": "https://govinfo.gov/pkg/PLAW-119publ60/xml/PLAW-119publ60.xml",
                "htmLink": "https://govinfo.gov/pkg/PLAW-119publ60/html/PLAW-119publ60.htm",
            },
            "related": {
                "billId": "S.1071",
            },
            "suDocClassNumber": "AE 2.110:119-60",
        }

        detail = PLAWPackageDetail.from_api_response(data)

        assert detail.package_id == "PLAW-119publ60"
        assert detail.congress == 119
        assert detail.law_number == 60
        assert detail.law_type == "public"
        assert detail.title == "An act to authorize appropriations for fiscal year 2026"
        assert (
            detail.short_title
            == "National Defense Authorization Act for Fiscal Year 2026"
        )
        assert detail.date_issued == datetime(2025, 12, 18)
        assert detail.government_author == "Congress"
        assert detail.pdf_url is not None
        assert "pdf" in detail.pdf_url
        assert detail.xml_url is not None
        assert detail.bill_id == "S.1071"
        assert detail.statutes_at_large_citation == "AE 2.110:119-60"

    def test_from_api_response_minimal(self) -> None:
        """Test parsing with minimal fields."""
        data = {
            "packageId": "PLAW-118publ1",
            "title": "Test Law.",
        }

        detail = PLAWPackageDetail.from_api_response(data)

        assert detail.package_id == "PLAW-118publ1"
        assert detail.congress == 118
        assert detail.law_number == 1
        assert detail.title == "Test Law"
        assert detail.short_title is None
        assert detail.pdf_url is None
        assert detail.xml_url is None
        assert detail.bill_id is None


class TestGovInfoClient:
    """Tests for GovInfoClient class."""

    def test_init_requires_api_key(self) -> None:
        """Test that client requires an API key."""
        # Mock settings to return None for govinfo_api_key
        with patch("app.config.settings") as mock_settings:
            mock_settings.govinfo_api_key = None
            with pytest.raises(ValueError, match="API key required"):
                GovInfoClient()

    def test_init_with_api_key(self) -> None:
        """Test client initialization with API key."""
        client = GovInfoClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.base_url == "https://api.govinfo.gov"

    def test_build_package_id_public(self) -> None:
        """Test building package ID for public law."""
        client = GovInfoClient(api_key="test-key")

        package_id = client.build_package_id(119, 60, "public")

        assert package_id == "PLAW-119publ60"

    def test_build_package_id_private(self) -> None:
        """Test building package ID for private law."""
        client = GovInfoClient(api_key="test-key")

        package_id = client.build_package_id(118, 5, "private")

        assert package_id == "PLAW-118pvt5"


def _make_detail(congress: int, law_number: int) -> PLAWPackageDetail:
    return PLAWPackageDetail(
        package_id=f"PLAW-{congress}publ{law_number}",
        congress=congress,
        law_number=law_number,
        law_type="public",
        title=f"Test Law {law_number}",
        short_title=None,
        date_issued=datetime(2024, 1, 1),
        government_author=None,
        publisher=None,
        collection_code="PLAW",
        doc_class="publ",
        pdf_url=None,
        xml_url=None,
        htm_url=None,
        bill_id=None,
        statutes_at_large_citation=None,
        committees=[],
    )


class TestPublicLawIngestionServiceParallelism:
    """Tests for parallel law detail fetching in PublicLawIngestionService."""

    @pytest.mark.asyncio
    async def test_ingest_congress_fetches_in_parallel(self) -> None:
        """All get_public_law_detail calls are issued concurrently via gather."""
        from pipeline.govinfo.ingestion import PublicLawIngestionService

        details = [_make_detail(119, n) for n in range(1, 4)]
        law_infos = [
            PLAWPackageInfo(
                package_id=d.package_id,
                congress=d.congress,
                law_number=d.law_number,
                law_type=d.law_type,
                title=d.title,
                last_modified=datetime(2024, 1, 1),
            )
            for d in details
        ]

        call_order: list[str] = []
        fetch_started: list[asyncio.Event] = [asyncio.Event() for _ in details]
        fetch_unblock = asyncio.Event()

        async def fake_get_detail(package_id: str) -> PLAWPackageDetail:
            idx = next(i for i, d in enumerate(details) if d.package_id == package_id)
            fetch_started[idx].set()
            await fetch_unblock.wait()
            call_order.append(package_id)
            return details[idx]

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.commit = AsyncMock()

        service = PublicLawIngestionService(session=mock_session, api_key="test-key")
        service.client.get_public_laws_for_congress = AsyncMock(return_value=law_infos)
        service.client.get_public_law_detail = fake_get_detail

        async def run() -> None:
            # Unblock fetches once all have started (proving overlap)
            await asyncio.gather(*[e.wait() for e in fetch_started])
            fetch_unblock.set()

        await asyncio.gather(
            service.ingest_congress(119),
            run(),
        )

        # All three fetches started before any completed — they overlapped
        assert len(call_order) == 3

    @pytest.mark.asyncio
    async def test_ingest_congress_skips_failed_fetches(self) -> None:
        """A fetch failure for one law is logged and skipped; others succeed."""
        from pipeline.govinfo.ingestion import PublicLawIngestionService

        good_detail = _make_detail(119, 2)
        law_infos = [
            PLAWPackageInfo(
                package_id=f"PLAW-119publ{n}",
                congress=119,
                law_number=n,
                law_type="public",
                title=f"Law {n}",
                last_modified=datetime(2024, 1, 1),
            )
            for n in (1, 2)
        ]

        async def fake_get_detail(package_id: str) -> PLAWPackageDetail:
            if package_id == "PLAW-119publ1":
                raise RuntimeError("network error")
            return good_detail

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.commit = AsyncMock()

        service = PublicLawIngestionService(session=mock_session, api_key="test-key")
        service.client.get_public_laws_for_congress = AsyncMock(return_value=law_infos)
        service.client.get_public_law_detail = fake_get_detail

        log = await service.ingest_congress(119)

        assert log.status == "completed"
        assert log.records_created == 1  # only the successful one

    @pytest.mark.asyncio
    async def test_ingest_recent_laws_fetches_in_parallel(self) -> None:
        """ingest_recent_laws also issues detail fetches concurrently."""
        from pipeline.govinfo.ingestion import PublicLawIngestionService

        details = [_make_detail(119, n) for n in range(1, 4)]
        law_infos = [
            PLAWPackageInfo(
                package_id=d.package_id,
                congress=d.congress,
                law_number=d.law_number,
                law_type=d.law_type,
                title=d.title,
                last_modified=datetime(2024, 1, 1),
            )
            for d in details
        ]

        fetch_started: list[asyncio.Event] = [asyncio.Event() for _ in details]
        fetch_unblock = asyncio.Event()
        call_order: list[str] = []

        async def fake_get_detail(package_id: str) -> PLAWPackageDetail:
            idx = next(i for i, d in enumerate(details) if d.package_id == package_id)
            fetch_started[idx].set()
            await fetch_unblock.wait()
            call_order.append(package_id)
            return details[idx]

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.commit = AsyncMock()

        service = PublicLawIngestionService(session=mock_session, api_key="test-key")
        service.client.get_public_laws = AsyncMock(return_value=law_infos)
        service.client.get_public_law_detail = fake_get_detail

        async def run() -> None:
            await asyncio.gather(*[e.wait() for e in fetch_started])
            fetch_unblock.set()

        await asyncio.gather(
            service.ingest_recent_laws(days=7),
            run(),
        )

        assert len(call_order) == 3
