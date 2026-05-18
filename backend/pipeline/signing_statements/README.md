# Signing Statements Pipeline

Fetches and stores presidential signing statements so the History tab can display them as an inline blockquote on the presidential action event.

## Modules

| Module | Role |
|---|---|
| `fetcher.py` | GovInfo CPD API client — searches for and retrieves signing statement text |
| `ingestion.py` | DB ingestion service — calls the fetcher and persists results on `PublicLaw` |

## Data Source

**GovInfo CPD** (`api.govinfo.gov`, collection code `CPD`) — the official government archive of the Compilation of Presidential Documents. Requires `GOVINFO_API_KEY`.

The collection uses two package-ID prefixes depending on era:
- `WCPD-YYYY-MM-DD` — Weekly Compilation (1993–2009, Clinton / Bush)
- `DCPD-YYYYMMDDXXX` — Daily Compilation (2009–present, Obama onwards)

Not every law receives a signing statement; most routine bills do not.

## Data Flow

```
GovInfo POST /search  →  filter collectionCode=CPD
       ↓ granuleId
GovInfo GET /packages/{pkg}/granules/{granule}/htm
       ↓ plain text (leading whitespace stripped per line)
fetcher.py: fetch_signing_statement(congress, law_number, title)
       ↓ SigningStatementResult(text, source_url, title, date_issued)
ingestion.py: SigningStatementIngestionService.seed_law(congress, law_number)
       ↓
public_law.signing_statement  (Text)
       ↓
get_law_history() attaches it to the presidential_action TimelineEventSchema
       ↓
GET /api/v1/laws/{congress}/{law_number}/history  →  TimelineEvent.signing_statement
       ↓
TimelineEvent.tsx renders inline blockquote with expand/collapse toggle
```

## Usage

```python
from sqlalchemy.ext.asyncio import AsyncSession
from pipeline.signing_statements import SigningStatementIngestionService

async def run(session: AsyncSession) -> None:
    svc = SigningStatementIngestionService(session)

    # Seed a single law
    found = await svc.seed_law(congress=118, law_number=5)

    # Seed all laws in a congress
    found, total = await svc.seed_congress(congress=118)
```

## Limitations

- Only laws that received a formal signing statement will be populated; the majority of laws do not have one.
- Search is by short title — if the title used in GovInfo differs from the law's `short_title`, the fetch will return `None`. The fallback queries by public law number (`"Public Law No. {congress}-{law_number}"`).
