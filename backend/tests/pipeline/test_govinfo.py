"""Tests for GovInfo API client."""

import os
from datetime import datetime

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
            "title": "National Defense Authorization Act for Fiscal Year 2026",
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
        assert detail.title == "National Defense Authorization Act for Fiscal Year 2026"
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
            "title": "Test Law",
        }

        detail = PLAWPackageDetail.from_api_response(data)

        assert detail.package_id == "PLAW-118publ1"
        assert detail.congress == 118
        assert detail.law_number == 1
        assert detail.pdf_url is None
        assert detail.xml_url is None
        assert detail.bill_id is None


class TestGovInfoClient:
    """Tests for GovInfoClient class."""

    def test_init_requires_api_key(self) -> None:
        """Test that client requires an API key."""
        # Clear any environment variable
        old_key = os.environ.pop("GOVINFO_API_KEY", None)

        try:
            with pytest.raises(ValueError, match="API key required"):
                GovInfoClient()
        finally:
            if old_key:
                os.environ["GOVINFO_API_KEY"] = old_key

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
