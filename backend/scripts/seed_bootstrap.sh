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

echo "=== Bootstrap: task ${CLOUD_RUN_TASK_INDEX:-0}/${CLOUD_RUN_TASK_COUNT:-1} ==="
uv run python -m pipeline.cli chrono-bootstrap
echo "=== Bootstrap task complete ==="
