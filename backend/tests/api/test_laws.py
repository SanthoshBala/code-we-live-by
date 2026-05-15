"""Tests for the laws list API endpoint."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.law_viewer import LawSummarySchema


def _make_law(congress: int, law_number: str) -> LawSummarySchema:
    return LawSummarySchema(
        congress=congress,
        law_number=law_number,
        official_title=f"An Act ({congress}-{law_number})",
        short_title=None,
        enacted_date="2013-01-01",
        sections_affected=0,
    )


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_returns_ok(mock_get: AsyncMock, client: TestClient) -> None:
    """Laws endpoint returns 200 with a list of law summaries."""
    mock_get.return_value = [
        _make_law(113, "296"),
        _make_law(113, "100"),
        _make_law(113, "9"),
    ]

    response = client.get("/api/v1/laws")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["law_number"] == "296"
    assert data[1]["law_number"] == "100"
    assert data[2]["law_number"] == "9"


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_passes_limit_and_offset(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Laws endpoint forwards limit and offset query params to the CRUD layer."""
    mock_get.return_value = []

    client.get("/api/v1/laws?limit=10&offset=20")
    mock_get.assert_called_once()
    _session, kwargs_limit, kwargs_offset = (
        mock_get.call_args[0][0],
        mock_get.call_args[1].get("limit") or mock_get.call_args[0][1],
        mock_get.call_args[1].get("offset") or mock_get.call_args[0][2],
    )
    assert kwargs_limit == 10
    assert kwargs_offset == 20


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_numeric_order_contract(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Laws endpoint returns laws in the order provided by the CRUD layer.

    The CRUD layer uses integer casting so law 296 > 100 > 9 (not lex "9" > "296").
    This test documents the expected numeric order contract.
    """
    # Simulate the CRUD layer returning laws in correct numeric-descending order
    # (law 296 before 100 before 9), which is what the integer-cast ORDER BY produces.
    mock_get.return_value = [
        _make_law(113, "296"),
        _make_law(113, "100"),
        _make_law(113, "29"),
        _make_law(113, "10"),
        _make_law(113, "9"),
    ]

    response = client.get("/api/v1/laws")
    assert response.status_code == 200
    data = response.json()
    law_numbers = [int(d["law_number"]) for d in data]
    # Verify numeric descending order
    assert law_numbers == sorted(law_numbers, reverse=True)
