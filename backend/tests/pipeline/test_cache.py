"""Tests for PipelineCache (local + optional GCS backing)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.cache import PipelineCache


@pytest.fixture
def tmp_cache(tmp_path: Path) -> PipelineCache:
    """Create a local-only PipelineCache in a temp dir."""
    return PipelineCache(local_root=tmp_path, bucket_name=None)


class TestLocalOnly:
    """Tests for local-only caching (no GCS)."""

    def test_put_and_get_text(self, tmp_cache: PipelineCache) -> None:
        tmp_cache.put_text("foo/bar.json", '{"x": 1}')
        assert tmp_cache.get_text("foo/bar.json") == '{"x": 1}'

    def test_get_text_miss(self, tmp_cache: PipelineCache) -> None:
        assert tmp_cache.get_text("missing/key.json") is None

    def test_put_and_get_bytes(self, tmp_cache: PipelineCache) -> None:
        data = b"\x00\x01\x02"
        tmp_cache.put_bytes("archive.zip", data)
        assert tmp_cache.get_bytes("archive.zip") == data

    def test_get_bytes_miss(self, tmp_cache: PipelineCache) -> None:
        assert tmp_cache.get_bytes("missing.zip") is None

    def test_has_local(self, tmp_cache: PipelineCache) -> None:
        assert not tmp_cache.has_local("thing.txt")
        tmp_cache.put_text("thing.txt", "hello")
        assert tmp_cache.has_local("thing.txt")

    def test_local_path(self, tmp_cache: PipelineCache) -> None:
        path = tmp_cache.local_path("sub/dir/file.xml")
        assert path == tmp_cache.local_root / "sub" / "dir" / "file.xml"

    def test_no_gcs_when_bucket_unset(self, tmp_cache: PipelineCache) -> None:
        assert tmp_cache._init_gcs() is False
        assert tmp_cache._gcs_available is False


class TestGCSIntegration:
    """Tests for GCS-backed caching with mocked google.cloud.storage."""

    def _make_cache_with_mock_gcs(
        self, tmp_path: Path
    ) -> tuple[PipelineCache, MagicMock]:
        """Create a PipelineCache with a mocked GCS bucket."""
        mock_bucket = MagicMock()
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        cache = PipelineCache(local_root=tmp_path, bucket_name="test-bucket")

        with patch("pipeline.cache.PipelineCache._init_gcs") as mock_init:
            # Simulate successful GCS init
            def init_gcs_side_effect() -> bool:
                cache._gcs_available = True
                cache._gcs_bucket = mock_bucket
                return True

            mock_init.side_effect = init_gcs_side_effect

            # Force init
            cache._init_gcs()

        return cache, mock_bucket

    def test_get_text_gcs_hit_backfills_local(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        blob.exists.return_value = True
        blob.download_as_text.return_value = '{"from": "gcs"}'
        mock_bucket.blob.return_value = blob

        result = cache.get_text("govinfo/plaw/test.json")

        assert result == '{"from": "gcs"}'
        # Verify local backfill
        local = tmp_path / "govinfo" / "plaw" / "test.json"
        assert local.exists()
        assert local.read_text() == '{"from": "gcs"}'

    def test_put_text_writes_both(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        mock_bucket.blob.return_value = blob

        cache.put_text("key.json", "content")

        # Local write
        assert (tmp_path / "key.json").read_text() == "content"
        # GCS write
        blob.upload_from_string.assert_called_once_with(
            "content", content_type="text/plain"
        )

    def test_get_bytes_gcs_hit_backfills_local(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        blob.exists.return_value = True
        blob.download_as_bytes.return_value = b"zipdata"
        mock_bucket.blob.return_value = blob

        result = cache.get_bytes("olrc/test.zip")

        assert result == b"zipdata"
        local = tmp_path / "olrc" / "test.zip"
        assert local.exists()
        assert local.read_bytes() == b"zipdata"

    def test_put_bytes_writes_both(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        mock_bucket.blob.return_value = blob

        cache.put_bytes("data.zip", b"\x01\x02")

        assert (tmp_path / "data.zip").read_bytes() == b"\x01\x02"
        blob.upload_from_string.assert_called_once_with(
            b"\x01\x02", content_type="application/octet-stream"
        )

    def test_local_hit_skips_gcs(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        # Pre-populate local
        local = tmp_path / "cached.json"
        local.write_text("local-content")

        result = cache.get_text("cached.json")

        assert result == "local-content"
        # GCS should not be called
        mock_bucket.blob.assert_not_called()

    def test_gcs_miss_returns_none(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        blob.exists.return_value = False
        mock_bucket.blob.return_value = blob

        assert cache.get_text("missing.json") is None

    def test_graceful_gcs_failure_on_get(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        mock_bucket.blob.side_effect = Exception("GCS connection error")

        # Should not raise, just return None
        result = cache.get_text("failing.json")
        assert result is None

    def test_graceful_gcs_failure_on_put(self, tmp_path: Path) -> None:
        cache, mock_bucket = self._make_cache_with_mock_gcs(tmp_path)

        blob = MagicMock()
        blob.upload_from_string.side_effect = Exception("GCS upload error")
        mock_bucket.blob.return_value = blob

        # Should not raise; local write still succeeds
        cache.put_text("key.json", "content")
        assert (tmp_path / "key.json").read_text() == "content"


class TestGCSInitFailure:
    """Test that GCS init failure degrades gracefully to local-only."""

    def test_import_error_falls_back_to_local(self, tmp_path: Path) -> None:
        cache = PipelineCache(local_root=tmp_path, bucket_name="test-bucket")

        with (
            patch.dict("sys.modules", {"google.cloud.storage": None}),
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'google.cloud.storage'"),
            ),
        ):
            result = cache._init_gcs()

        assert result is False
        assert cache._gcs_available is False

        # Local caching still works
        cache.put_text("key.txt", "value")
        assert cache.get_text("key.txt") == "value"
