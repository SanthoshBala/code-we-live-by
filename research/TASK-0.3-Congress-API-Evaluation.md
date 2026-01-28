# Task 0.3: Congress.gov API Evaluation for Bill Information

**Task**: Evaluate Congress.gov API for bill information
**Status**: Complete
**Date**: 2026-01-23

---

## Executive Summary

The Congress.gov API (v3), provided by the Library of Congress, offers comprehensive programmatic access to bill metadata, legislator information, and vote records. The API provides excellent coverage from the 93rd Congress (1973) forward for bills, with member data available from the 71st Congress (1929). The API requires a free API key and has generous rate limits (5,000 requests/hour) suitable for our use case.

### Key Findings

| Criterion | Assessment | Rating |
|-----------|------------|--------|
| API Availability | RESTful API with OpenAPI documentation | Excellent |
| Bill Metadata Coverage | 93rd Congress (1973) to present (comprehensive) | Excellent |
| Historical Bill Coverage | 6th Congress (1799) to 42nd Congress (1873) (limited) | Fair |
| Member Data Coverage | 71st Congress (1929) to present | Excellent |
| Sponsor/Cosponsor Data | 93rd Congress (1973+) with dates from 97th (1981+) | Good |
| Vote Record Coverage | House votes: 118th Congress (2023+), Senate: TBD | Fair |
| Authentication | Free API key via api.data.gov | Excellent |
| Rate Limits | 5,000 requests/hour | Excellent |
| Metadata Richness | Comprehensive bill, member, and legislative data | Excellent |

**Recommendation**: The Congress.gov API is the preferred source for bill metadata, legislator information, and sponsor/cosponsor data. It is essential for CWLB's needs for tracking Public Law sponsors, co-sponsors, and legislative activity. For vote records, supplement with ProPublica Congress API until Senate vote endpoints are released.

---

## 1. API Overview

### Primary Source
- **Organization**: Library of Congress
- **API Base URL**: https://api.congress.gov/v3/
- **Current Version**: v3 (version 3)
- **Documentation**: https://api.congress.gov (Interactive OpenAPI/Swagger)
- **GitHub Repository**: https://github.com/LibraryOfCongress/api.congress.gov
- **Launch Date**: September 2022 (replaced previous beta APIs)

### Key Endpoints for CWLB

| Endpoint | Path | Description |
|----------|------|-------------|
| **Bill** | `/bill` | Bill and resolution metadata (primary interest) |
| **Member** | `/member` | Legislator profiles, terms, party affiliation |
| **Amendment** | `/amendment` | Amendments to bills and resolutions |
| **Committee** | `/committee` | Committee information and assignments |
| **House Vote** | `/house-vote` | House roll call votes (beta, 118th Congress+) |
| **Law** | `/law` | Public and Private Laws by law number |
| **Nomination** | `/nomination` | Presidential nominations |
| **Treaty** | `/treaty` | International treaties |
| **Congressional Record** | `/daily-congressional-record` | Floor debates |
| **Committee Report** | `/committee-report` | Committee reports |
| **Hearing** | `/hearing` | Committee hearings |

---

## 2. Authentication & Access

### 2.1 API Key Requirements

**An API key is required for all requests.**

- **Registration**: https://api.congress.gov/sign-up/ (via api.data.gov)
- **Key Format**: 40-character alphanumeric string
- **Cost**: Free
- **Usage**: Append `?api_key=YOUR_KEY` to requests or use `X-Api-Key` header

### 2.2 Key Submission Methods

Keys can be submitted via:
1. **Query Parameter**: `?api_key=YOUR_KEY` (simplest)
2. **HTTP Header**: `X-Api-Key: YOUR_KEY`
3. **Basic Auth**: `api_key:` as username (password empty)

### 2.3 Demo Key

A `DEMO_KEY` is available for initial exploration with significantly lower rate limits. Not suitable for production use.

---

## 3. Rate Limits

### 3.1 Default Limits

| Limit Type | Value | Notes |
|------------|-------|-------|
| Hourly Limit | 5,000 requests | Rolling window |
| DEMO_KEY Limit | Much lower | For exploration only |
| Results per Request | 250 (max), 20 (default) | Use offset for pagination |

