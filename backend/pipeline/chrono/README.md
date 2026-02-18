# Chrono Pipeline: Amendment Application Engine

Phase 4 of the chronological pipeline. Applies `LawChange` diffs to produce derived `CodeRevision` records with updated `SectionSnapshot` content.

## Pipeline Position

```
1.18 foundation → 1.19 bootstrap → 1.20 RP diffing →
    1.20b amendment application → 1.20c play-forward
```

## Architecture

```
┌─────────────────────────┐
│   revision_builder.py   │  Orchestrator (DB access)
│   RevisionBuilder       │
├─────────────────────────┤
│         │               │
│  ┌──────▼──────┐  ┌─────▼──────┐
│  │ amendment_  │  │  notes_    │
│  │ applicator  │  │  updater   │
│  │ (pure text) │  │ (metadata) │
│  └─────────────┘  └────────────┘
└─────────────────────────┘
```

### Modules

| Module | Purpose | DB Access |
|--------|---------|-----------|
| `amendment_applicator.py` | Pure text transforms (find/replace, add, delete, repeal) | None |
| `notes_updater.py` | Updates `normalized_notes` and `raw_notes` for applied laws | None |
| `revision_builder.py` | Orchestrates revision creation from `LawChange` records | Yes (async) |

## Data Flow

1. **Input**: A `PublicLaw` with `LawChange` records + a parent `CodeRevision`
2. **Process**:
   - Group changes by `(title_number, section_number)`
   - For each section: fetch parent state via `SnapshotService`
   - Apply changes sequentially (each change operates on result of previous)
   - Update notes metadata with amendment citation
   - Compute new text and notes hashes
   - Create `SectionSnapshot` for the new revision
3. **Output**: A `CodeRevision` (type=PUBLIC_LAW) with derived snapshots

## Text Matching Strategy

The amendment applicator uses a 3-tier matching strategy for MODIFY/DELETE:

1. **Exact match** — literal string match
2. **Whitespace-normalized** — collapse whitespace runs before matching
3. **Case-insensitive** — last resort, logs a warning

Only the first occurrence is replaced (matches typical legislative intent).

## Change Type Dispatch

| ChangeType | Behavior |
|------------|----------|
| MODIFY | Find `old_text`, replace with `new_text` |
| DELETE | Find `old_text`, remove it |
| ADD | Append `new_text` (or create new section) |
| REPEAL | Mark section as deleted, stop further changes |
| REDESIGNATE | Skip (structural, out of scope) |
| TRANSFER | Skip (structural, out of scope) |

## CLI

```bash
# Apply a law's changes
uv run python -m pipeline.cli chrono-apply-law 115 97

# With explicit parent revision
uv run python -m pipeline.cli chrono-apply-law 115 97 --parent-revision 5

# Dry run (preview changes)
uv run python -m pipeline.cli chrono-apply-law 115 97 --dry-run
```

## Dependencies

- `pipeline/olrc/snapshot_service.py` — parent state lookup
- `pipeline/olrc/parser.py` — `compute_text_hash()`
- `app/models/` — `CodeRevision`, `SectionSnapshot`, `PublicLaw`, `LawChange`
- `app/schemas/` — `SectionNotesSchema`, `AmendmentSchema`, `SourceLawSchema`
