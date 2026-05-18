"""Tests for the presidential signing statement fetcher (GovInfo CPD source)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.signing_statements.fetcher import (
    SigningStatementResult,
    _fetch_statement_text,
    _search_govinfo,
    fetch_signing_statement,
)

# ---------------------------------------------------------------------------
# _search_govinfo
# ---------------------------------------------------------------------------


class TestSearchGovinfo:
    @pytest.mark.asyncio
    async def test_returns_first_cpd_hit(self) -> None:
        payload = {
            "count": 3,
            "results": [
                # Non-CPD result should be skipped
                {
                    "collectionCode": "USCOURTS",
                    "granuleId": "court-123",
                    "title": "Court case",
                },
                # CPD hit should be returned
                {
                    "collectionCode": "CPD",
                    "granuleId": "WCPD-2010-03-29-Pg1234",
                    "packageId": "WCPD-2010-03-29",
                    "title": "Statement on Signing the Affordable Care Act",
                    "dateIssued": "2010-03-23",
                },
            ],
        }

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=payload)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await _search_govinfo(
            "Affordable Care Act", 111, "148", "fake-key", mock_client
        )

        assert result is not None
        assert result["granuleId"] == "WCPD-2010-03-29-Pg1234"
        assert result["collectionCode"] == "CPD"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_cpd_results(self) -> None:
        payload = {"count": 0, "results": []}

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=payload)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await _search_govinfo(
            "Some Obscure Act", 118, "99", "fake-key", mock_client
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_cpd_result_without_granule_id(self) -> None:
        payload = {
            "results": [
                {
                    "collectionCode": "CPD",
                    "granuleId": None,
                    "title": "Package-level result",
                },
            ]
        }

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=payload)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        result = await _search_govinfo("Some Act", 118, "5", "fake-key", mock_client)

        assert result is None


# ---------------------------------------------------------------------------
# _fetch_statement_text
# ---------------------------------------------------------------------------


class TestFetchStatementText:
    @pytest.mark.asyncio
    async def test_extracts_text_from_pre_tag(self) -> None:
        html = """
        <html><body><pre>
[Weekly Compilation of Presidential Documents]
[Pages 1234-1235]

Statement on Signing the Foo Act

October 28, 1998

    Today I am pleased to sign the Foo Act into law.
    This legislation will help all Americans.

                                            William J. Clinton
</pre></body></html>
        """

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        text = await _fetch_statement_text(
            "WCPD-1998-11-02-Pg1234", "WCPD-1998-11-02", "fake-key", mock_client
        )

        assert text is not None
        assert "Foo Act" in text
        assert "William J. Clinton" in text
        # Bracketed header lines should be stripped
        assert "[Weekly Compilation" not in text

    @pytest.mark.asyncio
    async def test_returns_none_when_no_pre_tag(self) -> None:
        html = "<html><body><p>Not found</p></body></html>"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await _fetch_statement_text("g-id", "pkg-id", "fake-key", mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )

        result = await _fetch_statement_text("g-id", "pkg-id", "fake-key", mock_client)

        assert result is None


# ---------------------------------------------------------------------------
# fetch_signing_statement (integration of search + fetch)
# ---------------------------------------------------------------------------


class TestFetchSigningStatement:
    @pytest.mark.asyncio
    async def test_returns_result_when_found(self) -> None:
        search_payload = {
            "results": [
                {
                    "collectionCode": "CPD",
                    "granuleId": "WCPD-1998-11-02-Pg2168-2",
                    "packageId": "WCPD-1998-11-02",
                    "title": "Statement on Signing the Digital Millennium Copyright Act",
                    "dateIssued": "1998-10-28",
                }
            ]
        }
        text_html = """<html><body><pre>
Statement on Signing the Digital Millennium Copyright Act
October 28, 1998

    Today I am pleased to sign H.R. 2281.
                                            William J. Clinton
</pre></body></html>"""

        mock_search_resp = MagicMock()
        mock_search_resp.raise_for_status = MagicMock()
        mock_search_resp.json = MagicMock(return_value=search_payload)

        mock_text_resp = MagicMock()
        mock_text_resp.raise_for_status = MagicMock()
        mock_text_resp.text = text_html

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_search_resp)
        mock_client.get = AsyncMock(return_value=mock_text_resp)
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(
            105,
            "304",
            title="Digital Millennium Copyright Act",
            api_key="fake-key",
            client=mock_client,
        )

        assert result is not None
        assert isinstance(result, SigningStatementResult)
        assert "H.R. 2281" in result.text
        assert "govinfo.gov" in result.source_url
        assert "WCPD-1998-11-02-Pg2168-2" in result.source_url
        assert result.date_issued == "1998-10-28"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_statement_found(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"results": []})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(
            118, "5", title="Some Minor Act", api_key="fake-key", client=mock_client
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_search_error(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(
            118, "5", title="Some Act", api_key="fake-key", client=mock_client
        )

        assert result is None