### 3.2 Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4998
```

### 3.3 Exceeding Limits

- **HTTP Status**: 429 (Too Many Requests)
- **Behavior**: Temporary block on API key
- **Recovery**: Automatic reset on rolling hourly basis

### 3.4 Higher Limits

Contact the Library of Congress API team for higher limits if needed for production use.

---

## 4. Bill Endpoint - Metadata and Structure

### 4.1 Overview

The Bill endpoint provides comprehensive metadata about bills and resolutions introduced in Congress.

**Base Paths:**
- List: `GET /bill` (all bills)
- By Congress: `GET /bill/{congress}` (e.g., `/bill/117`)
- By Type: `GET /bill/{congress}/{type}` (e.g., `/bill/117/hr`)
- Individual: `GET /bill/{congress}/{type}/{number}` (e.g., `/bill/117/hr/3076`)

### 4.2 Bill Types

| Code | Description | Example |
|------|-------------|---------|
| **hr** | House Bill | H.R. 1 |
| **s** | Senate Bill | S. 1 |
| **hjres** | House Joint Resolution | H.J.Res. 1 |
| **sjres** | Senate Joint Resolution | S.J.Res. 1 |
| **hconres** | House Concurrent Resolution | H.Con.Res. 1 |
| **sconres** | Senate Concurrent Resolution | S.Con.Res. 1 |
| **hres** | House Simple Resolution | H.Res. 1 |
| **sres** | Senate Simple Resolution | S.Res. 1 |

### 4.3 Bill Metadata Fields

**Core Metadata:**
- `congress`: Congress number (e.g., 117)
- `type`: Bill type (hr, s, etc.)
- `number`: Bill number
- `originChamber`: House or Senate
- `title`: Official title
- `introducedDate`: Date introduced
- `updateDate`: Last update timestamp

**Legislative Status:**
- `latestAction`: Most recent action and date
- `constitutionalAuthorityStatementText`: Constitutional basis (House bills)

**Related Data Containers:**
- `sponsors`: Bill sponsor
- `cosponsors`: Co-sponsors with dates
- `committees`: Committee assignments
- `relatedBills`: Related legislation
- `actions`: Legislative actions timeline
- `summaries`: Bill summaries (CRS)
- `titles`: All titles (official, short, popular)
- `amendments`: Amendments to the bill
- `subjects`: Policy area and subject terms
- `laws`: Public/Private Law numbers if enacted
- `notes`: Special notes about the bill

### 4.4 Sub-Endpoints

| Sub-Endpoint | Path | Description |
|--------------|------|-------------|
| Actions | `/bill/{congress}/{type}/{number}/actions` | Legislative actions timeline |
| Amendments | `/bill/{congress}/{type}/{number}/amendments` | Amendments to the bill |
| Committees | `/bill/{congress}/{type}/{number}/committees` | Committee assignments |
| Cosponsors | `/bill/{congress}/{type}/{number}/cosponsors` | Co-sponsor list with dates |
| Related Bills | `/bill/{congress}/{type}/{number}/relatedbills` | Related legislation |
| Subjects | `/bill/{congress}/{type}/{number}/subjects` | Policy areas and subjects |
| Summaries | `/bill/{congress}/{type}/{number}/summaries` | Bill summaries (CRS) |
| Text | `/bill/{congress}/{type}/{number}/text` | Bill text versions |
| Titles | `/bill/{congress}/{type}/{number}/titles` | All bill titles |

### 4.5 Example Response Structure (JSON)

```json
{
  "bill": {
    "congress": 117,
    "type": "HR",
    "number": "3076",
    "originChamber": "House",
    "title": "Infrastructure Investment and Jobs Act",
    "introducedDate": "2021-05-06",
    "sponsors": [
      {
        "bioguideId": "D000617",
        "fullName": "Rep. DelBene, Suzan K. [D-WA-1]",
        "firstName": "Suzan",
        "lastName": "DelBene",
        "party": "D",
        "state": "WA",
        "district": 1
      }
    ],
    "cosponsors": {
      "count": 217,
      "countIncludingWithdrawnCosponsors": 218,
      "url": "https://api.congress.gov/v3/bill/117/hr/3076/cosponsors?api_key=..."
    },
    "latestAction": {
      "actionDate": "2021-11-15",
      "text": "Became Public Law No: 117-58."
    },
    "laws": [
      {
        "type": "Public Law",
        "number": "117-58"
      }
    ]
  }
}
```

---

## 5. Sponsor and Cosponsor Data

### 5.1 Sponsor Information

Every bill has exactly one sponsor (primary author).

**Sponsor Fields:**
- `bioguideId`: Unique identifier (e.g., "D000617")
- `fullName`: Full name with title, party, state, district
- `firstName`, `middleName`, `lastName`: Name components
- `party`: Party code (D, R, I, etc.)
- `state`: Two-letter state code
- `district`: Congressional district (House only, 0 for at-large)
- `isByRequest`: Boolean indicating presidential or entity request

**Availability:**
- Bills from 93rd Congress (1973) forward have sponsor data
- Earlier historical bills (1799-1873) lack sponsor metadata

### 5.2 Cosponsor Information

The `/cosponsors` sub-endpoint provides detailed co-sponsor data.

**Cosponsor Fields:**
- Same biographical fields as sponsors
- `sponsorshipDate`: Date added as co-sponsor
- `isOriginalCosponsor`: Boolean for original vs. added later
- `sponsorshipWithdrawnDate`: If withdrawn (rare)

**Cosponsor Counts:**
- `count`: Current active co-sponsors
- `countIncludingWithdrawnCosponsors`: Total including withdrawn

**Historical Coverage:**
- **97th Congress (1981) forward**: Full cosponsor data with dates
- **93rd-96th Congress (1973-1980)**: Cosponsor names available, but dates not tracked
- **Pre-1973**: Cosponsor data not available

**Example Cosponsor Response:**

```json
{
  "cosponsors": [
    {
      "bioguideId": "B001281",
      "fullName": "Rep. Beatty, Joyce [D-OH-3]",
      "firstName": "Joyce",
      "lastName": "Beatty",
      "party": "D",
      "state": "OH",
      "district": 3,
      "sponsorshipDate": "2021-05-06",
      "isOriginalCosponsor": true
    },
    {
      "bioguideId": "S001145",
      "fullName": "Rep. Schakowsky, Janice D. [D-IL-9]",
      "firstName": "Janice",
      "middleName": "D.",
      "lastName": "Schakowsky",
      "party": "D",
      "state": "IL",
      "district": 9,
      "sponsorshipDate": "2021-05-11",
      "isOriginalCosponsor": false
    }
  ],
  "pagination": {
    "count": 217
  }
}
```

---

## 6. Member Endpoint - Legislator Data

### 6.1 Overview

The Member endpoint provides comprehensive biographical and service information for current and former members of Congress.

**Base Paths:**
- List: `GET /member` (all members, no filtering at list level)
- Individual: `GET /member/{bioguideId}` (e.g., `/member/B000944`)
- By Congress: `GET /member/congress/{congress}` (e.g., `/member/congress/117`)
- By District: `GET /member/congress/{congress}/{stateCode}/{district}`

### 6.2 Member Data Fields

**List-Level Fields:**
- `bioguideId`: Unique identifier (e.g., "B000944")
- `name`: Full name
- `state`: Two-letter state code
- `district`: District number (House only, 0 for at-large)
- `partyName`: Current/last party affiliation
- `terms`: Array of service terms
- `depiction`: Container for member photo with attribution
- `url`: Link to member detail endpoint

**Item-Level Fields (Additional):**
- `currentMember`: Boolean (true if currently serving)
- `partyHistory`: Array of party affiliations over time
- `leadership`: Leadership positions held
- `officialWebsiteUrl`: Member's official website
- `addressInformation`: Office address and phone
  - House members: Full address
  - Senate members: Complete address including zip code
- `birthYear`, `deathYear`: Birth and death years
- `updateDate`: Last data update timestamp
- `previousNames`: Container for name changes (if applicable)

**Terms Container:**
- `chamber`: "House of Representatives" or "Senate"
- `congress`: Congress number
- `startYear`, `endYear`: Term dates
- `memberType`: Representative, Senator, Delegate, Resident Commissioner

**Sponsored Legislation:**
- `/member/{bioguideId}/sponsored-legislation`: Bills sponsored by member
- `/member/{bioguideId}/cosponsored-legislation`: Bills co-sponsored by member

### 6.3 Member Photos

Member photos are available via the `depiction` container with source attribution.

**Photo URLs:**
- Hosted by Congress.gov
- Follow predictable pattern using bioguideId
- Collected primarily from GPO Member Guide
- Example: `https://www.congress.gov/img/member/{bioguideId}.jpg`

