# Task 0.1: US House Office of Law Revision Counsel Data Evaluation

**Task**: Evaluate US House Office of Law Revision Counsel API/data formats
**Status**: Complete
**Date**: 2026-01-19

---

## Executive Summary

The Office of the Law Revision Counsel (OLRC) provides comprehensive, well-structured XML data for the entire United States Code. The data is available in USLM (United States Legislative Markup) format, a second-generation XML schema based on international standards. The data source is highly suitable for CWLB with excellent coverage, continuous updates, and rich metadata. No API is required - data is available for bulk download via HTTP.

### Key Findings

| Criterion | Assessment | Rating |
|-----------|------------|--------|
| Data Availability | All 54 titles available in XML | Excellent |
| Update Frequency | Continuous (per public law) | Excellent |
| Schema Quality | Well-documented USLM 2.x standard | Excellent |
| Historical Coverage | XML from 2013; prior release points archived | Good |
| Metadata Richness | Dublin Core + legislative-specific metadata | Excellent |
| Accessibility | Free bulk download via HTTP | Excellent |

**Recommendation**: The OLRC data source is the authoritative and preferred source for US Code data. Proceed with implementation using this as the primary data source.

---

## 1. Data Source Overview

### Primary Source
- **Organization**: Office of the Law Revision Counsel (OLRC), US House of Representatives
- **URL**: https://uscode.house.gov
- **Authority**: Statutory authority under 2 U.S.C. 285b

### Purpose
The OLRC prepares and publishes the United States Code, which is a consolidation and codification by subject matter of the general and permanent laws of the United States.

---

## 2. XML/Data Structure Assessment

### 2.1 Schema: United States Legislative Markup (USLM)

The US Code is published in **USLM (United States Legislative Markup)** format, a sophisticated XML schema.

#### Schema Characteristics
- **Version**: USLM 2.x (versions 2.0.14 through 2.1.0 currently available)
- **Standard Basis**: Derivative of international LegalDocML (Akoma Ntoso) standard
- **Versioning**: major.minor.point format (point = non-breaking, minor = breaking change)
- **Namespaces**: Uses Dublin Core (dcterms) and XHTML namespaces

#### Schema Resources
| Resource | URL |
|----------|-----|
| GitHub Repository | https://github.com/usgpo/uslm |
| USLM User Guide (PDF) | https://xml.house.gov/schemas/uslm/1.0/USLM-User-Guide.pdf |
| USLM User Guide (MD) | https://github.com/usgpo/uslm/blob/main/USLM-User-Guide.md |
| XSD Schema | https://xml.house.gov/schemas/uslm/1.0/USLM-1.0.xsd |

### 2.2 Document Structure

The USLM schema organizes legislative documents hierarchically:

```
<lawDoc>
├── <meta>          # Metadata section (Dublin Core + legislative metadata)
├── <preface>       # Optional introductory material
├── <main>          # Primary content body
│   └── <level>     # Hierarchical provision structure
│       ├── <num>       # Numerical designation (§1, Sec. 2)
│       ├── <heading>   # Section title
│       └── <level>     # Nested subsections
├── <backmatter>    # Indexes and supplementary content
└── <appendix>      # Optional appendices
```

### 2.3 US Code Hierarchical Structure

The schema supports the full US Code hierarchy:

| Level | Element Prefix | Numbering Convention | Example |
|-------|---------------|---------------------|---------|
| Title | - | Arabic numerals | Title 17 |
| Chapter | `ch` | Arabic numerals | Chapter 1 |
| Subchapter | `sch` | - | - |
| Section | `s` | Arabic numerals | §106 |
| Subsection | `ss` | Lower-case letters | (a), (b), (c) |
| Paragraph | `p` | Arabic numerals | (1), (2), (3) |
| Subparagraph | - | Upper-case letters | (A), (B), (C) |
| Clause | - | Lower-case Roman | (i), (ii), (iii) |
| Subclause | - | Upper-case Roman | (I), (II), (III) |
| Item | - | Double lower-case | (aa), (bb) |
| Subitem | - | Double upper-case | (AA), (BB) |

### 2.4 Temporal ID System

USLM uses a hierarchical `@temporalId` attribute for unique identification:

```
s1          → Section 1
s1_a        → Subsection (a) of Section 1
s1_a_2      → Paragraph (2) of Subsection (a) of Section 1
s1_a_2_A    → Subparagraph (A) of Paragraph (2)...
```

This system aligns perfectly with CWLB's subsection path requirements (e.g., "(c)(1)(A)(ii)").

---

## 3. Available Formats

The OLRC provides multiple download formats:

| Format | Description | CWLB Suitability |
|--------|-------------|------------------|
| **XML (USLM)** | Structured markup with full metadata | **Primary choice** |
| XHTML | Rendered HTML version | Display reference |
| PDF | Print-ready format | Not suitable for parsing |
| PCC | GPO photocomposition codes | Not suitable |

