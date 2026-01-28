# Task 0.14: Data Pipeline Architecture Design

**Task**: Design data pipeline architecture
**Status**: Complete
**Date**: 2026-01-28

---

## Executive Summary

This document defines the data pipeline architecture for CWLB, covering the ETL process flow, ingestion frequency strategy, and error handling approach. The pipeline ingests data from four primary sources (OLRC, GovInfo, Congress.gov, ProPublica) and transforms it into the CWLB data model to support code browsing, blame view, time travel, and analytics features.

---

## 1. ETL Process Flow

### 1.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CWLB DATA PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    OLRC      │  │   GovInfo    │  │ Congress.gov │  │  ProPublica  │         │
│  │  (US Code)   │  │(Public Laws) │  │   (Bills)    │  │ (Legislators)│         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                 │                  │
│         ▼                 ▼                 ▼                 ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │                         EXTRACT LAYER                                │        │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │        │
│  │  │  HTTP   │  │   API   │  │   API   │  │   API   │                 │        │
│  │  │Download │  │  Client │  │  Client │  │  Client │                 │        │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘                 │        │
│  └───────┼────────────┼────────────┼────────────┼──────────────────────┘        │
│          │            │            │            │                                │
│          ▼            ▼            ▼            ▼                                │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │                          RAW STAGING                                 │        │
│  │         (S3/Cloud Storage - Raw XML, JSON, API Responses)           │        │
│  └─────────────────────────────┬───────────────────────────────────────┘        │
│                                │                                                 │
│                                ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │                        TRANSFORM LAYER                               │        │
│  │                                                                      │        │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │        │
│  │  │  XML Parser   │  │  Legal Lang   │  │  Line-Level   │            │        │
│  │  │ (USLM Schema) │  │    Parser     │  │    Parser     │            │        │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘            │        │
│  │          │                  │                  │                     │        │
│  │          ▼                  ▼                  ▼                     │        │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │        │
│  │  │   Section     │  │  LawChange    │  │  USCodeLine   │            │        │
│  │  │  Extractor    │  │   Builder     │  │ Tree Builder  │            │        │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘            │        │
│  │          │                  │                  │                     │        │
│  │          ▼                  ▼                  ▼                     │        │
│  │  ┌─────────────────────────────────────────────────────────┐        │        │
│  │  │              VALIDATION & RECONCILIATION                 │        │        │
│  │  │   • Schema validation    • Referential integrity         │        │        │
│  │  │   • Data quality checks  • Duplicate detection           │        │        │
│  │  └─────────────────────────────┬───────────────────────────┘        │        │
│  └────────────────────────────────┼────────────────────────────────────┘        │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │                          LOAD LAYER                                  │        │
│  │                                                                      │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │        │
│  │  │ PostgreSQL  │  │Elasticsearch│  │    Redis    │                  │        │
│  │  │  (Primary)  │  │  (Search)   │  │  (Cache)    │                  │        │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │        │
│  │                                                                      │        │
│  └──────────────────────────────────────────────────────────────────────┘        │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Detailed Pipeline Stages

#### Stage 1: Extract

| Source | Method | Format | Frequency |
|--------|--------|--------|-----------|
| OLRC (US Code) | HTTP bulk download | XML (USLM 2.x) | Per release point |
| GovInfo (Public Laws) | REST API | XML/JSON | Daily |
| Congress.gov (Bills) | REST API | JSON | Daily |
| ProPublica (Legislators) | REST API | JSON | Weekly |

**Extract Process Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTRACT WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK FOR UPDATES                                            │
│     ┌─────────────┐                                              │
│     │ Poll OLRC   │──▶ Compare release point with last ingested │
│     │ Currency    │                                              │
│     └─────────────┘                                              │
│            │                                                     │
│            ▼ (if new release)                                    │
│  2. DOWNLOAD                                                     │
│     ┌─────────────┐                                              │
│     │ Download    │──▶ Fetch changed titles (ZIP archives)      │
│     │ XML Files   │──▶ Extract to staging area                   │
│     └─────────────┘                                              │
│            │                                                     │
│            ▼                                                     │
│  3. STAGE RAW DATA                                               │
│     ┌─────────────┐                                              │
│     │ Store in    │──▶ s3://cwlb-raw/olrc/{release_point}/      │
│     │ Raw Storage │──▶ Maintain full audit trail                 │
│     └─────────────┘                                              │
│            │                                                     │
│            ▼                                                     │
│  4. LOG EXTRACTION                                               │
│     ┌─────────────┐                                              │
│     │ Record in   │──▶ extraction_id, source, timestamp         │
│     │ Extract Log │──▶ file_count, bytes_downloaded             │
│     └─────────────┘                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Stage 2: Transform

