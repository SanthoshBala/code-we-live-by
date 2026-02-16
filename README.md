# The Code We Live By (CWLB)

A civic engagement platform that makes federal legislation accessible and understandable by treating the US Code as a software repository.

## Vision

Using familiar version control metaphors (commits, pull requests, diffs, blame view), CWLB enables citizens to:
- Explore how laws evolve over time
- See exactly what changed, when, and by whom
- Understand congressional activity patterns
- Gain insights into the legislative process

## Documentation

- [Full Specification](THE_CODE_WE_LIVE_BY_SPEC.md) - Complete product specification
- [Tasks](TASKS.md) - Implementation backlog (Phase 0-3)
- [Research](research/) - Completed research and design documents
- [Display Conventions](DISPLAY_CONVENTIONS.md) - How CWLB renders the US Code

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for Postgres)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) / npm

### Development Environment

```bash
# Start Postgres, run migrations, launch backend + frontend
./dev.sh

# Start with data seeding (Phase 1 titles + sample Public Laws)
./dev.sh --seed

# Stop all services
./dev.sh stop

# Full reset (destroy DB, re-migrate, re-ingest)
./dev.sh reset
```

Once running:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Postgres**: localhost:5432 (cwlb/cwlb_dev)

### Manual Setup

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend
cd backend
uv run pytest

# Frontend
cd frontend
npm run test
```

## Status

Currently in **Phase 1: MVP** — building the US Code Viewer (Milestone 1A).

- **Phase 0**: Research & Validation — complete
- **Phase 1**: Infrastructure, data pipeline, and core ingestion — complete
- **Milestone 1A**: US Code Viewer (tip of trunk) — in progress
- **Tasks 1.12-1.13**: Law ingestion diff framework — in progress

See [TASKS.md](TASKS.md) for full progress details.
