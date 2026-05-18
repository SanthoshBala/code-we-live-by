"""Tests for the standalone-provisions endpoint and XML extraction logic."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.crud.public_law import _extract_standalone_provisions_from_xml
from app.schemas.law_viewer import StandaloneProvisionSchema

# ---------------------------------------------------------------------------
# Minimal USLM XML fixtures
# ---------------------------------------------------------------------------

_INSTRUCTION_ONLY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section role="instruction" identifier="/us/pl/113/23/s2">
    <num>Sec. 2.</num>
    <heading>Amendments to title 16</heading>
    <content>
      <amendingAction type="insert"/>
      <quotedText>new text here</quotedText>
    </content>
  </section>
</document>
"""

_FREESTANDING_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section role="instruction" identifier="/us/pl/113/23/s2">
    <num>Sec. 2.</num>
    <heading>Amendments to title 16</heading>
    <content>
      <amendingAction type="insert"/>
    </content>
  </section>
  <section identifier="/us/pl/113/23/s3">
    <num>Sec. 3.</num>
    <heading>The bridge shall be known as the Liberty Bridge.</heading>
    <content>The bridge located in Springfield shall henceforth be known as the Liberty Bridge.</content>
  </section>
  <section identifier="/us/pl/113/23/s4">
    <num>Sec. 4.</num>
    <heading>Effective Date.</heading>
    <content>This Act shall take effect 90 days after the date of enactment.</content>
  </section>
</document>
"""

_SIDENOTE_SECTION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section identifier="/us/pl/113/23/s5">
    <sidenote>16 U.S.C. 797 note</sidenote>
    <num>Sec. 5.</num>
    <content>This is a statutory note provision.</content>
  </section>
</document>
"""

_EMPTY_BODY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section identifier="/us/pl/113/23/s6">
    <num>Sec. 6.</num>
    <heading>Reserved</heading>
  </section>
</document>
"""


# ---------------------------------------------------------------------------
# Unit tests: _extract_standalone_provisions_from_xml
# ---------------------------------------------------------------------------


def test_no_standalone_provisions_when_instruction_only() -> None:
    """Amending instruction sections are not returned as standalone provisions."""
    result = _extract_standalone_provisions_from_xml(_INSTRUCTION_ONLY_XML, 113, 23)
    assert result == []


def test_extracts_freestanding_sections() -> None:
    """Non-instruction, non-sidenote sections are returned as standalone provisions."""
    result = _extract_standalone_provisions_from_xml(_FREESTANDING_XML, 113, 23)
    assert len(result) == 2
    nums = {p.section_num for p in result}
    assert "Sec. 3." in nums
    assert "Sec. 4." in nums


def test_headings_are_extracted() -> None:
    """Headings are extracted from freestanding sections."""
    result = _extract_standalone_provisions_from_xml(_FREESTANDING_XML, 113, 23)
    headings = {p.heading for p in result}
    assert "Effective Date." in headings


def test_sidenote_sections_are_excluded() -> None:
    """Sections with sidenotes (Add_Note stubs) are not returned."""
    result = _extract_standalone_provisions_from_xml(_SIDENOTE_SECTION_XML, 113, 23)
    assert result == []


def test_empty_body_sections_are_excluded() -> None:
    """Sections with no text body after stripping num/heading are skipped."""
    result = _extract_standalone_provisions_from_xml(_EMPTY_BODY_XML, 113, 23)
    assert result == []


def test_govinfo_url_is_set() -> None:
    """GovInfo URL is constructed from congress and law_number."""
    result = _extract_standalone_provisions_from_xml(_FREESTANDING_XML, 113, 23)
    assert all(p.govinfo_url is not None for p in result)
    assert all("PLAW-113publ23" in (p.govinfo_url or "") for p in result)


def test_excerpt_truncated_at_limit() -> None:
    """text_excerpt is truncated at 300 chars with an ellipsis."""
    long_text = "x" * 500
    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section identifier="/us/pl/113/23/s3">
    <num>Sec. 3.</num>
    <content>{long_text}</content>
  </section>
</document>
"""
    result = _extract_standalone_provisions_from_xml(xml, 113, 23)
    assert len(result) == 1
    assert result[0].text_excerpt.endswith("…")
    assert len(result[0].text_excerpt) <= 304  # 300 + ellipsis


def test_full_text_is_not_truncated() -> None:
    """full_text contains the complete provision text."""
    long_text = "x" * 500
    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://schemas.gpo.gov/xml/uslm">
  <section identifier="/us/pl/113/23/s3">
    <num>Sec. 3.</num>
    <content>{long_text}</content>
  </section>
</document>
"""
    result = _extract_standalone_provisions_from_xml(xml, 113, 23)
    assert len(result) == 1
    assert long_text in result[0].full_text


def test_malformed_xml_returns_empty() -> None:
    """Malformed XML is handled gracefully."""
    result = _extract_standalone_provisions_from_xml("<not valid xml>>>", 113, 23)
    assert result == []


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@patch(
    "app.api.v1.laws.get_law_standalone_provisions",
    new_callable=AsyncMock,
)
def test_endpoint_returns_provisions(mock_fn: AsyncMock, client: TestClient) -> None:
    """The standalone-provisions endpoint returns provisions from the CRUD layer."""
    mock_fn.return_value = [
        StandaloneProvisionSchema(
            section_num="Sec. 3.",
            heading="Naming",
            text_excerpt="The bridge shall be known…",
            full_text="The bridge shall be known as the Liberty Bridge.",
            govinfo_url="https://www.govinfo.gov/content/pkg/PLAW-113publ23/htm/PLAW-113publ23.htm",
        )
    ]

    response = client.get("/api/v1/laws/113/23/standalone-provisions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["section_num"] == "Sec. 3."
    assert data[0]["heading"] == "Naming"
    assert "govinfo_url" in data[0]


@patch(
    "app.api.v1.laws.get_law_standalone_provisions",
    new_callable=AsyncMock,
)
def test_endpoint_returns_empty_list_when_none(
    mock_fn: AsyncMock, client: TestClient
) -> None:
    """Returns an empty list when there are no standalone provisions."""
    mock_fn.return_value = []

    response = client.get("/api/v1/laws/113/23/standalone-provisions")
    assert response.status_code == 200
    assert response.json() == []
