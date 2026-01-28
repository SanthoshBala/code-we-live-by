# Task 0.2: GovInfo.gov API Evaluation for Public Laws

**Task**: Evaluate GovInfo.gov API for Public Laws
**Status**: Complete
**Date**: 2026-01-23

---

## Executive Summary

The GovInfo.gov API, provided by the U.S. Government Publishing Office (GPO), offers comprehensive programmatic access to Public Law documents and related legislative materials. The API provides excellent coverage from the 104th Congress (1995) to present, with structured XML/USLM formats available from the 113th Congress (2013) forward. The API requires a free API key and has reasonable rate limits for our use case.

### Key Findings

| Criterion | Assessment | Rating |
|-----------|------------|--------|
| API Availability | RESTful API with OpenAPI documentation | Excellent |
| Public Law Coverage | 104th Congress (1995) to present | Excellent |
| Structured XML Coverage | 113th Congress (2013) to present (USLM) | Good |
| Historical Depth | Statutes at Large from 1789 (digitized) | Excellent |
| Authentication | Free API key via api.data.gov | Excellent |
| Rate Limits | 1,000 requests/hour (default) | Good |
| Metadata Richness | MODS metadata with bill linkage | Excellent |
| Bulk Data Access | Available via separate bulk repository | Excellent |

**Recommendation**: The GovInfo API is the preferred source for Public Law documents. Use as the primary data source for law metadata, full text, and related document linkage. Combine with OLRC data (Task 0.1) for complete US Code + Public Law coverage.

---

## 1. API Overview

### Primary Source
- **Organization**: U.S. Government Publishing Office (GPO)
- **API Base URL**: https://api.govinfo.gov
- **Documentation**: https://api.govinfo.gov/docs (Interactive OpenAPI/Swagger)
- **GitHub Repository**: https://github.com/usgpo/api

### Key Collections for CWLB

| Collection Code | Name | Description |
|-----------------|------|-------------|
| **PLAW** | Public and Private Laws | Individual Public Laws (primary interest) |
| **STATUTE** | Statutes at Large | Session laws compiled by volume |
| **BILLS** | Congressional Bills | Bill text at various stages |
| **BILLSTATUS** | Bill Status | Legislative activity and status |
| **CREC** | Congressional Record | Floor debates and proceedings |
| **CPD** | Presidential Documents | Signing statements, remarks |

---

## 2. Authentication & Access

### 2.1 API Key Requirements

**An API key is required for all requests.**

- **Registration**: https://www.govinfo.gov/api-signup (or https://api.data.gov/signup/)
- **Key Format**: 40-character alphanumeric string
- **Cost**: Free
- **Usage**: Append `?api_key=YOUR_KEY` to requests

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
| Hourly Limit | 1,000 requests | Rolling window |
| DEMO_KEY Limit | Much lower | For exploration only |

