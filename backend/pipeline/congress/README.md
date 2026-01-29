# Congress.gov Pipeline

This module provides data ingestion capabilities from the Congress.gov API for legislator data.

## Overview

The Congress.gov API (v3) provides comprehensive programmatic access to legislator information, bill metadata, and sponsor/cosponsor data. This pipeline fetches and stores:

- **Legislators**: Members of Congress with biographical data
- **Terms**: Service periods for each legislator (House/Senate)
- **Future**: Sponsorship links to Public Laws

## Prerequisites

### API Key

A Congress.gov API key is required. Get a free key at:
https://api.congress.gov/sign-up/

Set the key via environment variable:
```bash
export CONGRESS_API_KEY=your-api-key-here
```

Or add to your `.env` file:
```
CONGRESS_API_KEY=your-api-key-here
```

### Database

Ensure the database is running and migrations are applied:
```bash
docker-compose up -d db
cd backend
alembic upgrade head
```

## CLI Commands

### List Members

List members of Congress:

```bash
# List all members (first 20)
python -m pipeline.cli congress-list-members

# List current members only
python -m pipeline.cli congress-list-members --current

# List members from a specific Congress
python -m pipeline.cli congress-list-members --congress 118

# Show more results
python -m pipeline.cli congress-list-members --limit 50
```

### Ingest Single Member

Ingest a specific member by their Bioguide ID:

```bash
# Ingest Sherrod Brown
python -m pipeline.cli congress-ingest-member B000944

# Force update existing record
python -m pipeline.cli congress-ingest-member B000944 --force
```

### Ingest Congress Members

Ingest all members who served in a specific Congress:

```bash
# Ingest 118th Congress members
python -m pipeline.cli congress-ingest-congress 118

# Force update existing records
python -m pipeline.cli congress-ingest-congress 118 --force
```

### Ingest Current Members

Ingest all currently serving members:

```bash
# Ingest current members
python -m pipeline.cli congress-ingest-current

# Force update
python -m pipeline.cli congress-ingest-current --force
```

## Programmatic Usage

### Client

```python
from pipeline.congress import CongressClient

client = CongressClient()  # Uses CONGRESS_API_KEY from settings

# List members by Congress
members = await client.get_members_by_congress(118)

# Get member details
detail = await client.get_member_detail("B000944")

# Get bill sponsors
sponsor, cosponsors = await client.get_bill_sponsors(117, "hr", 3076)
```

### Ingestion Service

```python
from app.models.base import async_session_maker
from pipeline.congress import LegislatorIngestionService

async with async_session_maker() as session:
    service = LegislatorIngestionService(session)

    # Ingest single member
    log = await service.ingest_member("B000944")

    # Ingest Congress
    log = await service.ingest_congress(118)

    # Ingest current members
    log = await service.ingest_current_members()
```

## Data Mapping

### Legislator Fields

| Congress.gov API | Database Field | Notes |
|------------------|----------------|-------|
| `bioguideId` | `bioguide_id` | Unique identifier |
| `firstName` | `first_name` | |
| `middleName` | `middle_name` | |
| `lastName` | `last_name` | |
| `suffixName` | `suffix` | Jr., Sr., III, etc. |
| `directOrderName` | `full_name` | "Sherrod Brown" format |
| `partyName` | `party` | Mapped to PoliticalParty enum |
| `state` | `state` | Two-letter code |
| `district` | `district` | House only |
| `currentMember` | `is_current_member` | Boolean |
| `birthYear` | `birth_date` | Converted to date |
| `deathYear` | `death_date` | Converted to date |
| `depiction.imageUrl` | `photo_url` | Member photo |
| `officialWebsiteUrl` | `official_website` | |

### Party Mapping

| API Value | Enum Value |
|-----------|------------|
| "Democratic" | `PoliticalParty.DEMOCRAT` |
| "Republican" | `PoliticalParty.REPUBLICAN` |
| "Independent" | `PoliticalParty.INDEPENDENT` |
| "Libertarian" | `PoliticalParty.LIBERTARIAN` |
| "Green" | `PoliticalParty.GREEN` |
| Other | `PoliticalParty.OTHER` |

### Chamber Mapping

| API Value | Enum Value |
|-----------|------------|
| "Senate" | `Chamber.SENATE` |
| "House of Representatives" | `Chamber.HOUSE` |

## API Coverage

Per the Congress.gov API documentation:

| Data Type | Coverage |
|-----------|----------|
| Member Profiles | 71st Congress (1929) to present* |
| Terms of Service | Complete for all included members |
| Party Affiliation | Current/last party only |
| Member Photos | Primarily recent Congresses |

*Members serving in 93rd Congress (1973) or later

## Rate Limits

- **5,000 requests/hour** (rolling window)
- Response includes `X-RateLimit-Remaining` header
- 429 errors trigger exponential backoff retry

## Error Handling

The client implements:
- Automatic retry for 5xx server errors
- Exponential backoff (2s, 4s, 8s)
- Maximum 3 retry attempts
- Detailed logging of failures

## Related Documentation

- [Congress.gov API Documentation](https://api.congress.gov)
- [API GitHub Repository](https://github.com/LibraryOfCongress/api.congress.gov)
- [Task 0.3 Research](../../research/TASK-0.3-Congress-API-Evaluation.md)