The transform stage is the most complex, involving multiple specialized parsers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSFORM WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PIPELINE A: US CODE SECTIONS                      │    │
│  │                                                                      │    │
│  │   Raw XML ──▶ USLM Parser ──▶ Section Extractor ──▶ USCodeSection   │    │
│  │                    │                                                 │    │
│  │                    ▼                                                 │    │
│  │              Line-Level Parser ──▶ Tree Builder ──▶ USCodeLine      │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PIPELINE B: PUBLIC LAWS                           │    │
│  │                                                                      │    │
│  │   Raw XML/JSON ──▶ Law Metadata ──▶ Legal Language ──▶ PublicLaw    │    │
│  │                      Extractor       Parser                          │    │
│  │                          │              │                            │    │
│  │                          │              ▼                            │    │
│  │                          │        Amendment Pattern ──▶ LawChange   │    │
│  │                          │           Matcher                         │    │
│  │                          ▼                                           │    │
│  │                    Diff Generator ──▶ old_text / new_text           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PIPELINE C: LEGISLATORS & VOTES                   │    │
│  │                                                                      │    │
│  │   ProPublica ──▶ Legislator ──▶ Photo Fetch ──▶ Legislator          │    │
│  │      API          Parser                                             │    │
│  │                                                                      │    │
│  │   Congress.gov ──▶ Vote Record ──▶ Vote Normalizer ──▶ Vote         │    │
│  │       API           Parser                                           │    │
│  │                                                                      │    │
│  │   Bill Data ──▶ Sponsor ──▶ Sponsorship                             │    │
│  │                  Extractor                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PIPELINE D: HISTORY BUILDING                      │    │
│  │                                                                      │    │
│  │   Current Section ──▶ Compare with ──▶ SectionHistory               │    │
│  │                        Previous                                      │    │
│  │                                                                      │    │
│  │   Current Lines ──▶ Hash Compare ──▶ LineHistory                    │    │
│  │                     (detect changes)                                 │    │
│  │                                                                      │    │
│  │   Law Attribution ──▶ Blame ──▶ created_by_law_id                   │    │
│  │                       Calculator   last_modified_by_law_id          │    │
│  │                                    codified_by_law_id               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Transform Components:**

| Component | Input | Output | Description |
|-----------|-------|--------|-------------|
| USLM Parser | XML (USLM 2.x) | Parsed DOM | Validates against XSD schema, handles namespaces |
| Section Extractor | Parsed DOM | USCodeSection records | Extracts title, chapter, section, heading, text |
| Line-Level Parser | Section content | USCodeLine records | Parses into lines with types (Heading, Prose, ListItem) |
| Tree Builder | USCodeLine list | Tree structure | Builds parent/child relationships, calculates depth |
| Legal Language Parser | Amendment text | Structured changes | Parses "strike X, insert Y" patterns |
| Diff Generator | Old/new text | LawChange records | Calculates line-by-line differences |
| Blame Calculator | Lines + Laws | Attribution | Assigns created_by and last_modified_by law IDs |

#### Stage 3: Load

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LOAD WORKFLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRANSFORMED DATA                                                            │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    POSTGRESQL (Primary Store)                        │    │
│  │                                                                      │    │
│  │   Transaction Boundary ──────────────────────────────────────────   │    │
│  │   │                                                                  │    │
│  │   │  1. Upsert USCodeSection (ON CONFLICT UPDATE)                   │    │
│  │   │  2. Upsert USCodeLine (maintain tree integrity)                 │    │
│  │   │  3. Insert PublicLaw (if new)                                   │    │
│  │   │  4. Insert LawChange records                                    │    │
│  │   │  5. Insert SectionHistory / LineHistory snapshots               │    │
│  │   │  6. Upsert Legislator, Sponsorship, Vote                        │    │
│  │   │                                                                  │    │
│  │   COMMIT ────────────────────────────────────────────────────────   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        │ (async, post-commit)                                                │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    ELASTICSEARCH (Search Index)                      │    │
│  │                                                                      │    │
│  │   • Index USCodeSection (full-text on text field)                   │    │
│  │   • Index PublicLaw (full-text on summary, popular_name)            │    │
│  │   • Index USCodeLine (for line-level search)                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    REDIS (Cache Layer)                               │    │
│  │                                                                      │    │
│  │   • Invalidate affected section caches                              │    │
│  │   • Pre-warm popular sections                                       │    │
│  │   • Update currency metadata                                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Component Specifications

