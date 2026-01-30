# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Conventions

- **Date format**: Use `YYYY.MM.DD` or `MM.DD` if the year is obvious from context
- **Atomic commits**: Make commits as atomic as possible (separate commits for separate features/tasks, separate commits for independently testable units)
- **Commit messages**: Use the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard for semantic commit messages (e.g., `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`). Include the task reference at the end of the subject line: `feat: add feature X (Task 1.10)`
- **Branching**: Always start new tasks in a fresh branch and create a pull request back into main when done
- **LLM-agnostic code**: Keep comments, variable names, and logic generic to allow for different LLM providers in the future. Use "LLM" instead of specific model names (e.g., "Claude") in code comments and documentation
- **Directory READMEs**: Every directory should include a README.md explaining the architecture of that sub-directory—what modules exist, how they relate to each other, and the data flow between them

## Project Overview

**The Code We Live By (CWLB)** is a civic engagement platform that makes federal legislation accessible by treating the US Code as a software repository. Using version control metaphors (commits, pull requests, diffs, blame view), the platform enables citizens to explore how laws evolve over time.

## Commands

### Backend (Python/FastAPI)

```bash
cd backend

# Install dependencies (uses uv for package management)
uv sync

# Run development server
uv run uvicorn app.main:app --reload --port 8000

# Linting and formatting
uv run ruff check .       # Lint
uv run black .            # Format
uv run mypy app           # Type check

# Testing
uv run pytest             # Run tests
uv run pytest --cov=app   # With coverage
```

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev               # http://localhost:3000

# Linting and formatting
npm run lint              # Lint
npm run format            # Format
npm run type-check        # Type check

# Testing
npm run test              # Run tests
npm run build             # Production build
```

## Repository Structure

```
/
├── backend/                      # Python/FastAPI backend
│   ├── app/
│   │   ├── api/v1/              # API route handlers
│   │   ├── core/                # Business logic
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   └── crud/                # Database operations
│   ├── tests/                   # Pytest tests
│   ├── alembic/                 # Database migrations
│   ├── pipeline/                # Data ingestion scripts
│   └── pyproject.toml           # Python dependencies & tool config
│
├── frontend/                     # Next.js frontend
│   ├── src/app/                 # App Router pages
│   ├── src/components/          # React components
│   └── package.json             # Node dependencies
│
├── research/                     # Completed research (TASK-0.x-*.md)
├── TASKS.md                      # Implementation backlog
├── THE_CODE_WE_LIVE_BY_SPEC.md   # Product specification
└── .github/workflows/ci.yml      # CI/CD pipeline
```

## Architecture

CWLB treats federal legislation as version control:
- **US Code sections** → Source code files
- **Public Laws** → Merged pull requests
- **Law sponsors** → PR authors
- **Congressional votes** → Code reviewers

### Tech Stack (from Task 0.13):
- **Frontend**: Next.js 14, React 18, Tailwind CSS, TypeScript
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x
- **Database**: PostgreSQL 15+ (with full-text search for MVP)
- **Hosting**: GCP Cloud Run (scales to zero)

### Key Data Model Entities:
- `USCodeSection` - Individual law sections
- `USCodeLine` - Line-level content for "blame view"
- `PublicLaw` - Enacted legislation with metadata
- `LawChange` - Diffs showing what each law modified

### Phase 1 Titles (from Task 0.8):
10, 17, 18, 20, 22, 26, 42, 50

## Working with Tasks

Tasks are tracked in `TASKS.md`. Format: `Task X.Y` where X is phase (0-3 or M).
