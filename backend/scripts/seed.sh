#!/usr/bin/env bash
# seed.sh — Wipe and reseed the database from scratch.
# Intended for CI/CD (Cloud Run Jobs). Intentionally destructive:
# every run resets all data. Acceptable during early development.
set -euo pipefail

echo "=== Downgrading database to base ==="
uv run alembic downgrade base

echo "=== Upgrading database to head ==="
uv run alembic upgrade head

echo "=== Bootstrapping oldest release point ==="
uv run python -m pipeline.cli chrono-bootstrap

echo "=== Ingesting Congress 113 laws ==="
uv run python -m pipeline.cli govinfo-ingest-congress 113

echo "=== Advancing chronological pipeline (2 revisions) ==="
uv run python -m pipeline.cli chrono-advance --count 2

echo "=== Seed complete ==="