#### USLM XML Parser

```python
# Pseudocode for USLM parsing
class USLMParser:
    NAMESPACES = {
        'uslm': 'http://xml.house.gov/schemas/uslm/1.0',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/'
    }

    def parse_title(self, xml_path: Path) -> ParsedTitle:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        # Validate against USLM XSD
        self.validate_schema(root)

        # Extract metadata
        title_num = root.get('number')
        heading = root.find('.//heading').text

        # Extract all sections
        sections = []
        for section_elem in root.findall('.//section'):
            section = self.parse_section(section_elem)
            sections.append(section)

        return ParsedTitle(
            number=title_num,
            heading=heading,
            sections=sections
        )

    def parse_section(self, elem) -> ParsedSection:
        # Extract section metadata
        section_num = elem.get('number')
        temporal_id = elem.get('temporalId')  # e.g., "s106"
        heading = elem.find('heading').text

        # Parse content into lines
        lines = self.parse_content_to_lines(elem.find('content'))

        return ParsedSection(
            number=section_num,
            temporal_id=temporal_id,
            heading=heading,
            lines=lines
        )
```

#### Line-Level Parser

```python
# Pseudocode for line parsing with tree structure
class LineParser:
    def parse_content_to_lines(self, content_elem) -> List[USCodeLine]:
        lines = []
        line_counter = LineCounter()

        def process_element(elem, parent_line_id=None, depth=0):
            if elem.tag == 'heading':
                line = USCodeLine(
                    line_id=line_counter.next(),
                    line_type='Heading',
                    text_content=elem.text,
                    parent_line_id=parent_line_id,
                    depth_level=depth
                )
                lines.append(line)
                return line.line_id

            elif elem.tag == 'para' or elem.tag == 'text':
                line = USCodeLine(
                    line_id=line_counter.next(),
                    line_type='Prose',
                    text_content=self.extract_text(elem),
                    parent_line_id=parent_line_id,
                    depth_level=depth
                )
                lines.append(line)
                return line.line_id

            elif elem.tag == 'enum' or elem.tag == 'item':
                item_num = elem.get('number')
                subsection_path = self.build_path(parent_line_id, item_num)

                line = USCodeLine(
                    line_id=line_counter.next(),
                    line_type='ListItem',
                    text_content=self.extract_text(elem),
                    subsection_path=subsection_path,
                    parent_line_id=parent_line_id,
                    depth_level=depth
                )
                lines.append(line)

                # Process nested children
                for child in elem:
                    process_element(child, line.line_id, depth + 1)

                return line.line_id

        # Start processing from content root
        for child in content_elem:
            process_element(child, None, 0)

        # Calculate hashes for change detection
        for line in lines:
            line.hash = hashlib.sha256(
                line.text_content.encode('utf-8')
            ).hexdigest()

        return lines
```

#### Legal Language Parser

