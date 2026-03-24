"""Benchmarks comparing branch optimizations vs baseline implementations.

Measures:
1. Recursive CTE vs sequential revision chain walking
2. Snapshot query with vs without revision_id index
3. Column projection: fetching all columns vs only needed columns
4. Cache-Control middleware overhead per request

Run: uv run pytest tests/benchmarks/test_perf_comparison.py -v -s

Note: Uses in-memory SQLite to isolate algorithmic differences. Real
PostgreSQL over a network amplifies the sequential-query penalties due
to per-round-trip latency (~1-10ms on Cloud SQL vs ~0.01ms in-memory).
"""

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, Text, text
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


class FakeSnapshot(Base):
    """Mimics section_snapshot with realistic column sizes."""

    __tablename__ = "section_snapshot"
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    revision_id = Column(Integer, nullable=False)
    title_number = Column(Integer, nullable=False)
    section_number = Column(String, nullable=False)
    heading = Column(String, nullable=True)
    text_content = Column(Text, nullable=True)  # ~2-20KB per section
    normalized_provisions = Column(Text, nullable=True)  # JSON blob
    notes = Column(Text, nullable=True)
    normalized_notes = Column(Text, nullable=True)
    text_hash = Column(String, nullable=True)
    notes_hash = Column(String, nullable=True)
    full_citation = Column(String, nullable=True)
    is_deleted = Column(Integer, default=0)
    group_id = Column(Integer, nullable=True)
    sort_order = Column(Integer, default=0)


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


def _print_comparison(
    label: str,
    old_label: str,
    old_stats: dict[str, float],
    new_label: str,
    new_stats: dict[str, float],
) -> float:
    """Print a comparison table and return speedup factor."""
    speedup = (
        old_stats["mean_ms"] / new_stats["mean_ms"]
        if new_stats["mean_ms"] > 0
        else float("inf")
    )
    print(f"\n{'=' * 65}")
    print(f"  {label}")
    print(f"{'=' * 65}")
    print(
        f"  {old_label:25s}  mean={old_stats['mean_ms']:8.3f}ms  "
        f"median={old_stats['median_ms']:8.3f}ms  "
        f"p95={old_stats['p95_ms']:8.3f}ms"
    )
    print(
        f"  {new_label:25s}  mean={new_stats['mean_ms']:8.3f}ms  "
        f"median={new_stats['median_ms']:8.3f}ms  "
        f"p95={new_stats['p95_ms']:8.3f}ms"
    )
    print(f"  Speedup: {speedup:.1f}x faster")
    print(f"{'=' * 65}")
    return speedup


# ---------------------------------------------------------------------------
# Database seeding
# ---------------------------------------------------------------------------

# Realistic sizes for Title 16 (Conservation/Energy):
# ~800 sections, ~20 revisions, ~5KB avg text per section
TITLE_NUMBER = 16
NUM_SECTIONS = 800
NUM_REVISIONS = 20
SECTIONS_CHANGED_PER_REVISION = 40  # ~5% of sections change per revision
TEXT_SIZE = 5000  # ~5KB per section