**Recommendation**: Use XML (USLM) as the primary data source for parsing and ingestion.

---

## 4. Completeness Assessment

### 4.1 Title Coverage

**All 54 titles of the United States Code are available in XML format.**

The Code is organized into 53 subject titles (1-52 and 54; title 53 reserved):
- Titles 1-52 and 54 are complete and available
- 27 titles have been enacted into "positive law" (statutory law): 1, 3, 4, 5, 9, 10, 11, 13, 14, 17, 18, 23, 28, 31, 32, 35, 36, 37, 38, 39, 40, 41, 44, 46, 49, 51, and 54

### 4.2 CWLB Phase 1 Target Titles

All Phase 1 target titles are available:

| Title | Subject | Status |
|-------|---------|--------|
| Title 10 | Armed Forces | ✅ Available (Positive Law) |
| Title 17 | Copyright | ✅ Available (Positive Law) |
| Title 18 | Crimes and Criminal Procedure | ✅ Available (Positive Law) |
| Title 20 | Education | ✅ Available |
| Title 22 | Foreign Relations | ✅ Available |
| Title 26 | Internal Revenue Code | ✅ Available |
| Title 42 | Public Health and Social Welfare | ✅ Available |
| Title 50 | War and National Defense | ✅ Available |

### 4.3 Historical Coverage

| Time Period | Coverage | Format |
|-------------|----------|--------|
| July 2013 - Present | Full coverage | XML (USLM) |
| Pre-2013 | Prior editions | Available in Annual Historical Archives |

**Note**: XML production began July 30, 2013. For historical versions before 2013, alternative sources (GovInfo, historical archives) may be needed.

---

## 5. Update Frequency

### 5.1 Update Mechanism

The OLRC uses a **Release Point System**:
- Each update creates a new "release point"
- Release points are tied to specific Public Law numbers
- Updates are **continuous** as new laws are enacted

### 5.2 Current Status (as of 2026-01-19)

> All files are current through Public Law 119-69 (01/14/2026), except 119-60.
> Titles in bold have been changed since the last release point.

### 5.3 Update Tracking Features

| Feature | Description |
|---------|-------------|
| Currency Page | https://uscode.house.gov/currency/currency.shtml |
| Pending Updates | Section-level tracking of laws not yet incorporated |
| Classification Tables | Track which sections affected by recent laws |
| Prior Release Points | Archive of all previous versions |
| View Details | Per-section impact information for each law |

### 5.4 Update Frequency Assessment

**Rating: Excellent**

- Updates occur within days of public law enactment
- Granular tracking at section level
- Full historical release points archived
- No fixed schedule (continuous delivery)

---

## 6. Metadata Schema Documentation

### 6.1 Core Metadata Elements (USLM 2.0)

The `<meta>` block contains rich metadata:

#### Document Properties
| Element | Description |
|---------|-------------|
| `docStage` | Document stage in legislative process |
| `docPart` | Part identifier |
| `publicPrivate` | Public or private law designation |
| `congress` | Congress number (e.g., 119) |
| `session` | Session number |
| `citableAs` | Official citation format |

#### Dates
| Element | Description |
|---------|-------------|
| `enrolledDateline` | Enrollment date |
| `createdDate` | Creation timestamp |
| `currentThroughPublicLaw` | Currency indicator |

#### References
| Element | Description |
|---------|-------------|
| `relatedDocument` | Links to related documents |
| `relatedDocuments` | Collection of related documents |
| `affected` | Sections affected by amendments |

#### Administrative
| Element | Description |
|---------|-------------|
| `processedBy` | Processing entity |
| `organization` | Organization identifier |
| `distributionCode` | Distribution classification |

### 6.2 Dublin Core Integration

USLM uses Dublin Core Terms (dcterms) namespace for standard metadata:
- `xmlns:dcterms="http://purl.org/dc/terms/"`

Common Dublin Core elements used:
- `dc:title` - Document title
- `dc:date` - Relevant dates
- `dc:identifier` - Unique identifiers
- `dc:publisher` - Publishing authority

### 6.3 Structural Metadata

Each structural element carries metadata attributes:

| Attribute | Purpose |
|-----------|---------|
| `@id` | Globally unique identifier (GUID with "id" prefix) |
| `@temporalId` | Hierarchical path identifier |
| `@version` | Schema version compliance |
| `@role` | Element classification |
| `@class` | Styling classification |

### 6.4 Amendment Representation

Amendments are tracked through:
- `<ins>` and `<del>` XHTML elements for text changes
- Version management attributes
- Amendment instruction elements in amendment-specific sections

---

## 7. Download and Access

### 7.1 Bulk Download

