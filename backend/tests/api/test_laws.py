"""Tests for public laws list endpoint."""

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
def test_list_laws_returns_laws(mock_list: AsyncMock, client: TestClient) -> None:
    """Laws list endpoint returns laws from the CRUD layer."""
    mock_list.return_value = [_make_law(113, "9"), _make_law(113, "8")]

    response = client.get("/api/v1/laws/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["law_number"] == "9"


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_passes_limit_to_crud(mock_list: AsyncMock, client: TestClient) -> None:
    """The limit query param is forwarded to the CRUD layer."""
    mock_list.return_value = []

    client.get("/api/v1/laws/?limit=500")
    mock_list.assert_called_once()
    _, kwargs = mock_list.call_args
    assert kwargs["limit"] == 500


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_limit_exceeds_old_cap(mock_list: AsyncMock, client: TestClient) -> None:
    """Limit of 500 is accepted (previously capped at 200, causing truncation)."""
    mock_list.return_value = []

    response = client.get("/api/v1/laws/?limit=500")
    assert response.status_code == 200
