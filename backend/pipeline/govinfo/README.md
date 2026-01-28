# GovInfo Data Pipeline

This module fetches and ingests Public Law data from the [GovInfo API](https://api.govinfo.gov/).

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   GovInfo API   │     │   PostgreSQL    │
│ api.govinfo.gov │     │    Database     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │ fetch                 │ ingest
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│    client.py    │────▶│  ingestion.py   │
│                 │     │                 │
│ - Collections   │     │ - Upserts laws  │
│ - Packages      │     │ - Tracks logs   │
│ - Downloads     │     │                 │
└─────────────────┘     └─────────────────┘
```

## Components

### 1. Client (`client.py`)

HTTP client for the GovInfo API.

**Key class:** `GovInfoClient`

```python
from pipeline.govinfo.client import GovInfoClient

# Requires API key (set GOVINFO_API_KEY env var or pass directly)
client = GovInfoClient(api_key="your-api-key")

# List public laws modified since a date
from datetime import datetime
laws = await client.get_public_laws(
    start_date=datetime(2025, 1, 1),
    congress=119,  # Optional filter
)

# Get all public laws for a specific Congress
laws = await client.get_public_laws_for_congress(119)

# Get detailed info for a specific law
detail = await client.get_public_law_detail("PLAW-119publ60")

# Download XML content
xml = await client.download_law_xml(detail)
```

**Data classes:**
- `PLAWPackageInfo` - Basic info from collections endpoint (id, congress, law number)
- `PLAWPackageDetail` - Full details from packages endpoint (title, dates, URLs)

### 2. Ingestion Service (`ingestion.py`)

Persists Public Law data to PostgreSQL.

**Key class:** `PublicLawIngestionService`

```python
from pipeline.govinfo.ingestion import PublicLawIngestionService
from sqlalchemy.ext.asyncio import AsyncSession

async with AsyncSession(engine) as session:
    service = PublicLawIngestionService(session)

    # Ingest all laws for a Congress
    log = await service.ingest_congress(119)

    # Ingest a single law
    log = await service.ingest_law(congress=119, law_number=60)

    # Ingest recently modified laws
    log = await service.ingest_recent_laws(days=30)
```

**Features:**
- Upserts records (creates or updates based on unique key)
- Creates `DataIngestionLog` records for audit trail
- Supports `force` flag for re-ingestion

## API Key Setup

The GovInfo API requires a free API key from [api.data.gov](https://api.data.gov/signup/).

### Option 1: Using .env file (recommended for local dev)

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```
   GOVINFO_API_KEY=your-api-key-here
   ```

The key is automatically loaded by the app settings.

### Option 2: Environment variable

```bash
export GOVINFO_API_KEY=your-api-key-here
```

### Option 3: Pass directly to client

```python
client = GovInfoClient(api_key="your-api-key")
```

## GovInfo API Reference

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/collections/PLAW/{date}` | List public laws modified since date |
| `/packages/{packageId}/summary` | Get details for a specific law |

### Package ID Format

Public Law package IDs follow the pattern: `PLAW-{congress}{type}{number}`

- `PLAW-119publ60` = Public Law 119-60 (public law)
- `PLAW-119pvt5` = Private Law 119-5 (private law)

### Rate Limits

The API doesn't document explicit rate limits, but be respectful:
- Use pagination (`offsetMark`) for large result sets
- Cache results where possible
- Consider delays between requests for bulk operations

## Database Tables

The ingestion service populates:

- `PublicLaw` - Public and private laws enacted by Congress

Future enhancements will also populate:
- `Bill` - Originating bill information
- `LawChange` - Changes made to US Code sections

## References

- [GovInfo API Documentation](https://api.govinfo.gov/docs/)
- [GovInfo Developer Hub](https://www.govinfo.gov/developers)
- [GovInfo GitHub](https://github.com/usgpo/api)
- [PLAW Collection Help](https://www.govinfo.gov/help/plaw)
- [API Key Signup](https://api.data.gov/signup/)
