# Task 0.12: API Architecture Design

**Status**: Complete
**Completed**: 2026-01-27
**Deliverables**:
- This documentation file

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [API Style Decision: REST vs GraphQL](#2-api-style-decision-rest-vs-graphql)
3. [API Design Principles](#3-api-design-principles)
4. [Authentication & Rate Limiting](#4-authentication--rate-limiting)
5. [API Endpoints Overview](#5-api-endpoints-overview)
6. [Code Browsing API](#6-code-browsing-api)
7. [Law Viewer API](#7-law-viewer-api)
8. [Search API](#8-search-api)
9. [Time Travel API](#9-time-travel-api)
10. [Blame View API](#10-blame-view-api)
11. [Analytics API](#11-analytics-api)
12. [Bills API (Future)](#12-bills-api-future)
13. [Error Handling](#13-error-handling)
14. [Pagination](#14-pagination)
15. [Versioning Strategy](#15-versioning-strategy)
16. [Performance Considerations](#16-performance-considerations)
17. [OpenAPI Specification](#17-openapi-specification)
18. [Implementation Checklist](#18-implementation-checklist)

---

## 1. Executive Summary

This document defines the API architecture for The Code We Live By (CWLB) platform. The API enables all core features:

- **Code Browsing**: Navigate US Code hierarchy (Titles > Chapters > Sections)
- **Law Viewer**: View Public Laws with diffs, sponsors, and votes
- **Search**: Full-text search across sections and laws
- **Time Travel**: View historical versions of any section
- **Blame View**: Line-by-line attribution showing which law modified each provision
- **Analytics**: Legislative productivity metrics and visualizations

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Style | **RESTful** | Simpler, better caching, wider tooling support, fits read-heavy workload |
| Data Format | **JSON** | Universal support, human-readable, efficient for web clients |
| Versioning | **URL Path** (`/api/v1/`) | Clear, explicit, easy routing |
| Authentication | **API Keys** (optional) | Anonymous access for public data, keys for rate limit increase |
| Rate Limiting | **Tiered** | Anonymous: 100/min, Authenticated: 1000/min |

### Endpoint Summary

| API Area | Endpoints | Primary Use Case |
|----------|-----------|------------------|
| Code Browsing | 7 | Navigate US Code hierarchy |
| Law Viewer | 6 | View individual laws with metadata |
| Search | 4 | Find sections and laws |
| Time Travel | 3 | View historical versions |
| Blame View | 2 | Line-by-line attribution |
| Analytics | 5 | Legislative metrics and trends |
| **Total** | **27** | |

---

## 2. API Style Decision: REST vs GraphQL

### Evaluation Criteria

| Criterion | REST | GraphQL | CWLB Need |
|-----------|------|---------|-----------|
| **Learning Curve** | Low | Medium | Team may be small/diverse |
| **Caching** | Excellent (HTTP) | Complex | Heavy read workload benefits from HTTP caching |
| **Tooling** | Mature, abundant | Growing | Need reliable tooling for MVP |
| **Over-fetching** | Possible | Solves | Moderate concern; can use sparse fieldsets |
| **Under-fetching** | Possible (N+1) | Solves | Can batch with well-designed endpoints |
| **Real-time** | Polling/SSE | Subscriptions | Not critical for MVP |
| **Documentation** | OpenAPI/Swagger | Self-documenting | Both adequate |
| **Client Flexibility** | Fixed responses | Dynamic queries | Moderate need |

### Decision: RESTful API

**Primary Reasons:**

1. **Read-heavy workload**: CWLB is predominantly read operations (browsing code, viewing laws). REST's native HTTP caching provides significant performance benefits.

2. **Predictable access patterns**: Users follow hierarchical navigation (Title > Chapter > Section), which maps naturally to REST resources.

3. **Simpler implementation**: Faster time-to-MVP with less infrastructure complexity.

4. **CDN compatibility**: REST responses can be cached at CDN edge locations for global performance.

5. **Wider ecosystem**: More tools, libraries, and developer familiarity.

**Mitigations for REST Limitations:**

- **Over-fetching**: Support sparse fieldsets via `?fields=` parameter
- **Under-fetching**: Design composite endpoints that return related data (e.g., section with blame data)
- **Multiple round-trips**: Support `?include=` parameter for related resources

**Future Consideration:** GraphQL could be added in Phase 2 as an alternative interface for power users and researchers who need flexible queries.

---

## 3. API Design Principles

### 3.1 Resource-Oriented Design

Resources are nouns, not verbs:
- `/sections` not `/getSections`
- `/laws/{lawId}` not `/fetchLaw`

### 3.2 Hierarchical URL Structure

URLs reflect the US Code hierarchy:
```
/api/v1/titles
/api/v1/titles/{titleNumber}
/api/v1/titles/{titleNumber}/chapters
/api/v1/titles/{titleNumber}/chapters/{chapterNumber}
/api/v1/titles/{titleNumber}/chapters/{chapterNumber}/sections
/api/v1/titles/{titleNumber}/sections/{sectionNumber}
```

### 3.3 HTTP Methods

| Method | Usage | Idempotent |
|--------|-------|------------|
| `GET` | Read resources | Yes |
| `POST` | Search queries (complex filters) | No |
| `HEAD` | Check resource existence | Yes |
| `OPTIONS` | CORS preflight | Yes |

Note: CWLB is read-only for public users. `PUT`, `PATCH`, `DELETE` are only for admin/data pipeline operations.

### 3.4 Consistent Response Structure

All responses follow this envelope:

```json
{
  "data": { ... },           // Primary response data
  "meta": {                  // Metadata about the response
    "timestamp": "2026-01-27T12:00:00Z",
    "version": "1.0.0",
    "requestId": "req_abc123"
  },
  "pagination": { ... },     // Present for list responses
  "links": { ... }           // HATEOAS links for navigation
}
```

### 3.5 HATEOAS Links

Responses include navigational links:

```json
{
  "data": { ... },
  "links": {
    "self": "/api/v1/titles/17/sections/106",
    "title": "/api/v1/titles/17",
    "chapter": "/api/v1/titles/17/chapters/1",
    "blame": "/api/v1/titles/17/sections/106/blame",
    "history": "/api/v1/titles/17/sections/106/history"
  }
}
```

---

## 4. Authentication & Rate Limiting

### 4.1 Authentication Model

CWLB data is public domain; authentication is optional but enables:
- Higher rate limits
- Saved searches and bookmarks (Phase 2)
- Analytics access

**Authentication Method**: API Key in header

```http
GET /api/v1/titles HTTP/1.1
Host: api.cwlb.gov
Authorization: Bearer cwlb_key_abc123xyz
```

### 4.2 Rate Limiting

| Tier | Limit | Use Case |
|------|-------|----------|
| Anonymous | 100 requests/minute | Casual browsing |
| Authenticated | 1,000 requests/minute | Regular users |
| Research | 10,000 requests/minute | Academic/research use |
| Enterprise | Custom | Institutional partners |

**Rate Limit Headers:**

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1706356800
```

**Rate Limit Exceeded Response:**

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please wait 45 seconds or authenticate for higher limits.",
    "retryAfter": 45
  }
}
```

### 4.3 CORS Configuration

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, HEAD, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

---

## 5. API Endpoints Overview

### Base URL

```
Production: https://api.cwlb.gov/v1
Staging:    https://api.staging.cwlb.gov/v1
```

### Endpoint Map

```
/api/v1
├── /titles                                    # List all US Code titles
│   └── /{titleNumber}                         # Get specific title
│       ├── /chapters                          # List chapters in title
│       │   └── /{chapterNumber}               # Get specific chapter
│       │       └── /sections                  # List sections in chapter
│       └── /sections                          # List all sections in title
│           └── /{sectionNumber}               # Get specific section
│               ├── /lines                     # Get line-level structure
│               ├── /blame                     # Get blame view
│               ├── /history                   # Get version history
│               ├── /at/{date}                 # Get section at date
│               ├── /compare                   # Compare versions
│               └── /references                # Get cross-references
├── /laws                                      # List public laws
│   └── /{lawId}                               # Get specific law
│       ├── /changes                           # Get all changes by law
│       ├── /diff/{sectionId}                  # Get diff for section
│       ├── /sponsors                          # Get sponsors
│       └── /votes                             # Get vote records
├── /search
│   ├── /sections                              # Search sections
│   ├── /laws                                  # Search laws
│   └── /legislators                           # Search legislators
├── /legislators
│   └── /{legislatorId}                        # Get legislator details
│       ├── /sponsored                         # Laws sponsored
│       └── /votes                             # Voting record
├── /analytics
│   ├── /productivity                          # Congressional productivity
│   ├── /focus-areas                           # Legislative focus areas
│   ├── /law-scope                             # Law scope metrics
│   └── /contributors                          # Legislator activity
└── /bills (Phase 2)                           # Proposed legislation
    └── /{billId}                              # Get specific bill
```

---

## 6. Code Browsing API

### 6.1 List Titles

**Endpoint:** `GET /api/v1/titles`

**Description:** List all 54 US Code titles with metadata.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `positivelaw` | boolean | Filter by positive law status |
| `fields` | string | Comma-separated fields to include |

**Response:**

```json
{
  "data": [
    {
      "titleNumber": 17,
      "titleName": "Copyrights",
      "isPositiveLaw": true,
      "positiveLawDate": "1976-10-19",
      "positiveLawCitation": "PL 94-553",
      "chapterCount": 15,
      "sectionCount": 312,
      "lastModifiedDate": "2025-12-15"
    },
    {
      "titleNumber": 18,
      "titleName": "Crimes and Criminal Procedure",
      "isPositiveLaw": true,
      "positiveLawDate": "1948-06-25",
      "positiveLawCitation": "PL 80-772",
      "chapterCount": 123,
      "sectionCount": 2847,
      "lastModifiedDate": "2025-11-20"
    }
  ],
  "meta": {
    "totalCount": 54,
    "timestamp": "2026-01-27T12:00:00Z"
  },
  "links": {
    "self": "/api/v1/titles"
  }
}
```

### 6.2 Get Title

**Endpoint:** `GET /api/v1/titles/{titleNumber}`

**Response:**

```json
{
  "data": {
    "titleNumber": 17,
    "titleName": "Copyrights",
    "isPositiveLaw": true,
    "positiveLawDate": "1976-10-19",
    "positiveLawCitation": "PL 94-553",
    "statutesAtLargeCitation": "90 Stat. 2541",
    "description": "Laws relating to copyrights, including subject matter, ownership, duration, and infringement.",
    "chapterCount": 15,
    "sectionCount": 312,
    "lastModifiedDate": "2025-12-15",
    "chapters": [
      {
        "chapterNumber": "1",
        "chapterName": "Subject Matter and Scope of Copyright",
        "sectionCount": 22
      },
      {
        "chapterNumber": "2",
        "chapterName": "Copyright Ownership and Transfer",
        "sectionCount": 12
      }
    ]
  },
  "links": {
    "self": "/api/v1/titles/17",
    "chapters": "/api/v1/titles/17/chapters",
    "sections": "/api/v1/titles/17/sections"
  }
}
```

### 6.3 List Chapters

**Endpoint:** `GET /api/v1/titles/{titleNumber}/chapters`

**Response:**

```json
{
  "data": [
    {
      "chapterNumber": "1",
      "chapterName": "Subject Matter and Scope of Copyright",
      "sectionCount": 22,
      "sectionRange": "101-122"
    },
    {
      "chapterNumber": "2",
      "chapterName": "Copyright Ownership and Transfer",
      "sectionCount": 12,
      "sectionRange": "201-205"
    }
  ],
  "meta": {
    "titleNumber": 17,
    "titleName": "Copyrights",
    "totalChapters": 15
  },
  "links": {
    "self": "/api/v1/titles/17/chapters",
    "title": "/api/v1/titles/17"
  }
}
```

### 6.4 List Sections

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections`

**Alternative:** `GET /api/v1/titles/{titleNumber}/chapters/{chapterNumber}/sections`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `chapter` | string | Filter by chapter |
| `modifiedAfter` | date | Sections modified after date |
| `modifiedBefore` | date | Sections modified before date |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Results per page (default: 50, max: 200) |

**Response:**

```json
{
  "data": [
    {
      "sectionNumber": "106",
      "heading": "Exclusive rights in copyrighted works",
      "fullCitation": "17 U.S.C. § 106",
      "chapterNumber": "1",
      "lastModifiedDate": "1998-10-28",
      "lastModifiedBy": {
        "lawNumber": "105-304",
        "popularName": "Digital Millennium Copyright Act"
      },
      "isRepealed": false
    },
    {
      "sectionNumber": "107",
      "heading": "Limitations on exclusive rights: Fair use",
      "fullCitation": "17 U.S.C. § 107",
      "chapterNumber": "1",
      "lastModifiedDate": "1992-10-24",
      "lastModifiedBy": {
        "lawNumber": "102-492",
        "popularName": null
      },
      "isRepealed": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "totalCount": 312,
    "totalPages": 7,
    "hasMore": true
  },
  "links": {
    "self": "/api/v1/titles/17/sections?page=1",
    "next": "/api/v1/titles/17/sections?page=2",
    "title": "/api/v1/titles/17"
  }
}
```

### 6.5 Get Section

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `include` | string | Related resources: `lines`, `blame`, `history` |
| `fields` | string | Specific fields to return |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "titleNumber": 17,
    "chapterNumber": "1",
    "sectionNumber": "106",
    "heading": "Exclusive rights in copyrighted works",
    "fullCitation": "17 U.S.C. § 106",
    "textContent": "Subject to sections 107 through 122, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following:\n\n(1) to reproduce the copyrighted work in copies or phonorecords;\n\n(2) to prepare derivative works based upon the copyrighted work;\n\n(3) to distribute copies or phonorecords of the copyrighted work to the public by sale or other transfer of ownership, or by rental, lease, or lending;\n\n(4) in the case of literary, musical, dramatic, and choreographic works, pantomimes, and motion pictures and other audiovisual works, to perform the copyrighted work publicly;\n\n(5) in the case of literary, musical, dramatic, and choreographic works, pantomimes, and pictorial, graphic, or sculptural works, including the individual images of a motion picture or other audiovisual work, to display the copyrighted work publicly; and\n\n(6) in the case of sound recordings, to perform the copyrighted work publicly by means of a digital audio transmission.",
    "enactedDate": "1976-10-19",
    "effectiveDate": "1978-01-01",
    "lastModifiedDate": "1998-10-28",
    "isPositiveLaw": true,
    "positiveLawEnactment": {
      "lawNumber": "94-553",
      "popularName": "Copyright Act of 1976",
      "enactedDate": "1976-10-19"
    },
    "lastModifiedBy": {
      "lawId": 456,
      "lawNumber": "105-304",
      "popularName": "Digital Millennium Copyright Act",
      "congress": 105,
      "enactedDate": "1998-10-28",
      "president": "Bill Clinton"
    },
    "isRepealed": false,
    "lineCount": 12,
    "versionCount": 4,
    "notes": null
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106",
    "title": "/api/v1/titles/17",
    "chapter": "/api/v1/titles/17/chapters/1",
    "lines": "/api/v1/titles/17/sections/106/lines",
    "blame": "/api/v1/titles/17/sections/106/blame",
    "history": "/api/v1/titles/17/sections/106/history",
    "references": "/api/v1/titles/17/sections/106/references"
  }
}
```

### 6.6 Get Section Lines

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/lines`

**Description:** Returns line-level structure of a section with parent/child tree relationships.

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "lines": [
      {
        "lineId": 100,
        "lineNumber": 1,
        "parentLineId": null,
        "lineType": "Heading",
        "textContent": "§ 106. Exclusive rights in copyrighted works",
        "subsectionPath": null,
        "depthLevel": 0
      },
      {
        "lineId": 101,
        "lineNumber": 2,
        "parentLineId": 100,
        "lineType": "Prose",
        "textContent": "Subject to sections 107 through 122, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following:",
        "subsectionPath": null,
        "depthLevel": 1
      },
      {
        "lineId": 102,
        "lineNumber": 3,
        "parentLineId": 101,
        "lineType": "ListItem",
        "textContent": "to reproduce the copyrighted work in copies or phonorecords;",
        "subsectionPath": "(1)",
        "depthLevel": 2
      },
      {
        "lineId": 103,
        "lineNumber": 4,
        "parentLineId": 101,
        "lineType": "ListItem",
        "textContent": "to prepare derivative works based upon the copyrighted work;",
        "subsectionPath": "(2)",
        "depthLevel": 2
      }
    ]
  },
  "meta": {
    "totalLines": 12,
    "maxDepth": 2
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/lines",
    "section": "/api/v1/titles/17/sections/106",
    "blame": "/api/v1/titles/17/sections/106/blame"
  }
}
```

### 6.7 Get Section Cross-References

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/references`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `direction` | string | `outgoing` (references by this section) or `incoming` (references to this section) |
| `type` | string | Filter by reference type |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "outgoingReferences": [
      {
        "targetSection": {
          "fullCitation": "17 U.S.C. § 107",
          "heading": "Limitations on exclusive rights: Fair use"
        },
        "referenceType": "Subject_To",
        "referenceText": "Subject to sections 107 through 122",
        "sourceSubsectionPath": null
      },
      {
        "targetSection": {
          "fullCitation": "17 U.S.C. § 108",
          "heading": "Limitations on exclusive rights: Reproduction by libraries and archives"
        },
        "referenceType": "Subject_To",
        "referenceText": "Subject to sections 107 through 122",
        "sourceSubsectionPath": null
      }
    ],
    "incomingReferences": [
      {
        "sourceSection": {
          "fullCitation": "17 U.S.C. § 501",
          "heading": "Infringement of copyright"
        },
        "referenceType": "Cross_Reference",
        "referenceText": "exclusive rights provided by sections 106 through 122"
      }
    ]
  },
  "meta": {
    "outgoingCount": 16,
    "incomingCount": 23
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/references",
    "section": "/api/v1/titles/17/sections/106"
  }
}
```

---

## 7. Law Viewer API

### 7.1 List Laws

**Endpoint:** `GET /api/v1/laws`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `congress` | integer | Filter by Congress number |
| `congressRange` | string | Congress range (e.g., "110-117") |
| `president` | string | Filter by signing president |
| `enactedAfter` | date | Laws enacted after date |
| `enactedBefore` | date | Laws enacted before date |
| `titleAffected` | integer | Laws affecting specific US Code title |
| `sort` | string | `enacted_desc` (default), `enacted_asc`, `impact_desc` |
| `page` | integer | Page number |
| `limit` | integer | Results per page |

**Response:**

```json
{
  "data": [
    {
      "lawId": 456,
      "lawNumber": "105-304",
      "congress": 105,
      "lawType": "Public",
      "popularName": "Digital Millennium Copyright Act",
      "shortTitle": "DMCA",
      "enactedDate": "1998-10-28",
      "effectiveDate": "1998-10-28",
      "president": "Bill Clinton",
      "billNumber": "H.R. 2281",
      "sectionsAffected": 47,
      "sectionsAdded": 23,
      "sectionsModified": 24
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "totalCount": 5234,
    "totalPages": 262
  },
  "links": {
    "self": "/api/v1/laws?page=1",
    "next": "/api/v1/laws?page=2"
  }
}
```

### 7.2 Get Law

**Endpoint:** `GET /api/v1/laws/{lawId}`

**Alternative formats:**
- `GET /api/v1/laws/PL-105-304` (by public law number)
- `GET /api/v1/laws/105/304` (by congress/number)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `include` | string | Related resources: `changes`, `sponsors`, `votes` |

**Response:**

```json
{
  "data": {
    "lawId": 456,
    "lawNumber": "105-304",
    "congress": 105,
    "lawType": "Public",
    "popularName": "Digital Millennium Copyright Act",
    "officialTitle": "An Act to amend title 17, United States Code, to implement the World Intellectual Property Organization Copyright Treaty and Performances and Phonograms Treaty, and for other purposes.",
    "shortTitle": "DMCA",
    "summary": "Implements two 1996 treaties of the World Intellectual Property Organization (WIPO). Criminalizes production and dissemination of technology intended to circumvent copyright protection measures. Heightens penalties for copyright infringement on the Internet.",
    "purpose": "To implement the WIPO Copyright Treaty and WIPO Performances and Phonograms Treaty.",
    "billNumber": "H.R. 2281",
    "timeline": {
      "introducedDate": "1997-07-29",
      "housePassedDate": "1998-08-04",
      "senatePassedDate": "1998-09-17",
      "presentedToPresidentDate": "1998-10-12",
      "enactedDate": "1998-10-28",
      "effectiveDate": "1998-10-28"
    },
    "president": "Bill Clinton",
    "presidentialAction": "Signed",
    "impact": {
      "sectionsAffected": 47,
      "sectionsAdded": 23,
      "sectionsModified": 24,
      "sectionsRepealed": 0,
      "titlesAffected": [17]
    },
    "externalLinks": {
      "govinfoUrl": "https://www.govinfo.gov/app/details/PLAW-105publ304",
      "congressUrl": "https://www.congress.gov/bill/105th-congress/house-bill/2281",
      "statutesAtLargeCitation": "112 Stat. 2860"
    }
  },
  "links": {
    "self": "/api/v1/laws/456",
    "changes": "/api/v1/laws/456/changes",
    "sponsors": "/api/v1/laws/456/sponsors",
    "votes": "/api/v1/laws/456/votes",
    "bill": "/api/v1/bills/H.R.2281-105"
  }
}
```

### 7.3 Get Law Changes

**Endpoint:** `GET /api/v1/laws/{lawId}/changes`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | integer | Filter by affected title |
| `changeType` | string | Filter by type: `Add`, `Modify`, `Delete`, `Repeal` |

**Response:**

```json
{
  "data": {
    "lawId": 456,
    "lawNumber": "105-304",
    "popularName": "Digital Millennium Copyright Act",
    "changes": [
      {
        "changeId": 789,
        "section": {
          "sectionId": 12345,
          "fullCitation": "17 U.S.C. § 512",
          "heading": "Limitations on liability relating to material online"
        },
        "changeType": "Add",
        "changeDescription": "Added new section establishing safe harbor provisions for online service providers",
        "effectiveDate": "1998-10-28",
        "subsectionPath": null,
        "oldText": null,
        "newText": "(a) Transitory Digital Network Communications.—..."
      },
      {
        "changeId": 790,
        "section": {
          "sectionId": 12346,
          "fullCitation": "17 U.S.C. § 1201",
          "heading": "Circumvention of copyright protection systems"
        },
        "changeType": "Add",
        "changeDescription": "Added new chapter on anti-circumvention provisions",
        "effectiveDate": "1998-10-28"
      }
    ]
  },
  "meta": {
    "totalChanges": 47,
    "byType": {
      "Add": 23,
      "Modify": 24,
      "Delete": 0,
      "Repeal": 0
    }
  },
  "links": {
    "self": "/api/v1/laws/456/changes",
    "law": "/api/v1/laws/456"
  }
}
```

### 7.4 Get Section Diff for Law

**Endpoint:** `GET /api/v1/laws/{lawId}/diff/{sectionId}`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | `unified` (default) or `side-by-side` |
| `context` | integer | Lines of context around changes (default: 3) |

**Response:**

```json
{
  "data": {
    "lawId": 456,
    "lawNumber": "105-304",
    "section": {
      "sectionId": 12345,
      "fullCitation": "17 U.S.C. § 106",
      "heading": "Exclusive rights in copyrighted works"
    },
    "changeType": "Modify",
    "effectiveDate": "1998-10-28",
    "diff": {
      "format": "unified",
      "hunks": [
        {
          "oldStart": 1,
          "oldLines": 7,
          "newStart": 1,
          "newLines": 8,
          "lines": [
            { "type": "context", "content": "Subject to sections 107 through 118, the owner of" },
            { "type": "deletion", "content": "copyright under this title has the exclusive rights" },
            { "type": "addition", "content": "copyright under this title has the exclusive rights" },
            { "type": "context", "content": "to do and to authorize any of the following:" },
            { "type": "context", "content": "" },
            { "type": "context", "content": "(1) to reproduce the copyrighted work in copies or phonorecords;" },
            { "type": "addition", "content": "" },
            { "type": "addition", "content": "(6) in the case of sound recordings, to perform the copyrighted work publicly by means of a digital audio transmission." }
          ]
        }
      ]
    },
    "statistics": {
      "linesAdded": 2,
      "linesRemoved": 1,
      "linesModified": 1
    }
  },
  "links": {
    "self": "/api/v1/laws/456/diff/12345",
    "law": "/api/v1/laws/456",
    "section": "/api/v1/titles/17/sections/106",
    "sectionBefore": "/api/v1/titles/17/sections/106/at/1998-10-27",
    "sectionAfter": "/api/v1/titles/17/sections/106/at/1998-10-28"
  }
}
```

### 7.5 Get Law Sponsors

**Endpoint:** `GET /api/v1/laws/{lawId}/sponsors`

**Response:**

```json
{
  "data": {
    "lawId": 456,
    "lawNumber": "105-304",
    "sponsor": {
      "legislatorId": 123,
      "bioguideId": "C000880",
      "fullName": "Howard Coble",
      "party": "Republican",
      "state": "NC",
      "chamber": "House",
      "district": "6",
      "photoUrl": "https://bioguide.congress.gov/bioguide/photo/C/C000880.jpg",
      "sponsoredDate": "1997-07-29"
    },
    "cosponsors": [
      {
        "legislatorId": 124,
        "bioguideId": "B000574",
        "fullName": "Earl Blumenauer",
        "party": "Democrat",
        "state": "OR",
        "chamber": "House",
        "sponsoredDate": "1997-08-01"
      }
    ]
  },
  "meta": {
    "sponsorCount": 1,
    "cosponsorCount": 25,
    "bipartisan": true
  },
  "links": {
    "self": "/api/v1/laws/456/sponsors",
    "law": "/api/v1/laws/456",
    "sponsor": "/api/v1/legislators/123"
  }
}
```

### 7.6 Get Law Votes

**Endpoint:** `GET /api/v1/laws/{lawId}/votes`

**Response:**

```json
{
  "data": {
    "lawId": 456,
    "lawNumber": "105-304",
    "votes": [
      {
        "voteId": 1001,
        "chamber": "House",
        "voteDate": "1998-08-04",
        "voteNumber": 423,
        "voteQuestion": "On Passage",
        "voteResult": "Passed",
        "tally": {
          "yea": 388,
          "nay": 18,
          "present": 1,
          "notVoting": 28
        },
        "requiredMajority": "1/2",
        "margin": "Overwhelming",
        "congressUrl": "https://clerk.house.gov/Votes/1998423"
      },
      {
        "voteId": 1002,
        "chamber": "Senate",
        "voteDate": "1998-09-17",
        "voteNumber": 290,
        "voteQuestion": "On Passage",
        "voteResult": "Passed",
        "tally": {
          "yea": 99,
          "nay": 0,
          "present": 0,
          "notVoting": 1
        },
        "requiredMajority": "1/2",
        "margin": "Unanimous"
      }
    ],
    "presidentialAction": {
      "action": "Signed",
      "date": "1998-10-28",
      "president": "Bill Clinton"
    }
  },
  "links": {
    "self": "/api/v1/laws/456/votes",
    "law": "/api/v1/laws/456",
    "houseVoteDetails": "/api/v1/votes/1001/individuals",
    "senateVoteDetails": "/api/v1/votes/1002/individuals"
  }
}
```

---

## 8. Search API

### 8.1 Search Sections

**Endpoint:** `GET /api/v1/search/sections`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | **Required.** Search query |
| `title` | integer | Filter by US Code title |
| `titles` | string | Comma-separated list of titles |
| `modifiedAfter` | date | Sections modified after date |
| `modifiedBefore` | date | Sections modified before date |
| `positiveLaw` | boolean | Filter by positive law status |
| `sort` | string | `relevance` (default), `modified_desc`, `citation` |
| `highlight` | boolean | Include highlighted snippets (default: true) |
| `page` | integer | Page number |
| `limit` | integer | Results per page (max: 100) |

**Response:**

```json
{
  "data": {
    "query": "copyright fair use",
    "results": [
      {
        "sectionId": 12347,
        "fullCitation": "17 U.S.C. § 107",
        "heading": "Limitations on exclusive rights: Fair use",
        "titleNumber": 17,
        "titleName": "Copyrights",
        "chapterNumber": "1",
        "relevanceScore": 0.95,
        "lastModifiedDate": "1992-10-24",
        "isPositiveLaw": true,
        "snippet": "...the <mark>fair use</mark> of a <mark>copyrighted</mark> work, including such use by reproduction in copies...",
        "highlightedHeading": "Limitations on exclusive rights: <mark>Fair use</mark>"
      },
      {
        "sectionId": 12345,
        "fullCitation": "17 U.S.C. § 106",
        "heading": "Exclusive rights in copyrighted works",
        "titleNumber": 17,
        "relevanceScore": 0.82,
        "snippet": "...the owner of <mark>copyright</mark> under this title has the exclusive rights..."
      }
    ]
  },
  "meta": {
    "totalResults": 47,
    "searchTime": "23ms"
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "totalPages": 3
  },
  "links": {
    "self": "/api/v1/search/sections?q=copyright+fair+use&page=1",
    "next": "/api/v1/search/sections?q=copyright+fair+use&page=2"
  }
}
```

### 8.2 Search Laws

**Endpoint:** `GET /api/v1/search/laws`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | **Required.** Search query |
| `congress` | integer | Filter by Congress |
| `congressRange` | string | Congress range (e.g., "110-117") |
| `president` | string | Filter by signing president |
| `sponsor` | string | Filter by sponsor name |
| `enactedAfter` | date | Enacted after date |
| `enactedBefore` | date | Enacted before date |
| `titleAffected` | integer | Laws affecting specific title |
| `minSections` | integer | Minimum sections affected |
| `maxSections` | integer | Maximum sections affected |
| `sort` | string | `relevance` (default), `enacted_desc`, `impact_desc` |
| `page` | integer | Page number |
| `limit` | integer | Results per page |

**Response:**

```json
{
  "data": {
    "query": "copyright digital",
    "results": [
      {
        "lawId": 456,
        "lawNumber": "105-304",
        "congress": 105,
        "popularName": "Digital Millennium Copyright Act",
        "shortTitle": "DMCA",
        "enactedDate": "1998-10-28",
        "president": "Bill Clinton",
        "sectionsAffected": 47,
        "relevanceScore": 0.98,
        "snippet": "An Act to amend title 17, United States Code, to implement the World Intellectual Property Organization <mark>Copyright</mark> Treaty..."
      }
    ]
  },
  "meta": {
    "totalResults": 23,
    "searchTime": "15ms"
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "totalPages": 2
  }
}
```

### 8.3 Search Legislators

**Endpoint:** `GET /api/v1/search/legislators`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search by name |
| `party` | string | Filter by party |
| `state` | string | Filter by state (2-letter code) |
| `chamber` | string | `House` or `Senate` |
| `congress` | integer | Served during this Congress |
| `current` | boolean | Currently serving |

**Response:**

```json
{
  "data": {
    "query": "Coble",
    "results": [
      {
        "legislatorId": 123,
        "bioguideId": "C000880",
        "fullName": "Howard Coble",
        "party": "Republican",
        "state": "NC",
        "chamber": "House",
        "district": "6",
        "photoUrl": "https://bioguide.congress.gov/bioguide/photo/C/C000880.jpg",
        "servedFrom": "1985-01-03",
        "servedTo": "2015-01-03",
        "isCurrentMember": false,
        "lawsSponsored": 12,
        "lawsCosponsored": 456
      }
    ]
  },
  "meta": {
    "totalResults": 1
  }
}
```

### 8.4 Advanced Search (POST)

**Endpoint:** `POST /api/v1/search`

**Description:** Complex searches with multiple filters. Useful when query parameters become unwieldy.

**Request Body:**

```json
{
  "type": "sections",
  "query": "privacy data breach",
  "filters": {
    "titles": [18, 42, 50],
    "modifiedAfter": "2010-01-01",
    "modifiedBefore": "2025-12-31",
    "positiveLaw": null
  },
  "sort": {
    "field": "relevance",
    "order": "desc"
  },
  "pagination": {
    "page": 1,
    "limit": 50
  },
  "options": {
    "highlight": true,
    "includeHistory": false
  }
}
```

---

## 9. Time Travel API

### 9.1 Get Section History

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/history`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Results per page |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "currentVersion": 4,
    "versions": [
      {
        "versionNumber": 4,
        "effectiveDate": "1998-10-28",
        "supersededDate": null,
        "modifiedBy": {
          "lawId": 456,
          "lawNumber": "105-304",
          "popularName": "Digital Millennium Copyright Act",
          "congress": 105,
          "president": "Bill Clinton"
        },
        "changeSummary": "Added clause (6) for digital audio transmissions"
      },
      {
        "versionNumber": 3,
        "effectiveDate": "1995-11-01",
        "supersededDate": "1998-10-28",
        "modifiedBy": {
          "lawId": 400,
          "lawNumber": "104-39",
          "popularName": "Digital Performance Right in Sound Recordings Act",
          "congress": 104,
          "president": "Bill Clinton"
        },
        "changeSummary": "Modified performance rights provisions"
      },
      {
        "versionNumber": 2,
        "effectiveDate": "1990-12-01",
        "supersededDate": "1995-11-01",
        "modifiedBy": {
          "lawId": 350,
          "lawNumber": "101-650",
          "popularName": "Visual Artists Rights Act",
          "congress": 101,
          "president": "George H.W. Bush"
        },
        "changeSummary": "Added visual artists rights"
      },
      {
        "versionNumber": 1,
        "effectiveDate": "1978-01-01",
        "supersededDate": "1990-12-01",
        "modifiedBy": {
          "lawId": 100,
          "lawNumber": "94-553",
          "popularName": "Copyright Act of 1976",
          "congress": 94,
          "president": "Gerald Ford"
        },
        "changeSummary": "Original enactment as positive law"
      }
    ]
  },
  "meta": {
    "totalVersions": 4,
    "oldestVersion": "1978-01-01",
    "newestVersion": "1998-10-28"
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/history",
    "section": "/api/v1/titles/17/sections/106",
    "version1": "/api/v1/titles/17/sections/106/at/1978-01-01",
    "version2": "/api/v1/titles/17/sections/106/at/1990-12-01",
    "version3": "/api/v1/titles/17/sections/106/at/1995-11-01",
    "version4": "/api/v1/titles/17/sections/106/at/1998-10-28"
  }
}
```

### 9.2 Get Section at Date

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/at/{date}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `date` | string | ISO date (YYYY-MM-DD) |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `include` | string | `lines`, `blame` |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "heading": "Exclusive rights in copyrighted works",
    "asOfDate": "1990-01-01",
    "versionNumber": 1,
    "effectiveDate": "1978-01-01",
    "textContent": "Subject to sections 107 through 118, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following:\n\n(1) to reproduce the copyrighted work in copies or phonorecords;\n\n(2) to prepare derivative works based upon the copyrighted work;\n\n(3) to distribute copies or phonorecords of the copyrighted work to the public by sale or other transfer of ownership, or by rental, lease, or lending;\n\n(4) in the case of literary, musical, dramatic, and choreographic works, pantomimes, and motion pictures and other audiovisual works, to perform the copyrighted work publicly;\n\n(5) in the case of literary, musical, dramatic, and choreographic works, pantomimes, and pictorial, graphic, or sculptural works, including the individual images of a motion picture or other audiovisual work, to display the copyrighted work publicly.",
    "authoritativeVersion": {
      "lawId": 100,
      "lawNumber": "94-553",
      "popularName": "Copyright Act of 1976",
      "enactedDate": "1976-10-19"
    },
    "note": "This version was effective from 1978-01-01 until 1990-12-01"
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/at/1990-01-01",
    "current": "/api/v1/titles/17/sections/106",
    "previousVersion": "/api/v1/titles/17/sections/106/at/1978-01-01",
    "nextVersion": "/api/v1/titles/17/sections/106/at/1990-12-01",
    "history": "/api/v1/titles/17/sections/106/history"
  }
}
```

### 9.3 Compare Section Versions

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/compare`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | date | **Required.** Start date |
| `to` | date | **Required.** End date |
| `format` | string | `unified` (default) or `side-by-side` |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "comparison": {
      "from": {
        "date": "1990-01-01",
        "versionNumber": 1,
        "effectiveDate": "1978-01-01",
        "authoritativeLaw": "PL 94-553"
      },
      "to": {
        "date": "2000-01-01",
        "versionNumber": 4,
        "effectiveDate": "1998-10-28",
        "authoritativeLaw": "PL 105-304"
      }
    },
    "lawsInBetween": [
      {
        "lawNumber": "101-650",
        "popularName": "Visual Artists Rights Act",
        "effectiveDate": "1990-12-01"
      },
      {
        "lawNumber": "104-39",
        "popularName": "Digital Performance Right in Sound Recordings Act",
        "effectiveDate": "1995-11-01"
      },
      {
        "lawNumber": "105-304",
        "popularName": "Digital Millennium Copyright Act",
        "effectiveDate": "1998-10-28"
      }
    ],
    "diff": {
      "format": "unified",
      "statistics": {
        "linesAdded": 3,
        "linesRemoved": 1,
        "linesModified": 2
      },
      "hunks": [
        {
          "oldStart": 1,
          "newStart": 1,
          "lines": [
            { "type": "context", "content": "Subject to sections 107 through 118, the owner of" },
            { "type": "deletion", "content": "copyright under this title has the exclusive rights" },
            { "type": "addition", "content": "Subject to sections 107 through 122, the owner of" },
            { "type": "addition", "content": "copyright under this title has the exclusive rights" }
          ]
        }
      ]
    }
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/compare?from=1990-01-01&to=2000-01-01",
    "fromVersion": "/api/v1/titles/17/sections/106/at/1990-01-01",
    "toVersion": "/api/v1/titles/17/sections/106/at/2000-01-01"
  }
}
```

---

## 10. Blame View API

### 10.1 Get Blame View

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/blame`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `asOf` | date | Historical blame view as of date |
| `depth` | integer | Maximum tree depth to return (default: all) |
| `includeHistory` | boolean | Include historical attribution chain |

**Response:**

```json
{
  "data": {
    "sectionId": 12345,
    "fullCitation": "17 U.S.C. § 106",
    "heading": "Exclusive rights in copyrighted works",
    "isPositiveLaw": true,
    "positiveLawEnactment": {
      "lawNumber": "94-553",
      "popularName": "Copyright Act of 1976",
      "enactedDate": "1976-10-19"
    },
    "blameLines": [
      {
        "lineId": 100,
        "lineNumber": 1,
        "lineType": "Heading",
        "textContent": "§ 106. Exclusive rights in copyrighted works",
        "subsectionPath": null,
        "depthLevel": 0,
        "attribution": {
          "createdBy": {
            "lawId": 100,
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976",
            "congress": 94,
            "president": "Gerald Ford",
            "enactedDate": "1976-10-19",
            "effectiveDate": "1978-01-01"
          },
          "lastModifiedBy": {
            "lawId": 100,
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976",
            "congress": 94,
            "president": "Gerald Ford",
            "enactedDate": "1976-10-19",
            "effectiveDate": "1978-01-01"
          },
          "codifiedBy": {
            "lawId": 100,
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976",
            "enactedDate": "1976-10-19"
          }
        }
      },
      {
        "lineId": 101,
        "lineNumber": 2,
        "lineType": "Prose",
        "textContent": "Subject to sections 107 through 122, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following:",
        "subsectionPath": null,
        "depthLevel": 1,
        "attribution": {
          "createdBy": {
            "lawId": 100,
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976",
            "congress": 94,
            "president": "Gerald Ford"
          },
          "lastModifiedBy": {
            "lawId": 456,
            "lawNumber": "105-304",
            "popularName": "Digital Millennium Copyright Act",
            "congress": 105,
            "president": "Bill Clinton",
            "enactedDate": "1998-10-28"
          },
          "note": "Modified: 'sections 107 through 118' changed to 'sections 107 through 122'"
        }
      },
      {
        "lineId": 102,
        "lineNumber": 3,
        "lineType": "ListItem",
        "textContent": "to reproduce the copyrighted work in copies or phonorecords;",
        "subsectionPath": "(1)",
        "depthLevel": 2,
        "attribution": {
          "createdBy": {
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976"
          },
          "lastModifiedBy": {
            "lawNumber": "94-553",
            "popularName": "Copyright Act of 1976"
          }
        }
      },
      {
        "lineId": 107,
        "lineNumber": 8,
        "lineType": "ListItem",
        "textContent": "in the case of sound recordings, to perform the copyrighted work publicly by means of a digital audio transmission.",
        "subsectionPath": "(6)",
        "depthLevel": 2,
        "attribution": {
          "createdBy": {
            "lawId": 456,
            "lawNumber": "105-304",
            "popularName": "Digital Millennium Copyright Act",
            "congress": 105,
            "president": "Bill Clinton",
            "enactedDate": "1998-10-28"
          },
          "lastModifiedBy": {
            "lawId": 456,
            "lawNumber": "105-304"
          },
          "note": "Added by DMCA"
        }
      }
    ]
  },
  "meta": {
    "totalLines": 12,
    "uniqueModifyingLaws": 4,
    "oldestAttribution": "1978-01-01",
    "newestAttribution": "1998-10-28"
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/blame",
    "section": "/api/v1/titles/17/sections/106",
    "lines": "/api/v1/titles/17/sections/106/lines",
    "history": "/api/v1/titles/17/sections/106/history"
  }
}
```

### 10.2 Get Blame for Specific Line

**Endpoint:** `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/blame/{lineId}`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `includeHistory` | boolean | Include full modification history |

**Response:**

```json
{
  "data": {
    "line": {
      "lineId": 107,
      "lineNumber": 8,
      "lineType": "ListItem",
      "textContent": "in the case of sound recordings, to perform the copyrighted work publicly by means of a digital audio transmission.",
      "subsectionPath": "(6)",
      "depthLevel": 2
    },
    "section": {
      "sectionId": 12345,
      "fullCitation": "17 U.S.C. § 106"
    },
    "attribution": {
      "createdBy": {
        "lawId": 456,
        "lawNumber": "105-304",
        "popularName": "Digital Millennium Copyright Act",
        "congress": 105,
        "president": "Bill Clinton",
        "enactedDate": "1998-10-28",
        "effectiveDate": "1998-10-28"
      },
      "lastModifiedBy": {
        "lawId": 456,
        "lawNumber": "105-304",
        "popularName": "Digital Millennium Copyright Act"
      }
    },
    "context": {
      "parentLine": {
        "lineId": 101,
        "textContent": "Subject to sections 107 through 122, the owner of copyright..."
      },
      "siblingLines": [
        { "lineId": 102, "subsectionPath": "(1)", "preview": "to reproduce the copyrighted work..." },
        { "lineId": 103, "subsectionPath": "(2)", "preview": "to prepare derivative works..." },
        { "lineId": 104, "subsectionPath": "(3)", "preview": "to distribute copies..." },
        { "lineId": 105, "subsectionPath": "(4)", "preview": "to perform the copyrighted work..." },
        { "lineId": 106, "subsectionPath": "(5)", "preview": "to display the copyrighted work..." }
      ]
    },
    "history": [
      {
        "versionNumber": 1,
        "textContent": "in the case of sound recordings, to perform the copyrighted work publicly by means of a digital audio transmission.",
        "effectiveDate": "1998-10-28",
        "modifiedBy": {
          "lawNumber": "105-304",
          "popularName": "Digital Millennium Copyright Act"
        }
      }
    ]
  },
  "links": {
    "self": "/api/v1/titles/17/sections/106/blame/107",
    "blame": "/api/v1/titles/17/sections/106/blame",
    "law": "/api/v1/laws/456",
    "permalink": "https://cwlb.gov/17/106#line-8"
  }
}
```

---

## 11. Analytics API

### 11.1 Congressional Productivity

**Endpoint:** `GET /api/v1/analytics/productivity`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `congress` | integer | Specific Congress |
| `congressRange` | string | Range (e.g., "110-117") |
| `metric` | string | `laws`, `sections`, `lines` (default: `laws`) |
| `groupBy` | string | `congress`, `year`, `month` |

**Response:**

```json
{
  "data": {
    "metric": "laws",
    "groupBy": "congress",
    "dataPoints": [
      {
        "congress": 117,
        "dateRange": { "start": "2021-01-03", "end": "2023-01-03" },
        "lawsEnacted": 362,
        "sectionsAffected": 4521,
        "linesChanged": 125000,
        "avgDaysToPassage": 287,
        "bipartisanPercentage": 68.5
      },
      {
        "congress": 116,
        "dateRange": { "start": "2019-01-03", "end": "2021-01-03" },
        "lawsEnacted": 344,
        "sectionsAffected": 3892,
        "linesChanged": 98000,
        "avgDaysToPassage": 312,
        "bipartisanPercentage": 72.1
      }
    ]
  },
  "meta": {
    "calculatedAt": "2026-01-27T12:00:00Z",
    "congressesIncluded": 8
  },
  "links": {
    "self": "/api/v1/analytics/productivity?congressRange=110-117",
    "export": "/api/v1/analytics/productivity?congressRange=110-117&format=csv"
  }
}
```

### 11.2 Legislative Focus Areas

**Endpoint:** `GET /api/v1/analytics/focus-areas`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `congress` | integer | Specific Congress |
| `congressRange` | string | Range of Congresses |
| `metric` | string | `laws`, `sections`, `lines` |
| `topN` | integer | Top N titles (default: 10) |

**Response:**

```json
{
  "data": {
    "congress": 117,
    "metric": "laws",
    "focusAreas": [
      {
        "titleNumber": 42,
        "titleName": "Public Health and Social Welfare",
        "lawCount": 89,
        "sectionsAffected": 1234,
        "percentage": 24.6
      },
      {
        "titleNumber": 26,
        "titleName": "Internal Revenue Code",
        "lawCount": 67,
        "sectionsAffected": 892,
        "percentage": 18.5
      },
      {
        "titleNumber": 10,
        "titleName": "Armed Forces",
        "lawCount": 54,
        "sectionsAffected": 678,
        "percentage": 14.9
      }
    ]
  },
  "meta": {
    "totalLaws": 362,
    "titlesWithActivity": 32
  }
}
```

### 11.3 Law Scope Metrics

**Endpoint:** `GET /api/v1/analytics/law-scope`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `congress` | integer | Specific Congress |
| `congressRange` | string | Range of Congresses |
| `scopeType` | string | `narrow` (1-5 sections), `moderate` (6-50), `broad` (51+), `all` |

**Response:**

```json
{
  "data": {
    "congressRange": "115-117",
    "distribution": {
      "narrow": {
        "count": 567,
        "percentage": 52.3,
        "avgSections": 2.3,
        "examples": [
          { "lawNumber": "117-100", "sectionsAffected": 1 },
          { "lawNumber": "117-89", "sectionsAffected": 3 }
        ]
      },
      "moderate": {
        "count": 412,
        "percentage": 38.0,
        "avgSections": 18.7
      },
      "broad": {
        "count": 105,
        "percentage": 9.7,
        "avgSections": 156.2,
        "examples": [
          {
            "lawNumber": "117-58",
            "popularName": "Infrastructure Investment and Jobs Act",
            "sectionsAffected": 847
          }
        ]
      }
    },
    "statistics": {
      "mean": 28.4,
      "median": 8,
      "mode": 1,
      "max": 1247,
      "standardDeviation": 67.2
    }
  }
}
```

### 11.4 Contributor Statistics

**Endpoint:** `GET /api/v1/analytics/contributors`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `congress` | integer | Specific Congress |
| `chamber` | string | `House`, `Senate`, or both |
| `party` | string | Filter by party |
| `metric` | string | `sponsored`, `cosponsored`, `impact` |
| `topN` | integer | Top N legislators (default: 20) |

**Response:**

```json
{
  "data": {
    "congress": 117,
    "metric": "sponsored",
    "contributors": [
      {
        "legislatorId": 500,
        "fullName": "Chuck Schumer",
        "party": "Democrat",
        "state": "NY",
        "chamber": "Senate",
        "lawsSponsored": 12,
        "lawsCosponsored": 156,
        "sectionsImpacted": 2345,
        "bipartisanIndex": 0.72,
        "specialization": [
          { "titleNumber": 42, "percentage": 35 },
          { "titleNumber": 26, "percentage": 22 }
        ]
      }
    ]
  },
  "meta": {
    "totalLegislators": 535,
    "legislatorsWithSponsorship": 412
  }
}
```

### 11.5 Export Analytics Data

**Endpoint:** `GET /api/v1/analytics/export`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | `productivity`, `focus-areas`, `law-scope`, `contributors` |
| `format` | string | `csv`, `json` |
| `congress` | integer | Filter parameters (same as individual endpoints) |

**Response:** File download with appropriate Content-Type header.

---

## 12. Bills API (Future)

*Included for completeness. Implementation scheduled for Phase 2/3.*

### 12.1 List Bills

**Endpoint:** `GET /api/v1/bills`

### 12.2 Get Bill

**Endpoint:** `GET /api/v1/bills/{billId}`

### 12.3 Get Proposed Changes

**Endpoint:** `GET /api/v1/bills/{billId}/proposed-changes`

---

## 13. Error Handling

### 13.1 Error Response Format

All errors follow a consistent structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific field with error",
      "reason": "detailed reason"
    },
    "requestId": "req_abc123",
    "timestamp": "2026-01-27T12:00:00Z",
    "documentation": "https://docs.cwlb.gov/errors/ERROR_CODE"
  }
}
```

### 13.2 HTTP Status Codes

| Status | Usage |
|--------|-------|
| `200` | Success |
| `201` | Created (for future write operations) |
| `400` | Bad Request - invalid parameters |
| `401` | Unauthorized - invalid API key |
| `403` | Forbidden - insufficient permissions |
| `404` | Not Found - resource doesn't exist |
| `422` | Unprocessable Entity - valid JSON but invalid data |
| `429` | Too Many Requests - rate limit exceeded |
| `500` | Internal Server Error |
| `502` | Bad Gateway |
| `503` | Service Unavailable |

### 13.3 Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_PARAMETER` | 400 | Query parameter is malformed |
| `MISSING_PARAMETER` | 400 | Required parameter missing |
| `INVALID_DATE_FORMAT` | 400 | Date must be YYYY-MM-DD |
| `INVALID_DATE_RANGE` | 400 | End date before start date |
| `RESOURCE_NOT_FOUND` | 404 | Section, law, or legislator not found |
| `TITLE_NOT_FOUND` | 404 | US Code title doesn't exist |
| `SECTION_NOT_FOUND` | 404 | Section doesn't exist in title |
| `HISTORICAL_NOT_AVAILABLE` | 404 | No data for requested date |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

### 13.4 Error Examples

**Invalid Parameter:**

```json
{
  "error": {
    "code": "INVALID_DATE_FORMAT",
    "message": "The 'asOf' parameter must be in YYYY-MM-DD format",
    "details": {
      "parameter": "asOf",
      "provided": "01-27-2026",
      "expected": "2026-01-27"
    },
    "requestId": "req_xyz789"
  }
}
```

**Resource Not Found:**

```json
{
  "error": {
    "code": "SECTION_NOT_FOUND",
    "message": "Section 999 does not exist in Title 17",
    "details": {
      "titleNumber": 17,
      "sectionNumber": "999",
      "suggestion": "Did you mean section 909?"
    }
  }
}
```

---

## 14. Pagination

### 14.1 Pagination Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | integer | 1 | - | Page number (1-indexed) |
| `limit` | integer | 20 | 200 | Results per page |
| `cursor` | string | - | - | Cursor for keyset pagination |

### 14.2 Offset Pagination Response

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "totalCount": 312,
    "totalPages": 16,
    "hasMore": true
  },
  "links": {
    "self": "/api/v1/titles/17/sections?page=2&limit=20",
    "first": "/api/v1/titles/17/sections?page=1&limit=20",
    "prev": "/api/v1/titles/17/sections?page=1&limit=20",
    "next": "/api/v1/titles/17/sections?page=3&limit=20",
    "last": "/api/v1/titles/17/sections?page=16&limit=20"
  }
}
```

### 14.3 Cursor Pagination (for large datasets)

For endpoints with potentially millions of records (e.g., all line history), cursor-based pagination provides consistent performance:

```json
{
  "data": [...],
  "pagination": {
    "limit": 100,
    "hasMore": true,
    "nextCursor": "eyJsYXN0SWQiOjEyMzQ1fQ=="
  },
  "links": {
    "self": "/api/v1/...",
    "next": "/api/v1/...?cursor=eyJsYXN0SWQiOjEyMzQ1fQ=="
  }
}
```

---

## 15. Versioning Strategy

### 15.1 URL Path Versioning

```
/api/v1/titles
/api/v2/titles  (future)
```

**Rationale:**
- Clear and explicit
- Easy to route at load balancer level
- No header inspection needed
- Cache-friendly

### 15.2 Version Lifecycle

| Version | Status | Support |
|---------|--------|---------|
| v1 | Current | Full support |
| v0 (beta) | Deprecated | Read-only, removed 6 months after v1 GA |

### 15.3 Deprecation Policy

1. Announce deprecation 6 months in advance
2. Add `Deprecation` and `Sunset` headers to deprecated endpoints
3. Continue serving deprecated endpoints read-only
4. Remove after sunset date

```http
Deprecation: true
Sunset: Sat, 01 Jan 2028 00:00:00 GMT
Link: </api/v2/titles>; rel="successor-version"
```

---

## 16. Performance Considerations

### 16.1 Caching Strategy

| Resource | Cache TTL | Cache-Control |
|----------|-----------|---------------|
| Title list | 24 hours | `public, max-age=86400` |
| Section (current) | 1 hour | `public, max-age=3600` |
| Section (historical) | 7 days | `public, max-age=604800, immutable` |
| Law metadata | 24 hours | `public, max-age=86400` |
| Search results | 5 minutes | `public, max-age=300` |
| Blame view | 1 hour | `public, max-age=3600` |
| Analytics | 1 hour | `public, max-age=3600` |

### 16.2 ETag Support

All GET responses include ETag headers:

```http
ETag: "abc123def456"
```

Conditional requests supported:

```http
GET /api/v1/titles/17/sections/106
If-None-Match: "abc123def456"
```

Response: `304 Not Modified` if unchanged.

### 16.3 Compression

All responses are gzip compressed when `Accept-Encoding: gzip` is present.

### 16.4 Rate Limiting Headers

Every response includes:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1706356800
```

### 16.5 Response Size Optimization

- Use `fields` parameter for sparse fieldsets
- Use `include` parameter judiciously
- Pagination enforced with maximum limits

---

## 17. OpenAPI Specification

A complete OpenAPI 3.0 specification will be generated and hosted at:

```
https://api.cwlb.gov/v1/openapi.json
https://api.cwlb.gov/v1/openapi.yaml
```

Interactive documentation (Swagger UI) at:

```
https://docs.cwlb.gov/api
```

### 17.1 Sample OpenAPI Excerpt

```yaml
openapi: 3.0.3
info:
  title: CWLB API
  description: The Code We Live By - US Code as a Repository
  version: 1.0.0
  contact:
    name: CWLB API Support
    url: https://cwlb.gov/support
    email: api@cwlb.gov
  license:
    name: Public Domain
    url: https://creativecommons.org/publicdomain/zero/1.0/

servers:
  - url: https://api.cwlb.gov/v1
    description: Production
  - url: https://api.staging.cwlb.gov/v1
    description: Staging

paths:
  /titles:
    get:
      summary: List all US Code titles
      operationId: listTitles
      tags:
        - Code Browsing
      parameters:
        - name: positivelaw
          in: query
          schema:
            type: boolean
          description: Filter by positive law status
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TitleListResponse'

components:
  schemas:
    TitleListResponse:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/Title'
        meta:
          $ref: '#/components/schemas/Meta'
        links:
          $ref: '#/components/schemas/Links'

    Title:
      type: object
      properties:
        titleNumber:
          type: integer
          example: 17
        titleName:
          type: string
          example: "Copyrights"
        isPositiveLaw:
          type: boolean
          example: true
        positiveLawDate:
          type: string
          format: date
          example: "1976-10-19"
        chapterCount:
          type: integer
          example: 15
        sectionCount:
          type: integer
          example: 312
```

---

## 18. Implementation Checklist

### Phase 1 (MVP) API Implementation

#### Code Browsing API (Task 1.20)
- [ ] `GET /api/v1/titles` - List all titles
- [ ] `GET /api/v1/titles/{titleNumber}` - Get title details
- [ ] `GET /api/v1/titles/{titleNumber}/chapters` - List chapters
- [ ] `GET /api/v1/titles/{titleNumber}/sections` - List sections
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}` - Get section
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/lines` - Get lines

#### Law Viewer API (Task 1.21)
- [ ] `GET /api/v1/laws` - List laws
- [ ] `GET /api/v1/laws/{lawId}` - Get law details
- [ ] `GET /api/v1/laws/{lawId}/changes` - Get law changes
- [ ] `GET /api/v1/laws/{lawId}/diff/{sectionId}` - Get diff
- [ ] `GET /api/v1/laws/{lawId}/sponsors` - Get sponsors
- [ ] `GET /api/v1/laws/{lawId}/votes` - Get votes

#### Search API (Task 1.22)
- [ ] `GET /api/v1/search/sections` - Search sections
- [ ] `GET /api/v1/search/laws` - Search laws
- [ ] `GET /api/v1/search/legislators` - Search legislators
- [ ] `POST /api/v1/search` - Advanced search

#### Time Travel API (Task 1.23)
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/history` - Version history
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/at/{date}` - Section at date
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/compare` - Compare versions

#### Blame View API (Task 1.24)
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/blame` - Full blame view
- [ ] `GET /api/v1/titles/{titleNumber}/sections/{sectionNumber}/blame/{lineId}` - Line blame

### Infrastructure Setup
- [ ] Set up API gateway (AWS API Gateway / Kong / Nginx)
- [ ] Configure rate limiting
- [ ] Set up caching layer (Redis / CDN)
- [ ] Configure CORS
- [ ] Set up monitoring and logging
- [ ] Generate OpenAPI documentation
- [ ] Deploy Swagger UI

### Phase 2 API Additions
- [ ] Analytics API endpoints
- [ ] Bills API endpoints
- [ ] Legislators API enhancements
- [ ] GraphQL interface (optional)

---

## Summary

This API architecture design provides:

1. **Comprehensive coverage**: 27 endpoints covering all core CWLB features
2. **RESTful design**: Resource-oriented, cacheable, widely understood
3. **Consistent patterns**: Uniform response structures, pagination, and error handling
4. **Performance-optimized**: Caching strategy, sparse fieldsets, cursor pagination for large datasets
5. **Developer-friendly**: HATEOAS links, comprehensive error messages, OpenAPI documentation
6. **Scalable**: Rate limiting tiers, versioning strategy, deprecation policy

The API is ready for implementation in Phase 1 Tasks 1.20-1.24.
