#!/usr/bin/env bash
# seed_init.sh — Phase 1 of the fan-out seed pipeline.
# Wipes the database and runs migrations so the bootstrap fan-out tasks
# start from a clean, migrated schema. Runs as a single Cloud Run task
# before cwlb-seed-bootstrap is launched.
set -euo pipefail

echo "=== Wiping database schema ==="
uv run python -c "
import asyncio, asyncpg, os, time

async def wipe():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    print('Connecting to database...', flush=True)
    t0 = time.monotonic()
    conn = await asyncpg.connect(url)
    print(f'Connected in {time.monotonic() - t0:.1f}s', flush=True)
    await conn.execute('DROP SCHEMA IF EXISTS public CASCADE')
    print('Schema dropped', flush=True)
    await conn.execute('CREATE SCHEMA public')
    print('Schema recreated', flush=True)
    await conn.close()

asyncio.run(wipe())
"
echo "=== Database wiped ==="

echo "=== Running migrations ==="
uv run alembic upgrade head

echo "=== Init complete ==="
