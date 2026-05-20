"""Tests for public laws list endpoint."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.law_viewer import LawSummarySchema, PaginatedLawsResponse


def _make_law(congress: int, law_number: str) -> LawSummarySchema:
    return LawSummarySchema(
        congress=congress,
        law_number=law_number,
        official_title=None,
        short_title=None,
        enacted_date="2013-01-01",
        sections_affected=0,
    )


def _make_paginated(
    laws: list[LawSummarySchema],
    total: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedLawsResponse:
    return PaginatedLawsResponse(
        total=total if total is not None else len(laws),
        items=laws,
        limit=limit,
        offset=offset,
    )


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_returns_paginated_response(
    mock_list: AsyncMock, client: TestClient
) -> None:
    """Laws list endpoint returns a paginated wrapper with total and items."""
    mock_list.return_value = _make_paginated(
        [_make_law(113, "9"), _make_law(113, "8")], total=42
    )

    response = client.get("/api/v1/laws/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 42
    assert len(data["items"]) == 2
    assert data["items"][0]["law_number"] == "9"
    assert data["limit"] == 50
    assert data["offset"] == 0


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_passes_limit_to_crud(
    mock_list: AsyncMock, client: TestClient
) -> None:
    """The limit query param is forwarded to the CRUD layer."""
    mock_list.return_value = _make_paginated([], limit=500)

    client.get("/api/v1/laws/?limit=500")
    mock_list.assert_called_once()
    _, kwargs = mock_list.call_args
    assert kwargs["limit"] == 500


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_passes_offset_to_crud(
    mock_list: AsyncMock, client: TestClient
) -> None:
    """The offset query param is forwarded to the CRUD layer."""
    mock_list.return_value = _make_paginated([], offset=50)

    client.get("/api/v1/laws/?offset=50")
    mock_list.assert_called_once()
    _, kwargs = mock_list.call_args
    assert kwargs["offset"] == 50


@patch("app.api.v1.laws.get_laws_list", new_callable=AsyncMock)
def test_list_laws_limit_exceeds_old_cap(
    mock_list: AsyncMock, client: TestClient
) -> None:
    """Limit of 500 is accepted (previously capped at 200, causing truncation)."""
    mock_list.return_value = _make_paginated([], limit=500)

    response = client.get("/api/v1/laws/?limit=500")
    assert response.status_code == 200
