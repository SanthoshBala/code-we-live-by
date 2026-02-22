#!/usr/bin/env bash
# seed.sh — Wipe and reseed the database from scratch.
# Intended for CI/CD (Cloud Run Jobs). Intentionally destructive:
# every run resets all data. Acceptable during early development.
set -euo pipefail

echo "=== Wiping database schema ==="
uv run python -c "
import asyncio, asyncpg, os

async def wipe():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.execute('DROP SCHEMA IF EXISTS public CASCADE')
    await conn.execute('CREATE SCHEMA public')
    await conn.close()

asyncio.run(wipe())
"

echo "=== Running migrations ==="
uv run alembic upgrade head

echo "=== Bootstrapping oldest release point ==="
uv run python -m pipeline.cli chrono-bootstrap

echo "=== Ingesting Congress 113 laws ==="
uv run python -m pipeline.cli govinfo-ingest-congress 113

echo "=== Advancing chronological pipeline (2 revisions) ==="
uv run python -m pipeline.cli chrono-advance --count 2

echo "=== Seed complete ==="