async def _create_seeded_engine():
    """Create an in-memory SQLite DB with realistic data volumes."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    make_session = sessionmaker(engine, class_=AsyncSession)

    async with make_session() as session:
        # Create revision chain: 1 -> 2 -> ... -> NUM_REVISIONS
        for i in range(1, NUM_REVISIONS + 1):
            parent = i - 1 if i > 1 else None
            await session.execute(
                text(
                    "INSERT INTO code_revision (revision_id, parent_revision_id) "
                    "VALUES (:rid, :pid)"
                ),
                {"rid": i, "pid": parent},
            )

        # Revision 1: all sections get initial snapshots
        fake_text = "x" * TEXT_SIZE
        fake_provisions = '{"lines": [' + ",".join(['{"n":1}'] * 50) + "]}"
        fake_notes = '{"amendments": [{"year": 2020}]}'
        snap_id = 0
        for sec in range(1, NUM_SECTIONS + 1):
            snap_id += 1
            await session.execute(
                text("""
                    INSERT INTO section_snapshot (
                        snapshot_id, revision_id, title_number, section_number,
                        heading, text_content, normalized_provisions, notes,
                        normalized_notes, text_hash, notes_hash, full_citation,
                        is_deleted, group_id, sort_order
                    ) VALUES (
                        :sid, :rid, :title, :sec,
                        :heading, :text, :provisions, :notes,
                        :nnotes, :thash, :nhash, :cite,
                        0, :gid, :sort
                    )
                """),
                {
                    "sid": snap_id,
                    "rid": 1,
                    "title": TITLE_NUMBER,
                    "sec": str(sec),
                    "heading": f"Section {sec}",
                    "text": fake_text,
                    "provisions": fake_provisions,
                    "notes": fake_notes,
                    "nnotes": fake_notes,
                    "thash": f"hash-r1-s{sec}",
                    "nhash": f"nhash-r1-s{sec}",
                    "cite": f"16 U.S.C. § {sec}",
                    "gid": (sec % 20) + 1,
                    "sort": sec,
                },
            )

        # Revisions 2+: ~5% of sections get new snapshots each
        for rev in range(2, NUM_REVISIONS + 1):
            for sec in range(1, SECTIONS_CHANGED_PER_REVISION + 1):
                # Rotate which sections change
                actual_sec = ((sec + rev * 7) % NUM_SECTIONS) + 1
                snap_id += 1
                await session.execute(
                    text("""
                        INSERT INTO section_snapshot (
                            snapshot_id, revision_id, title_number, section_number,
                            heading, text_content, normalized_provisions, notes,
                            normalized_notes, text_hash, notes_hash, full_citation,
                            is_deleted, group_id, sort_order
                        ) VALUES (
                            :sid, :rid, :title, :sec,
                            :heading, :text, :provisions, :notes,
                            :nnotes, :thash, :nhash, :cite,
                            0, :gid, :sort
                        )
                    """),
                    {
                        "sid": snap_id,
                        "rid": rev,
                        "title": TITLE_NUMBER,
                        "sec": str(actual_sec),
                        "heading": f"Section {actual_sec} (amended r{rev})",
                        "text": fake_text,
                        "provisions": fake_provisions,
                        "notes": fake_notes,
                        "nnotes": fake_notes,
                        "thash": f"hash-r{rev}-s{actual_sec}",
                        "nhash": f"nhash-r{rev}-s{actual_sec}",
                        "cite": f"16 U.S.C. § {actual_sec}",
                        "gid": (actual_sec % 20) + 1,
                        "sort": actual_sec,
                    },
                )

        await session.commit()

    total_snapshots = NUM_SECTIONS + (NUM_REVISIONS - 1) * SECTIONS_CHANGED_PER_REVISION
    print(
        f"\n  Seeded: {NUM_REVISIONS} revisions, {NUM_SECTIONS} sections, "
        f"{total_snapshots} total snapshots (~{total_snapshots * TEXT_SIZE // 1024 // 1024}MB text)"
    )

    return engine, make_session


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
                "SELECT parent_revision_id FROM code_revision WHERE revision_id = :rid"
            ),
            {"rid": current_id},
        )
        row = result.first()
        current_id = row[0] if row else None

    return chain


async def _cte_get_revision_chain(session: AsyncSession, revision_id: int) -> list[int]:
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
    _print_comparison(
        f"Revision chain walk — chain length: {chain_length}",
        "Sequential (old):",
        seq_stats,
        "Recursive CTE (new):",
        cte_stats,
    )

    # CTE should not be slower than sequential
    assert cte_stats["mean_ms"] <= seq_stats["mean_ms"] * 1.5, (
        f"CTE unexpectedly slower: {cte_stats['mean_ms']:.3f}ms vs "
        f"{seq_stats['mean_ms']:.3f}ms"
    )


# ---------------------------------------------------------------------------
# 2. Snapshot query: indexed vs unindexed
# ---------------------------------------------------------------------------


def test_snapshot_query_with_index() -> None:
    """Measure DISTINCT ON snapshot query with and without revision_id index.

    Simulates the main bottleneck in get_title_structure(): fetching the
    latest snapshot per section across the full revision chain.
    SQLite doesn't support DISTINCT ON, so we use GROUP BY + MAX instead.
    """

    # SQLite equivalent of the PostgreSQL DISTINCT ON query
    _QUERY_NO_INDEX = """
        SELECT s.snapshot_id, s.revision_id, s.title_number, s.section_number,
               s.heading, s.text_content, s.normalized_provisions, s.notes,
               s.normalized_notes, s.text_hash, s.notes_hash, s.full_citation,
               s.is_deleted, s.group_id, s.sort_order
        FROM section_snapshot s
        INNER JOIN (
            SELECT title_number, section_number, MAX(revision_id) AS max_rev
            FROM section_snapshot
            WHERE revision_id IN ({chain_placeholders})
              AND title_number = :title
            GROUP BY title_number, section_number
        ) latest ON s.title_number = latest.title_number
                 AND s.section_number = latest.section_number
                 AND s.revision_id = latest.max_rev
    """

    _QUERY_SUMMARY_ONLY = """
        SELECT s.section_number, s.heading, s.is_deleted,
               s.normalized_notes, s.group_id, s.sort_order
        FROM section_snapshot s
        INNER JOIN (
            SELECT title_number, section_number, MAX(revision_id) AS max_rev
            FROM section_snapshot
            WHERE revision_id IN ({chain_placeholders})
              AND title_number = :title
            GROUP BY title_number, section_number
        ) latest ON s.title_number = latest.title_number
                 AND s.section_number = latest.section_number
                 AND s.revision_id = latest.max_rev
    """

    async def _run():
        engine, make_session = await _create_seeded_engine()

        chain = list(range(NUM_REVISIONS, 0, -1))  # newest first
        chain_placeholders = ",".join(str(r) for r in chain)

        # --- No index ---
        async with make_session() as session:
            no_idx_stats = await _async_timed_runs(
                lambda: session.execute(
                    text(_QUERY_NO_INDEX.format(chain_placeholders=chain_placeholders)),
                    {"title": TITLE_NUMBER},
                ),
                n=30,
            )

        # --- Add indexes (matches the branch's migration) ---
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE INDEX idx_snap_rev ON section_snapshot (revision_id)")
            )
            await conn.execute(
                text(
                    "CREATE INDEX idx_snap_rev_title_sec ON section_snapshot "
                    "(revision_id, title_number, section_number)"
                )
            )

        async with make_session() as session:
            idx_stats = await _async_timed_runs(
                lambda: session.execute(
                    text(_QUERY_NO_INDEX.format(chain_placeholders=chain_placeholders)),
                    {"title": TITLE_NUMBER},
                ),
                n=30,
            )

        # --- Indexed + summary columns only (no text_content/provisions) ---
        async with make_session() as session:
            slim_stats = await _async_timed_runs(
                lambda: session.execute(
                    text(
                        _QUERY_SUMMARY_ONLY.format(
                            chain_placeholders=chain_placeholders
                        )
                    ),
                    {"title": TITLE_NUMBER},
                ),
                n=30,
            )

        await engine.dispose()
        return no_idx_stats, idx_stats, slim_stats

    no_idx_stats, idx_stats, slim_stats = asyncio.run(_run())

    _print_comparison(
        f"Snapshot query — {NUM_SECTIONS} sections × {NUM_REVISIONS} revisions (full scan)",
        "No index (baseline):",
        no_idx_stats,
        "With revision index:",
        idx_stats,
    )
    _print_comparison(
        "Snapshot query — indexed, all columns vs summary-only",
        "All columns (current):",
        idx_stats,
        "Summary columns only:",
        slim_stats,
    )

    print(
        f"\n  ** Column projection saves "
        f"~{idx_stats['mean_ms'] - slim_stats['mean_ms']:.1f}ms per query "
        f"({NUM_SECTIONS} sections × ~{TEXT_SIZE // 1024}KB text each)"
    )
    print("     In-memory savings are modest; over the network with real PG,")
    print(
        f"     transferring {NUM_SECTIONS * TEXT_SIZE // 1024 // 1024}MB+ of "
        f"unused text_content dominates latency.\n"
    )


# ---------------------------------------------------------------------------
# 3. Sequential per-revision snapshot loading vs single query
# ---------------------------------------------------------------------------


def test_snapshot_loading_single_query_vs_per_revision() -> None:
    """Compare the old per-revision loop vs single DISTINCT ON query.

    The old get_all_sections_at_revision() looped through each revision
    in the chain issuing a separate SELECT per revision. The new approach
    issues a single query with DISTINCT ON across the entire chain.
    """

    async def _per_revision_loop(session: AsyncSession, chain: list[int]) -> int:
        """OLD pattern: one query per revision in the chain."""
        section_map: dict[tuple[int, str], dict] = {}
        for rev_id in reversed(chain):
            result = await session.execute(
                text(
                    "SELECT title_number, section_number, heading "
                    "FROM section_snapshot WHERE revision_id = :rid"
                ),
                {"rid": rev_id},
            )
            for row in result:
                section_map[(row[0], row[1])] = {"heading": row[2]}
        return len(section_map)

    async def _single_query(session: AsyncSession, chain: list[int]) -> int:
        """NEW pattern: single query with GROUP BY."""
        chain_placeholders = ",".join(str(r) for r in chain)
        result = await session.execute(
            text(f"""
                SELECT s.title_number, s.section_number, s.heading
                FROM section_snapshot s
                INNER JOIN (
                    SELECT title_number, section_number, MAX(revision_id) AS max_rev
                    FROM section_snapshot
                    WHERE revision_id IN ({chain_placeholders})
                    GROUP BY title_number, section_number
                ) latest ON s.title_number = latest.title_number
                         AND s.section_number = latest.section_number
                         AND s.revision_id = latest.max_rev
            """),
        )
        return len(result.all())

    async def _run():
        engine, make_session = await _create_seeded_engine()

        chain = list(range(NUM_REVISIONS, 0, -1))

        # Add indexes
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE INDEX idx_snap_rev2 ON section_snapshot (revision_id)")
            )

        async with make_session() as session:
            loop_stats = await _async_timed_runs(
                lambda: _per_revision_loop(session, chain),
                n=20,
            )

        async with make_session() as session:
            single_stats = await _async_timed_runs(
                lambda: _single_query(session, chain),
                n=20,
            )

        # Verify same result count
        async with make_session() as session:
            loop_count = await _per_revision_loop(session, chain)
            single_count = await _single_query(session, chain)
            assert loop_count == single_count, (
                f"Counts differ: loop={loop_count}, single={single_count}"
            )

        await engine.dispose()
        return loop_stats, single_stats

    loop_stats, single_stats = asyncio.run(_run())
    _print_comparison(
        f"Section materialization — {NUM_SECTIONS} sections × {NUM_REVISIONS} revisions",
        "Per-revision loop (old):",
        loop_stats,
        "Single query (new):",
        single_stats,
    )


# ---------------------------------------------------------------------------
# 4. Middleware overhead
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

    print(f"\n{'=' * 65}")
    print("  API request latency (GET /api/v1/titles/) — with middleware")
    print(f"{'=' * 65}")
    print(
        f"  mean={stats['mean_ms']:.3f}ms  median={stats['median_ms']:.3f}ms  "
        f"p95={stats['p95_ms']:.3f}ms"
    )
    print(
        f"  min={stats['min_ms']:.3f}ms  max={stats['max_ms']:.3f}ms  "
        f"runs={stats['runs']}"
    )
    print(f"{'=' * 65}")

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
