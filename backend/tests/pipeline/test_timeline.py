"""Tests for the consolidated timeline builder."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.olrc.release_point import ReleasePointInfo
from pipeline.timeline import (
    TimelineBuilder,
    TimelineEvent,
    TimelineEventType,
)


class TestTimelineEvent:
    """Tests for TimelineEvent dataclass."""

    def test_sort_key_laws_before_rps(self) -> None:
        """Laws should sort before release points on the same date."""
        law = TimelineEvent(
            event_type=TimelineEventType.PUBLIC_LAW,
            identifier="PL 118-25",
            congress=118,
            law_number=25,
            event_date=date(2024, 1, 15),
        )
        rp = TimelineEvent(
            event_type=TimelineEventType.RELEASE_POINT,
            identifier="118-25",
            congress=118,
            law_number=25,
            event_date=date(2024, 1, 15),
        )
        assert law.sort_key < rp.sort_key

    def test_sort_key_chronological(self) -> None:
        """Earlier dates sort before later dates."""
        early = TimelineEvent(
            event_type=TimelineEventType.PUBLIC_LAW,
            identifier="PL 118-10",
            congress=118,
            law_number=10,
            event_date=date(2024, 1, 1),
        )
        late = TimelineEvent(
            event_type=TimelineEventType.PUBLIC_LAW,
            identifier="PL 118-20",
            congress=118,
            law_number=20,
            event_date=date(2024, 6, 1),
        )
        assert early.sort_key < late.sort_key

    def test_sort_key_none_date(self) -> None:
        """Events with None date sort to the beginning."""
        no_date = TimelineEvent(
            event_type=TimelineEventType.RELEASE_POINT,
            identifier="113-21",
            congress=113,
            law_number=21,
            event_date=None,
        )
        with_date = TimelineEvent(
            event_type=TimelineEventType.RELEASE_POINT,
            identifier="113-30",
            congress=113,
            law_number=30,
            event_date=date(2014, 6, 1),
        )
        assert no_date.sort_key < with_date.sort_key

    def test_str_release_point(self) -> None:
        event = TimelineEvent(
            event_type=TimelineEventType.RELEASE_POINT,
            identifier="118-158",
            congress=118,
            law_number=158,
            event_date=date(2024, 12, 1),
        )
        assert "[RP]" in str(event)
        assert "118-158" in str(event)

    def test_str_public_law(self) -> None:
        event = TimelineEvent(
            event_type=TimelineEventType.PUBLIC_LAW,
            identifier="PL 118-25",
            congress=118,
            law_number=25,
            event_date=date(2024, 3, 1),
        )
        assert "[LAW]" in str(event)
        assert "118-25" in str(event)

    def test_deferred_laws(self) -> None:
        event = TimelineEvent(
            event_type=TimelineEventType.RELEASE_POINT,
            identifier="119-72not60",
            congress=119,
            law_number=72,
            event_date=date(2025, 6, 1),
            deferred_laws=[60],
        )
        assert event.deferred_laws == [60]


class TestTimelineBuilder:
    """Tests for TimelineBuilder."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        registry = MagicMock()
        registry.fetch_release_points = AsyncMock(return_value=[])
        registry.get_release_points.return_value = [
            ReleasePointInfo(
                full_identifier="113-21",
                congress=113,
                law_identifier="21",
                publication_date=date(2014, 1, 15),
            ),
            ReleasePointInfo(
                full_identifier="113-30",
                congress=113,
                law_identifier="30",
                publication_date=date(2014, 3, 1),
            ),
        ]
        return registry

    def test_get_summary_empty(self, mock_session: AsyncMock) -> None:
        builder = TimelineBuilder(mock_session)
        stats = builder.get_summary([])
        assert stats["total_events"] == 0
        assert stats["total_rps"] == 0
        assert stats["total_laws"] == 0

    def test_get_summary_mixed(self, mock_session: AsyncMock) -> None:
        events = [
            TimelineEvent(
                event_type=TimelineEventType.PUBLIC_LAW,
                identifier="PL 113-22",
                congress=113,
                law_number=22,
                event_date=date(2014, 1, 20),
            ),
            TimelineEvent(
                event_type=TimelineEventType.RELEASE_POINT,
                identifier="113-30",
                congress=113,
                law_number=30,
                event_date=date(2014, 3, 1),
            ),
            TimelineEvent(
                event_type=TimelineEventType.PUBLIC_LAW,
                identifier="PL 118-10",
                congress=118,
                law_number=10,
                event_date=date(2024, 1, 5),
            ),
        ]
        builder = TimelineBuilder(mock_session)
        stats = builder.get_summary(events)
        assert stats["total_events"] == 3
        assert stats["total_rps"] == 1
        assert stats["total_laws"] == 2
        assert 113 in stats["by_congress"]
        assert 118 in stats["by_congress"]
        assert stats["by_congress"][113]["rp_count"] == 1
        assert stats["by_congress"][113]["law_count"] == 1
        assert stats["by_congress"][118]["law_count"] == 1


class TestTimelineEventType:
    """Tests for TimelineEventType enum."""

    def test_values(self) -> None:
        assert TimelineEventType.RELEASE_POINT == "release_point"
        assert TimelineEventType.PUBLIC_LAW == "public_law"
