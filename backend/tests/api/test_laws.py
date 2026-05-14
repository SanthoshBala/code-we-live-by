"""Tests for the laws list API endpoint."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.law_viewer import LawSummarySchema


def _make_law(congress: int, law_number: str) -> LawSummarySchema:
    return LawSummarySchema(
        congress=congress,
        law_number=law_number,
        official_title=None,
        short_title=None,
        enacted_date="2013-01-01",
        sections_affected=0,
    )


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_returns_laws(mock_get: AsyncMock, client: TestClient) -> None:
    """Laws endpoint returns the list from the CRUD layer."""
    mock_get.return_value = [
        _make_law(113, "296"),
        _make_law(113, "295"),
        _make_law(113, "1"),
    ]

    response = client.get("/api/v1/laws/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["law_number"] == "296"
    assert data[1]["law_number"] == "295"
    assert data[2]["law_number"] == "1"


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_default_limit(mock_get: AsyncMock, client: TestClient) -> None:
    """Default limit is 500 so all 296 Congress-113 laws are returned in one call."""
    mock_get.return_value = []

    client.get("/api/v1/laws/")
    _, kwargs = mock_get.call_args
    assert kwargs["limit"] == 500


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_accepts_limit_1000(mock_get: AsyncMock, client: TestClient) -> None:
    """Endpoint accepts limit=1000 (raised from prior cap of 200)."""
    mock_get.return_value = []

    response = client.get("/api/v1/laws/?limit=1000")
    assert response.status_code == 200
    _, kwargs = mock_get.call_args
    assert kwargs["limit"] == 1000


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_rejects_limit_above_max(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Limit above 1000 is rejected with 422."""
    response = client.get("/api/v1/laws/?limit=1001")
    assert response.status_code == 422