```python
# Pseudocode for parsing amendment instructions
class LegalLanguageParser:
    # Common amendment patterns
    PATTERNS = [
        # "Section X is amended by striking 'Y' and inserting 'Z'"
        (r"Section (\d+) is amended by striking ['\"](.+?)['\"] and inserting ['\"](.+?)['\"]",
         'STRIKE_INSERT'),

        # "Section X is amended by adding at the end the following"
        (r"Section (\d+) is amended by adding at the end the following[:\s]*(.+)",
         'ADD_END'),

        # "Section X is repealed"
        (r"Section (\d+) is repealed",
         'REPEAL'),

        # "Section X(a)(1) is amended to read as follows"
        (r"Section (\d+)(\([a-z0-9]+\))+ is amended to read as follows[:\s]*(.+)",
         'REPLACE_SUBSECTION'),

        # "by inserting after paragraph (X) the following"
        (r"by inserting after paragraph \((\d+)\) the following[:\s]*(.+)",
         'INSERT_AFTER'),
    ]

    def parse_amendment(self, text: str) -> List[AmendmentInstruction]:
        instructions = []

        for pattern, amendment_type in self.PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                instructions.append(
                    AmendmentInstruction(
                        type=amendment_type,
                        target_section=match[0],
                        parameters=match[1:],
                        raw_text=text
                    )
                )

        # Flag unparseable amendments for manual review
        if not instructions:
            instructions.append(
                AmendmentInstruction(
                    type='UNPARSEABLE',
                    raw_text=text,
                    requires_manual_review=True
                )
            )

        return instructions
```

---

## 2. Ingestion Frequency and Update Strategy

### 2.1 Update Schedule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION SCHEDULE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ CONTINUOUS (Event-Driven)                                            │    │
│  │                                                                      │    │
│  │   OLRC Release Points ──────────────────────────────────────────    │    │
│  │   • Trigger: New release point detected                             │    │
│  │   • Check frequency: Every 4 hours                                  │    │
│  │   • Action: Full ingestion of changed titles                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ DAILY (Scheduled)                                                    │    │
│  │                                                                      │    │
│  │   Public Laws ──────────────────────────────────────────────────    │    │
│  │   • Schedule: 2:00 AM UTC daily                                     │    │
│  │   • Source: GovInfo API                                             │    │
│  │   • Action: Fetch new Public Laws since last run                    │    │
│  │                                                                      │    │
│  │   Bill Status ──────────────────────────────────────────────────    │    │
│  │   • Schedule: 6:00 AM UTC daily                                     │    │
│  │   • Source: Congress.gov API                                        │    │
│  │   • Action: Update status of tracked bills                          │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ WEEKLY (Scheduled)                                                   │    │
│  │                                                                      │    │
│  │   Legislator Data ──────────────────────────────────────────────    │    │
│  │   • Schedule: Sundays 4:00 AM UTC                                   │    │
│  │   • Source: ProPublica Congress API                                 │    │
│  │   • Action: Refresh all legislator records                          │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ MONTHLY (Scheduled)                                                  │    │
│  │                                                                      │    │
│  │   Full Reconciliation ──────────────────────────────────────────    │    │
│  │   • Schedule: 1st of month, 1:00 AM UTC                             │    │
│  │   • Action: Compare all sections against OLRC source                │    │
│  │   • Purpose: Catch any missed updates, verify data integrity        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Update Detection Strategy

#### OLRC Release Point Monitoring

```python
# Pseudocode for release point detection
class OLRCMonitor:
    CURRENCY_URL = "https://uscode.house.gov/currency/currency.shtml"

    def check_for_updates(self) -> Optional[ReleasePoint]:
        # Fetch current currency page
        response = requests.get(self.CURRENCY_URL)

        # Parse to find current release point
        # Format: "Public Law 119-69 (01/14/2026)"
        current_release = self.parse_currency_page(response.text)

        # Compare with last ingested
        last_ingested = self.get_last_ingested_release()

        if current_release.law_number > last_ingested.law_number:
            return ReleasePoint(
                law_number=current_release.law_number,
                date=current_release.date,
                changed_titles=self.get_changed_titles(current_release)
            )

        return None

    def get_changed_titles(self, release: ReleasePoint) -> List[int]:
        # OLRC marks changed titles in bold on currency page
        # Parse to identify which titles need re-ingestion
        changed = []
        for title_num in range(1, 55):
            if self.title_changed_since(title_num, release):
                changed.append(title_num)
        return changed
```

### 2.3 Incremental vs Full Ingestion

| Scenario | Strategy | Description |
|----------|----------|-------------|
| New release point | Incremental | Only ingest changed titles |
| New Public Law | Incremental | Ingest single law + affected sections |
| Monthly reconciliation | Full scan | Compare all sections, update if different |
| Initial load | Full | Complete ingestion of all titles and history |
| Schema migration | Full rebuild | Re-process all raw data with new schema |

