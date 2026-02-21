# Chrono Pipeline: Amendment Application & Play-Forward Engine

Phases 4-5 of the chronological pipeline. Phase 4 applies `LawChange` diffs to produce derived `CodeRevision` records. Phase 5 walks the timeline forward event-by-event, coordinating law application and RP ingestion with checkpoint validation.

## Pipeline Position

```
1.18 foundation → 1.19 bootstrap → 1.20 RP diffing →
    1.20b amendment application → 1.20c play-forward
```

## Architecture

```
┌───────────────────────────────────────────────────────┐
│               play_forward.py                         │
│               PlayForwardEngine                       │
│   (timeline walker, event dispatcher, checkpoint)     │
├───────────────────────────────────────────────────────┤
│         │                    │                │       │
│  ┌──────▼──────┐   ┌────────▼───────┐  ┌─────▼────┐ │
│  │ revision_   │   │  RPIngestor    │  │checkpoint│ │
│  │ builder.py  │   │  (olrc/)       │  │  .py     │ │
│  │ (law apply) │   │  (RP ingest)   │  │  (pure)  │ │
│  └──────┬──────┘   └────────────────┘  └──────────┘ │
│         │                                            │
│  ┌──────▼──────┐  ┌─────────────┐                    │
│  │ amendment_  │  │  notes_     │                    │
│  │ applicator  │  │  updater    │                    │
│  │ (pure text) │  │ (metadata)  │                    │
│  └─────────────┘  └─────────────┘                    │
└───────────────────────────────────────────────────────┘
```

### Modules

| Module | Purpose | DB Access |
|--------|---------|-----------|
| `play_forward.py` | Timeline walker: dispatches law and RP events, auto-processes laws, runs checkpoint validation | Yes (async) |
| `checkpoint.py` | Pure comparison of derived state against RP ground truth | None |
| `revision_builder.py` | Orchestrates revision creation from `LawChange` records | Yes (async) |
| `amendment_applicator.py` | Pure text transforms (find/replace, add, delete, repeal) | None |
| `notes_updater.py` | Updates `normalized_notes` and `raw_notes` for applied laws | None |

## Play-Forward Engine

The `PlayForwardEngine` coordinates the chronological pipeline by walking through `TimelineBuilder` events and dispatching each to the appropriate handler:

- **PUBLIC_LAW events** → auto-process law if needed, then `RevisionBuilder.build_revision()` (derived revision)
- **RELEASE_POINT events** → `RPIngestor.ingest_release_point()` (ground truth)

### Auto-Processing Laws

When advancing through a PUBLIC_LAW event, the engine checks if `LawChange` records exist for the law. If not, it automatically:
1. Fetches the law text from GovInfo
2. Parses amendments (via `RegExParsingSession`)
3. Resolves section references to `USCodeSection` records
4. Generates validated diffs
5. Persists `LawChange` records

This is handled by `LawChangeService.process_law()`, making `chrono-advance` fully self-contained — no need to manually run `parse-law` or `process-law` first.

### Advance Modes

- **`advance(count=N)`**: Process the next N events from current position
- **`advance_to(rp_identifier)`**: Process all events up to and including a target RP

### Checkpoint Validation

After each RP ingestion, the engine compares the last derived revision's state against the RP ground truth:

1. Find the last non-ground-truth revision before the RP
2. Materialize both states via `SnapshotService.get_all_sections_at_revision()`
3. Compare by `(title_number, section_number)` — check `text_hash` and `notes_hash`
4. Classify: match, text mismatch, notes mismatch, both, deleted mismatch, only-in-derived, only-in-rp

Standalone validation (read-only) is available via `validate_at_rp()`.

### Deferred Laws

Before applying a law, the engine checks if its `(congress, law_number)` appears in any upcoming RP's `deferred_laws` list. Deferred laws are skipped (they'll be picked up after the RP that defers them).

## Amendment Application (Phase 4)

### Data Flow

1. **Input**: A `PublicLaw` with `LawChange` records + a parent `CodeRevision`
2. **Process**:
   - Group changes by `(title_number, section_number)`
   - For each section: fetch parent state via `SnapshotService`
   - Apply changes sequentially (each change operates on result of previous)
   - Update notes metadata with amendment citation
   - Compute new text and notes hashes
   - Create `SectionSnapshot` for the new revision
3. **Output**: A `CodeRevision` (type=PUBLIC_LAW) with derived snapshots

### Text Matching Strategy

The amendment applicator uses a 3-tier matching strategy for MODIFY/DELETE:

1. **Exact match** — literal string match
2. **Whitespace-normalized** — collapse whitespace runs before matching
3. **Case-insensitive** — last resort, logs a warning

Only the first occurrence is replaced (matches typical legislative intent).

### Change Type Dispatch

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
# Advance one event
uv run python -m pipeline.cli chrono-advance

# Advance 5 events
uv run python -m pipeline.cli chrono-advance --count 5

# Advance to a target RP (with checkpoint validation)
uv run python -m pipeline.cli chrono-advance-to 113-37

# Standalone validation (read-only)
uv run python -m pipeline.cli chrono-validate 113-37

# Apply a specific law's changes
uv run python -m pipeline.cli chrono-apply-law 115 97

# Dry run (preview changes)
uv run python -m pipeline.cli chrono-apply-law 115 97 --dry-run
```

## Dependencies

- `pipeline/timeline.py` — `TimelineBuilder` for event ordering
- `pipeline/olrc/rp_ingestor.py` — `RPIngestor` for RP events
- `pipeline/olrc/snapshot_service.py` — `SnapshotService` for state materialization
- `pipeline/olrc/downloader.py` — `OLRCDownloader` (passed to RPIngestor)
- `pipeline/olrc/parser.py` — `USLMParser`, `compute_text_hash()`
- `pipeline/legal_parser/law_change_service.py` — `LawChangeService` for auto-processing laws
- `app/models/` — `CodeRevision`, `SectionSnapshot`, `PublicLaw`, `LawChange`
- `app/schemas/` — `SectionNotesSchema`, `AmendmentSchema`, `SourceLawSchema`
