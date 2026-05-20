"""Tests for the CODEOWNERS /committees API endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.committees import (
    CommitteeBaseSchema,
    CommitteeCongressInstanceSchema,
    CommitteeOwnershipSchema,
)

_HOUSE_JUDICIARY = CommitteeBaseSchema(
    committee_code="house-judiciary",
    chamber="House",
    name="Committee on the Judiciary",
    url="https://judiciary.house.gov/",
)
_SENATE_JUDICIARY = CommitteeBaseSchema(
    committee_code="senate-judiciary",
    chamber="Senate",
    name="Committee on the Judiciary",
    url="https://www.judiciary.senate.gov/",
)
_HOUSE_WAYS_MEANS = CommitteeBaseSchema(
    committee_code="house-ways-and-means",
    chamber="House",
    name="Committee on Ways and Means",
    url="https://waysandmeans.house.gov/",
)
_SENATE_FINANCE = CommitteeBaseSchema(
    committee_code="senate-finance",
    chamber="Senate",
    name="Committee on Finance",
    url="https://www.finance.senate.gov/",
)
_HOUSE_ENERGY = CommitteeBaseSchema(
    committee_code="house-energy-and-commerce",
    chamber="House",
    name="Committee on Energy and Commerce",
    url="https://energycommerce.house.gov/",
)
_SENATE_HELP = CommitteeBaseSchema(
    committee_code="senate-help",
    chamber="Senate",
    name="Committee on Health, Education, Labor, and Pensions",
    url="https://www.help.senate.gov/",
)


def _ownership(
    committee: CommitteeBaseSchema,
    title: int,
    chapter: str | None = None,
    jtype: str = "primary",
    order: int = 0,
) -> CommitteeOwnershipSchema:
    return CommitteeOwnershipSchema(
        committee=committee,
        jurisdiction_type=jtype,
        display_order=order,
        title_number=title,
        chapter_number=chapter,
        notes=None,
        congress_start=106,
        congress_end=None,
    )


# ── GET /committees/owners/title/{title_number} ──────────────────────────────


@patch("app.api.v1.committees.get_owners_for_title", new_callable=AsyncMock)
def test_owners_for_title_17_returns_judiciary(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Title 17 ownership returns Judiciary committees."""
    mock_get.return_value = [
        _ownership(_HOUSE_JUDICIARY, 17, order=0),
        _ownership(_SENATE_JUDICIARY, 17, order=1),
    ]
    resp = client.get("/api/v1/committees/owners/title/17")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title_number"] == 17
    assert data["chapter_number"] is None
    assert len(data["owners"]) == 2
    codes = [o["committee"]["committee_code"] for o in data["owners"]]
    assert "house-judiciary" in codes
    assert "senate-judiciary" in codes


@patch("app.api.v1.committees.get_owners_for_title", new_callable=AsyncMock)
def test_owners_for_title_congress_param_forwarded(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """congress query param is forwarded to the CRUD function."""
    mock_get.return_value = []
    client.get("/api/v1/committees/owners/title/17?congress=110")
    mock_get.assert_awaited_once()
    _, kwargs = mock_get.call_args
    assert kwargs.get("congress") == 110 or mock_get.call_args.args[2] == 110


# ── GET /committees/owners/title/{title}/chapter/{chapter} ───────────────────


@patch("app.api.v1.committees.get_owners_for_chapter", new_callable=AsyncMock)
def test_chapter_7_of_title_42_returns_finance(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """Title 42 chapter 7 returns Finance/Ways and Means, not HELP/E&C."""
    mock_get.return_value = [
        _ownership(_HOUSE_WAYS_MEANS, 42, chapter="7", order=0),
        _ownership(_SENATE_FINANCE, 42, chapter="7", order=1),
    ]
    resp = client.get("/api/v1/committees/owners/title/42/chapter/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title_number"] == 42
    assert data["chapter_number"] == "7"
    codes = [o["committee"]["committee_code"] for o in data["owners"]]
    assert "house-ways-and-means" in codes
    assert "senate-finance" in codes
    assert "house-energy-and-commerce" not in codes
    assert "senate-help" not in codes


@patch("app.api.v1.committees.get_owners_for_chapter", new_callable=AsyncMock)
def test_title_level_fallback_for_unknown_chapter(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """When no chapter-level override exists, falls back to title-level ownership."""
    mock_get.return_value = [
        _ownership(_HOUSE_ENERGY, 42, order=0),
        _ownership(_SENATE_HELP, 42, order=1),
    ]
    resp = client.get("/api/v1/committees/owners/title/42/chapter/999")
    assert resp.status_code == 200
    data = resp.json()
    codes = [o["committee"]["committee_code"] for o in data["owners"]]
    assert "house-energy-and-commerce" in codes


# ── GET /committees/congress/{congress}/owners ────────────────────────────────


@patch("app.api.v1.committees.get_all_mappings", new_callable=AsyncMock)
def test_all_owners_for_congress(mock_get: AsyncMock, client: TestClient) -> None:
    """Returns all mappings for the given Congress."""
    mock_get.return_value = [
        _ownership(_HOUSE_JUDICIARY, 17),
        _ownership(_SENATE_JUDICIARY, 17, order=1),
    ]
    resp = client.get("/api/v1/committees/congress/119/owners")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


# ── GET /committees/congress/{congress}/instances ─────────────────────────────


@patch("app.api.v1.committees.get_congress_instances", new_callable=AsyncMock)
def test_congress_instances(mock_get: AsyncMock, client: TestClient) -> None:
    """Returns committee congress instances for the given Congress."""
    mock_get.return_value = [
        CommitteeCongressInstanceSchema(
            committee_code="house-judiciary",
            chamber="House",
            official_name="Committee on the Judiciary",
            congress=119,
            rule_citation="House Rule X, Clause 1(l)",
        )
    ]
    resp = client.get("/api/v1/committees/congress/119/instances")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["committee_code"] == "house-judiciary"
    assert data[0]["rule_citation"] == "House Rule X, Clause 1(l)"


@patch("app.api.v1.committees.get_congress_instances", new_callable=AsyncMock)
def test_congress_instances_chamber_filter(
    mock_get: AsyncMock, client: TestClient
) -> None:
    """chamber query param is forwarded to the CRUD function."""
    mock_get.return_value = []
    client.get("/api/v1/committees/congress/119/instances?chamber=Senate")
    mock_get.assert_awaited_once()
