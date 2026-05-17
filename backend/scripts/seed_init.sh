#!/usr/bin/env bash
# seed_init.sh — Phase 1 of the fan-out seed pipeline.
# Wipes the database and runs migrations so the bootstrap fan-out tasks
# start from a clean, migrated schema. Runs as a single Cloud Run task
# before cwlb-seed-bootstrap is launched.
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

echo "=== Init complete ==="