### 6.4 Historical Coverage

| Data Type | Coverage | Notes |
|-----------|----------|-------|
| Member Profiles | 71st Congress (1929) to present | Members serving in 93rd Congress (1973) or later |
| BioGuide IDs | 1774 to present | Via Biographical Directory |
| Terms of Service | Complete for all included members | Chronological order |
| Party Affiliation | Complete but static | `partyName` doesn't reflect mid-term changes |
| Member Photos | Modern era | Primarily recent Congresses |

**Important Note**: Congress.gov includes members from 1929 (71st Congress) forward **only if they were still serving in 1973 (93rd Congress)**. For complete historical member data back to 1774, use the Biographical Directory of the United States Congress or alternative sources.

### 6.5 Query Parameters

**For `/member/congress/{congress}` endpoint:**
- `currentMember=False`: Get all members who served during that Congress (recommended for historical data)
- `currentMember=True`: Get only current representatives of districts as of now

**Important**: Use `currentMember=False` for historical Congresses to get the most complete data, as redistricting can cause members to be excluded if querying by district alone.

### 6.6 Example Member Response

```json
{
  "member": {
    "bioguideId": "B000944",
    "name": "Sherrod Brown",
    "state": "OH",
    "partyName": "Democratic",
    "currentMember": true,
    "terms": [
      {
        "chamber": "Senate",
        "congress": 119,
        "memberType": "Senator",
        "startYear": 2025
      },
      {
        "chamber": "Senate",
        "congress": 118,
        "memberType": "Senator",
        "startYear": 2023,
        "endYear": 2025
      }
    ],
    "depiction": {
      "imageUrl": "https://www.congress.gov/img/member/b000944.jpg",
      "attribution": "Image courtesy of the Member"
    },
    "officialWebsiteUrl": "https://www.brown.senate.gov/",
    "addressInformation": {
      "officeAddress": "713 Hart Senate Office Building",
      "city": "Washington",
      "district": null,
      "phoneNumber": "202-224-2315",
      "zipCode": 20510
    }
  }
}
```

