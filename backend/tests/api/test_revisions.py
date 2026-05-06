"""Tests for revision API endpoints."""

from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.revision import HeadRevisionSchema

# ---------------------------------------------------------------------------
# GET /api/v1/revisions/{revision_id}
# ---------------------------------------------------------------------------


@patch("app.api.v1.revisions.get_revision_by_id", new_callable=AsyncMock)
def test_get_revision_by_id_success(mock_get: AsyncMock, client: TestClient) -> None:
    """Revision endpoint returns metadata for a valid revision ID."""
    mock_get.return_value = HeadRevisionSchema(
        revision_id=5,
        revision_type="Release_Point",
        effective_date=date(2020, 1, 15),
        summary="Release Point 116-78",
        sequence_number=5,
    )

    response = client.get("/api/v1/revisions/5")
    assert response.status_code == 200

    data = response.json()
    assert data["revision_id"] == 5
    assert data["revision_type"] == "Release_Point"
    assert data["effective_date"] == "2020-01-15"
    assert data["summary"] == "Release Point 116-78"
    assert data["sequence_number"] == 5


@patch("app.api.v1.revisions.get_revision_by_id", new_callable=AsyncMock)
def test_get_revision_by_id_not_found(mock_get: AsyncMock, client: TestClient) -> None:
    """Revision endpoint returns 404 for nonexistent revision."""
    mock_get.return_value = None

    response = client.get("/api/v1/revisions/9999")
    assert response.status_code == 404
    assert "9999" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/revisions/head
# ---------------------------------------------------------------------------


@patch("app.api.v1.revisions.get_head_revision", new_callable=AsyncMock)
def test_get_head_revision_success(mock_get: AsyncMock, client: TestClient) -> None:
    """Head revision endpoint returns the latest ingested revision."""
    mock_get.return_value = HeadRevisionSchema(
        revision_id=10,
        revision_type="Release_Point",
        effective_date=date(2023, 6, 1),
        summary="Release Point 118-5",
        sequence_number=10,
    )

    response = client.get("/api/v1/revisions/head")
    assert response.status_code == 200

    data = response.json()
    assert data["revision_id"] == 10
    assert data["revision_type"] == "Release_Point"
    assert data["effective_date"] == "2023-06-01"


@patch("app.api.v1.revisions.get_head_revision", new_callable=AsyncMock)
def test_get_head_revision_not_found(mock_get: AsyncMock, client: TestClient) -> None:
    """Head revision endpoint returns 404 when no revisions exist."""
    mock_get.return_value = None

    response = client.get("/api/v1/revisions/head")
    assert response.status_code == 404
    assert "No ingested revisions found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/revisions/latest?title=N
# ---------------------------------------------------------------------------


@patch("app.api.v1.revisions.get_latest_revision_for_title", new_callable=AsyncMock)
def test_get_latest_revision_for_title_success(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Latest revision endpoint returns revision for a title."""
    mock_get.return_value = HeadRevisionSchema(
        revision_id=8,
        revision_type="Release_Point",
        effective_date=date(2022, 3, 10),
        summary="Release Point 117-95",
        sequence_number=8,
    )

    response = client.get("/api/v1/revisions/latest?title=17")
    assert response.status_code == 200

    data = response.json()
    assert data["revision_id"] == 8
    assert data["effective_date"] == "2022-03-10"


@patch("app.api.v1.revisions.get_latest_revision_for_title", new_callable=AsyncMock)
def test_get_latest_revision_for_title_not_found(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Latest revision endpoint returns 404 for title with no revisions."""
    mock_get.return_value = None

    response = client.get("/api/v1/revisions/latest?title=99")
    assert response.status_code == 404
    assert "99" in response.json()["detail"]
