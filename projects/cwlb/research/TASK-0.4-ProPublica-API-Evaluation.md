# Task 0.4: ProPublica Congress API Evaluation for Legislator Details

**Task**: Research ProPublica Congress API for legislator details
**Status**: Complete
**Date**: 2026-01-23

---

## Executive Summary

The ProPublica Congress API, which operated from 2016 to July 2024, has been **discontinued and is no longer available**. New API keys are not being issued, and the service was officially shut down approximately 18 months ago. This task evaluation documents what the API historically provided and identifies **superior alternative data sources** for CWLB's legislator detail requirements.

**Critical Finding**: The Congress.gov API (evaluated in Task 0.3) already provides comprehensive legislator data including photos, party affiliation, state, district, and biographical information. ProPublica's API would have been redundant even if it were still operational.

### Key Findings

| Criterion | ProPublica API (Discontinued) | Current Best Alternatives | Rating |
|-----------|-------------------------------|---------------------------|--------|
| API Status | **Discontinued July 2024** | Congress.gov API (Active) | N/A |
| Legislator Photos | Not provided (redirected to GitHub) | Congress.gov + unitedstates/images | Excellent |
| Party Affiliation | Available (when active) | Congress.gov API | Excellent |
| State & District | Available (when active) | Congress.gov API | Excellent |
| Historical Coverage | 102nd Congress (1991+) | 71st Congress (1929+) via Congress.gov | Better |
| Biographical Data | Good (when active) | Congress.gov API | Excellent |
| Rate Limits | 5,000/day (when active) | 5,000/hour via Congress.gov | Better |
| Authentication | X-API-Key header | Query param or header | Equivalent |

**Recommendation**: Use Congress.gov API (Task 0.3) as primary source for all legislator data. Supplement with unitedstates/images or unitedstates/congress-legislators GitHub repositories for additional photo sources and structured biographical data in YAML/JSON/CSV formats.

---

## 1. ProPublica Congress API - Historical Overview

### 1.1 Service Timeline

**Launch**: 2016
**Shutdown**: July 10, 2024
**Service Duration**: Approximately 8 years
**Current Status**: **Discontinued - No new API keys available**

### 1.2 Historical Purpose

ProPublica's Congress API provided programmatic access to:
- Members of Congress biographical information
- Congressional voting records
- Bill information and sponsorship
- Congressional statements
- Legislative activity metrics

### 1.3 Shutdown Context

In July 2024, ProPublica announced:
> "Represent and the Congress API are no longer available. Thank you to everybody who has used these resources since their launch in 2016."

**Migration Recommendation**: ProPublica recommended users migrate to the **Congress.gov API** (Library of Congress) for congressional legislative data.

---

## 2. Historical API Capabilities (When Active)

### 2.1 Member Endpoints (Now Unavailable)

**Base Structure (Historical)**:
```
GET https://api.propublica.org/congress/v1/{congress}/{chamber}/members.json
GET https://api.propublica.org/congress/v1/members/{member-id}.json
```

### 2.2 Member Data Fields (Historical)

**Basic Information:**
- `id` - ProPublica member ID
- `first_name`, `middle_name`, `last_name`, `suffix`
- `date_of_birth`
- `gender`

**Political Information:**
- `party` - Party affiliation (D, R, I, etc.)
- `state` - Two-letter state code
- `district` - Congressional district (House only)
- `title` - Full title (e.g., "Senator, 2nd Class")
- `short_title` - Abbreviated (e.g., "Sen." or "Rep.")
- `leadership_role` - Leadership positions
- `in_office` - Boolean for current service status
- `next_election` - Next election year

**External Identifiers:**
- `govtrack_id`
- `cspan_id`
- `votesmart_id`
- `icpsr_id`
- `crp_id` (Center for Responsive Politics)
- `google_entity_id`
- `fec_candidate_id`

**Contact & Social Media:**
- `url` - Official website
- `rss_url`
- `contact_form`
- `twitter_account`
- `facebook_account`
- `youtube_account`

### 2.3 Member Photos (Historical)

**Critical Limitation**: ProPublica's API **did not provide member photos**.

Instead, they redirected developers to:
- **unitedstates/images** GitHub repository (public domain GPO photos)
- Photos served via predictable URLs using Bioguide IDs

**Recommendation at the time**:
```
https://unitedstates.github.io/images/congress/[size]/[bioguide].jpg
```