---

## 7. Vote Records

### 7.1 House Roll Call Votes

**Endpoint**: `/house-vote/{congress}/{session}/{voteNumber}`

**Status**: Beta (released May 2025)

**Coverage**: 118th Congress (2023) to present

**Sub-Endpoints:**
- Item level: `/house-vote/{congress}/{session}/{voteNumber}`
- Member votes: `/house-vote/{congress}/{session}/{voteNumber}/members`

**Vote Data Fields:**
- Vote number and date
- Question/description (e.g., "On Passage", "On Motion to Recommit")
- Vote result (Passed, Failed)
- Vote counts: Yea, Nay, Present, Not Voting
- Related bill (if applicable)
- Amendment information (if applicable)

**Member Vote Data:**
- `bioguideId`, name, party, state, district
- `votePosition`: "Yea", "Nay", "Present", "Not Voting"
- Recorded vote timestamp

**Non-Legislation Votes**: Includes procedural votes (e.g., "Election of the Speaker")

**Filtering**: By congress and session

### 7.2 Senate Roll Call Votes

**Status**: Not yet available via Congress.gov API (as of January 2026)

**Current Access**: Vote URLs referenced in Bill actions link to Senate.gov XML
- Links provided in bill actions for roll call votes
- Format: XML on Senate.gov

**Expected**: Senate vote endpoints planned for future release (similar to House vote structure)

### 7.3 Alternative Vote Data Sources

Until Senate votes are available via Congress.gov API:

**ProPublica Congress API**: Comprehensive vote data for both chambers
- House and Senate votes
- 102nd Congress (1991) to present
- Member-by-member voting records
- Nomination votes

**Senate.gov**: Direct XML access to roll call votes
- Complete historical coverage
- XML format
- Links provided in Congress.gov bill actions

**GovTrack**: Third-party aggregator with comprehensive vote data

---

## 8. Actions and Legislative Timeline

### 8.1 Actions Endpoint

**Path**: `/bill/{congress}/{type}/{number}/actions`

**Purpose**: Provides chronological timeline of legislative actions on a bill

**Action Types:**
- Introduction
- Committee referral
- Committee action (hearings, markups, reports)
- Floor action (debates, votes)
- Passed chamber
- Sent to other chamber
- Presidential action (signed, vetoed)
- Became law

**Action Fields:**
- `actionDate`: Date of action
- `text`: Action description
- `type`: Action type code
- `actionCode`: Numeric action code
- `sourceSystem`: Source (House, Senate, Library of Congress)
- `recordedVotes`: Array of roll call vote references
  - Links to vote XML on House Clerk or Senate.gov

**Roll Call Vote References:**

When an action involves a recorded vote, the `recordedVotes` container provides:
- `chamber`: House or Senate
- `congress`: Congress number
- `date`: Vote date
- `rollNumber`: Roll call number
- `sessionNumber`: Session (1 or 2)
- `url`: Link to XML vote record on Clerk.House.gov or Senate.gov

This is currently the primary way to access Senate vote data until Senate vote endpoints are released.

### 8.2 Coverage Notes

**Comprehensive Action Data**: 93rd Congress (1973) forward

**Limited Action Data**: 93rd-96th Congress (1973-1980)
- Committee and subcommittee actions incomplete
- Available actions: reporting from committee, referral to committee, discharge from committee

---

## 9. Related Bills

### 9.1 Related Bills Endpoint

**Path**: `/bill/{congress}/{type}/{number}/relatedbills`

**Purpose**: Identifies related legislation as determined by CRS, House, and Senate

**Relationship Types:**
- Identical bill
- Related bill
- Companion measure (House/Senate versions)
- Procedurally related

**Fields:**
- `congress`, `type`, `number`: Related bill identifiers
- `relationshipDetails`: Array describing the relationship
  - `type`: Relationship type
  - `identifiedBy`: Who identified relationship (CRS, House, Senate)

**Use Case for CWLB**: Track bills that ultimately became the same Public Law (e.g., when a House bill is used as vehicle for Senate text)

---

## 10. Summaries

### 10.1 Summaries Endpoint

**Path**: `/bill/{congress}/{type}/{number}/summaries`

