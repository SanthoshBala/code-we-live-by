"""Pipeline cache abstraction with local filesystem + optional GCS backing.

Provides a two-layer cache: local filesystem (fast) backed by GCS (shared).
When GCS_CACHE_BUCKET is unset, behaves as local-only cache.

Cache keys mirror the local data/ directory structure, e.g.:
    govinfo/plaw/PLAW-119publ60.json
    olrc/downloads/title10@119-72not60.zip
    congress/member/B000944.json
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PipelineCache:
    """Two-layer cache: local filesystem -> GCS bucket -> API.

    When bucket_name is None, only local caching is used.
    The google-cloud-storage library is imported lazily so it remains optional.
    """

    def __init__(
        self,
        local_root: Path | str = "data",
        bucket_name: str | None = None,
    ) -> None:
        self.local_root = Path(local_root)
        self.bucket_name = bucket_name
        self._gcs_bucket: Any = None
        self._gcs_available: bool | None = None

    # =========================================================================
    # Lazy GCS initialization
    # =========================================================================

    def _init_gcs(self) -> bool:
        """Lazily initialize GCS client. Returns True if GCS is available."""
        if self._gcs_available is not None:
            return self._gcs_available

        if not self.bucket_name:
            self._gcs_available = False
            return False

        try:
            from google.cloud.storage import Client

            client = Client()
            self._gcs_bucket = client.bucket(self.bucket_name)
            self._gcs_available = True
            logger.info(f"GCS cache enabled: gs://{self.bucket_name}")
        except Exception as e:
            logger.warning(f"GCS cache unavailable (falling back to local): {e}")
            self._gcs_available = False

        return self._gcs_available

    # =========================================================================
    # Public API — text (JSON, XML, HTML)
    # =========================================================================

    def get_text(self, key: str) -> str | None:
        """Get cached text content by key.

        Checks local first, then GCS. On GCS hit, backfills local.
        """
        # Local hit
        local = self._local_path(key)
        if local.exists():
            return local.read_text()

        # GCS hit
        if self._init_gcs() and self._gcs_bucket is not None:
            try:
                blob = self._gcs_bucket.blob(key)
                if blob.exists():
                    content: str = blob.download_as_text()
                    # Backfill local
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_text(content)
                    logger.debug(f"Cache backfill from GCS: {key}")
                    return content
            except Exception as e:
                logger.warning(f"GCS read failed for {key}: {e}")

        return None

    def put_text(self, key: str, content: str) -> None:
        """Write text content to both local and GCS caches."""
        # Local write
        local = self._local_path(key)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(content)

        # GCS write
        if self._init_gcs() and self._gcs_bucket is not None:
            try:
                blob = self._gcs_bucket.blob(key)
                blob.upload_from_string(content, content_type="text/plain")
                logger.debug(f"Cache uploaded to GCS: {key}")
            except Exception as e:
                logger.warning(f"GCS write failed for {key}: {e}")

    # =========================================================================
    # Public API — bytes (ZIP files)
    # =========================================================================

    def get_bytes(self, key: str) -> bytes | None:
        """Get cached binary content by key.

        Checks local first, then GCS. On GCS hit, backfills local.
        """
        local = self._local_path(key)
        if local.exists():
            return local.read_bytes()

        if self._init_gcs() and self._gcs_bucket is not None:
            try:
                blob = self._gcs_bucket.blob(key)
                if blob.exists():
                    data: bytes = blob.download_as_bytes()
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(data)
                    logger.debug(f"Cache backfill from GCS (bytes): {key}")
                    return data
            except Exception as e:
                logger.warning(f"GCS read failed for {key}: {e}")

        return None

    def put_bytes(self, key: str, content: bytes) -> None:
        """Write binary content to both local and GCS caches."""
        local = self._local_path(key)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(content)

        if self._init_gcs() and self._gcs_bucket is not None:
            try:
                blob = self._gcs_bucket.blob(key)
                blob.upload_from_string(
                    content, content_type="application/octet-stream"
                )
                logger.debug(f"Cache uploaded to GCS (bytes): {key}")
            except Exception as e:
                logger.warning(f"GCS write failed for {key}: {e}")

    # =========================================================================
    # Local-only helpers (for directory-level checks like OLRC extraction)
    # =========================================================================

    def has_local(self, key: str) -> bool:
        """Check whether a key exists in the local cache."""
        return self._local_path(key).exists()

    def local_path(self, key: str) -> Path:
        """Return the local filesystem path for a cache key."""
        return self._local_path(key)

    # =========================================================================
    # Internal
    # =========================================================================

    def _local_path(self, key: str) -> Path:
        return self.local_root / key


def get_pipeline_cache() -> PipelineCache:
    """Factory that reads settings and returns a configured PipelineCache."""
    from app.config import settings

    return PipelineCache(
        local_root=Path("data"),
        bucket_name=settings.gcs_cache_bucket,
    )