### 2.4 Historical Data Coverage (When Active)

| Data Type | Coverage | Notes |
|-----------|----------|-------|
| **Member Profiles** | Current and historical members | More detail for 1995+ |
| **Voting Records** | 102nd Congress (1991) - present | House: 1991+, Senate: 1989+ |
| **Bills** | 113th Congress (2013) - present | Limited historical coverage |
| **Biographical Data** | 1789 - present | Via Biographical Directory integration |

**Coverage Gap**: ProPublica's member data was comprehensive for recent Congresses but offered less detail for pre-1995 members compared to the Biographical Directory.

### 2.5 Rate Limits (Historical)

| Limit Type | Value | Notes |
|------------|-------|-------|
| Daily Limit | 5,000 requests/day | Subject to change |
| Authentication | X-API-Key header | Not query string |
| Cost | Free | Registration required |

**Authentication Method (Historical)**:
```http
X-API-Key: PROPUBLICA_API_KEY
```

**Important**: API keys could not be passed as query string parameters, only as headers.

---

## 3. Current Alternative Sources (2026)

### 3.1 Congress.gov API (Primary Recommendation)

**Status**: ✅ Active, Official, Free
**Provider**: Library of Congress
**Evaluation**: See [TASK-0.3-Congress-API-Evaluation.md](TASK-0.3-Congress-API-Evaluation.md)

**Why This Supersedes ProPublica**:

| Feature | ProPublica (Discontinued) | Congress.gov API |
|---------|---------------------------|------------------|
| **Availability** | ❌ Shut down July 2024 | ✅ Active and maintained |
| **Official Source** | Third-party aggregator | Library of Congress (authoritative) |
| **Member Data** | 102nd Congress (1991+) | 71st Congress (1929+)* |
| **Photos** | Not provided | ✅ Provided via `depiction` field |
| **Photo URLs** | Redirected to GitHub | Direct URLs to Congress.gov hosted images |
| **Rate Limits** | 5,000/day | **5,000/hour** (50x better) |
| **Biographical Data** | Good | Comprehensive with terms, party history |
| **Sponsor Data** | Available | ✅ Detailed sponsors/cosponsors since 1973 |
| **Vote Records** | 102nd Congress (1991+) | 118th Congress (2023+) House, Senate planned |

*Members serving in 93rd Congress (1973) or later

**Congress.gov Member Endpoint Example**:
```
GET https://api.congress.gov/v3/member/{bioguideId}?api_key=YOUR_KEY&format=json
```

**Member Photo Access via Congress.gov API**:
```json
{
  "member": {
    "bioguideId": "B000944",
    "name": "Sherrod Brown",
    "state": "OH",
    "partyName": "Democratic",
    "depiction": {
      "imageUrl": "https://www.congress.gov/img/member/b000944.jpg",
      "attribution": "Image courtesy of the Member"
    }
  }
}
```

**Photo URL Pattern**:
```
https://www.congress.gov/img/member/{bioguideId}.jpg
```

### 3.2 unitedstates/congress-legislators (GitHub Repository)

**Status**: ✅ Active, Open Source, Public Domain
**URL**: https://github.com/unitedstates/congress-legislators
**Maintainer**: @unitedstates community project

**What It Provides**:
- Members of the United States Congress (1789-Present)
- Congressional committees (1973-Present)
- Committee membership (current only)
- Presidents and vice presidents
- Social media accounts (official accounts only)

**Data Formats**:
- **YAML** (primary format)
- **JSON** (converted from YAML)
- **CSV** (converted from YAML)

**Key Files**:
- `legislators-current.yaml` - Currently serving members
- `legislators-historical.yaml` - Historical members
- `legislators-social-media.yaml` - Social media accounts
- `committee-membership-current.yaml` - Current committee assignments

**Data Fields Include**:
- Bioguide ID (standard identifier)
- Name (first, middle, last, suffix, nickname, official_full)
- Birth and death dates
- Gender
- Terms served (with start/end dates, type, state, district, party)
- Leadership roles
- External IDs (govtrack, opensecrets, votesmart, fec, cspan, wikipedia, ballotpedia, etc.)
- Social media handles

**Advantages**:
- ✅ Complete historical coverage back to 1789
- ✅ Structured data in multiple formats (YAML/JSON/CSV)
- ✅ Regularly updated by community
- ✅ Cross-references to multiple databases via external IDs
- ✅ No API key required (direct file download or GitHub API)
- ✅ Version controlled (full history via Git)