**Purpose**: Provides bill summaries prepared by Congressional Research Service (CRS)

**Summary Types:**
- Introduced
- Reported to House/Senate
- Passed House/Senate
- Public Law
- Conference report

**Summary Fields:**
- `actionDate`: Date of legislative action
- `actionDesc`: Description (e.g., "Introduced in Senate")
- `text`: HTML summary text
- `updateDate`: When summary was last updated

**Coverage**: 93rd Congress (1973) forward

**Availability**: Not all bills have summaries; CRS prioritizes major legislation

---

## 11. Data Format and Response Structure

### 11.1 Response Formats

**Supported Formats:**
- **JSON** (recommended): `format=json` parameter or Accept header
- **XML**: `format=xml` parameter or default

**Format Selection:**
- Query parameter: `?format=json`
- HTTP Accept header: `Accept: application/json`

### 11.2 Response Structure

Every API response includes three standard components:

**1. Request Element:**
```json
{
  "request": {
    "contentType": "application/json",
    "format": "json"
  }
}
```

**2. Pagination Element:**
```json
{
  "pagination": {
    "count": 250,
    "next": "https://api.congress.gov/v3/bill?offset=250&limit=250&api_key=..."
  }
}
```

**3. Data Element:**
```json
{
  "bills": [
    { ... },
    { ... }
  ]
}
```

### 11.3 Pagination

- **Default**: 20 results per request
- **Maximum**: 250 results per request
- **Parameters**:
  - `limit`: Number of results (max 250)
  - `offset`: Starting position for results
- **Navigation**: Use `next` URL from pagination element

---

## 12. Coverage Dates Summary

### 12.1 Bills and Resolutions

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **Comprehensive Metadata** | 93rd Congress (1973) - present | Sponsors, cosponsors, actions, committees, summaries |
| **Limited Historical** | 6th Congress (1799) - 42nd Congress (1873) | Text and titles only, no sponsors/summaries |
| **Partial Historical** | 82nd Congress (1951) - 102nd Congress (1992) | Some text availability |
| **Bill Text** | Variable | May be missing, incomplete, or inaccurate for historical |
| **Bill Numbering** | 15th Congress (1817) forward | Pre-1817 bills were not numbered |

### 12.2 Sponsors and Cosponsors

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **Sponsors** | 93rd Congress (1973) - present | Full sponsor metadata |
| **Cosponsors with Dates** | 97th Congress (1981) - present | Sponsorship dates, original vs. added |
| **Cosponsors without Dates** | 93rd-96th Congress (1973-1980) | Names only, order listed, no dates |
| **Sponsor Statements** | 103rd Congress (1993) - present | Introductory remarks |

### 12.3 Members

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **Member Profiles** | 71st Congress (1929) - present | Members serving in 93rd Congress (1973) or later |
| **BioGuide IDs** | 1774 - present | Via Biographical Directory |
| **Terms** | Complete for included members | Chronological service terms |
| **Photos** | Modern era | Primarily recent Congresses |

### 12.4 Votes

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **House Roll Calls (API)** | 118th Congress (2023) - present | Beta endpoint with member votes |
| **Senate Roll Calls (API)** | Not yet available | XML links provided in bill actions |
| **Roll Call References** | 93rd Congress (1973) - present | URLs to Clerk.House.gov / Senate.gov |

### 12.5 Amendments

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **Amendments** | 97th Congress (1981) - present | Complete for House, limited for Senate pre-97th |
| **Amendment Actions** | 93rd Congress (1973) - present | With gaps in 93rd-96th |

### 12.6 Actions

| Data Element | Coverage | Notes |
|--------------|----------|-------|
| **Full Actions** | 97th Congress (1981) - present | All action types |
| **Limited Actions** | 93rd-96th Congress (1973-1980) | Committee actions incomplete |

---

## 13. Data Quality and Limitations

### 13.1 Known Limitations

**Historical Data:**
- Bills from 1799-1873: Text only, no sponsors/summaries
- Bills from 1973-1980: Incomplete committee actions
- Historical text may be missing or inaccurate

**Member Data:**
- Party affiliation: `partyName` field doesn't reflect mid-term party changes
- Historical members: Only those serving in 93rd Congress (1973) or later
- Redistricting: May affect district queries; use `currentMember=False` for accuracy

**Vote Data:**
- Senate votes: Not yet available via API (use XML links or ProPublica API)
- House votes: Only 118th Congress (2023) forward in API

**Update Frequency:**
- Data updates occur throughout the day but not in real-time
- Legislative days vs. calendar days may cause timing discrepancies

### 13.2 Data Sources

The Congress.gov API aggregates data from multiple authoritative sources:
- **Library of Congress**: Primary curator
- **Congressional Research Service (CRS)**: Bill summaries
- **House Clerk**: House legislative data
- **Senate Secretary**: Senate legislative data
- **Government Publishing Office (GPO)**: Bill text
- **Biographical Directory**: Member bioguide IDs

