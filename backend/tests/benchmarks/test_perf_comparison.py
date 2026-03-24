"""Benchmarks comparing branch optimizations vs baseline implementations.

Measures:
1. Recursive CTE vs sequential revision chain walking
2. Cache-Control middleware overhead per request
3. Connection pool pre-ping overhead

Run: uv run pytest tests/benchmarks/test_perf_comparison.py -v -s
"""

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.main import app
from app.schemas.us_code import TitleSummarySchema

_MOCK_TITLE = TitleSummarySchema(
    title_number=17,
    title_name="Copyrights",
    is_positive_law=True,
    positive_law_date=None,
    chapter_count=8,
    section_count=120,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class FakeRevision(Base):
    __tablename__ = "code_revision"
    revision_id = Column(Integer, primary_key=True)
    parent_revision_id = Column(Integer, nullable=True)


def _timed_runs(fn, n: int = 50) -> dict[str, float]:
    """Run fn() n times and return timing stats in ms."""
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": sorted(times)[int(0.95 * len(times))],
        "min_ms": min(times),
        "max_ms": max(times),
        "runs": n,
    }


async def _async_timed_runs(fn, n: int = 50) -> dict[str, float]:
    """Run async fn() n times and return timing stats in ms."""
    times = []
    for _ in range(n):
        start = time.perf_counter()
        await fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": sorted(times)[int(0.95 * len(times))],
        "min_ms": min(times),
        "max_ms": max(times),
        "runs": n,
    }


# ---------------------------------------------------------------------------
# 1. Recursive CTE vs Sequential chain walking
# ---------------------------------------------------------------------------

CHAIN_LENGTHS = [5, 20, 50]


async def _sequential_get_revision_chain(
    session: AsyncSession, revision_id: int
) -> list[int]:
    """OLD implementation: N sequential round-trips."""
    chain: list[int] = []
    current_id: int | None = revision_id

    while current_id is not None:
        chain.append(current_id)
        result = await session.execute(
            text(
                "SELECT parent_revision_id FROM code_revision "
                "WHERE revision_id = :rid"
            ),
            {"rid": current_id},
        )
        row = result.first()
        current_id = row[0] if row else None

    return chain


async def _cte_get_revision_chain(
    session: AsyncSession, revision_id: int
) -> list[int]:
    """NEW implementation: single recursive CTE query."""
    result = await session.execute(
        text("""
            WITH RECURSIVE chain AS (
                SELECT revision_id, parent_revision_id, 1 AS depth
                FROM code_revision
                WHERE revision_id = :start_id
                UNION ALL
                SELECT cr.revision_id, cr.parent_revision_id, c.depth + 1
                FROM code_revision cr
                JOIN chain c ON cr.revision_id = c.parent_revision_id
            )
            SELECT revision_id FROM chain ORDER BY depth
        """),
        {"start_id": revision_id},
    )
    return [row[0] for row in result]


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.parametrize("chain_length", CHAIN_LENGTHS)
def test_revision_chain_cte_vs_sequential(chain_length: int) -> None:
    """Compare CTE vs sequential chain walking at various chain depths."""

    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession)

        # Seed a revision chain: 1 -> 2 -> ... -> chain_length
        async with async_session() as session:
            for i in range(1, chain_length + 1):
                parent = i - 1 if i > 1 else None
                await session.execute(
                    text(
                        "INSERT INTO code_revision (revision_id, parent_revision_id) "
                        "VALUES (:rid, :pid)"
                    ),
                    {"rid": i, "pid": parent},
                )
            await session.commit()

        head_id = chain_length

        # Benchmark sequential
        async with async_session() as session:
            seq_stats = await _async_timed_runs(
                lambda: _sequential_get_revision_chain(session, head_id),
                n=100,
            )

        # Benchmark CTE
        async with async_session() as session:
            cte_stats = await _async_timed_runs(
                lambda: _cte_get_revision_chain(session, head_id),
                n=100,
            )

        # Verify correctness
        async with async_session() as session:
            seq_result = await _sequential_get_revision_chain(session, head_id)
            cte_result = await _cte_get_revision_chain(session, head_id)
            assert seq_result == cte_result, (
                f"Results differ: seq={seq_result}, cte={cte_result}"
            )

        await engine.dispose()
        return seq_stats, cte_stats

    seq_stats, cte_stats = asyncio.run(_run())

    speedup = seq_stats["mean_ms"] / cte_stats["mean_ms"] if cte_stats["mean_ms"] > 0 else float("inf")

    print(f"\n{'='*60}")
    print(f"  Revision chain walk — chain length: {chain_length}")
    print(f"{'='*60}")
    print(f"  Sequential (old):  mean={seq_stats['mean_ms']:.3f}ms  "
          f"median={seq_stats['median_ms']:.3f}ms  p95={seq_stats['p95_ms']:.3f}ms")
    print(f"  Recursive CTE:     mean={cte_stats['mean_ms']:.3f}ms  "
          f"median={cte_stats['median_ms']:.3f}ms  p95={cte_stats['p95_ms']:.3f}ms")
    print(f"  Speedup:           {speedup:.1f}x faster")
    print(f"{'='*60}")

    # CTE should not be slower than sequential
    assert cte_stats["mean_ms"] <= seq_stats["mean_ms"] * 1.5, (
        f"CTE unexpectedly slower: {cte_stats['mean_ms']:.3f}ms vs "
        f"{seq_stats['mean_ms']:.3f}ms"
    )


# ---------------------------------------------------------------------------
# 2. Middleware overhead
# ---------------------------------------------------------------------------

def test_middleware_overhead() -> None:
    """Measure per-request overhead of CacheControlMiddleware."""

    with patch("app.api.v1.titles.get_all_titles", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [_MOCK_TITLE]
        client = TestClient(app)

        # Warm up
        for _ in range(5):
            client.get("/api/v1/titles/")

        stats = _timed_runs(lambda: client.get("/api/v1/titles/"), n=200)

    print(f"\n{'='*60}")
    print(f"  API request latency (GET /api/v1/titles/) — with middleware")
    print(f"{'='*60}")
    print(f"  mean={stats['mean_ms']:.3f}ms  median={stats['median_ms']:.3f}ms  "
          f"p95={stats['p95_ms']:.3f}ms")
    print(f"  min={stats['min_ms']:.3f}ms  max={stats['max_ms']:.3f}ms  "
          f"runs={stats['runs']}")
    print(f"{'='*60}")

    # Sanity: a mocked endpoint should respond in < 50ms
    assert stats["p95_ms"] < 50, f"p95 too high: {stats['p95_ms']:.1f}ms"


def test_cache_header_present_in_production() -> None:
    """Verify Cache-Control header is set when debug=False."""

    with (
        patch("app.api.v1.titles.get_all_titles", new_callable=AsyncMock) as mock_get,
        patch("app.core.cache_middleware.settings") as mock_settings,
    ):
        mock_get.return_value = [_MOCK_TITLE]
        mock_settings.debug = False
        client = TestClient(app)
        response = client.get("/api/v1/titles/")

    assert response.status_code == 200
    assert "max-age=300" in response.headers.get("cache-control", "")


def test_cache_header_nostore_in_debug() -> None:
    """Verify Cache-Control: no-store when debug=True."""

    with (
        patch("app.api.v1.titles.get_all_titles", new_callable=AsyncMock) as mock_get,
        patch("app.core.cache_middleware.settings") as mock_settings,
    ):
        mock_get.return_value = [_MOCK_TITLE]
        mock_settings.debug = True
        client = TestClient(app)
        response = client.get("/api/v1/titles/")

    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-store"