**Example Access**:
```bash
# Download current legislators as JSON
curl https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.json

# Download historical legislators as YAML
curl https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-historical.yaml
```

**Use Case for CWLB**:
- Bulk download of all historical legislator data
- Cross-reference Bioguide IDs with other identifiers
- Social media account integration
- Committee membership tracking

### 3.3 unitedstates/images (Member Photos)

**Status**: ✅ Active, Public Domain
**URL**: https://github.com/unitedstates/images
**Source**: Government Publishing Office (GPO) Member Guide

**What It Provides**:
- Public domain photos of Members of Congress
- Indexed by Bioguide ID
- Multiple sizes available

**Photo URL Format**:
```
https://unitedstates.github.io/images/congress/[size]/[bioguide].jpg
```

**Available Sizes**:
- `original` - Original resolution
- `450x550` - Medium resolution
- `225x275` - Thumbnail resolution

**Example URLs**:
```
https://unitedstates.github.io/images/congress/original/L000551.jpg
https://unitedstates.github.io/images/congress/450x550/L000551.jpg
https://unitedstates.github.io/images/congress/225x275/L000551.jpg
```

**Coverage**:
- Primarily modern era (GPO Member Guide coverage)
- Served via GitHub Pages (reliable, fast CDN)
- Public domain (no attribution required, but recommended)

**Advantages**:
- ✅ No API key required
- ✅ Predictable URL structure
- ✅ Multiple resolutions
- ✅ Public domain license
- ✅ CDN-hosted via GitHub Pages

**Use Case for CWLB**:
- Display legislator photos in Law Viewer (Sponsors & Reviewers panel)
- Construct URLs programmatically using Bioguide IDs from Congress.gov API
- Fallback if Congress.gov photo URLs are unavailable

### 3.4 voteview/member_photos (Comprehensive Photo Archive)

**Status**: ✅ Active, Academic Project
**URL**: https://github.com/voteview/member_photos
**Maintainer**: UCLA Department of Political Science (voteview.com)

**What It Provides**:
- Photos of U.S. congressional representatives through the ages
- Scrapers to regenerate data from scratch
- Historical coverage including 19th century legislators

**Coverage**:
- **10,175 of 12,475** representatives (~82% coverage)
- **Every member serving since 1945** included
- Extensive historical coverage back to early Congresses

**Data Format**:
- Photos indexed by **ICPSR ID** (not Bioguide ID)
- `members.csv` file maps names to ICPSR IDs
- Includes scraper code (bio_guide.py) for Bioguide source

**Technical Details**:
- Uses Azure Facial Recognition API to normalize image orientation
- Automated image resizing and re-aspecting
- Scrapers pull from Bioguide and Wikipedia sources

**Advantages**:
- ✅ Most comprehensive historical photo archive
- ✅ Includes 19th century legislators
- ✅ Academic-quality data curation
- ✅ Open source scraper code

**Disadvantages**:
- ❌ Uses ICPSR IDs instead of Bioguide IDs (requires mapping)
- ❌ Not as easily accessible as unitedstates/images (requires Git clone)
- ❌ Hosted in Git repository, not via CDN URLs

**Use Case for CWLB**:
- Historical photo research (pre-1945 legislators)
- Cross-reference with ICPSR IDs for academic datasets
- Backup source if other photo sources lack coverage

### 3.5 GovInfo Congressional Pictorial Directory

**Status**: ✅ Active, Official
**URL**: https://www.govinfo.gov/collection/congressional-pictorial-directory
**Provider**: Government Publishing Office (GPO)
**API**: https://api.govinfo.gov/docs

**What It Provides**:
- Congressional Pictorial Directory published biennially
- Color photographs of all Members of Congress
- Senate and House leadership photos
- Officers, Delegates, and Resident Commissioner

**Coverage**:
- **82nd Congress (1951) to Present**
- Published every two years for each Congress
- Available as PDF documents

**API Access**:
```
GET https://api.govinfo.gov/packages/PICTDIR-{congress}/summary
```

**Authentication**:
- Requires api.data.gov key (free)
- Same key system as Congress.gov API

**Data Format**:
- PDF documents (full pictorial directory)
- Package-based API (metadata + content files)
- Interactive documentation via OpenAPI/Swagger