---

## 14. Comparison with Alternative APIs

### 14.1 ProPublica Congress API

**Strengths:**
- Complete vote data (both chambers, 102nd Congress forward)
- Member voting records and statistics
- Nomination votes
- Statement positions

**Limitations:**
- 102nd Congress (1991) forward only
- Less comprehensive bill metadata
- Commercial restrictions on some use cases

**Use Case**: Supplement Congress.gov API for Senate votes and voting statistics

### 14.2 GovInfo API

**Strengths:**
- Public Law documents (text, PDF)
- Statutes at Large
- Congressional Record

**Use Case**: Primary source for enacted law text (complements Congress.gov bill data)

### 14.3 Comparative Coverage

| Feature | Congress.gov API | ProPublica API | GovInfo API |
|---------|------------------|----------------|-------------|
| Bill Metadata | 93rd Congress+ (1973+) | 102nd Congress+ (1991+) | Limited |
| Sponsors | 93rd Congress+ (1973+) | 102nd Congress+ (1991+) | N/A |
| Member Profiles | 71st Congress+ (1929+)* | 102nd Congress+ (1991+) | N/A |
| House Votes | 118th Congress+ (2023+) | 102nd Congress+ (1991+) | N/A |
| Senate Votes | Planned (links to XML) | 102nd Congress+ (1991+) | N/A |
| Public Law Text | Links to GovInfo | N/A | 104th Congress+ (1995+) |
| Rate Limit | 5,000/hour | 5,000/day | 1,000/hour |

*Members serving in 93rd Congress (1973) or later

---

## 15. API Usage Examples

### 15.1 Get Bill Metadata

```
GET https://api.congress.gov/v3/bill/117/hr/3076?api_key=YOUR_KEY&format=json
```

**Response**: Complete bill metadata including sponsors, title, status, actions

### 15.2 Get Bill Cosponsors

```
GET https://api.congress.gov/v3/bill/117/hr/3076/cosponsors?api_key=YOUR_KEY&format=json
```

**Response**: List of all cosponsors with dates and biographical info

### 15.3 Get Member Information

```
GET https://api.congress.gov/v3/member/B000944?api_key=YOUR_KEY&format=json
```

**Response**: Complete member profile with terms, party, contact info

### 15.4 Get Member's Sponsored Legislation

```
GET https://api.congress.gov/v3/member/B000944/sponsored-legislation?api_key=YOUR_KEY&format=json
```

**Response**: All bills sponsored by the member

### 15.5 Get House Vote Details

```
GET https://api.congress.gov/v3/house-vote/118/1/100?api_key=YOUR_KEY&format=json
```

**Response**: Vote details including counts and result

### 15.6 Get Member Votes on House Vote

```
GET https://api.congress.gov/v3/house-vote/118/1/100/members?api_key=YOUR_KEY&format=json
```

**Response**: How each member voted (Yea, Nay, Present, Not Voting)

### 15.7 List All Bills in a Congress

```
GET https://api.congress.gov/v3/bill/117?limit=250&offset=0&api_key=YOUR_KEY&format=json
```

**Response**: Paginated list of bills (max 250 per request)

### 15.8 Get Member by District

```
GET https://api.congress.gov/v3/member/congress/117/OH/13?api_key=YOUR_KEY&format=json
```

**Response**: Member representing OH-13 in 117th Congress

---

## 16. Integration Recommendations for CWLB

### 16.1 Primary Use Cases

**1. Public Law Sponsor Attribution**
- Use Bill endpoint to get sponsor and cosponsors for bills that became Public Laws
- Link bills to Public Laws via `laws` container in bill metadata
- Extract bioguideId, name, party, state, district for attribution

**2. Legislator Profiles**
- Use Member endpoint to build comprehensive legislator database
- Include photos, party affiliation, terms of service
- Link to sponsored and cosponsored legislation

**3. Legislative Timeline**
- Use Actions endpoint to build legislative journey timeline
- Track bill progress from introduction to enactment
- Identify key dates (introduced, passed House, passed Senate, signed)

**4. Vote Records**
- Use House Vote endpoint for House roll calls (118th Congress forward)
- Supplement with ProPublica API for Senate votes and historical votes
- Link votes to Public Laws via bill actions

### 16.2 Data Pipeline Strategy

**Phase 1 (MVP):**
1. Ingest enacted Public Laws (use GovInfo API from Task 0.2)
2. For each Public Law, query Congress.gov API to get:
   - Originating bill(s) via `/law` endpoint
   - Bill metadata (sponsors, timeline) via `/bill/{congress}/{type}/{number}`
   - Cosponsors via `/bill/.../cosponsors`
   - Actions and votes via `/bill/.../actions`
