"""Tests for OLRC release point infrastructure."""

from datetime import date

import pytest

from pipeline.olrc.downloader import OLRCDownloader
from pipeline.olrc.release_point import (
    ReleasePointInfo,
    ReleasePointRegistry,
    parse_release_point_identifier,
)


class TestParseReleasePointIdentifier:
    """Tests for parse_release_point_identifier."""

    def test_simple_identifier(self) -> None:
        congress, law_id = parse_release_point_identifier("118-158")
        assert congress == 118
        assert law_id == "158"

    def test_identifier_with_exclusion(self) -> None:
        congress, law_id = parse_release_point_identifier("119-72not60")
        assert congress == 119
        assert law_id == "72not60"

    def test_early_congress(self) -> None:
        congress, law_id = parse_release_point_identifier("113-21")
        assert congress == 113
        assert law_id == "21"

    def test_invalid_no_dash(self) -> None:
        with pytest.raises(ValueError, match="Invalid release point identifier"):
            parse_release_point_identifier("118158")

    def test_invalid_non_numeric_congress(self) -> None:
        with pytest.raises(ValueError, match="Invalid congress number"):
            parse_release_point_identifier("abc-158")


class TestReleasePointInfo:
    """Tests for ReleasePointInfo dataclass."""

    def test_primary_law_number(self) -> None:
        rp = ReleasePointInfo(
            full_identifier="118-158",
            congress=118,
            law_identifier="158",
        )
        assert rp.primary_law_number == 158

    def test_primary_law_number_with_exclusion(self) -> None:
        rp = ReleasePointInfo(
            full_identifier="119-72not60",
            congress=119,
            law_identifier="72not60",
        )
        assert rp.primary_law_number == 72

    def test_excluded_laws(self) -> None:
        rp = ReleasePointInfo(
            full_identifier="119-72not60",
            congress=119,
            law_identifier="72not60",
        )
        assert rp.excluded_laws == [60]

    def test_excluded_laws_none(self) -> None:
        rp = ReleasePointInfo(
            full_identifier="118-158",
            congress=118,
            law_identifier="158",
        )
        assert rp.excluded_laws == []

    def test_str(self) -> None:
        rp = ReleasePointInfo(
            full_identifier="118-158",
            congress=118,
            law_identifier="158",
        )
        assert str(rp) == "PL 118-158"