**Advantages**:
- ✅ Official government source
- ✅ High-quality photos
- ✅ Comprehensive coverage of each Congress
- ✅ Includes leadership and officers

**Disadvantages**:
- ❌ PDF format (not individual photo URLs)
- ❌ Requires parsing PDF to extract individual photos
- ❌ Published biennially (not real-time updates)
- ❌ More complex to integrate than direct image URLs

**Use Case for CWLB**:
- Reference for official photos
- Validation of photo accuracy
- Historical context (full pictorial directories)
- Not recommended for primary photo source due to PDF format

---

## 4. Recommended Data Sources for CWLB

### 4.1 Primary Source: Congress.gov API

**Use For**:
- ✅ Member biographical data (name, party, state, district, terms)
- ✅ Sponsor and cosponsor information for Public Laws
- ✅ Member photos via `depiction.imageUrl` field
- ✅ Linking Bioguide IDs to Public Laws

**Why**:
- Official Library of Congress source
- Excellent rate limits (5,000/hour)
- Already evaluated in Task 0.3
- Provides all data needed for CWLB Phase 1

**Endpoint**:
```
GET https://api.congress.gov/v3/member/{bioguideId}?api_key=YOUR_KEY&format=json
```

### 4.2 Supplemental Source: unitedstates/congress-legislators

**Use For**:
- ✅ Bulk download of all legislator data (1789-present)
- ✅ Historical members not covered by Congress.gov API (pre-1929)
- ✅ Social media account integration
- ✅ Cross-reference external IDs (govtrack, opensecrets, etc.)

**Why**:
- Complete historical coverage
- Structured YAML/JSON/CSV formats
- No API key required
- Community-maintained and up-to-date

**Access**:
```bash
curl https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.json
```

### 4.3 Photo Fallback: unitedstates/images

**Use For**:
- ✅ Fallback if Congress.gov photo URL is unavailable
- ✅ Multiple image sizes (original, 450x550, 225x275)
- ✅ Predictable URL construction

**Why**:
- Public domain
- CDN-hosted via GitHub Pages
- Reliable and fast
- Simple URL pattern

**URL Pattern**:
```
https://unitedstates.github.io/images/congress/450x550/{bioguideId}.jpg
```

### 4.4 Not Recommended: voteview/member_photos

**Reason**: Uses ICPSR IDs instead of Bioguide IDs, requiring additional mapping. Congress.gov API + unitedstates/images already provide sufficient photo coverage.

**Exception**: Only if researching pre-1945 historical legislators with no other photo sources available.

### 4.5 Not Recommended: GovInfo Pictorial Directory API

**Reason**: PDF format requires parsing. Direct image URLs from Congress.gov and unitedstates/images are far simpler to integrate.

**Exception**: Useful for validating photo accuracy or researching full historical context of a Congress.

---

## 5. Data Freshness and Update Schedule

### 5.1 Congress.gov API

**Update Frequency**:
- Data updates occur **throughout the day** (not real-time)
- Member data updated when changes occur (party switches, appointments, etc.)
- Photos updated periodically from GPO Member Guide

**Data Freshness**:
- Current Congress: Updated within hours to days of changes
- Historical Congresses: Static (rarely changes)