### 3.2 Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
```

### 3.3 Exceeding Limits

- **HTTP Status**: 429 (Too Many Requests)
- **Behavior**: Temporary block on API key
- **Recovery**: Automatic reset on rolling hourly basis

### 3.4 Higher Limits

Contact GPO directly to request higher rate limits for production applications.

### 3.5 Assessment for CWLB

**Rating: Good**

1,000 requests/hour is adequate for:
- Initial data ingestion (pace over several days)
- Incremental updates (few laws per day)
- On-demand lookups (user requests)

For bulk historical ingestion, use the Bulk Data Repository instead (see Section 7).

---

## 4. API Endpoints

### 4.1 Discovery Services

#### Collections Endpoint
```
GET /collections
GET /collections/{collectionCode}
GET /collections/{collectionCode}/{startDate}
GET /collections/{collectionCode}/{startDate}/{endDate}
```

Lists packages modified within date range. Supports pagination via `offsetMark` parameter.

**Example**:
```
GET https://api.govinfo.gov/collections/PLAW/2025-01-01T00:00:00Z?api_key=YOUR_KEY
```

#### Published Endpoint
```
GET /published/{startDate}
GET /published/{startDate}/{endDate}
```

Retrieves packages by official publication date (dateIssued) rather than modification date.

#### Search Endpoint
```
POST /search
```

Elasticsearch-style queries against GovInfo content and metadata.

**Example Search Body**:
```json
{
  "query": "copyright",
  "pageSize": 10,
  "offsetMark": "*",
  "sorts": [
    { "field": "publishdate", "sortOrder": "DESC" }
  ]
}
```

#### Related Documents Endpoint
```
GET /related/{accessId}
```

Finds related content (bill versions, reports, laws, signing statements) for a given document.

### 4.2 Retrieval Services

#### Package Summary
```
GET /packages/{packageId}/summary
```

Returns metadata including title, dates, and download links.

**Example PLAW Package ID**: `PLAW-117publ167`

#### Package Content
```
GET /packages/{packageId}/{format}
```

Available formats: `htm`, `xml`, `pdf`, `mods`, `premis`, `zip`

#### Granules
```
GET /packages/{packageId}/granules
GET /packages/{packageId}/granules/{granuleId}/summary
```

For packages with sub-documents (not typically used for PLAW).

---

## 5. Public Law (PLAW) Collection Details

### 5.1 Coverage

| Congress | Years | Coverage |
|----------|-------|----------|
| 104th - Present | 1995-2026 | Full text PDF, HTML, XML |
| 113th - Present | 2013-2026 | USLM XML (structured) |

**Total Coverage**: ~30 years of Public Laws in machine-readable format.

### 5.2 Package ID Format

```
PLAW-{congress}publ{number}
PLAW-{congress}pvtl{number}  (private laws)
```

**Examples**:
- `PLAW-117publ167` - Public Law 117-167 (117th Congress)
- `PLAW-94publ553` - Public Law 94-553 (Copyright Act of 1976)

### 5.3 Available Formats

| Format | Extension | Content | CWLB Suitability |
|--------|-----------|---------|------------------|
| PDF | .pdf | Official published version | Display/download |
| HTML | .htm | Rendered text | Display fallback |
| **XML (USLM)** | .xml | Structured markup | **Primary choice** |
| MODS | mods.xml | Descriptive metadata | **Metadata source** |
| PREMIS | premis.xml | Preservation metadata | Not needed |
| ZIP | .zip | All formats bundled | Bulk download |

### 5.4 Metadata Available (MODS)

MODS (Metadata Object Description Schema) files contain rich metadata:

| Field | Description | CWLB Mapping |
|-------|-------------|--------------|
| `titleInfo` | Official title and short title | PublicLaw.name, popular_name |
| `name` | Associated bill number | Link to BILLS collection |
| `originInfo/dateIssued` | Enactment date | PublicLaw.date_enacted |
| `identifier` | PL number (e.g., "113-5") | PublicLaw.number |
| `extension/congress` | Congress number | PublicLaw.congress |
| `relatedItem` | Related bills and documents | Cross-references |
| `subject` | Topic classifications | Search/filtering |

### 5.5 Accessing Related Documents

The Related Documents service links Public Laws to:
- **Source Bill**: Original bill text (BILLS collection)
- **Bill Status**: Legislative history (BILLSTATUS)
- **Signing Statement**: Presidential remarks (CPD collection)
- **Congressional Reports**: Committee reports (CRPT collection)
- **Statutes at Large**: Session law volume (STATUTE)
- **US Code Sections**: Affected code sections (USCODE)

This enables building the "legislative journey" timeline for each law.

---

## 6. Statutes at Large (STATUTE) Collection

### 6.1 Coverage

| Volume Range | Years | Format |
|--------------|-------|--------|
| Volumes 1-64 | 1789-1950 | Digitized images |
| Volumes 65-116 | 1951-2002 | Digital images (Library of Congress) |
| Volumes 117+ | 2003-present | XML (USLM), PDF |

**USLM XML** is available for volumes 117+ (108th Congress, 2003 forward).

### 6.2 Use Case for CWLB

The Statutes at Large collection is useful for:
- Historical law text before PLAW collection (pre-1995)
- Session law citations and cross-references
- Complete legislative history research

### 6.3 Limitations

- Pre-2003 volumes are image-based (require OCR for text extraction)
- Less structured than PLAW packages
- Better suited for historical research than primary ingestion

---

## 7. Bulk Data Repository

### 7.1 Overview

For large-scale data ingestion, GPO provides a separate Bulk Data Repository:

- **URL**: https://www.govinfo.gov/bulkdata
- **Access**: Direct HTTP download (no API key required)
- **Format**: XML files organized by collection

### 7.2 Available Collections

| Collection | Path | Format |
|------------|------|--------|
| Public Laws | `/bulkdata/PLAW/` | USLM XML |
| Bills | `/bulkdata/BILLS/` | XML |
| Bill Status | `/bulkdata/BILLSTATUS/` | XML |
| Congressional Record | `/bulkdata/CREC/` | XML |

### 7.3 Bulk Data Benefits

- **No rate limits**: Download at network speed
- **Complete datasets**: All historical data available
- **Machine-friendly**: JSON/XML directory listings
- **Documentation**: User guides in repository

### 7.4 Recommendation for CWLB

Use **Bulk Data Repository** for:
- Initial historical data ingestion
- Batch processing of all Public Laws

Use **API** for:
- Incremental updates (new laws)
- Related document lookups
- Search functionality
- On-demand metadata retrieval

---

## 8. Data Format Assessment

### 8.1 USLM XML Structure

Public Laws in USLM format follow the same schema as US Code (evaluated in Task 0.1):

```xml
<lawDoc xmlns="http://xml.house.gov/schemas/uslm/1.0"
        xmlns:dcterms="http://purl.org/dc/terms/">
  <meta>
    <docNumber>117-167</docNumber>
    <docPublicationName>Public Law 117-167</docPublicationName>
    <dc:title>CHIPS and Science Act</dc:title>
    <congress>117</congress>
    <session>2</session>
    <enrolledDateline>August 9, 2022</enrolledDateline>
  </meta>
  <preface>
    <officialTitle>An Act to provide for...</officialTitle>
  </preface>
  <main>
    <level name="title">
      <num>I</num>
      <heading>SCIENCE AND TECHNOLOGY</heading>
      <level name="section">
        <num>10101</num>
        <heading>Definitions</heading>
        <content>...</content>
      </level>
    </level>
  </main>
