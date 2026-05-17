#!/usr/bin/env bash
# seed_finalize.sh — Phase 3 of the fan-out seed pipeline.
# Runs after all bootstrap fan-out tasks complete. Finalizes the bootstrap
# revision (marks it INGESTED), then runs the rest of the seed pipeline.
set -euo pipefail

echo "=== Finalizing bootstrap revision ==="
uv run python -m pipeline.cli chrono-bootstrap-finalize

echo "=== Ingesting Congress 113 laws ==="
uv run python -m pipeline.cli govinfo-ingest-congress 113

echo "=== Seeding legislative history for Congress 113 ==="
uv run python -m pipeline.cli seed-congress-law-history 113

echo "=== Advancing chronological pipeline (2 revisions) ==="
uv run python -m pipeline.cli chrono-advance --count 2

echo "=== Seed complete ==="