### 2.4 Historical Backfill Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HISTORICAL BACKFILL PROCESS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Recent History (2013-Present)                                      │
│  ───────────────────────────────────────                                     │
│  • Source: OLRC prior release points (XML available)                         │
│  • Process: Download each release point, build version history               │
│  • Priority: High (full XML coverage)                                        │
│                                                                              │
│  Phase 2: Pre-XML History (2004-2013)                                        │
│  ───────────────────────────────────────                                     │
│  • Source: OLRC annual archives, GovInfo historical                         │
│  • Process: Parse older formats, map to current schema                      │
│  • Priority: Medium (may require format conversion)                         │
│                                                                              │
│  Phase 3: Deep History (Pre-2004)                                            │
│  ───────────────────────────────────────                                     │
│  • Source: Historical archives, OCR of printed documents                    │
│  • Process: Manual digitization where needed                                │
│  • Priority: Low (Phase 2+ scope)                                           │
│                                                                              │
│  Backfill Order (by Title):                                                  │
│  1. Title 17 (Copyright) - High public interest, positive law               │
│  2. Title 18 (Crimes) - High public interest, positive law                  │
│  3. Title 10 (Armed Forces) - Positive law                                  │
│  4. Title 26 (Tax) - High public interest                                   │
│  5. Title 42 (Public Health) - High public interest                         │
│  6-8. Titles 20, 22, 50 - Remaining Phase 1 titles                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Error Handling and Data Validation

### 3.1 Error Classification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERROR CLASSIFICATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SEVERITY LEVELS:                                                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ CRITICAL (Pipeline Halt)                                             │    │
│  │ • Database connection failure                                        │    │
│  │ • Schema validation failure on entire title                         │    │
│  │ • Storage quota exceeded                                            │    │
│  │ • Authentication/authorization failure                              │    │
│  │                                                                      │    │
│  │ Action: Stop pipeline, alert on-call, require manual intervention   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ ERROR (Section-Level Failure)                                        │    │
│  │ • Individual section parse failure                                  │    │
│  │ • Referential integrity violation                                   │    │
│  │ • Legal language parse failure                                      │    │
│  │ • Line-level tree structure invalid                                 │    │
│  │                                                                      │    │
│  │ Action: Skip section, log error, continue pipeline, queue for review│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ WARNING (Data Quality Issue)                                         │    │
│  │ • Missing optional metadata                                         │    │
│  │ • Unexpected but parseable format                                   │    │
│  │ • Duplicate detection triggered                                     │    │
│  │ • Date parsing ambiguity                                            │    │
│  │                                                                      │    │
│  │ Action: Log warning, apply default/fallback, continue               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ INFO (Operational)                                                   │    │
│  │ • Successful ingestion metrics                                      │    │
│  │ • Cache invalidation events                                         │    │
│  │ • No-op updates (data unchanged)                                    │    │
│  │                                                                      │    │
│  │ Action: Log for metrics/audit                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Validation Rules

#### Schema Validation

| Entity | Validation Rule | Failure Action |
|--------|-----------------|----------------|
| USCodeSection | title 1-54, section required | ERROR: Skip section |
| USCodeLine | parent_line_id exists if non-null | ERROR: Reject line |
| USCodeLine | depth_level matches tree depth | WARNING: Recalculate |
| PublicLaw | law_number format PL \d+-\d+ | ERROR: Skip law |
| LawChange | section_id exists | ERROR: Skip change |
| Vote | vote_type in enum | WARNING: Default to 'Not Voting' |

#### Referential Integrity

```python
# Pseudocode for integrity validation
class IntegrityValidator:
    def validate_batch(self, batch: IngestBatch) -> ValidationResult:
        errors = []

        # 1. All parent_line_ids must reference existing lines
        line_ids = {line.line_id for line in batch.lines}
        for line in batch.lines:
            if line.parent_line_id and line.parent_line_id not in line_ids:
                errors.append(IntegrityError(
                    entity='USCodeLine',
                    field='parent_line_id',
                    value=line.parent_line_id,
                    message='Parent line does not exist'
                ))

        # 2. All law_id references must be valid
        law_ids = {law.law_id for law in batch.laws}
        for change in batch.changes:
            if change.law_id not in law_ids:
                errors.append(IntegrityError(
                    entity='LawChange',
                    field='law_id',
                    value=change.law_id,
                    message='Referenced law does not exist'
                ))

        # 3. Tree structure validation (no cycles)
        if self.has_cycles(batch.lines):
            errors.append(IntegrityError(
                entity='USCodeLine',
                field='parent_line_id',
                message='Cycle detected in line tree structure'
            ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
```

