"""Tests for OLRC downloader."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

        assert "usc17" in url
        assert "119" in url  # Congress number
        assert url.startswith("https://uscode.house.gov/download/releasepoints/")

    def test_get_title_url_different_release_point(self, tmp_path) -> None:
        """Test URL generation with different release point."""
        downloader = OLRCDownloader(download_dir=tmp_path, release_point="118-100")
        url = downloader.get_title_url(17)

        assert "118" in url
        assert "100" in url

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


class TestDownloadTitleAtReleasePoint:
    """Tests for download_title_at_release_point's response validation."""

    @pytest.mark.asyncio
    async def test_non_zip_response_skipped_and_not_cached(self, tmp_path) -> None:
        """If the OLRC returns HTML (e.g., title not yet codified at this RP),
        treat it as 'not available' and skip — don't cache the bad bytes,
        otherwise every retry hits the cache and fails the same way."""
        cache = MagicMock()
        cache.get_bytes.return_value = None
        cache.put_bytes = MagicMock()

        downloader = OLRCDownloader(download_dir=tmp_path, cache=cache)

        html_body = b"<!DOCTYPE html><html><body>Not Found</body></html>"

        mock_response = MagicMock()
        mock_response.content = html_body
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(httpx, "AsyncClient", return_value=mock_client):
            result = await downloader.download_title_at_release_point(54, "113-21")

        assert result is None
        # Critical: HTML body must NOT be cached, otherwise subsequent runs
        # read the bogus bytes from GCS and fail the same way every time.
        cache.put_bytes.assert_not_called()