</lawDoc>
```

### 8.2 Amendment Pattern Recognition

Public Laws contain amendment instructions that CWLB needs to parse:

Common patterns:
- "Section 123 of title 17, United States Code, is amended by striking 'X' and inserting 'Y'"
- "Section 123 is amended by adding at the end the following new subsection:"
- "Section 123 is repealed"
- "Title 17, United States Code, is amended by inserting after section 122 the following:"

### 8.3 Schema Compatibility

USLM XML from GovInfo uses the same schema as OLRC data (Task 0.1), ensuring:
- Consistent parsing logic
- Shared element definitions
- Compatible metadata structures

---

## 9. API Response Examples

### 9.1 Collections Response

```json
{
  "count": 50,
  "message": null,
  "nextPage": "https://api.govinfo.gov/collections/PLAW/2025-01-01?offsetMark=ABC123",
  "previousPage": null,
  "packages": [
    {
      "packageId": "PLAW-119publ5",
      "lastModified": "2025-03-15T10:30:00Z",
      "packageLink": "https://api.govinfo.gov/packages/PLAW-119publ5/summary",
      "docClass": "PLAW",
      "title": "An Act to provide for...",
      "congress": "119",
      "dateIssued": "2025-03-10"
    }
  ]
}
```

### 9.2 Package Summary Response

```json
{
  "packageId": "PLAW-117publ167",
  "title": "CHIPS and Science Act",
  "collectionCode": "PLAW",
  "collectionName": "Public and Private Laws",
  "category": "Legislative",
  "dateIssued": "2022-08-09",
  "congress": "117",
  "session": "2",
  "download": {
    "pdfLink": "https://api.govinfo.gov/packages/PLAW-117publ167/pdf",
    "xmlLink": "https://api.govinfo.gov/packages/PLAW-117publ167/xml",
    "htmLink": "https://api.govinfo.gov/packages/PLAW-117publ167/htm",
    "modsLink": "https://api.govinfo.gov/packages/PLAW-117publ167/mods",
    "premisLink": "https://api.govinfo.gov/packages/PLAW-117publ167/premis",
    "zipLink": "https://api.govinfo.gov/packages/PLAW-117publ167/zip"
  },
  "branch": "legislative",
  "pages": 1054,
  "governmentAuthor1": "Congress",
  "governmentAuthor2": "House",
  "suDocClassNumber": "AE 2.110:117-167",
  "isAppropriation": false,
  "isPrivate": false,
  "docNumber": "167",
  "otherIdentifier": {
    "type": "migrated-doc-id",
    "value": "f:publ167.117.pdf"
  }
}
```

### 9.3 Related Documents Response

```json
{
  "count": 5,
  "relatedDocuments": [
    {
      "type": "Bill Version",
      "packageId": "BILLS-117hr4346enr",
      "title": "H.R.4346 - Enrolled Bill"
    },
    {
      "type": "Congressional Report",
      "packageId": "CRPT-117hrpt617",
      "title": "House Report 117-617"
    },
    {
      "type": "Presidential Signing Statement",
      "packageId": "CPD-2022DCPD20220610",
      "title": "Statement on Signing..."
    }
  ]
}
```

---

## 10. Error Handling

### 10.1 Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 401 | Unauthorized | Check API key |
| 404 | Not Found | Package doesn't exist |
| 429 | Rate Limited | Wait and retry |
| 503 | Temporarily Unavailable | Retry with backoff |

### 10.2 503 ZIP Generation

When requesting ZIP files, a 503 response with `Retry-After` header indicates the file is being generated:

```
HTTP/1.1 503 Service Unavailable
Retry-After: 30
Content-Type: application/json

