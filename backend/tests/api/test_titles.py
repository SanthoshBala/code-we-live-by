"""Tests for tree navigation API endpoints."""

from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.us_code import (
    ChapterTreeSchema,
    SectionSummarySchema,
    SubchapterTreeSchema,
    TitleStructureSchema,
    TitleSummarySchema,
)

# ---------------------------------------------------------------------------
# GET /api/v1/titles/
# ---------------------------------------------------------------------------


@patch("app.api.v1.titles.get_all_titles", new_callable=AsyncMock)
def test_list_titles_returns_list(mock_get: AsyncMock, client: TestClient) -> None:
    """Titles endpoint returns a list of title summaries."""
    mock_get.return_value = [
        TitleSummarySchema(
            title_number=17,
            title_name="Copyrights",
            is_positive_law=True,
            positive_law_date=date(1947, 7, 30),
            chapter_count=8,
            section_count=120,
        ),
        TitleSummarySchema(
            title_number=18,
            title_name="Crimes and Criminal Procedure",
            is_positive_law=True,
            positive_law_date=date(1948, 6, 25),
            chapter_count=45,
            section_count=500,
        ),
    ]

    response = client.get("/api/v1/titles/")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert data[0]["title_number"] == 17
    assert data[0]["title_name"] == "Copyrights"
    assert data[0]["chapter_count"] == 8
    assert data[0]["section_count"] == 120
    assert data[1]["title_number"] == 18


@patch("app.api.v1.titles.get_all_titles", new_callable=AsyncMock)
def test_list_titles_empty(mock_get: AsyncMock, client: TestClient) -> None:
    """Titles endpoint returns an empty list when no titles exist."""
    mock_get.return_value = []

    response = client.get("/api/v1/titles/")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/titles/{title_number}/structure
# ---------------------------------------------------------------------------


@patch("app.api.v1.titles.get_title_structure", new_callable=AsyncMock)
def test_get_title_structure_success(mock_get: AsyncMock, client: TestClient) -> None:
    """Structure endpoint returns a nested tree for a valid title."""
    mock_get.return_value = TitleStructureSchema(
        title_number=17,
        title_name="Copyrights",
        is_positive_law=True,
        chapters=[
            ChapterTreeSchema(
                chapter_number="1",
                chapter_name="Subject Matter and Scope of Copyright",
                sort_order=0,
                subchapters=[
                    SubchapterTreeSchema(
                        subchapter_number="A",
                        subchapter_name="General Provisions",
                        sort_order=0,
                        sections=[
                            SectionSummarySchema(
                                section_number="101",
                                heading="Definitions",
                                sort_order=0,
                            ),
                        ],
                    ),
                ],
                sections=[
                    SectionSummarySchema(
                        section_number="100",
                        heading="Preliminary provisions",
                        sort_order=0,
                    ),
                ],
            ),
        ],
    )

    response = client.get("/api/v1/titles/17/structure")
    assert response.status_code == 200

    data = response.json()
    assert data["title_number"] == 17
    assert data["title_name"] == "Copyrights"
    assert len(data["chapters"]) == 1

    chapter = data["chapters"][0]
    assert chapter["chapter_number"] == "1"
    assert len(chapter["subchapters"]) == 1
    assert len(chapter["sections"]) == 1

    subchapter = chapter["subchapters"][0]
    assert subchapter["subchapter_number"] == "A"
    assert len(subchapter["sections"]) == 1
    assert subchapter["sections"][0]["section_number"] == "101"

    # Direct sections (no subchapter)
    assert chapter["sections"][0]["section_number"] == "100"


@patch("app.api.v1.titles.get_title_structure", new_callable=AsyncMock)
def test_get_title_structure_not_found(mock_get: AsyncMock, client: TestClient) -> None:
    """Structure endpoint returns 404 for a nonexistent title."""
    mock_get.return_value = None

    response = client.get("/api/v1/titles/999/structure")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]
