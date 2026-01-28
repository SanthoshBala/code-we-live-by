"""Tests for title endpoints."""

from fastapi.testclient import TestClient


def test_list_titles(client: TestClient) -> None:
    """Test listing titles endpoint returns 200."""
    response = client.get("/api/v1/titles/")
    assert response.status_code == 200


def test_get_title(client: TestClient) -> None:
    """Test getting a specific title returns 200."""
    response = client.get("/api/v1/titles/17")
    assert response.status_code == 200
