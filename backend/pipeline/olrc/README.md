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
- `DataIngestionLog` - Audit trail of ingestion operations

## References

- [OLRC Download Page](https://uscode.house.gov/download/download.shtml)
- [OLRC Prior Release Points](https://uscode.house.gov/download/priorreleasepoints.htm)
- [Positive Law Codification](https://uscode.house.gov/codification/legislation.shtml)
- [USLM Schema Documentation](https://uscode.house.gov/download/resources/USLM-User-Guide.pdf)