#### Data Quality Checks

```python
# Pseudocode for quality validation
class QualityValidator:
    def validate_section(self, section: USCodeSection) -> List[QualityWarning]:
        warnings = []

        # 1. Text should not be empty
        if not section.text or len(section.text.strip()) == 0:
            warnings.append(QualityWarning(
                level='ERROR',
                message=f'Section {section.section} has empty text'
            ))

        # 2. Heading should exist
        if not section.heading:
            warnings.append(QualityWarning(
                level='WARNING',
                message=f'Section {section.section} missing heading'
            ))

        # 3. Dates should be reasonable
        if section.enacted_date and section.enacted_date > datetime.now():
            warnings.append(QualityWarning(
                level='ERROR',
                message=f'Section {section.section} has future enacted_date'
            ))

        # 4. Check for unexpected characters
        if self.contains_control_chars(section.text):
            warnings.append(QualityWarning(
                level='WARNING',
                message=f'Section {section.section} contains control characters'
            ))

        return warnings

    def validate_line_tree(self, lines: List[USCodeLine]) -> List[QualityWarning]:
        warnings = []

        # 1. Should have exactly one root (parent_line_id = None)
        roots = [l for l in lines if l.parent_line_id is None]
        if len(roots) != 1:
            warnings.append(QualityWarning(
                level='ERROR',
                message=f'Expected 1 root line, found {len(roots)}'
            ))

        # 2. Line numbers should be sequential
        line_nums = sorted([l.line_number for l in lines])
        expected = list(range(1, len(lines) + 1))
        if line_nums != expected:
            warnings.append(QualityWarning(
                level='WARNING',
                message='Line numbers are not sequential'
            ))

        # 3. Depth levels should be consistent with tree
        for line in lines:
            calculated_depth = self.calculate_depth(line, lines)
            if line.depth_level != calculated_depth:
                warnings.append(QualityWarning(
                    level='WARNING',
                    message=f'Line {line.line_id} depth mismatch: stored={line.depth_level}, calculated={calculated_depth}'
                ))

        return warnings
```

