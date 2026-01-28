# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Conventions

- **Date format**: Use `YYYY.MM.DD` or `MM.DD` if the year is obvious from context
- **Atomic commits**: Make commits as atomic as possible (separate commits for separate features/tasks, separate commits for independently testable units)
- **Commit messages**: Use the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard for semantic commit messages (e.g., `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`)
- **Branching**: Always start new tasks in a fresh branch and create a pull request back into main when done

## Project Overview

**The Code We Live By (CWLB)** is a civic engagement platform that makes federal legislation accessible by treating the US Code as a software repository. Using version control metaphors (commits, pull requests, diffs, blame view), the platform enables citizens to explore how laws evolve over time.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Jupyter notebooks
jupyter notebook
```

## Repository Structure

```
/
├── TASKS.md                      # Implementation task backlog (Phase 0-3)
├── THE_CODE_WE_LIVE_BY_SPEC.md   # Full product specification
├── research/                     # Completed research tasks (TASK-0.x-*.md)
├── explore_us_code_structure.ipynb  # Jupyter notebook for exploration
└── .claude/skills/               # Custom Claude Code slash commands
```

## Architecture

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

## Working with Tasks

Tasks are tracked in `TASKS.md`. Format: `Task X.Y` where X is phase number (0-3 or M for maintenance).

Example: "Complete CWLB Task 0.14" means design the data pipeline architecture.
