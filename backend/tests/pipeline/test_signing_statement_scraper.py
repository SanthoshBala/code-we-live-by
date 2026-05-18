"""Tests for the presidential signing statement scraper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.signing_statements.scraper import (
    SigningStatementResult,
    _build_search_url,
    _normalize_law_number,
    _parse_search_results,
    _parse_statement_page,
    _query_for_law,
    fetch_signing_statement,
)


class TestBuildSearchUrl:
    def test_includes_query_and_category(self) -> None:
        url = _build_search_url("Public Law 118-5")
        assert "presidency.ucsb.edu" in url
        assert "Public+Law+118-5" in url or "Public%20Law%20118-5" in url
        assert "category2" in url
        assert "50" in url

    def test_includes_items_per_page(self) -> None:
        url = _build_search_url("test query")
        assert "items_per_page=10" in url


class TestQueryForLaw:
    def test_formats_congress_and_number(self) -> None:
        assert _query_for_law(118, "5") == "Public Law 118-5"

    def test_multi_digit_law_number(self) -> None:
        assert _query_for_law(117, "234") == "Public Law 117-234"


class TestNormalizeLawNumber:
    def test_strips_leading_zeros(self) -> None:
        assert _normalize_law_number("005") == "5"

    def test_plain_number_unchanged(self) -> None:
        assert _normalize_law_number("42") == "42"

    def test_no_digits_returns_as_is(self) -> None:
        assert _normalize_law_number("abc") == "abc"


class TestParseSearchResults:
    def test_extracts_titles_and_hrefs(self) -> None:
        html = """
        <html><body>
          <h3 class="field-content">
            <a href="/documents/statement-signing-something">Statement on Signing the Foo Act</a>
          </h3>
          <h3 class="field-content">
            <a href="/documents/statement-signing-another">Statement on Signing the Bar Act</a>
          </h3>
        </body></html>
        """
        results = _parse_search_results(html)
        assert len(results) == 2
        assert results[0] == (
            "Statement on Signing the Foo Act",
            "/documents/statement-signing-something",
        )
        assert results[1] == (
            "Statement on Signing the Bar Act",
            "/documents/statement-signing-another",
        )

    def test_empty_page_returns_empty_list(self) -> None:
        html = "<html><body><p>No results found.</p></body></html>"
        results = _parse_search_results(html)
        assert results == []

    def test_ignores_anchors_without_href(self) -> None:
        html = '<html><body><h3 class="field-content"><a>No href here</a></h3></body></html>'
        results = _parse_search_results(html)
        assert results == []


class TestParseStatementPage:
    def test_extracts_paragraphs_from_field_docs_content(self) -> None:
        html = """
        <html><body>
          <div class="field-docs-content">
            <p>I have signed into law the Foo Act of 2023.</p>
            <p>This legislation will improve the lives of all Americans.</p>
          </div>
        </body></html>
        """
        text = _parse_statement_page(html)
        assert text is not None
        assert "Foo Act" in text
        assert "Americans" in text

    def test_returns_none_when_no_body_div(self) -> None:
        html = "<html><body><p>Nothing here</p></body></html>"
        result = _parse_statement_page(html)
        assert result is None

    def test_joins_paragraphs_with_double_newline(self) -> None:
        html = """
        <html><body>
          <div class="field-docs-content">
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
          </div>
        </body></html>
        """
        text = _parse_statement_page(html)
        assert text is not None
        assert "\n\n" in text


class TestFetchSigningStatement:
    @pytest.mark.asyncio
    async def test_returns_result_when_found(self) -> None:
        search_html = """
        <html><body>
          <h3 class="field-content">
            <a href="/documents/statement-signing-foo">Statement on Signing the Foo Act</a>
          </h3>
        </body></html>
        """
        doc_html = """
        <html><body>
          <div class="field-docs-content">
            <p>I have signed the Foo Act into law.</p>
          </div>
        </body></html>
        """

        mock_search_response = MagicMock()
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.text = search_html

        mock_doc_response = MagicMock()
        mock_doc_response.raise_for_status = MagicMock()
        mock_doc_response.text = doc_html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[mock_search_response, mock_doc_response]
        )
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(118, "5", client=mock_client)

        assert result is not None
        assert isinstance(result, SigningStatementResult)
        assert "Foo Act" in result.text
        assert "presidency.ucsb.edu" in result.source_url
        assert result.title == "Statement on Signing the Foo Act"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_search_results(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html><body><p>No results.</p></body></html>"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(118, "5", client=mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(118, "5", client=mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_doc_body_unparseable(self) -> None:
        search_html = """
        <html><body>
          <h3 class="field-content">
            <a href="/documents/statement-signing-foo">Statement on Signing</a>
          </h3>
        </body></html>
        """
        # Doc page with no recognisable body div
        doc_html = "<html><body><p>Error 404</p></body></html>"

        mock_search_response = MagicMock()
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.text = search_html

        mock_doc_response = MagicMock()
        mock_doc_response.raise_for_status = MagicMock()
        mock_doc_response.text = doc_html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[mock_search_response, mock_doc_response]
        )
        mock_client.aclose = AsyncMock()

        result = await fetch_signing_statement(118, "5", client=mock_client)

        assert result is None
