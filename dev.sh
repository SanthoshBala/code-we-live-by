#!/usr/bin/env bash
# dev.sh — Start the full CWLB local development environment
#
# Usage:
#   ./dev.sh              Start Postgres, backend, and frontend
#   ./dev.sh --seed       Also build chronology: bootstrap RP, load laws,
#                         advance chronology
#   ./dev.sh stop         Stop Postgres container
#   ./dev.sh reset        Destroy DB and rebuild everything from scratch
#
# Prerequisites:
#   - Docker (for Postgres)
#   - uv (Python package manager)
#   - Node.js / npm

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[dev]${NC} $*"; }
warn() { echo -e "${YELLOW}[dev]${NC} $*"; }
err()  { echo -e "${RED}[dev]${NC} $*" >&2; }

# Track background PIDs for cleanup
PIDS=()

cleanup() {
    log "Shutting down..."
    if [[ ${#PIDS[@]} -gt 0 ]]; then
        for pid in "${PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done
    fi
    wait 2>/dev/null || true
    log "Done."
}

trap cleanup EXIT INT TERM

# ── Stop command ──────────────────────────────────────────────────────────────

if [[ "${1:-}" == "stop" ]]; then
    log "Stopping Postgres container..."
    docker compose -f "$ROOT_DIR/docker-compose.yml" down
    exit 0
fi

# ── Reset command ────────────────────────────────────────────────────────────

if [[ "${1:-}" == "reset" ]]; then
    warn "This will destroy all local data and rebuild from scratch."
    read -rp "Continue? [y/N] " confirm
    if [[ "$confirm" != [yY] ]]; then
        log "Aborted."
        exit 0
    fi

    log "Stopping Postgres and removing volume..."
    docker compose -f "$ROOT_DIR/docker-compose.yml" down -v

    log "Starting fresh Postgres..."
    docker compose -f "$ROOT_DIR/docker-compose.yml" up -d
    until docker exec cwlb-postgres pg_isready -U cwlb -d cwlb &>/dev/null; do
        sleep 1
    done
    log "Postgres is ready."

    log "Running migrations..."
    cd "$BACKEND_DIR"
    uv run python -m alembic upgrade head

    log "Step 1/4: Bootstrapping oldest release point (downloads all titles)..."
    uv run python -m pipeline.cli chrono-bootstrap

    log "Step 2/4: Ingesting all Public Laws for Congress 113..."
    uv run python -m pipeline.cli govinfo-ingest-congress 113

    log "Step 3/4: Checking chronology status..."
    uv run python -m pipeline.cli chrono-status

    log "Step 4/4: Applying first law after RP (auto-fetches and parses)..."
    uv run python -m pipeline.cli chrono-advance

    log "Reset complete. Current state:"
    uv run python -m pipeline.cli chrono-status

    exit 0
fi

# ── Parse flags ───────────────────────────────────────────────────────────────

SEED=false
for arg in "$@"; do
    case "$arg" in
        --seed) SEED=true ;;
        *) err "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Check prerequisites ──────────────────────────────────────────────────────

for cmd in docker uv npm; do
    if ! command -v "$cmd" &>/dev/null; then
        err "Missing prerequisite: $cmd"
        exit 1
    fi
done

# ── 1. Start Postgres ────────────────────────────────────────────────────────

log "Starting Postgres..."
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d

log "Waiting for Postgres to be ready..."
until docker exec cwlb-postgres pg_isready -U cwlb -d cwlb &>/dev/null; do
    sleep 1
done
log "Postgres is ready."

# ── 2. Run migrations ────────────────────────────────────────────────────────

log "Running database migrations..."
cd "$BACKEND_DIR"
uv run python -m alembic upgrade head

# ── 3. Optionally seed data ──────────────────────────────────────────────────

if [[ "$SEED" == true ]]; then
    log "Step 1/4: Bootstrapping oldest release point (downloads all titles)..."
    uv run python -m pipeline.cli chrono-bootstrap

    log "Step 2/4: Ingesting all Public Laws for Congress 113..."
    uv run python -m pipeline.cli govinfo-ingest-congress 113

    log "Step 3/4: Checking chronology status..."
    uv run python -m pipeline.cli chrono-status

    log "Step 4/4: Applying first law after RP (auto-fetches and parses)..."
    uv run python -m pipeline.cli chrono-advance

    log "Chronology built. Current state:"
    uv run python -m pipeline.cli chrono-status
fi

# ── 4. Start backend ─────────────────────────────────────────────────────────

log "Starting backend on ${CYAN}http://localhost:8000${NC} ..."
cd "$BACKEND_DIR"
uv run uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)

# ── 5. Start frontend ────────────────────────────────────────────────────────

log "Starting frontend on ${CYAN}http://localhost:3000${NC} ..."
cd "$FRONTEND_DIR"
npm run dev &
PIDS+=($!)

# ── Wait ──────────────────────────────────────────────────────────────────────

echo ""
log "Local environment is running:"
echo -e "  ${CYAN}Frontend${NC}  http://localhost:3000"
echo -e "  ${CYAN}Backend${NC}   http://localhost:8000"
echo -e "  ${CYAN}API docs${NC}  http://localhost:8000/docs"
echo -e "  ${CYAN}Postgres${NC}  localhost:5432 (cwlb/cwlb_dev)"
echo ""
log "Press Ctrl+C to stop all services."

wait
