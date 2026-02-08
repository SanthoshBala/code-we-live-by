"""Tests for section viewer API endpoints."""

from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.us_code import (
    CodeLineSchema,
    SectionNotesSchema,
    SectionViewerSchema,
)

# ---------------------------------------------------------------------------
# GET /api/v1/sections/{title_number}/{section_number}
# ---------------------------------------------------------------------------


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_success(mock_get: AsyncMock, client: TestClient) -> None:
    """Section endpoint returns full section content."""
    mock_get.return_value = SectionViewerSchema(
        title_number=17,
        section_number="106",
        heading="Exclusive rights in copyrighted works",
        full_citation="17 U.S.C. § 106",
        text_content="Subject to sections 107 through 122...",
        enacted_date=date(1976, 10, 19),
        last_modified_date=date(2002, 11, 2),
        is_positive_law=True,
        is_repealed=False,
        notes=None,
    )

    response = client.get("/api/v1/sections/17/106")
    assert response.status_code == 200

    data = response.json()
    assert data["title_number"] == 17
    assert data["section_number"] == "106"
    assert data["heading"] == "Exclusive rights in copyrighted works"
    assert data["full_citation"] == "17 U.S.C. § 106"
    assert data["text_content"] == "Subject to sections 107 through 122..."
    assert data["enacted_date"] == "1976-10-19"
    assert data["last_modified_date"] == "2002-11-02"
    assert data["is_positive_law"] is True
    assert data["is_repealed"] is False
    assert data["notes"] is None


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_with_notes(mock_get: AsyncMock, client: TestClient) -> None:
    """Section endpoint returns structured notes when present."""
    mock_get.return_value = SectionViewerSchema(
        title_number=17,
        section_number="106",
        heading="Exclusive rights in copyrighted works",
        full_citation="17 U.S.C. § 106",
        text_content="Subject to sections 107 through 122...",
        enacted_date=date(1976, 10, 19),
        last_modified_date=date(2002, 11, 2),
        is_positive_law=True,
        is_repealed=False,
        notes=SectionNotesSchema(
            citations=[],
            amendments=[],
            short_titles=[],
            notes=[],
        ),
    )

    response = client.get("/api/v1/sections/17/106")
    assert response.status_code == 200

    data = response.json()
    assert data["notes"] is not None
    assert data["notes"]["citations"] == []
    assert data["notes"]["amendments"] == []
    assert data["notes"]["short_titles"] == []
    assert data["notes"]["notes"] == []


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_not_found(mock_get: AsyncMock, client: TestClient) -> None:
    """Section endpoint returns 404 for a nonexistent section."""
    mock_get.return_value = None

    response = client.get("/api/v1/sections/99/9999")
    assert response.status_code == 404
    assert "9999" in response.json()["detail"]


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_repealed(mock_get: AsyncMock, client: TestClient) -> None:
    """Section endpoint returns repealed section metadata."""
    mock_get.return_value = SectionViewerSchema(
        title_number=18,
        section_number="1071",
        heading="Repealed",
        full_citation="18 U.S.C. § 1071",
        text_content=None,
        enacted_date=date(1948, 6, 25),
        last_modified_date=None,
        is_positive_law=True,
        is_repealed=True,
        notes=None,
    )

    response = client.get("/api/v1/sections/18/1071")
    assert response.status_code == 200

    data = response.json()
    assert data["is_repealed"] is True
    assert data["text_content"] is None
    assert data["heading"] == "Repealed"


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_with_provisions(mock_get: AsyncMock, client: TestClient) -> None:
    """Section endpoint returns structured provisions when present."""
    mock_get.return_value = SectionViewerSchema(
        title_number=18,
        section_number="112",
        heading="Protection of foreign officials",
        full_citation="18 U.S.C. § 112",
        text_content="(a) In General\n\tWhoever assaults...",
        provisions=[
            CodeLineSchema(
                line_number=1,
                content="In General",
                indent_level=0,
                marker="(a)",
                is_header=True,
                start_char=0,
                end_char=14,
            ),
            CodeLineSchema(
                line_number=2,
                content="Whoever assaults...",
                indent_level=1,
                marker=None,
                is_header=False,
                start_char=15,
                end_char=34,
            ),
        ],
        enacted_date=date(1948, 6, 25),
        last_modified_date=None,
        is_positive_law=True,
        is_repealed=False,
        notes=None,
    )

    response = client.get("/api/v1/sections/18/112")
    assert response.status_code == 200

    data = response.json()
    assert data["provisions"] is not None
    assert len(data["provisions"]) == 2

    first = data["provisions"][0]
    assert first["line_number"] == 1
    assert first["content"] == "In General"
    assert first["indent_level"] == 0
    assert first["marker"] == "(a)"
    assert first["is_header"] is True

    second = data["provisions"][1]
    assert second["line_number"] == 2
    assert second["content"] == "Whoever assaults..."
    assert second["indent_level"] == 1
    assert second["marker"] is None
    assert second["is_header"] is False


@patch("app.api.v1.sections.get_section", new_callable=AsyncMock)
def test_get_section_provisions_null_by_default(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Section endpoint returns null provisions when not available."""
    mock_get.return_value = SectionViewerSchema(
        title_number=17,
        section_number="106",
        heading="Exclusive rights in copyrighted works",
        full_citation="17 U.S.C. § 106",
        text_content="Subject to sections 107 through 122...",
        enacted_date=date(1976, 10, 19),
        last_modified_date=None,
        is_positive_law=True,
        is_repealed=False,
        notes=None,
    )

    response = client.get("/api/v1/sections/17/106")
    assert response.status_code == 200
    assert response.json()["provisions"] is None