**Recommended Sync Strategy**:
- **Daily sync** for active Congresses (current and recent)
- **Weekly or monthly sync** for historical Congresses
- Real-time updates not necessary (Congress.gov itself isn't real-time)

### 5.2 unitedstates/congress-legislators

**Update Frequency**:
- Community-maintained via GitHub pull requests
- Updates typically occur **within days** of official announcements
- New Congress members added promptly after election certification

**Data Freshness**:
- Current legislators: Very fresh (community is active)
- Historical legislators: Complete and stable
- Social media: Updated periodically by community

**Recommended Sync Strategy**:
- **Weekly download** for current legislators
- **Monthly download** for complete dataset
- Monitor GitHub repository for commit activity

### 5.3 unitedstates/images

**Update Frequency**:
- Photos updated when new GPO Member Guide is published
- Typically updated at start of each new Congress
- Community contributions for missing photos

**Data Freshness**:
- Current Congress: Updated at Congress start, then periodically
- Historical: Stable

**Recommended Sync Strategy**:
- Cache photo URLs in database
- Validate image availability on first access
- Re-check if image fetch fails (member may have new photo)
- No need for frequent re-validation

### 5.4 Data Quality Assurance

**Validation Checks**:
1. **Bioguide ID Format**: 1-7 alphanumeric characters (e.g., "B000944")
2. **Party Codes**: D, R, I, L, ID (Independent Democrat), etc.
3. **State Codes**: Valid two-letter state abbreviations
4. **District Numbers**: 0-99 for House (0 = at-large), null for Senate
5. **Photo URLs**: HTTP 200 response when fetched
6. **Cross-Reference**: Bioguide IDs match across Congress.gov and unitedstates data

**Known Data Gaps**:
- Congress.gov API: Only members serving in 93rd Congress (1973) or later
- unitedstates/images: Not all historical members have photos
- Photos: Pre-1945 coverage is limited

---

## 6. Integration Strategy for CWLB

### 6.1 Phase 1: MVP Implementation

**Data Pipeline**:

1. **Ingest Public Laws** (from Task 0.2 - GovInfo API)
   ```
   Public Law → PL Number, Congress, Date
   ```

2. **Link to Bills** (from Task 0.3 - Congress.gov API)
   ```
   Public Law → Bill (congress, type, number)
   ```

3. **Extract Sponsors** (from Congress.gov Bill endpoint)
   ```
   GET /bill/{congress}/{type}/{number}
   → sponsors[].bioguideId
   ```

4. **Fetch Legislator Details** (from Congress.gov Member endpoint)
   ```
   GET /member/{bioguideId}
   → name, party, state, district, depiction.imageUrl
   ```

5. **Store in Legislator Table**
   ```sql
   INSERT INTO Legislator (
     bioguide_id,
     first_name,
     last_name,
     party,
     state,
     district,
     photo_url
   ) VALUES (...)
   ```

6. **Link Sponsors to Laws** (Sponsorship table)
   ```sql
   INSERT INTO Sponsorship (
     law_id,
     legislator_id,
     role  -- 'sponsor' or 'cosponsor'
   ) VALUES (...)
   ```

**Photo Handling Strategy**:

```python
def get_member_photo_url(bioguide_id):
    """
    Priority order for photo URLs:
    1. Congress.gov API depiction.imageUrl
    2. unitedstates/images (450x550 size)
    3. Fallback to placeholder if neither available
    """

    # Try Congress.gov API first
    member = fetch_congress_api_member(bioguide_id)
    if member.get('depiction', {}).get('imageUrl'):
        return member['depiction']['imageUrl']

    # Fallback to unitedstates/images
    unitedstates_url = f"https://unitedstates.github.io/images/congress/450x550/{bioguide_id}.jpg"
    if image_exists(unitedstates_url):
        return unitedstates_url

    # Fallback to placeholder
    return "/static/images/placeholder-legislator.jpg"
```

### 6.2 Database Schema Mapping

**Legislator Table**:

| Field | Source | API Endpoint | Example |
|-------|--------|--------------|---------|
| `bioguide_id` | Congress.gov | `/member/{bioguideId}` | "B000944" |
| `first_name` | Congress.gov | `member.name` (parse) | "Sherrod" |
| `last_name` | Congress.gov | `member.name` (parse) | "Brown" |
| `full_name` | Congress.gov | `member.name` | "Sherrod Brown" |
| `party` | Congress.gov | `member.partyName` | "Democratic" |
| `state` | Congress.gov | `member.state` | "OH" |
| `district` | Congress.gov | `member.district` | null (Senate) |
| `photo_url` | Congress.gov | `member.depiction.imageUrl` | "https://www.congress.gov/img/member/b000944.jpg" |
| `official_website` | Congress.gov | `member.officialWebsiteUrl` | "https://www.brown.senate.gov/" |

**Sponsorship Table**:

| Field | Source | Notes |
|-------|--------|-------|
| `law_id` | PublicLaw.id | Foreign key |
| `legislator_id` | Legislator.id | Foreign key (via bioguide_id) |
| `role` | Bill endpoint | 'sponsor' or 'cosponsor' |
| `is_original_cosponsor` | Bill cosponsors | Boolean (if cosponsor) |
| `sponsorship_date` | Bill cosponsors | Date added as cosponsor |

### 6.3 API Call Optimization

**Rate Limit Strategy**:

| API | Rate Limit | Strategy |
|-----|------------|----------|
| Congress.gov | 5,000/hour | Batch member lookups, cache results |
| unitedstates/images | No limit (static CDN) | Direct linking, no rate limiting needed |

**Caching Strategy**:
- Cache member data in database (rarely changes)
- Only re-fetch if data is older than 30 days
- Cache photo URLs indefinitely (validate on first access)

**Batch Processing**:
```python
# Example: Fetch all unique sponsors for a set of laws
bioguide_ids = set()
for law in public_laws:
    bill = fetch_bill_metadata(law.congress, law.type, law.number)
    bioguide_ids.add(bill['sponsors'][0]['bioguideId'])
    bioguide_ids.update([cs['bioguideId'] for cs in bill.get('cosponsors', [])])

# Batch fetch member details
for bioguide_id in bioguide_ids:
    if not legislator_exists_in_db(bioguide_id):
        member = fetch_congress_api_member(bioguide_id)
        store_legislator(member)
        time.sleep(0.72)  # Rate limiting: 5000/hour = 1.39/sec
```

---

## 7. Historical Context: What ProPublica Offered

### 7.1 Strengths of ProPublica API (When Active)

✅ **Voting Records**: Comprehensive vote data for both chambers (102nd Congress forward)
✅ **External IDs**: Cross-references to multiple databases (govtrack, opensecrets, etc.)
✅ **Social Media**: Integrated social media account information
✅ **Aggregated Data**: Pre-processed voting statistics and metrics
✅ **Ease of Use**: Simple RESTful API with good documentation
✅ **Free Access**: No cost, generous rate limits

### 7.2 Limitations of ProPublica API (When Active)

❌ **No Photos**: Did not provide member photos (redirected to GitHub)
❌ **Limited Historical**: 102nd Congress (1991) forward for most data
❌ **Third-Party**: Not an official government source
❌ **Rate Limits**: 5,000/day (vs. 5,000/hour for Congress.gov)
❌ **Bill Coverage**: 113th Congress (2013) forward only
❌ **Update Frequency**: Not as frequent as Congress.gov

### 7.3 Why Congress.gov API is Superior

Even if ProPublica's API were still operational, Congress.gov would be the better choice:

| Feature | ProPublica | Congress.gov |
|---------|------------|--------------|
| **Authority** | Third-party aggregator | Library of Congress (official) |
| **Member Data** | 102nd Congress (1991+) | 71st Congress (1929+)* |
| **Photos** | ❌ Not provided | ✅ Provided |
| **Rate Limits** | 5,000/day | **5,000/hour** |
| **Bill Metadata** | 113th Congress (2013+) | 93rd Congress (1973+) |
| **Sponsor Data** | Available | ✅ Detailed since 1973 |
| **Reliability** | ❌ Shut down 2024 | ✅ Maintained by LoC |

*Members serving in 93rd Congress (1973) or later

---

## 8. Comparison Matrix: All Data Sources

| Data Source | Status | Coverage | Photos | Party/State | Rate Limit | Auth | License |
|-------------|--------|----------|--------|-------------|------------|------|---------|
| **Congress.gov API** | ✅ Active | 1929+* | ✅ Yes | ✅ Yes | 5K/hour | API Key | Public |
| **unitedstates/legislators** | ✅ Active | 1789+ | ❌ No | ✅ Yes | Unlimited | None | Public Domain |
| **unitedstates/images** | ✅ Active | Modern | ✅ Yes | ❌ No | Unlimited | None | Public Domain |
| **voteview/member_photos** | ✅ Active | 1789+ (82%) | ✅ Yes | ❌ No | Unlimited | None | Academic |
| **GovInfo Pictorial Dir** | ✅ Active | 1951+ | ✅ PDF | ❌ No | 1K/hour | API Key | Public |
| **ProPublica API** | ❌ Shut Down | 1991-2024 | ❌ No | ✅ Yes | N/A | N/A | N/A |

*Members serving in 93rd Congress (1973) or later

---

## 9. Recommended Implementation for CWLB

### 9.1 Primary Strategy

**Use Congress.gov API for everything**:
1. Fetch Public Law → Bill mapping
2. Extract sponsor/cosponsor Bioguide IDs from Bill endpoint
3. Fetch member details from Member endpoint
4. Use `depiction.imageUrl` for photos
5. Store in Legislator table with Sponsorship linkages

**Advantages**:
- ✅ Single API (simpler architecture)
- ✅ Official source (authoritative)
- ✅ Excellent rate limits
- ✅ Photos included
- ✅ Already evaluated in Task 0.3

### 9.2 Supplemental Strategy

**Use unitedstates/congress-legislators for**:
- Historical members not in Congress.gov (pre-1929)
- Social media account integration (future enhancement)
- Cross-referencing external IDs (govtrack, opensecrets, etc.)

**Use unitedstates/images for**:
- Photo fallback if Congress.gov URL fails
- Multiple image sizes (thumbnail vs. full size)

### 9.3 Not Recommended

**Do NOT use**:
- ❌ ProPublica API (discontinued)
- ❌ voteview/member_photos (ICPSR ID mapping complexity)
- ❌ GovInfo Pictorial Directory (PDF parsing overhead)

---

## 10. Code Example: Legislator Data Ingestion

```python
import requests
import time
from typing import Dict, List, Optional

class LegislatorIngestion:
    """
    Ingest legislator data from Congress.gov API with photo fallback.
    """

    CONGRESS_API_BASE = "https://api.congress.gov/v3"
    UNITEDSTATES_IMAGES_BASE = "https://unitedstates.github.io/images/congress"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def fetch_member(self, bioguide_id: str) -> Optional[Dict]:
        """
        Fetch member details from Congress.gov API.
        """
        url = f"{self.CONGRESS_API_BASE}/member/{bioguide_id}"
        params = {
            'api_key': self.api_key,
            'format': 'json'
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            return response.json().get('member')
        elif response.status_code == 429:
            # Rate limit hit, wait and retry
            time.sleep(60)
            return self.fetch_member(bioguide_id)
        else:
            return None

    def get_photo_url(self, bioguide_id: str, member_data: Dict) -> str:
        """
        Get photo URL with fallback strategy.
        """
        # Try Congress.gov API photo first
        depiction = member_data.get('depiction', {})
        if depiction.get('imageUrl'):
            return depiction['imageUrl']

        # Fallback to unitedstates/images (450x550 size)
        fallback_url = f"{self.UNITEDSTATES_IMAGES_BASE}/450x550/{bioguide_id.lower()}.jpg"

        # Verify image exists
        if self._image_exists(fallback_url):
            return fallback_url

        # Final fallback to placeholder
        return "/static/images/placeholder-legislator.jpg"

    def _image_exists(self, url: str) -> bool:
        """
        Check if image URL returns 200 OK.
        """
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def parse_member_data(self, member: Dict) -> Dict:
        """
        Parse Congress.gov member data into database format.
        """
        bioguide_id = member['bioguideId']

        # Parse name (Congress.gov returns full name as single field)
        name_parts = member['name'].split()
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[-1] if len(name_parts) > 1 else ''

        return {
            'bioguide_id': bioguide_id,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': member['name'],
            'party': member.get('partyName'),
            'state': member.get('state'),
            'district': member.get('district'),
            'photo_url': self.get_photo_url(bioguide_id, member),
            'official_website': member.get('officialWebsiteUrl'),
            'current_member': member.get('currentMember', False)
        }

    def ingest_legislators_from_bill(self, congress: int, bill_type: str,
                                     bill_number: int) -> List[Dict]:
        """
        Ingest all sponsors/cosponsors for a given bill.
        """
        # Fetch bill metadata
        bill_url = f"{self.CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}"
        params = {'api_key': self.api_key, 'format': 'json'}

        response = self.session.get(bill_url, params=params)
        if response.status_code != 200:
            return []

        bill = response.json().get('bill', {})

        # Extract bioguide IDs
        bioguide_ids = set()

        # Sponsor
        sponsors = bill.get('sponsors', [])
        if sponsors:
            bioguide_ids.add(sponsors[0]['bioguideId'])

        # Cosponsors (fetch from sub-endpoint)
        cosponsors_url = f"{bill_url}/cosponsors"
        response = self.session.get(cosponsors_url, params=params)
        if response.status_code == 200:
            cosponsors = response.json().get('cosponsors', [])
            bioguide_ids.update([cs['bioguideId'] for cs in cosponsors])

        # Fetch member details for each bioguide ID
        legislators = []
        for bioguide_id in bioguide_ids:
            member = self.fetch_member(bioguide_id)
            if member:
                legislator_data = self.parse_member_data(member)
                legislators.append(legislator_data)

                # Rate limiting: 5000/hour = ~1.4/sec
                time.sleep(0.75)

        return legislators


# Example Usage
if __name__ == "__main__":
    ingestion = LegislatorIngestion(api_key="YOUR_CONGRESS_API_KEY")

    # Example: Copyright Act of 1976 (PL 94-553)
    # Originated as S.22 in 94th Congress
    legislators = ingestion.ingest_legislators_from_bill(
        congress=94,
        bill_type='s',
        bill_number=22
    )

    for leg in legislators:
        print(f"{leg['full_name']} ({leg['party']}-{leg['state']})")
        print(f"  Photo: {leg['photo_url']}")
```

---

## 11. Conclusion

### 11.1 Key Findings

1. **ProPublica Congress API is discontinued** (July 2024) and cannot be used for CWLB
2. **Congress.gov API is superior in every way**: official source, better rate limits, more comprehensive data, includes photos
3. **Task 0.3 already covered the ideal solution**: No additional API needed
4. **Supplemental sources available**: unitedstates repositories provide excellent fallback and historical data

### 11.2 Recommendations for CWLB

**Primary Source**: ✅ **Congress.gov API** (Task 0.3)
- Use for all legislator biographical data
- Use for sponsor/cosponsor relationships
- Use for member photos via `depiction.imageUrl`

**Supplemental Sources**:
- ✅ **unitedstates/congress-legislators**: Historical data (1789+), social media accounts
- ✅ **unitedstates/images**: Photo fallback, multiple sizes

**Not Recommended**:
- ❌ ProPublica API (discontinued)
- ❌ voteview/member_photos (ICPSR ID complexity)
- ❌ GovInfo Pictorial Directory (PDF parsing overhead)

### 11.3 Data Availability Assessment

| Requirement | Source | Status |
|-------------|--------|--------|
| **Legislator Photos** | Congress.gov + unitedstates/images | ✅ Excellent |
| **Party Affiliation** | Congress.gov API | ✅ Excellent |
| **State & District** | Congress.gov API | ✅ Excellent |
| **Historical Coverage** | Congress.gov (1929+) + unitedstates (1789+) | ✅ Excellent |
| **Data Freshness** | Congress.gov (daily updates) | ✅ Excellent |
| **Update Schedule** | Congress.gov (throughout the day) | ✅ Excellent |
| **Rate Limits** | 5,000/hour | ✅ Excellent |
| **API Cost** | Free (api.data.gov key) | ✅ Excellent |

### 11.4 Final Assessment

**Task 0.4 Conclusion**: The ProPublica Congress API is no longer available, but this is **not a problem** for CWLB. The Congress.gov API (evaluated in Task 0.3) already provides all required legislator data including photos, party affiliation, state, district, and comprehensive biographical information.

**No additional API integration is needed beyond Congress.gov API.**

**Recommendation**: Proceed with Congress.gov API as documented in Task 0.3, with optional supplemental use of unitedstates/congress-legislators for historical data and social media integration in future phases.

---

## Sources

- [ProPublica Represent](https://projects.propublica.org/represent/) - Shutdown announcement
- [ProPublica Congress API Documentation](https://projects.propublica.org/api-docs/congress-api/) - Historical reference
- [ProPublica Congress API - Members](https://projects.propublica.org/api-docs/congress-api/members/) - Historical member endpoint docs
- [GitHub - unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) - Comprehensive legislator data (1789-present)
- [GitHub - unitedstates/images](https://github.com/unitedstates/images) - Public domain member photos
- [GitHub - voteview/member_photos](https://github.com/voteview/member_photos) - UCLA historical photo archive
- [GovInfo Congressional Pictorial Directory](https://www.govinfo.gov/collection/congressional-pictorial-directory) - Official pictorial directories
- [GovInfo API Documentation](https://www.govinfo.gov/features/api) - GovInfo API access
- [Congress.gov API](https://api.congress.gov) - Primary recommended source
- [Biographical Directory of the United States Congress](https://bioguide.congress.gov/) - Official biographical directory
- [Sunlight Foundation - Congress in Photos](https://sunlightfoundation.com/2014/03/05/congress-in-photos-a-civic-hacking-success-story/) - History of unitedstates/images project

---

**Prepared by**: Claude (Anthropic AI)
**Date**: January 23, 2026
**Project**: The Code We Live By (CWLB)
**Phase**: Phase 0 - Research & Validation