3. Build Legislator database from Member endpoint
4. Store sponsor/cosponsor relationships in Sponsorship table

**Phase 2 (Enhancement):**
1. Expand vote record ingestion (House and Senate via ProPublica API)
2. Build Vote table with member-by-member voting records
3. Track legislative journey with Actions data

**Phase 3 (Open PRs):**
1. Ingest current bills (not yet enacted) from Bill endpoint
2. Track bill status and proposed changes
3. Update in real-time as bills progress

### 16.3 API Call Optimization

**Rate Limit Management:**
- 5,000 requests/hour is generous for initial ingestion
- For 117th Congress: ~15,000 bills total
  - ~3 hours to fetch all bill metadata (at max rate)
  - Add sub-endpoint calls: ~12-15 hours for comprehensive data
- Implement exponential backoff for 429 errors
- Cache responses to avoid redundant calls

**Pagination Strategy:**
- Use `limit=250` (maximum) for list endpoints
- Track offset for resumable ingestion
- Store last update timestamp to fetch only new/changed data

**Data Freshness:**
- Daily sync for active Congresses (current and recent)
- Weekly sync for historical Congresses (data rarely changes)
- Real-time updates not necessary; Congress.gov itself isn't real-time

### 16.4 Required API Keys

| API | Purpose | Rate Limit |
|-----|---------|------------|
| Congress.gov API | Primary (bills, members, votes) | 5,000/hour |
| ProPublica Congress API | Supplemental (Senate votes, statistics) | 5,000/day |
| GovInfo API | Public Law text and documents | 1,000/hour |

### 16.5 Error Handling

**Common Errors:**
- `404 Not Found`: Bill/member doesn't exist (normal for gaps in numbering)
- `429 Too Many Requests`: Rate limit exceeded (backoff and retry)
- `503 Service Unavailable`: Temporary outage (retry with exponential backoff)

**Data Quality Checks:**
- Verify bioguideId format (1-7 characters, alphanumeric)
- Validate congress numbers (range: 1-current)
- Check for null/missing sponsor data on historical bills
- Handle cosponsors without dates for pre-1981 bills

---

## 17. Strengths and Weaknesses for CWLB

### 17.1 Strengths

✅ **Official Source**: Library of Congress authoritative data
✅ **Comprehensive Coverage**: 93rd Congress (1973) forward for bills
✅ **Rich Metadata**: Sponsors, cosponsors, actions, committees, summaries
✅ **Member Data**: Complete legislator profiles with photos and terms
✅ **Generous Rate Limits**: 5,000 requests/hour suitable for batch ingestion
✅ **Well-Documented**: OpenAPI specification and GitHub documentation
✅ **Active Development**: Regular updates and new endpoints (e.g., House votes)
✅ **Free Access**: No cost for API key
✅ **Multiple Formats**: JSON and XML support

### 17.2 Weaknesses

❌ **Limited Historical Data**: Pre-1973 bills lack sponsor/summary metadata
❌ **Incomplete Vote Data**: Senate votes not yet available via API (must use XML links)
❌ **Member Coverage Gap**: Only members serving in 93rd Congress (1973) or later
❌ **No Real-Time Updates**: Data updates throughout day but not instant
❌ **Party Affiliation Static**: Doesn't track mid-term party changes
❌ **Cosponsorship Dates**: Not available for 1973-1980 period
❌ **Action Data Gaps**: Committee actions incomplete for 1973-1980

### 17.3 Suitability for CWLB

**Overall Assessment**: ⭐⭐⭐⭐⭐ Excellent

The Congress.gov API is the ideal primary source for:
- Bill metadata linking Public Laws to sponsors
- Legislator profiles and biographical data
- Cosponsorship relationships
- Legislative timelines and actions

**Recommended Supplements**:
- ProPublica Congress API for vote records (especially Senate)
- GovInfo API for Public Law text (already covered in Task 0.2)
- Biographical Directory for pre-1929 member data (if expanding beyond Phase 1 scope)

---

## 18. Next Steps and Recommendations

### 18.1 Immediate Actions

1. **Register for API Key**: https://api.congress.gov/sign-up/
2. **Test API Endpoints**: Verify access and response formats
3. **Build Prototype Ingestion**: Test with one Public Law (e.g., PL 94-553)
   - Fetch bill metadata
   - Extract sponsors and cosponsors
   - Parse actions and timeline
4. **Design Data Model Mapping**: Map API responses to CWLB database schema
   - PublicLaw ↔ Law endpoint
   - Legislator ↔ Member endpoint
   - Sponsorship ↔ Bill sponsors/cosponsors
   - Vote ↔ House Vote endpoint (+ ProPublica for Senate)

### 18.2 Phase 1 Implementation

1. **Legislator Database**:
   - Ingest all members from 93rd Congress (1973) forward
   - Store bioguideId, names, party, state, district, photos
   - Build terms table for service periods