### 3.3 Error Recovery Strategies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ERROR RECOVERY STRATEGIES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ RETRY WITH BACKOFF (Transient Errors)                                │    │
│  │                                                                      │    │
│  │   Applicable to:                                                     │    │
│  │   • Network timeouts                                                │    │
│  │   • API rate limits (429)                                           │    │
│  │   • Temporary service unavailability (503)                          │    │
│  │                                                                      │    │
│  │   Strategy:                                                          │    │
│  │   • Retry 1: Wait 1 second                                          │    │
│  │   • Retry 2: Wait 5 seconds                                         │    │
│  │   • Retry 3: Wait 30 seconds                                        │    │
│  │   • Retry 4: Wait 5 minutes                                         │    │
│  │   • After 4 retries: Mark as failed, alert                          │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ SKIP AND CONTINUE (Non-Critical Failures)                            │    │
│  │                                                                      │    │
│  │   Applicable to:                                                     │    │
│  │   • Individual section parse failure                                │    │
│  │   • Single legislator data fetch failure                            │    │
│  │   • Optional metadata extraction failure                            │    │
│  │                                                                      │    │
│  │   Strategy:                                                          │    │
│  │   • Log error with full context                                     │    │
│  │   • Skip the problematic record                                     │    │
│  │   • Continue processing remaining records                           │    │
│  │   • Queue for manual review                                         │    │
│  │   • Include in summary report                                       │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ ROLLBACK (Transaction Failures)                                      │    │
│  │                                                                      │    │
│  │   Applicable to:                                                     │    │
│  │   • Database constraint violation                                   │    │
│  │   • Partial batch load failure                                      │    │
│  │   • Integrity check failure                                         │    │
│  │                                                                      │    │
│  │   Strategy:                                                          │    │
│  │   • Rollback entire transaction                                     │    │
│  │   • Log all records that would have been affected                   │    │
│  │   • Preserve raw data in staging for reprocessing                   │    │
│  │   • Alert for investigation                                         │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ MANUAL REVIEW QUEUE (Complex Failures)                               │    │
│  │                                                                      │    │
│  │   Applicable to:                                                     │    │
│  │   • Unparseable legal language                                      │    │
│  │   • Ambiguous amendment instructions                                │    │
│  │   • Complex nested structures                                       │    │
│  │   • Data quality anomalies                                          │    │
│  │                                                                      │    │
│  │   Strategy:                                                          │    │
│  │   • Store in manual_review_queue table                              │    │
│  │   • Include: raw_data, error_message, suggested_fix                 │    │
│  │   • Admin UI for reviewing and correcting                           │    │
│  │   • After correction, re-run through pipeline                       │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Monitoring and Alerting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MONITORING DASHBOARD METRICS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Pipeline Health                                                             │
│  ────────────────                                                            │
│  • Last successful run: timestamp                                            │
│  • Current status: Running / Idle / Failed                                   │
│  • Records processed (last 24h): count                                       │
│  • Error rate (last 24h): percentage                                         │
│                                                                              │
│  Data Currency                                                               │
│  ─────────────────                                                           │
│  • Current through Public Law: PL xxx-xxx                                   │
│  • Last OLRC release point: date                                            │
│  • Days since last update: count                                            │
│  • Pending updates: count                                                    │
│                                                                              │
│  Error Summary                                                               │
│  ─────────────────                                                           │
│  • Critical errors (last 7 days): count                                     │
│  • Sections in manual review queue: count                                   │
│  • Parse failures by type: breakdown                                        │
│  • Retry queue depth: count                                                 │
│                                                                              │
│  Performance                                                                 │
│  ─────────────────                                                           │
│  • Average section parse time: ms                                           │
│  • Average line-level parse time: ms                                        │
│  • Database write throughput: records/sec                                   │
│  • Elasticsearch index lag: seconds                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           ALERT RULES                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CRITICAL (Page On-Call):                                                    │
│  • Pipeline failed and not recovering after 4 retries                       │
│  • Database connection lost for > 5 minutes                                 │
│  • Error rate > 10% in last hour                                           │
│  • No successful run in > 24 hours                                         │
│                                                                              │
│  WARNING (Slack Channel):                                                    │
│  • Manual review queue > 50 items                                          │
│  • Error rate > 2% in last hour                                            │
│  • OLRC has new release not yet ingested (> 8 hours)                       │
│  • Elasticsearch index lag > 5 minutes                                     │
│                                                                              │
│  INFO (Daily Digest):                                                        │
│  • Summary of records processed                                             │
│  • New Public Laws ingested                                                 │
│  • Sections updated                                                         │
│  • Performance metrics                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Audit Trail

```sql
-- Pipeline run logging
CREATE TABLE pipeline_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failed', 'partial'
    trigger_type VARCHAR(20) NOT NULL, -- 'scheduled', 'manual', 'event'
    source VARCHAR(50) NOT NULL, -- 'olrc', 'govinfo', 'congress', 'propublica'

    -- Metrics
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    warnings_count INTEGER DEFAULT 0,

    -- Context
    release_point VARCHAR(50),
    config_snapshot JSONB,
    error_summary JSONB
);

-- Detailed error logging
CREATE TABLE pipeline_errors (
    error_id UUID PRIMARY KEY,
    run_id UUID REFERENCES pipeline_runs(run_id),
    occurred_at TIMESTAMP NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'critical', 'error', 'warning'
    error_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50), -- 'USCodeSection', 'USCodeLine', 'PublicLaw', etc.
    entity_id VARCHAR(100),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    raw_data JSONB,
    resolution_status VARCHAR(20) DEFAULT 'open', -- 'open', 'resolved', 'ignored'
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

-- Manual review queue
CREATE TABLE manual_review_queue (
    review_id UUID PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    run_id UUID REFERENCES pipeline_runs(run_id),
    entity_type VARCHAR(50) NOT NULL,
    entity_identifier VARCHAR(200) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL,
    suggested_fix JSONB,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'corrected'
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    correction_applied JSONB
);
```

