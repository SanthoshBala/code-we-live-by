# OLRC Data Pipeline

This module downloads, parses, and ingests US Code data from the [Office of Law Revision Counsel (OLRC)](https://uscode.house.gov/).

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OLRC Website  │     │   Local Files   │     │   PostgreSQL    │
│  uscode.house.  │     │   data/olrc/    │     │    Database     │
│      gov        │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ download              │ parse                 │ ingest
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   downloader.py │────▶│    parser.py    │────▶│  ingestion.py   │
│                 │     │                 │     │                 │
│ - Downloads ZIP │     │ - Parses USLM   │     │ - Upserts to DB │
│ - Extracts XML  │     │   XML format    │     │ - Tracks logs   │
│ - Manages cache │     │ - Returns DTOs  │     │ - Handles refs  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Components

### 1. Downloader (`downloader.py`)

Downloads US Code XML files from the OLRC website.

**Key class:** `OLRCDownloader`

```python
from pipeline.olrc.downloader import OLRCDownloader

downloader = OLRCDownloader(download_dir="data/olrc")

# Download a single title
xml_path = await downloader.download_title(17)  # Title 17 - Copyrights

# Download all Phase 1 titles
results = await downloader.download_phase1_titles()

# Check what's already downloaded
downloaded = downloader.get_downloaded_titles()  # [17, 18, 26, ...]
```

**Features:**
- Downloads from OLRC release points (e.g., `119-72not60`)
- Extracts ZIP archives to `data/olrc/title{N}/`
- Caches downloads (skips if already present unless `force=True`)
- Configurable release point for reproducibility

### 2. Parser (`parser.py`)

Parses USLM (United States Legislative Markup) XML files into Python dataclasses.

**Key class:** `USLMParser`

```python
from pipeline.olrc.parser import USLMParser

parser = USLMParser()
result = parser.parse_file("data/olrc/title17/usc17.xml")

print(result.title.title_name)      # "COPYRIGHTS"
print(result.title.is_positive_law) # True
print(len(result.chapters))         # 15
print(len(result.sections))         # 155
```

**Output dataclasses:**
- `ParsedTitle` - Title metadata (number, name, positive law status)
- `ParsedChapter` - Chapter within a title
- `ParsedSubchapter` - Subchapter within a chapter
- `ParsedSection` - Individual code section with text content

**Features:**
- Handles OLRC's USLM XML namespace conventions
- Extracts hierarchical structure (Title → Chapter → Subchapter → Section)
- Detects positive law status from XML metadata
- Preserves section text, headings, and notes

### 3. Ingestion Service (`ingestion.py`)

Persists parsed data to the PostgreSQL database.

**Key class:** `USCodeIngestionService`

```python
from pipeline.olrc.ingestion import USCodeIngestionService
from sqlalchemy.ext.asyncio import AsyncSession

async with AsyncSession(engine) as session:
    service = USCodeIngestionService(session)

    # Ingest a single title (downloads if needed)
    log = await service.ingest_title(17)
    print(log.status)           # "completed"
    print(log.records_created)  # 171

    # Ingest all Phase 1 titles
    logs = await service.ingest_phase1_titles()
```

**Features:**
- Orchestrates download → parse → insert workflow
- Upserts records (creates or updates based on unique keys)
- Maintains referential integrity (Title → Chapter → Subchapter → Section)
- Creates `DataIngestionLog` records for audit trail
- Supports `force_download` and `force_parse` flags for re-ingestion

### 4. Release Point Registry (`release_point.py`)

Discovers and manages OLRC release points — snapshots of the US Code published after each Public Law is incorporated.

**Key class:** `ReleasePointRegistry`

```python
from pipeline.olrc.release_point import ReleasePointRegistry

registry = ReleasePointRegistry()
await registry.fetch_release_points()

# Get all release points for a congress
rps = registry.get_for_congress(118)

# Get consecutive pairs for validation
pairs = registry.get_adjacent_pairs(congress=118)
# [(RP 118-22, RP 118-30), (RP 118-30, RP 118-34), ...]

# Find laws enacted between two release points
laws = registry.get_laws_in_range("118-22", "118-30")
# [(118, 23), (118, 24), ..., (118, 30)]
```

**Helper:** `parse_release_point_identifier("118-158")` → `(118, "158")`

### 5. Initial Commit Service (`initial_commit.py`)

Establishes the base state of the US Code by loading the first OLRC release point as an "initial commit."

**Key class:** `InitialCommitService`

```python
from pipeline.olrc.initial_commit import InitialCommitService

service = InitialCommitService(session)
rp = await service.create_initial_commit(
    release_point="113-21",
    titles=[10, 17, 18, 20, 22, 26, 42, 50],
)
```

Creates `OLRCReleasePoint` (with `is_initial=True`) and `SectionHistory` version 1 records for all sections in the specified titles.

## CLI Usage

A command-line interface is available for manual operations:

```bash
# Download titles
uv run python -m pipeline.cli download --titles 17 18 26

# Download all Phase 1 titles
uv run python -m pipeline.cli download

# Parse and view summary
uv run python -m pipeline.cli parse 17

# List downloaded titles
uv run python -m pipeline.cli list

# Establish initial commit from first release point
uv run python -m pipeline.cli initial-commit 113-21 --titles 10 17 18
```

## Data Flow Example

```python
# Complete ingestion flow (what USCodeIngestionService does internally):

# 1. Download
downloader = OLRCDownloader()
xml_path = await downloader.download_title(17)
# Result: data/olrc/title17/usc17.xml

# 2. Parse
parser = USLMParser()
result = parser.parse_file(xml_path)
# Result: USLMParseResult with title, chapters, subchapters, sections

# 3. Ingest
# For each parsed entity, upsert to database:
#   - USCodeTitle (from result.title)
#   - USCodeChapter (from result.chapters)
#   - USCodeSubchapter (from result.subchapters)
#   - USCodeSection (from result.sections)
```

## Configuration

Key constants that may need updates (see inline documentation for sources):

| Constant | File | Description |
|----------|------|-------------|
| `DEFAULT_RELEASE_POINT` | downloader.py | OLRC release point (e.g., `119-72not60`) |
| `PHASE_1_TITLES` | downloader.py | Priority titles for initial ingestion |
| `POSITIVE_LAW_TITLES` | parser.py | Fallback list of positive law titles |

## Database Tables

The ingestion service populates these SQLAlchemy models:

- `USCodeTitle` - One row per title (54 total)
- `USCodeChapter` - Chapters within titles
- `USCodeSubchapter` - Subchapters within chapters
- `USCodeSection` - Individual sections with full text
- `OLRCReleasePoint` - Release point metadata (identifier, congress, dates, parent chain)
- `SectionHistory` - Version snapshots at each commit point
- `DataIngestionLog` - Audit trail of ingestion operations

## Known Edge Case: Duplicate Section Numbers

The US Code contains legitimate duplicate section numbers where Congress enacted
two different provisions with the same number. The OLRC preserves both in the
XML with a footnote: *"So in original. Two sections 4781 have been enacted."*

### How duplicates arise

Congress occasionally passes two laws that create or amend the same section
number independently. For example:

- **PL 114-328** (Dec 23, 2016) created **10 USC § 4781** — "Cyber Center for
  Education and Innovation-Home of the National Cryptologic Museum"
- **PL 115-31** (May 5, 2017) created a *second* **10 USC § 4781** with the
  same title but slightly different drafting (different subsection structure,
  minor wording variations)

Both versions are substantively similar but not identical. They have different
XML `id` attributes but the same `identifier` attribute
(`/us/usc/t10/s4781.1`).

### How duplicates get resolved

Congress fixes duplicates via **technical corrections laws**. In the § 4781
example:

1. **PL 115-91** (Dec 12, 2017) — Section 1081(a)(49) explicitly repealed the
   second § 4781 (the PL 115-31 version) and struck it from the table of
   sections
2. **PL 115-232** (2018) — Renumbered the surviving § 4781 to **§ 7781** as
   part of a broader Title 10 reorganization

The cleanup took about 7 months. Until the corrections law passes, both
versions coexist in the OLRC XML.

### Scope of the issue

As of the `115-40u1` release point, duplicate section-level identifiers appear
in at least:

| Title | Duplicate sections | Notes |
|-------|-------------------|-------|
| 2 | §601, §602, §641-§688, §921, §1301, §1302, §1361 | Many whole sections |
| 5 | §3598.1, §5757.1 | Same "two sections enacted" pattern |
| 10 | §4781.1 | The example above |

Many other titles have duplicates at the *subsection* level (e.g.,
`/us/usc/t10/s2324/e/1/P`), which don't affect section-level storage.

### Impact on our data model

The `section_snapshot` table does **not** have a unique constraint on
`(revision_id, title_number, section_number)` because of this edge case. Both
duplicate sections are stored as separate rows. Downstream consumers
(SnapshotService, the API) should be aware that a query by section number may
return multiple rows at a given revision.

See [GitHub issue #89](https://github.com/SanthoshBala/code-we-live-by/issues/89)
for the TODO on correctly displaying and tracking these duplicates through the
chrono pipeline.

## References

- [OLRC Download Page](https://uscode.house.gov/download/download.shtml)
- [OLRC Prior Release Points](https://uscode.house.gov/download/priorreleasepoints.htm)
- [Positive Law Codification](https://uscode.house.gov/codification/legislation.shtml)
- [USLM Schema Documentation](https://uscode.house.gov/download/resources/USLM-User-Guide.pdf)
