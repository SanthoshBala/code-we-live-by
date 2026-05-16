"""Tests for is_positive_law propagation from title group to section response."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.olrc.snapshot_service import SectionState


def _make_section_state(
    title_number: int = 17,
    section_number: str = "107",
    heading: str = "Limitations on exclusive rights: Fair use",
) -> SectionState:
    return SectionState(
        title_number=title_number,
        section_number=section_number,
        heading=heading,
        text_content="Notwithstanding the provisions of sections 106 and 106A...",
        text_hash="abc",
        normalized_provisions=None,
        notes=None,
        normalized_notes=None,
        notes_hash=None,
        full_citation=f"{title_number} USC {section_number}",
        snapshot_id=1,
        revision_id=1,
        is_deleted=False,
    )


@pytest.mark.asyncio
@patch("app.crud.us_code.get_last_changed_revision_for_section", new_callable=AsyncMock)
@patch("app.crud.us_code._resolve_head_and_chain", new_callable=AsyncMock)
@patch("pipeline.olrc.snapshot_service.SnapshotService.get_section_at_revision")
async def test_get_section_inherits_is_positive_law_true(
    mock_get_state: AsyncMock,
    mock_resolve: AsyncMock,
    mock_last_rev: AsyncMock,
) -> None:
    """get_section propagates is_positive_law=True from the title's SectionGroup."""
    from app.crud.us_code import get_section

    mock_resolve.return_value = (1, [1])
    mock_get_state.return_value = _make_section_state()
    mock_last_rev.return_value = None

    # Mock session.execute to return a title group with is_positive_law=True
    title_group = MagicMock()
    title_group.is_positive_law = True
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = title_group

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    result = await get_section(session, title_number=17, section_number="107")

    assert result is not None
    assert result.is_positive_law is True


@pytest.mark.asyncio
@patch("app.crud.us_code.get_last_changed_revision_for_section", new_callable=AsyncMock)
@patch("app.crud.us_code._resolve_head_and_chain", new_callable=AsyncMock)
@patch("pipeline.olrc.snapshot_service.SnapshotService.get_section_at_revision")
async def test_get_section_is_positive_law_false_for_non_positive_title(
    mock_get_state: AsyncMock,
    mock_resolve: AsyncMock,
    mock_last_rev: AsyncMock,
) -> None:
    """get_section returns is_positive_law=False for non-positive-law titles."""
    from app.crud.us_code import get_section

    mock_resolve.return_value = (1, [1])
    mock_get_state.return_value = _make_section_state(title_number=2, section_number="3")
    mock_last_rev.return_value = None

    title_group = MagicMock()
    title_group.is_positive_law = False
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = title_group

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    result = await get_section(session, title_number=2, section_number="3")

    assert result is not None
    assert result.is_positive_law is False


@pytest.mark.asyncio
@patch("app.crud.us_code.get_last_changed_revision_for_section", new_callable=AsyncMock)
@patch("app.crud.us_code._resolve_head_and_chain", new_callable=AsyncMock)
@patch("pipeline.olrc.snapshot_service.SnapshotService.get_section_at_revision")
async def test_get_section_is_positive_law_false_when_title_group_missing(
    mock_get_state: AsyncMock,
    mock_resolve: AsyncMock,
    mock_last_rev: AsyncMock,
) -> None:
    """get_section defaults is_positive_law=False when title group is absent."""
    from app.crud.us_code import get_section

    mock_resolve.return_value = (1, [1])
    mock_get_state.return_value = _make_section_state()
    mock_last_rev.return_value = None

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None  # title group not found

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    result = await get_section(session, title_number=17, section_number="107")

    assert result is not None
    assert result.is_positive_law is False
