# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Conventions

- **Date format**: Use `YYYY.MM.DD` or `MM.DD` if the year is obvious from context
- **Atomic commits**: Make commits as atomic as possible (separate commits for separate features/tasks, separate commits for independently testable units)
- **Commit messages**: Use the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard for semantic commit messages (e.g., `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`)
- **Branching**: Always start new tasks in a fresh branch and create a pull request back into main when done

## Project Overview

This repository contains:
1. A Flask web application (`app.py`) with Jinja2 templates
2. The **CWLB (Code We Live By)** project - a civic engagement platform that treats the US Code as a software repository

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py
# Runs on http://localhost:5000

# Run Jupyter notebooks
jupyter notebook
```

## Repository Structure

```
/
├── app.py                    # Flask application (routes: /, /projects, /clock)
├── templates/                # Jinja2 HTML templates
├── requirements.txt          # Python dependencies (Flask, pandas, lxml, jupyter, etc.)
├── projects/cwlb/            # CWLB project files
│   ├── TASKS.md              # Implementation task backlog (Phase 0-3)
│   ├── THE_CODE_WE_LIVE_BY_SPEC.md  # Full product specification
│   ├── research/             # Completed research tasks
│   └── *.ipynb               # Jupyter notebooks for exploration
└── .claude/skills/           # Custom Claude Code slash commands
```

## CWLB Project Architecture

CWLB treats federal legislation as version control:
- **US Code sections** → Source code files
- **Public Laws** → Merged pull requests
- **Law sponsors** → PR authors
- **Congressional votes** → Code reviewers

### Key Data Model Entities (from spec Section 6):
- `USCodeSection` - Individual law sections (the fundamental unit)
- `USCodeLine` - Line-level content with parent/child tree structure for "blame view"
- `PublicLaw` - Enacted legislation with metadata
- `LawChange` - Diffs showing what each law modified
- `SectionHistory` / `LineHistory` - Time-travel snapshots

### Primary Data Source:
- **OLRC (Office of Law Revision Counsel)**: https://uscode.house.gov
- XML format (USLM schema) for all 54 US Code titles
- See `research/TASK-0.1-OLRC-Data-Evaluation.md` for complete evaluation

### Phase 1 Scope:
- Titles: 10, 17, 18, 20, 22, 26, 42, 50
- Features: Code browsing, law viewer with diffs, blame view, basic search
- 20 years of legislative history

## Working with CWLB Tasks

Tasks are tracked in `projects/cwlb/TASKS.md`. Format: `Task X.Y` where X is phase number (0-3 or M for maintenance).

Example: "Complete CWLB Task 0.14" means design the data pipeline architecture.
