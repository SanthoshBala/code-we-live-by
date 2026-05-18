# Signing Statements Pipeline

Scrapes and stores presidential signing statements so the History tab can display them as collapsible comments attached to the presidential action event.

## Modules

| Module | Role |
|---|---|
| `scraper.py` | HTTP scraper targeting the UCSB American Presidency Project |
| `ingestion.py` | DB ingestion service — fetches via the scraper and persists on `PublicLaw` |

## Data Source

**UCSB American Presidency Project** (`presidency.ucsb.edu`) — the most comprehensive public archive of presidential signing statements. No API key required.

Search URL pattern:
```
https://www.presidency.ucsb.edu/advanced-search?field-keywords=Public+Law+118-5&category2[]=50
```

## Data Flow

```
UCSB advanced search
       ↓
scraper.py: fetch_signing_statement(congress, law_number)
       ↓ SigningStatementResult(text, source_url, title)
ingestion.py: SigningStatementIngestionService.seed_law(congress, law_number)
       ↓
public_law.signing_statement  (Text)
public_law.signing_statement_url  (String)
       ↓
get_law_history() in crud/public_law.py attaches it to the presidential_action TimelineEventSchema
       ↓
GET /api/v1/laws/{congress}/{law_number}/history  →  TimelineEvent.signing_statement
       ↓
TimelineEvent.tsx renders collapsible <details> block
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

- No public law has a signing statement by default; only a subset of laws receive one.
- The scraper searches by "Public Law {congress}-{number}"; if UCSB's search returns a false positive, the wrong text may be stored. Validate manually for high-visibility laws.
- UCSB HTML structure may change; update `_parse_search_results` and `_parse_statement_page` in `scraper.py` if the selectors break.
