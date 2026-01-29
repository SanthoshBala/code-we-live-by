# Congress.gov Pipeline

This module provides data ingestion capabilities from the Congress.gov API for legislator and vote data.

## Congressional Concepts

### Congress Numbers

A **Congress** is a two-year period that begins on January 3rd of odd-numbered years. Each Congress is numbered sequentially:

| Congress | Years | Notable Events |
|----------|-------|----------------|
| 118th | 2023-2025 | Current Congress |
| 117th | 2021-2023 | Biden administration begins |
| 116th | 2019-2021 | Trump impeachment |
| 1st | 1789-1791 | First Congress under Constitution |

The formula: `Congress = ((Year - 1789) / 2) + 1` (rounded down)

### Sessions

Each Congress has two **sessions**, one per calendar year:
- **Session 1**: January of odd year to adjournment (typically late December)
- **Session 2**: January of even year to adjournment

### Chambers

Congress consists of two chambers:
- **House of Representatives**: 435 voting members, 2-year terms, represent districts
- **Senate**: 100 members (2 per state), 6-year staggered terms

### Roll Call Votes

A **roll call vote** (or **recorded vote**) is when each member's vote is individually recorded. Types include:

| Vote Type | Description |
|-----------|-------------|
| **Yea/Aye** | Vote in favor |
| **Nay/No** | Vote against |
| **Present** | Counted for quorum but not voting |
| **Not Voting** | Absent or abstaining |

Roll calls are numbered sequentially within each session (e.g., "Roll Call 296" in Session 1).

### Vote Outcomes

- **Passed**: Motion received required majority
- **Failed**: Motion did not receive required majority
- **Agreed to**: Resolution or amendment adopted
- **Rejected**: Resolution or amendment not adopted

Required majorities vary:
- Simple majority (>50%) for most legislation
- 2/3 majority for veto overrides, constitutional amendments
- 3/5 majority (60 votes) to end Senate filibusters

## Overview

The Congress.gov API (v3) provides comprehensive programmatic access to:

- **Legislators**: Members of Congress with biographical data
- **Terms**: Service periods for each legislator (House/Senate)
- **Votes**: Roll call votes with individual member positions (House only, 118th Congress+)

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

### Legislator Commands

```bash
# List members of Congress
python -m pipeline.cli congress-list-members --congress 118 --limit 20

# Ingest a single member by Bioguide ID
python -m pipeline.cli congress-ingest-member B000944

# Ingest all members from a Congress
python -m pipeline.cli congress-ingest-congress 118

# Ingest all current members
python -m pipeline.cli congress-ingest-current
```

### Vote Commands (House only, 118th Congress+)

```bash
# List House roll call votes
python -m pipeline.cli house-list-votes 118 --session 1 --limit 20

# Ingest a single House vote
python -m pipeline.cli house-ingest-vote 118 1 296

# Ingest all House votes for a Congress/session
python -m pipeline.cli house-ingest-votes 118 --session 1 --limit 50
```

**Important**: For individual votes to be linked to legislators, ingest legislators first:
```bash
python -m pipeline.cli congress-ingest-congress 118
python -m pipeline.cli house-ingest-votes 118 --session 1
```

## Programmatic Usage

### Client

```python
from pipeline.congress import CongressClient

client = CongressClient()  # Uses CONGRESS_API_KEY from settings

# Legislators
members = await client.get_members_by_congress(118)
detail = await client.get_member_detail("B000944")

# Votes (House only)
votes = await client.get_house_votes(118, session=1, limit=10)
vote_detail = await client.get_house_vote_detail(118, 1, 296)
member_votes = await client.get_house_vote_members(118, 1, 296)
```

### Ingestion Services

```python
from app.models.base import async_session_maker
from pipeline.congress import LegislatorIngestionService, VoteIngestionService

async with async_session_maker() as session:
    # Legislators
    leg_service = LegislatorIngestionService(session)
    await leg_service.ingest_congress(118)

    # Votes
    vote_service = VoteIngestionService(session)
    await vote_service.ingest_house_vote(118, 1, 296)
    await vote_service.ingest_house_votes_for_congress(118, session_num=1)
```

## Data Mapping

### Legislator Fields

| Congress.gov API | Database Field | Notes |
|------------------|----------------|-------|
| `bioguideId` | `bioguide_id` | Unique identifier |
| `firstName` | `first_name` | |
| `lastName` | `last_name` | |
| `directOrderName` | `full_name` | "Sherrod Brown" format |
| `partyName` | `party` | Mapped to PoliticalParty enum |
| `state` (from terms) | `state` | Two-letter code |
| `currentMember` | `is_current_member` | Boolean |
| `depiction.imageUrl` | `photo_url` | Member photo |

### Vote Fields

| Congress.gov API | Database Field | Notes |
|------------------|----------------|-------|
| `congress` | `congress` | Congress number |
| `sessionNumber` | `session` | 1 or 2 |
| `rollCallNumber` | `vote_number` | Roll call number |
| `startDate` | `vote_date` | When vote occurred |
| `result` | `result` | "Passed", "Failed", etc. |
| `votePartyTotal[].yeaTotal` | `yeas` | Sum across parties |
| `votePartyTotal[].nayTotal` | `nays` | Sum across parties |

### Member Vote Fields

| Congress.gov API | Database Field | Notes |
|------------------|----------------|-------|
| `bioguideID` | `legislator_id` | Linked via Legislator table |
| `voteCast` | `vote_cast` | "Aye", "No", "Present", etc. |

## API Coverage

| Data Type | Coverage |
|-----------|----------|
| Member Profiles | 71st Congress (1929) to present |
| House Votes | **118th Congress (2023) forward only** |
| Senate Votes | Not available via API (XML from Senate.gov required) |

## Limitations

1. **House votes only**: Senate votes are not yet available via Congress.gov API
2. **Recent data only**: House vote API covers 118th Congress (2023) forward
3. **Individual votes require legislators**: Must ingest legislators before votes to link member positions

## Rate Limits

- **5,000 requests/hour** (rolling window)
- Automatic retry with exponential backoff for server errors
- Maximum 3 retry attempts

## Related Documentation

- [Congress.gov API Documentation](https://api.congress.gov)
- [API GitHub Repository](https://github.com/LibraryOfCongress/api.congress.gov)
- [House Roll Call Votes Blog Post](https://blogs.loc.gov/law/2025/05/introducing-house-roll-call-votes-in-the-congress-gov-api/)
