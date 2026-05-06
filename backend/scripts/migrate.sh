#!/usr/bin/env bash
# migrate.sh — Run database migrations only (no data changes).
# Runs on every deploy via CI/CD to keep the schema up to date.
set -euo pipefail

echo "=== Running migrations ==="
uv run alembic upgrade head
echo "=== Migrations complete ==="
