#!/usr/bin/env bash
# seed_bootstrap.sh — Phase 2 of the fan-out seed pipeline.
# Each Cloud Run Job task ingests one title. Cloud Run sets
# CLOUD_RUN_TASK_INDEX (0-based) and CLOUD_RUN_TASK_COUNT automatically
# when the job is deployed with --tasks N.
#
# Task 0 creates the OLRCReleasePoint + CodeRevision records and ingests
# its title slice. Tasks 1+ poll until the records appear, then ingest
# their slice. The revision is marked INGESTED by chrono-bootstrap-finalize
# in seed_finalize.sh after all tasks complete.
set -euo pipefail

# Each task processes one title sequentially — one connection is sufficient.
# Keeping pool_size=1 prevents connection storms when many tasks start together.
export PIPELINE_POOL_SIZE=1

# Use asyncpg binary COPY instead of INSERT for the snapshot bulk-write.
# Avoids the RETURNING clause SQLAlchemy adds (we don't need the generated PKs)
# and streams rows via the binary protocol — ~5-10x faster than executemany.
export PIPELINE_USE_COPY=1

echo "=== Bootstrap: task ${CLOUD_RUN_TASK_INDEX:-0}/${CLOUD_RUN_TASK_COUNT:-1} ==="
uv run python -m pipeline.cli chrono-bootstrap
echo "=== Bootstrap task complete ==="
