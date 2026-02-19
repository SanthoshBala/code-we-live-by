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

## Known Edge Case: Duplicate Section and Subsection Numbers

The US Code contains legitimate duplicate section numbers where Congress enacted
two different provisions with the same number. The OLRC preserves both in the
XML with a footnote, e.g., *"So in original. Two sections 4781 have been
enacted."*

### How duplicates arise

Congress occasionally passes two laws that create or amend the same section (or
subsection) number independently. This typically happens when two bills move
through Congress concurrently and both add the same section without awareness of
the other.

### How duplicates get resolved

Congress fixes duplicates via **technical corrections laws**. In the 10 USC
§ 4781 example below:

1. **PL 115-91** (Dec 12, 2017) — Section 1081(a)(49) explicitly repealed the
   second § 4781 (the PL 115-31 version) and struck it from the table of
   sections
2. **PL 115-232** (2018) — Renumbered the surviving § 4781 to **§ 7781** as
   part of a broader Title 10 reorganization

The cleanup took about 7 months. Until the corrections law passes, both
versions coexist in the OLRC XML.

### Section-level duplicates

These are entire sections where two laws created the same section number
independently. Both appear in the XML with the same `identifier` attribute but
different `id` attributes.

As of the `115-40u1` release point:

**10 USC § 4781** — "Cyber Center for Education and Innovation-Home of the
National Cryptologic Museum"

| | Enacted by | Date | Content |
|---|---|---|---|
| V1 | PL 114-328 | Dec 23, 2016 | Establishment in a single paragraph under (a), paragraph headings throughout (e.g., "Acceptance of facility", "Use of funds") |
| V2 | PL 115-31 | May 5, 2017 | Establishment split into (a)(1)-(3), no paragraph headings, minor wording differences |

Both are substantively the same law with slightly different legislative
drafting. OLRC footnote: *"So in original. Two sections 4781 have been
enacted."*

**5 USC § 3598** — "Federal Bureau of Investigation Reserve Service"

| | Enacted by | Date | Content |
|---|---|---|---|
| V1 | PL 108-447 | Dec 8, 2004 | FBI Reserve Service provisions (118 Stat. 2869) |
| V2 | PL 108-458 | Dec 17, 2004 | FBI Reserve Service provisions (118 Stat. 3703) |

Two laws passed 9 days apart in the same Congress both created § 3598. OLRC
footnote: *"Another section 3598 is set out after this section."*

**5 USC § 5757** — Two completely different provisions sharing a section number:

| | Enacted by | Content |
|---|---|---|
| V1 | PL 107-107 | "Payment of expenses to obtain professional credentials" |
| V2 | PL 107-273 | "Extended assignment incentive" |

Unlike the previous examples, these are substantively *different* provisions
that happen to share the same section number. OLRC footnote: *"Another section
5757 is set out after this section."*

### Subsection-level duplicates

Many titles also have duplicate *subsections* within a section — two laws
amended the same section and independently added a subsection with the same
letter or number. These don't affect our section-level storage (both subsections
are part of the same section's text content) but do mean the rendered text
contains duplicate subsection designations.

Selected examples at the `115-40u1` release point where the two versions have
distinct content:

**6 USC § 341(e)** — Two completely different subsections (e):

| | Content |
|---|---|
| V1 | "System for Award Management consultation" — contracting/grant officials must consult SAM |
| V2 | "Interoperable communications defined" — defines the term per § 194(g) |

OLRC footnote: *"So in original. There are two subsecs. (e)."*

**8 USC § 1182(t)** — Two subsections (t) of the Immigration and Nationality
Act:

| | Content |
|---|---|
| V1 | "Nonimmigrant professionals; labor attestations" — H-visa labor requirements |
| V2 | "Foreign residence requirement" — Q-visa residence rules |

OLRC footnote: *"So in original. Two subsecs. (t) have been enacted."*

**8 USC § 1228(c)** — Two subsections (c):

| | Content |
|---|---|
| V1 | "Presumption of deportability" — aggravated felony creates conclusive presumption |
| V2 | "Judicial removal" — district court jurisdiction for judicial orders of removal |

