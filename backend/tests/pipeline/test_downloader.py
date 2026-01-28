"""Tests for OLRC downloader."""

import pytest

from pipeline.olrc.downloader import PHASE_1_TITLES, OLRCDownloader


class TestOLRCDownloader:
    """Tests for OLRCDownloader class."""

    @pytest.fixture
    def downloader(self, tmp_path) -> OLRCDownloader:
        """Create a downloader instance with temp directory."""
        return OLRCDownloader(download_dir=tmp_path)

    def test_init_creates_directory(self, tmp_path) -> None:
        """Test that initialization creates the download directory."""
        download_dir = tmp_path / "olrc_data"
        downloader = OLRCDownloader(download_dir=download_dir)

        assert download_dir.exists()
        assert downloader.download_dir == download_dir

    def test_get_title_url(self, downloader: OLRCDownloader) -> None:
        """Test URL generation for titles."""
        url = downloader.get_title_url(17)

        assert "title17" in url
        assert "2024" in url
        assert url.startswith("https://uscode.house.gov/download/xml/")

    def test_get_title_url_different_year(self, tmp_path) -> None:
        """Test URL generation with different year."""
        downloader = OLRCDownloader(download_dir=tmp_path, year=2023)
        url = downloader.get_title_url(17)

        assert "2023" in url

    def test_get_downloaded_titles_empty(self, downloader: OLRCDownloader) -> None:
        """Test get_downloaded_titles with no downloads."""
        titles = downloader.get_downloaded_titles()

        assert titles == []

    def test_get_downloaded_titles_with_files(self, tmp_path) -> None:
        """Test get_downloaded_titles with downloaded files."""
        downloader = OLRCDownloader(download_dir=tmp_path)

        # Create fake downloaded title directories
        (tmp_path / "title17").mkdir()
        (tmp_path / "title17" / "test.xml").write_text("<xml/>")
        (tmp_path / "title18").mkdir()
        (tmp_path / "title18" / "test.xml").write_text("<xml/>")

        titles = downloader.get_downloaded_titles()

        assert sorted(titles) == [17, 18]

    def test_get_xml_path_exists(self, tmp_path) -> None:
        """Test get_xml_path when file exists."""
        downloader = OLRCDownloader(download_dir=tmp_path)

        # Create fake downloaded file
        (tmp_path / "title17").mkdir()
        xml_file = tmp_path / "title17" / "USCODE-2024-title17.xml"
        xml_file.write_text("<xml/>")

        path = downloader.get_xml_path(17)

        assert path is not None
        assert path == xml_file

    def test_get_xml_path_not_exists(self, downloader: OLRCDownloader) -> None:
        """Test get_xml_path when file doesn't exist."""
        path = downloader.get_xml_path(99)

        assert path is None


class TestPhase1Titles:
    """Tests for Phase 1 title configuration."""

    def test_phase1_titles_defined(self) -> None:
        """Test that Phase 1 titles are defined."""
        assert len(PHASE_1_TITLES) > 0

    def test_phase1_titles_valid_range(self) -> None:
        """Test that Phase 1 titles are in valid range (1-54)."""
        for title in PHASE_1_TITLES:
            assert 1 <= title <= 54

    def test_phase1_includes_key_titles(self) -> None:
        """Test that Phase 1 includes key titles for the project."""
        # Title 17 (Copyrights) and Title 18 (Crimes) are commonly referenced
        assert 17 in PHASE_1_TITLES
        assert 18 in PHASE_1_TITLES