class TestReleasePointRegistry:
    """Tests for ReleasePointRegistry."""

    @pytest.fixture
    def registry_with_data(self) -> ReleasePointRegistry:
        """Create a registry pre-populated with test data."""
        registry = ReleasePointRegistry()
        registry._release_points = [
            ReleasePointInfo(
                full_identifier="113-21",
                congress=113,
                law_identifier="21",
            ),
            ReleasePointInfo(
                full_identifier="113-30",
                congress=113,
                law_identifier="30",
            ),
            ReleasePointInfo(
                full_identifier="113-50",
                congress=113,
                law_identifier="50",
            ),
            ReleasePointInfo(
                full_identifier="118-22",
                congress=118,
                law_identifier="22",
            ),
            ReleasePointInfo(
                full_identifier="118-30",
                congress=118,
                law_identifier="30",
            ),
        ]
        return registry

    def test_get_release_points_not_loaded(self) -> None:
        registry = ReleasePointRegistry()
        with pytest.raises(RuntimeError, match="not loaded"):
            registry.get_release_points()

    def test_get_release_points(self, registry_with_data: ReleasePointRegistry) -> None:
        rps = registry_with_data.get_release_points()
        assert len(rps) == 5

    def test_get_by_identifier(self, registry_with_data: ReleasePointRegistry) -> None:
        rp = registry_with_data.get_by_identifier("113-21")
        assert rp is not None
        assert rp.congress == 113
        assert rp.law_identifier == "21"

    def test_get_by_identifier_not_found(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        rp = registry_with_data.get_by_identifier("999-999")
        assert rp is None

    def test_get_for_congress(self, registry_with_data: ReleasePointRegistry) -> None:
        rps = registry_with_data.get_for_congress(113)
        assert len(rps) == 3
        assert all(rp.congress == 113 for rp in rps)

    def test_get_for_congress_empty(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        rps = registry_with_data.get_for_congress(999)
        assert len(rps) == 0

    def test_get_adjacent_pairs(self, registry_with_data: ReleasePointRegistry) -> None:
        pairs = registry_with_data.get_adjacent_pairs()
        assert len(pairs) == 4
        # First pair
        assert pairs[0][0].full_identifier == "113-21"
        assert pairs[0][1].full_identifier == "113-30"
        # Last pair
        assert pairs[3][0].full_identifier == "118-22"
        assert pairs[3][1].full_identifier == "118-30"

    def test_get_adjacent_pairs_filtered(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        pairs = registry_with_data.get_adjacent_pairs(congress=113)
        assert len(pairs) == 2

    def test_get_laws_in_range_same_congress(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        laws = registry_with_data.get_laws_in_range("118-22", "118-30")
        assert len(laws) == 8
        assert laws[0] == (118, 23)
        assert laws[-1] == (118, 30)

    def test_get_laws_in_range_single_law(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        laws = registry_with_data.get_laws_in_range("113-21", "113-22")
        assert laws == [(113, 22)]

    def test_get_laws_in_range_cross_congress(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        """Cross-congress range with last_law_of_congress provided."""
        laws = registry_with_data.get_laws_in_range(
            "113-50",
            "118-22",
            last_law_of_congress={113: 52},
        )
        # 113-51, 113-52, then 118-1 through 118-22
        assert laws[0] == (113, 51)
        assert laws[1] == (113, 52)
        assert laws[2] == (118, 1)
        assert laws[-1] == (118, 22)
        assert len(laws) == 2 + 22

    def test_get_laws_in_range_cross_congress_no_lookup(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        """Cross-congress range without lookup returns empty with warning."""
        laws = registry_with_data.get_laws_in_range("113-50", "118-22")
        assert laws == []

    def test_get_titles_at_release_point(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        titles = registry_with_data.get_titles_at_release_point("113-21")
        assert titles == []  # No titles set in test data

    def test_get_titles_at_release_point_not_found(
        self, registry_with_data: ReleasePointRegistry
    ) -> None:
        titles = registry_with_data.get_titles_at_release_point("999-999")
        assert titles == []

    def test_parse_link_simple(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "/download/releasepoints/us/pl/118/158/xml_usc17@118-158.zip"
        )
        assert rp is not None
        assert rp.full_identifier == "118-158"
        assert rp.congress == 118
        assert rp.law_identifier == "158"

    def test_parse_link_with_exclusion(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "/download/releasepoints/us/pl/119/72not60/xml_usc17@119-72not60.zip"
        )
        assert rp is not None
        assert rp.full_identifier == "119-72not60"
        assert rp.congress == 119
        assert rp.law_identifier == "72not60"

    def test_parse_link_no_match(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link("/some/other/path")
        assert rp is None

    def test_parse_link_with_date_and_titles(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "releasepoints/us/pl/119/72not60/usc-rp@119-72not60.htm",
            "Public Law 119-72 (01/20/2026) , except 119-60, "
            "affecting titles 38, 42.",
        )
        assert rp is not None
        assert rp.full_identifier == "119-72not60"
        assert rp.publication_date == date(2026, 1, 20)
        assert rp.titles_available == [38, 42]

    def test_parse_link_single_title(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "releasepoints/us/pl/119/59/usc-rp@119-59.htm",
            "Public Law 119-59 (12/18/2025), affecting title 16.",
        )
        assert rp is not None
        assert rp.publication_date == date(2025, 12, 18)
        assert rp.titles_available == [16]

    def test_parse_link_many_titles_with_letter_suffix(self) -> None:
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "releasepoints/us/pl/119/43/usc-rp@119-43.htm",
            "Public Law 119-43 (12/01/2025), affecting titles "
            "1, 2, 5, 7, 10, 11A, 12, 16, 18, 18A, 21, 22, 26, "
            "28, 28A, 38, 42, 49, 54.",
        )
        assert rp is not None
        assert rp.publication_date == date(2025, 12, 1)
        assert 11 in rp.titles_available
        assert 18 in rp.titles_available
        assert 28 in rp.titles_available
        assert 54 in rp.titles_available

    def test_parse_link_no_text(self) -> None:
        """Backwards compatibility: no link text still works."""
        registry = ReleasePointRegistry()
        rp = registry._parse_release_point_link(
            "releasepoints/us/pl/118/158/xml_usc17@118-158.zip",
        )
        assert rp is not None
        assert rp.full_identifier == "118-158"
        assert rp.publication_date is None
        assert rp.titles_available == []


class TestReleasePointSortOrder:
    """Tests for release point chronological ordering."""

    def test_exclusions_sort_before_no_exclusions(self) -> None:
        """More exclusions = earlier state, should sort first."""
        registry = ReleasePointRegistry()
        registry._release_points = [
            ReleasePointInfo(
                full_identifier="113-296",
                congress=113,
                law_identifier="296",
            ),
            ReleasePointInfo(
                full_identifier="113-296not287",
                congress=113,
                law_identifier="296not287",
            ),
            ReleasePointInfo(
                full_identifier="113-296not287not291not295",
                congress=113,
                law_identifier="296not287not291not295",
            ),
            ReleasePointInfo(
                full_identifier="113-296not287not291",
                congress=113,
                law_identifier="296not287not291",
            ),
        ]
        # Re-sort using the same logic as fetch_release_points
        registry._release_points.sort(
            key=lambda rp: (
                rp.congress,
                rp.primary_law_number or 0,
                -len(rp.excluded_laws),
            )
        )

        ids = [rp.full_identifier for rp in registry._release_points]
        assert ids == [
            "113-296not287not291not295",  # 3 exclusions (earliest)
            "113-296not287not291",  # 2 exclusions
            "113-296not287",  # 1 exclusion
            "113-296",  # 0 exclusions (latest, most comprehensive)
        ]

    def test_exclusions_sort_within_congress(self) -> None:
        """Normal law progression sorts before exclusion variants."""
        registry = ReleasePointRegistry()
        registry._release_points = [
            ReleasePointInfo(
                full_identifier="113-296",
                congress=113,
                law_identifier="296",
            ),
            ReleasePointInfo(
                full_identifier="113-200",
                congress=113,
                law_identifier="200",
            ),
            ReleasePointInfo(
                full_identifier="113-296not287",
                congress=113,
                law_identifier="296not287",
            ),
        ]
        registry._release_points.sort(
            key=lambda rp: (
                rp.congress,
                rp.primary_law_number or 0,
                -len(rp.excluded_laws),
            )
        )

        ids = [rp.full_identifier for rp in registry._release_points]
        assert ids == [
            "113-200",
            "113-296not287",
            "113-296",
        ]


    def test_update_suffix_sorts_by_date(self) -> None:
        """Update suffixes (u1) sort after the base RP by publication date."""
        registry = ReleasePointRegistry()
        registry._release_points = [
            ReleasePointInfo(
                full_identifier="113-145not128u1",
                congress=113,
                law_identifier="145not128u1",
                publication_date=date(2014, 8, 20),
            ),
            ReleasePointInfo(
                full_identifier="113-145not128",
                congress=113,
                law_identifier="145not128",
                publication_date=date(2014, 8, 4),
            ),
        ]
        registry._release_points.sort(
            key=lambda rp: (
                rp.congress,
                rp.primary_law_number or 0,
                -len(rp.excluded_laws),
                rp.publication_date or date.min,
            )
        )

        ids = [rp.full_identifier for rp in registry._release_points]
        assert ids == [
            "113-145not128",  # 2014.08.04 (earlier)
            "113-145not128u1",  # 2014.08.20 (later update)
        ]


class TestOLRCDownloaderReleasePoints:
    """Tests for multi-release-point download support."""

    @pytest.fixture
    def downloader(self, tmp_path) -> OLRCDownloader:
        return OLRCDownloader(download_dir=tmp_path)

    def test_get_xml_path_at_release_point_not_exists(
        self, downloader: OLRCDownloader
    ) -> None:
        path = downloader.get_xml_path_at_release_point(17, "113-21")
        assert path is None

    def test_get_xml_path_at_release_point_exists(self, tmp_path) -> None:
        downloader = OLRCDownloader(download_dir=tmp_path)

        # Create fake downloaded file at release point
        rp_dir = tmp_path / "releases" / "113-21" / "title17"
        rp_dir.mkdir(parents=True)
        xml_file = rp_dir / "usc17@113-21.xml"
        xml_file.write_text("<xml/>")

        path = downloader.get_xml_path_at_release_point(17, "113-21")
        assert path is not None
        assert path == xml_file

    def test_release_point_cache_isolation(self, tmp_path) -> None:
        """Different release points should have separate cache directories."""
        downloader = OLRCDownloader(download_dir=tmp_path)

        # Create fake files for two different release points
        for rp in ["113-21", "113-30"]:
            rp_dir = tmp_path / "releases" / rp / "title17"
            rp_dir.mkdir(parents=True)
            (rp_dir / f"usc17@{rp}.xml").write_text(f"<xml rp='{rp}'/>")

        path_21 = downloader.get_xml_path_at_release_point(17, "113-21")
        path_30 = downloader.get_xml_path_at_release_point(17, "113-30")

        assert path_21 is not None
        assert path_30 is not None
        assert path_21 != path_30
        assert "113-21" in str(path_21)
        assert "113-30" in str(path_30)