OLRC footnote: *"So in original. Two subsecs. (c) have been enacted."*

**7 USC § 21(q)** — Two subsections (q) of the Commodity Exchange Act:

| | Content |
|---|---|
| V1 | "Major disciplinary rule violations" — reporting requirements for futures associations |
| V2 | "Program for implementation of rules" — compliance program requirements |

OLRC footnote: *"Two subsecs. (q) have been enacted."*

**7 USC § 2143(f)** — Two subsections (f) of the Animal Welfare Act:

| | Content |
|---|---|
| V1 | "Suspension or revocation of Federal support for research projects" |
| V2 | "Veterinary certificate; contents; exceptions" — delivery requirements for dealers |

OLRC footnote: *"So in original. Two subsecs. (f) have been enacted."*

**10 USC § 2330a(h)(6)** — Two paragraphs (6):

| | Content |
|---|---|
| V1 | Definition of "service acquisition portfolio groups" per DoD Instruction 5000.74 |
| V2 | "Small business act definitions" — defines "small business concern" per 15 USC 632 |

OLRC footnote: *"So in original. There are two pars. (6)."*

Additional subsection duplicates without detailed content differences (typically
minor numbering collisions):

| Location | Type | Notes |
|---|---|---|
| 10 USC § 2324(e)(1)(P) | subparagraph | Two subparagraphs (P) |
| 10 USC § 2614(a)(1) | paragraph | Two paragraphs (1) |
| 10 USC § 7730(1), (2) | paragraph | Two each of paragraphs (1) and (2) |
| 5 USC § 5584(g) | subsection | Two subsections (g), each with child paragraphs |
| 5 USC § 5373(a)(4) | paragraph | Two paragraphs (4) |
| 5 USC § 604(a)(6) | paragraph | Two paragraphs (6) |
| 5 USC § 6304(f)(1)(H) | subparagraph | Two subparagraphs (H) |
| 5 USC § 6307(d) | subsection | Two subsections (d) |
| 5 USC § 8339(s) | subsection | Two subsections (s) |
| 5 USC § 8411(i) | subsection | Two subsections (i) |
| 5 USC § 9507(b)(1) | paragraph | **Three** paragraphs (1) |
| 5 USC § 9507(b)(6) | paragraph | Two paragraphs (6) |
| 7 USC § 1431(b)(7)(D)(ii)(I-II) | subclause | Two each of subclauses (I) and (II) |
| 7 USC § 1446(d)(2)(F) | subparagraph | Two subparagraphs (F) |
| 7 USC § 1631(c)(5) | paragraph | Two paragraphs (5) |
| 7 USC § 4808(a)(2) | paragraph | Two paragraphs (2) |
| 8 USC § 1154(a)(1)(B)(i)(I) | subclause | Two subclauses (I) |
| 2 USC § 6634(c)(3) | paragraph | OLRC note: *"Probably should be (4)"* |

### Impact on our data model

The `section_snapshot` table does **not** have a unique constraint on
`(revision_id, title_number, section_number)` because of section-level
duplicates. Both duplicate sections are stored as separate rows. Downstream
consumers (SnapshotService, the API) should be aware that a query by section
number may return multiple rows at a given revision.

Subsection-level duplicates are embedded within the section's `text_content` and
`normalized_provisions` and don't create duplicate rows. They may, however,
cause issues for provision-level diffing or rendering if the parser produces
duplicate provision identifiers.

See [GitHub issue #89](https://github.com/SanthoshBala/code-we-live-by/issues/89)
for the TODO on correctly displaying and tracking these duplicates through the
chrono pipeline.

## References

- [OLRC Download Page](https://uscode.house.gov/download/download.shtml)
- [OLRC Prior Release Points](https://uscode.house.gov/download/priorreleasepoints.htm)
- [Positive Law Codification](https://uscode.house.gov/codification/legislation.shtml)
- [USLM Schema Documentation](https://uscode.house.gov/download/resources/USLM-User-Guide.pdf)