2. **Public Law to Bill Mapping**:
   - For each Public Law from Phase 1 titles (Task 0.2):
     - Query `/law/{congress}/{type}/{number}` to get bill reference
     - Fetch bill metadata via `/bill/{congress}/{type}/{number}`
     - Extract sponsors/cosponsors
     - Link to Legislator table via bioguideId

3. **Legislative Timeline**:
   - Ingest actions for each bill
   - Store key dates: introduced, passed House, passed Senate, signed
   - Extract vote references for roll call votes

### 18.3 Alternative Data Sources (if needed)

**For Historical Members (pre-1929)**:
- Biographical Directory of the United States Congress (bioguide.congress.gov)
- GitHub: unitedstates/congress-legislators (YAML/JSON/CSV)

**For Senate Votes**:
- ProPublica Congress API (102nd Congress forward)
- Senate.gov XML (complete historical, linked from Congress.gov actions)

**For Additional Legislator Data**:
- ProPublica Congress API (voting statistics, statements)
- House.gov and Senate.gov (official websites)

### 18.4 Data Quality Assurance

**Verification Strategy**:
1. Cross-reference bill sponsors with known Public Laws (e.g., Copyright Act of 1976)
2. Validate bioguideId format and uniqueness
3. Check for missing sponsor data on historical bills (expected for pre-1973)
4. Verify party affiliation codes (D, R, I, etc.)
5. Ensure cosponsorship dates are present for 1981+ bills

**Testing Scenarios**:
- Modern bill with many cosponsors (e.g., Infrastructure Investment and Jobs Act)
- Historical bill from 1970s (limited metadata)
- Bill with multiple related bills
- Bill with extensive action timeline
- Member with long service history and party change

---

## 19. Documentation and Support

### 19.1 Official Resources

**Primary Documentation:**
- API Documentation: https://api.congress.gov
- GitHub Repository: https://github.com/LibraryOfCongress/api.congress.gov
- OpenAPI Specification: Available at API root

**Guides:**
- Endpoint-specific documentation in GitHub repo
- Change log: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/ChangeLog.md
- Coverage dates: https://www.congress.gov/help/coverage-dates

**Community Resources:**
- R package documentation: https://cran.r-project.org/package=congress
- Postman collection: https://documenter.getpostman.com/view/6803158/VV56LCkZ

### 19.2 Support Channels

**Issues and Questions:**
- GitHub Issues: https://github.com/LibraryOfCongress/api.congress.gov/issues
- Email: Contact through Congress.gov help

**Updates and Announcements:**
- In Custodia Legis (Law Library blog): https://blogs.loc.gov/law/
- GitHub repository (watch for releases)

---

## 20. Conclusion

The Congress.gov API (v3) is an excellent data source for CWLB's needs regarding bill metadata, legislator information, and sponsor/cosponsor tracking. Its comprehensive coverage from 1973 forward, generous rate limits, and official authoritative status make it the ideal primary API for linking Public Laws to the legislators who authored them.

**Key Takeaways:**

✅ **Use for**: Bill metadata, sponsors, cosponsors, member profiles, actions, legislative timeline
✅ **Coverage**: Comprehensive from 93rd Congress (1973) forward
✅ **Rate Limits**: 5,000 requests/hour (excellent for batch ingestion)
✅ **Supplement with**: ProPublica API for Senate votes, GovInfo API for law text

**Recommendation**: Proceed with Congress.gov API as the primary source for Task 0.3 requirements. Register for API key and begin prototype development with sample Public Laws from Phase 1 titles.

---

## Sources

- [Congress.gov API - Official Documentation](https://api.congress.gov)
- [GitHub - LibraryOfCongress/api.congress.gov](https://github.com/LibraryOfCongress/api.congress.gov)
- [Bill Endpoint Documentation](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md)
- [Member Endpoint Documentation](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md)
- [Congress.gov API Changelog](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/ChangeLog.md)
- [Library of Congress - Congress.gov API](https://www.loc.gov/apis/additional-apis/congress-dot-gov-api/)
- [Introducing House Roll Call Votes in the Congress.gov API](https://blogs.loc.gov/law/2025/05/introducing-house-roll-call-votes-in-the-congress-gov-api/)
- [Coverage Dates for Congress.gov Collections](https://www.congress.gov/help/coverage-dates)
- [About Congressional Member Profiles](https://www.congress.gov/help/members)
- [Member BioGuide IDs](https://www.congress.gov/help/field-values/member-bioguide-ids)
- [ProPublica Congress API](https://projects.propublica.org/api-docs/congress-api/)

---

**Prepared by**: Claude (Anthropic AI)
**Date**: January 23, 2026
**Project**: The Code We Live By (CWLB)
**Phase**: Phase 0 - Research & Validation
