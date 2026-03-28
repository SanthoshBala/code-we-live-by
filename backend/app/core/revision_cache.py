"""In-memory cache for HEAD revision ID and revision chain.

The revision chain (recursive CTE walking parent pointers) is the most
frequently executed expensive query — called by every titles, structure,
and section endpoint.  The chain is immutable between ingestions, so
caching it in-process eliminates ~100-300 ms per request.

The cache is invalidated explicitly after a new ingestion completes
(see ``invalidate``), or automatically after ``TTL_SECONDS`` as a
safety net.
"""

from __future__ import annotations

import logging
import time
from typing import ClassVar

logger = logging.getLogger(__name__)

TTL_SECONDS = 300  # 5-minute safety TTL


class _RevisionCache:
    """Process-level singleton cache for HEAD revision data."""

    _head_id: ClassVar[int | None] = None
    _chain: ClassVar[list[int] | None] = None
    _cached_at: ClassVar[float] = 0.0

    @classmethod
    def get(cls) -> tuple[int | None, list[int] | None]:
        """Return cached (head_id, chain), or (None, None) if stale/empty."""
        if cls._head_id is None:
            return None, None
        if time.monotonic() - cls._cached_at > TTL_SECONDS:
            logger.debug("Revision cache TTL expired, clearing")
            cls.invalidate()
            return None, None
        return cls._head_id, cls._chain

    @classmethod
    def set(cls, head_id: int, chain: list[int]) -> None:
        """Store the HEAD revision ID and its chain."""
        cls._head_id = head_id
        cls._chain = chain
        cls._cached_at = time.monotonic()
        logger.debug("Revision cache set: head_id=%d, chain length=%d", head_id, len(chain))

    @classmethod
    def invalidate(cls) -> None:
        """Clear the cache (call after ingestion completes)."""
        cls._head_id = None
        cls._chain = None
        cls._cached_at = 0.0


revision_cache = _RevisionCache