**URL**: https://uscode.house.gov/download/download.shtml

Download options:
- Individual titles (recommended for initial testing)
- Entire US Code (all titles at once)
- Specific release points

### 7.2 Access Method

- **Protocol**: HTTP (no authentication required)
- **Format**: Direct file download (ZIP archives)
- **Rate Limits**: None documented (public access)

### 7.3 URL Structure

```
https://uscode.house.gov/download/[format]/[title]/
```

Example paths:
- Current XML: `/download/xml/`
- Prior release points: `/download/releasepoints/us/pl/[congress]/[law]/`
- Annual archives: `/download/annualhistoricalarchives/`

---

## 8. Comparison with Alternative Sources

| Source | Coverage | Format | Update Frequency | Notes |
|--------|----------|--------|------------------|-------|
| **OLRC (uscode.house.gov)** | Complete | XML (USLM) | Continuous | **Authoritative, preferred** |
| GovInfo (GPO) | Complete | XML, PDF | Periodic | Good alternative |
| Cornell LII | Complete | HTML | Daily | Display-focused |
| FDsys/GovInfo | Historical | XML | As enacted | Public Laws source |

**Recommendation**: Use OLRC as primary source; GovInfo as supplementary source for Public Laws.

---

## 9. Implementation Recommendations

### 9.1 Data Ingestion Strategy

1. **Initial Load**
   - Download current XML for all Phase 1 titles
   - Parse USLM structure into CWLB data model
   - Extract metadata and store in database

2. **Incremental Updates**
   - Monitor currency page for new release points
   - Download and parse updated titles
   - Apply changes to database

3. **Historical Backfill**
   - Download prior release points for historical versions
   - Build SectionHistory records chronologically

### 9.2 Mapping to CWLB Data Model

| USLM Element | CWLB Entity |
|--------------|-------------|
| `<title>` | USCodeSection.title |
| `<chapter>` | USCodeSection.chapter |
| `<section>` | USCodeSection |
| `<level>` (nested) | USCodeLine tree structure |
| `@temporalId` | USCodeLine.subsection_path |
| `<num>` | Line number designation |
| `<heading>` | USCodeLine.line_type = "Heading" |
| `<p>` (prose) | USCodeLine.line_type = "Prose" |
| List items | USCodeLine.line_type = "ListItem" |

### 9.3 Technical Considerations

1. **Parser Development**
   - Use XML parsing library (Python: lxml; Node: xml2js)
   - Handle namespace declarations properly
   - Validate against USLM XSD schema

2. **Tree Structure Building**
   - Leverage `@temporalId` for parent/child relationships
   - Calculate depth_level from nesting
   - Generate subsection_path from hierarchy

3. **Change Detection**
   - Use element hashes for identifying unchanged content
   - Track effective dates from release point metadata
   - Link changes to Public Law numbers

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Pre-2013 historical data gaps | Use GovInfo/historical archives; manual digitization |
| Schema version changes | Monitor GitHub; implement schema version detection |
| Complex nested structures | Build robust recursive parser; test on §512(c) |
| Large file sizes | Implement streaming XML parsing; title-by-title processing |

---

## 11. Next Steps

1. **Task 0.2**: Evaluate GovInfo API for Public Laws data
2. **Task 0.5**: Build prototype parser for single Public Law
3. **Task 0.6**: Build prototype line-level parser for 17 USC §106
4. **Task 0.7**: Test parser on complex nested section (17 USC §512(c))

---

## 12. References

### Primary Sources
- [OLRC Download Page](https://uscode.house.gov/download/download.shtml)
- [USLM GitHub Repository](https://github.com/usgpo/uslm)
- [USLM User Guide (PDF)](https://xml.house.gov/schemas/uslm/1.0/USLM-User-Guide.pdf)
- [USLM User Guide (GitHub)](https://github.com/usgpo/uslm/blob/main/USLM-User-Guide.md)
- [Currency Page](https://uscode.house.gov/currency/currency.shtml)
- [Prior Release Points](https://uscode.house.gov/download/priorreleasepoints.htm)

### Schema Documentation
- [USLM XSD Schema](http://xml.house.gov/schemas/uslm/1.0/USLM-1.0.xsd)
- [USLM 2.0 Review Guide](https://github.com/usgpo/uslm/blob/main/USLM-2_0-Review-Guide-v2_0_12.md)
- [GovInfo USLM](https://www.govinfo.gov/features/beta-uslm-xml)

### Background Reading
- [Library of Congress: US Code Online](https://blogs.loc.gov/law/2013/11/the-united-states-code-online-downloadable-xml-files-and-more/)
- [XML at House.gov](http://xml.house.gov/)
- [GovInfo US Code Help](https://www.govinfo.gov/help/uscode)

---

*Report prepared as part of CWLB Phase 0 Research & Validation*