---

## 4. Infrastructure and Orchestration

### 4.1 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Orchestration | Apache Airflow | DAG scheduling, monitoring, retries |
| Message Queue | Redis (or SQS) | Job queuing, event distribution |
| Raw Storage | S3 / Cloud Storage | Raw XML/JSON archive |
| Primary Database | PostgreSQL 15+ | Relational data, transactions |
| Search | Elasticsearch 8.x | Full-text search indexing |
| Cache | Redis | Query caching, rate limiting |
| Monitoring | Datadog / Prometheus | Metrics, alerting |
| Logging | ELK Stack / CloudWatch | Centralized logging |

### 4.2 Airflow DAG Structure

```python
# Simplified DAG definition
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'cwlb',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
}

# DAG 1: OLRC Ingestion (event-driven, checked every 4 hours)
with DAG(
    'cwlb_olrc_ingestion',
    default_args=default_args,
    schedule_interval='0 */4 * * *',  # Every 4 hours
    catchup=False,
) as olrc_dag:

    check_updates = PythonOperator(
        task_id='check_olrc_updates',
        python_callable=check_olrc_for_updates,
    )

    download_xml = PythonOperator(
        task_id='download_xml_files',
        python_callable=download_changed_titles,
    )

    parse_sections = PythonOperator(
        task_id='parse_sections',
        python_callable=parse_uslm_sections,
    )

    parse_lines = PythonOperator(
        task_id='parse_lines',
        python_callable=parse_line_level,
    )

    validate = PythonOperator(
        task_id='validate_data',
        python_callable=run_validation,
    )

    load_postgres = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_database,
    )

    index_elasticsearch = PythonOperator(
        task_id='index_elasticsearch',
        python_callable=update_search_index,
    )

    invalidate_cache = PythonOperator(
        task_id='invalidate_cache',
        python_callable=invalidate_redis_cache,
    )

    check_updates >> download_xml >> parse_sections >> parse_lines >> validate >> load_postgres >> [index_elasticsearch, invalidate_cache]

# DAG 2: Daily Public Law Ingestion
with DAG(
    'cwlb_public_law_ingestion',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # 2 AM UTC daily
    catchup=False,
) as law_dag:

    fetch_laws = PythonOperator(
        task_id='fetch_new_laws',
        python_callable=fetch_govinfo_laws,
    )

    parse_amendments = PythonOperator(
        task_id='parse_amendments',
        python_callable=parse_legal_language,
    )

    generate_diffs = PythonOperator(
        task_id='generate_diffs',
        python_callable=generate_law_changes,
    )

    # ... continue DAG
```

---

## 5. Summary

### Key Design Decisions

1. **Event-driven ingestion for OLRC**: Monitor release points every 4 hours rather than fixed schedule to ensure timely updates.

2. **Separate pipelines per source**: Each data source (OLRC, GovInfo, Congress.gov, ProPublica) has its own pipeline with appropriate scheduling.

3. **Two-phase parsing**: First parse sections, then parse line-level structure. This allows partial success if line parsing fails.

4. **Skip-and-continue error handling**: Individual record failures don't halt the entire pipeline. Failed records are queued for manual review.

5. **Full audit trail**: Every pipeline run, error, and manual correction is logged for debugging and compliance.

6. **Raw data preservation**: Original XML/JSON is always preserved in staging storage, enabling reprocessing if parsing logic improves.

### Dependencies on Other Tasks

| This Task Uses | From Task |
|----------------|-----------|
| USLM XML schema details | Task 0.1 (OLRC Evaluation) |
| Data model entities | Spec Section 6 |

| Other Tasks Use This |
|---------------------|
| Task 1.6: US Code section ingestion |
| Task 1.7: Public Law ingestion |
| Task 1.13-1.16: Line-level parsing |
| Task M.1-M.3: Ongoing maintenance |

---

## 6. Next Steps

1. **Task 0.11**: Design database schema (detailed table definitions)
2. **Task 0.12**: Design API architecture
3. **Task 0.13**: Select technology stack (finalize choices above)
4. **Task 1.6**: Begin implementing US Code section ingestion

---

*Document prepared as part of CWLB Phase 0 Research & Validation*