{"message": "Generating ZIP file. Please retry your request again after 30 seconds."}
```

### 10.3 Retry Strategy

Implement exponential backoff for transient errors:
1. Initial retry: 2 seconds
2. Second retry: 4 seconds
3. Third retry: 8 seconds
4. Maximum: 4 retries

---

## 11. Implementation Recommendations

### 11.1 Data Ingestion Strategy

**Phase 1: Historical Bulk Load**
1. Download all PLAW packages from Bulk Data Repository (113th Congress onward)
2. Parse USLM XML for law text and structure
3. Extract MODS metadata for each law
4. Store in PublicLaw table

**Phase 2: Incremental Updates**
1. Poll Collections endpoint daily for new/modified PLAW packages
2. Fetch and parse new packages
3. Update database with changes

**Phase 3: Related Data Enrichment**
1. Use Related Documents endpoint to link bills, reports, signing statements
2. Build legislative journey timeline
3. Cross-reference with US Code sections (from OLRC data)

### 11.2 Mapping to CWLB Data Model

| GovInfo Field | CWLB Entity/Field |
|---------------|-------------------|
| `packageId` | PublicLaw.govinfo_id |
| `docNumber` | PublicLaw.number (e.g., "117-167") |
| `title` | PublicLaw.name |
| `shortTitle` (from MODS) | PublicLaw.popular_name |
| `dateIssued` | PublicLaw.date_enacted |
| `congress` | PublicLaw.congress |
| `session` | PublicLaw.session |
| Related Bill | Link to Bill entity |
| Related Signing Statement | Store president from CPD |

### 11.3 Technical Considerations

1. **Caching**: Cache package summaries and MODS metadata locally
2. **Idempotency**: Use packageId as unique key for upserts
3. **Parallelization**: Process multiple packages concurrently (within rate limits)
4. **Validation**: Verify XML against USLM schema before parsing

---

## 12. Comparison with Alternative Sources

| Source | Public Law Coverage | Format | Update Frequency | Notes |
|--------|---------------------|--------|------------------|-------|
| **GovInfo API** | 104th Congress+ | XML, PDF | Daily | **Primary choice** |
| Congress.gov | 93rd Congress+ | HTML, PDF | Daily | Less structured |
| Library of Congress | Historical | Images | Static | For pre-1995 |
| Cornell LII | Current | HTML | Weekly | Display-focused |

**Recommendation**: Use GovInfo API as primary source for Public Laws; supplement with Congress.gov API (Task 0.3) for bill metadata and legislator information.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Rate limit impact on bulk ingestion | Use Bulk Data Repository for historical data |
| API downtime | Implement retry logic; cache fetched data |
| XML schema changes | Monitor GPO GitHub; implement schema version detection |
| Missing related documents | Graceful degradation; show "not available" |
| Pre-2013 USLM gaps | Use PDF/HTML with OCR if structured text needed |

---

## 14. Conclusion

The GovInfo.gov API is an excellent and authoritative source for Public Law documents. Key strengths:

1. **Comprehensive Coverage**: 30+ years of Public Laws in machine-readable format
2. **Structured Data**: USLM XML with consistent schema (compatible with OLRC data)
3. **Rich Metadata**: MODS provides bill linkage, dates, and classifications
4. **Related Documents**: Links to bills, reports, signing statements enable full legislative history
5. **Bulk Data Option**: No rate limits for historical data ingestion
6. **Free Access**: No cost for API key or data usage

Combined with the OLRC US Code data (Task 0.1), GovInfo provides the complete data foundation for CWLB's core features: Code Browser, Law Viewer, and Blame View.

---

## 15. Next Steps

1. **Task 0.3**: Evaluate Congress.gov API for bill and legislator information
2. **Task 0.4**: Research ProPublica Congress API for legislator photos and party data
3. **Task 0.5**: Build prototype parser for a single Public Law (PL 94-553 recommended)
4. **Task 0.6**: Build prototype line-level parser for 17 USC §106

---

## 16. References

### API Documentation
- [GovInfo API Documentation](https://api.govinfo.gov/docs) - Interactive OpenAPI specification
- [GovInfo API GitHub](https://github.com/usgpo/api) - Examples and detailed documentation
- [api.data.gov Rate Limits](https://api.data.gov/docs/rate-limits/) - Rate limiting details

### Data Collections
- [Public and Private Laws Collection](https://www.govinfo.gov/app/collection/plaw)
- [Public Laws Help Page](https://www.govinfo.gov/help/plaw)
- [Statutes at Large Collection](https://www.govinfo.gov/app/collection/statute)
- [Statutes at Large Help](https://www.govinfo.gov/help/statute)

### Bulk Data
- [GovInfo Bulk Data Repository](https://www.govinfo.gov/bulkdata)
- [Bulk Data GitHub](https://github.com/usgpo/bulk-data) - User guides for XML bulk data
- [Beta USLM XML Information](https://www.govinfo.gov/features/beta-uslm-xml)

### Schema Documentation
- [USLM GitHub Repository](https://github.com/usgpo/uslm) - Schema documentation
- [MODS Standard](https://www.loc.gov/standards/mods/) - Library of Congress MODS specification

### Developer Resources
- [GovInfo Developer Hub](https://www.govinfo.gov/developers)
- [GovInfo Features](https://www.govinfo.gov/features/api)
- [Related Document Service](https://www.govinfo.gov/features/api-related-document-service)

---

*Report prepared as part of CWLB Phase 0 Research & Validation*
