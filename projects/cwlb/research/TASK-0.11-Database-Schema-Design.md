# Task 0.11: Database Schema Design

**Status**: Complete
**Completed**: 2026-01-23
**Deliverables**:
- SQL schema: [`/prototypes/database_schema.sql`](../prototypes/database_schema.sql)
- This documentation file

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Entity Overview](#2-entity-overview)
3. [Entity-Relationship Diagram](#3-entity-relationship-diagram)
4. [Detailed Table Specifications](#4-detailed-table-specifications)
5. [Relationships and Foreign Keys](#5-relationships-and-foreign-keys)
6. [Indexing Strategy](#6-indexing-strategy)
7. [Temporal Data Strategy](#7-temporal-data-strategy)
8. [Scalability Analysis](#8-scalability-analysis)
9. [Migration Tooling Recommendation](#9-migration-tooling-recommendation)
10. [Performance Optimization Strategies](#10-performance-optimization-strategies)
11. [Implementation Checklist](#11-implementation-checklist)

---

## 1. Executive Summary

This document presents the complete database schema design for The Code We Live By (CWLB) platform. The schema is designed to support:

- **Code browsing**: Navigate US Code by Title > Chapter > Section hierarchy
- **Law viewing**: Display Public Laws as "merged PRs" with diffs and metadata
- **Blame view**: Line-by-line attribution showing which law modified each provision
- **Time travel**: View any section as it existed at any historical date
- **Search**: Full-text search across sections and laws
- **Analytics**: Legislative productivity metrics and visualizations
- **Dependency graph**: Cross-references between sections

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | PostgreSQL 15+ | Best-in-class for relational data, recursive CTEs, full-text search, JSONB support |
| Primary keys | SERIAL (auto-increment) | Simple, performant, sufficient for expected scale |
| Temporal strategy | Version tables (SectionHistory, LineHistory) | Clean separation, efficient queries, supports time travel |
| Text search | Native pg_trgm + tsvector | Adequate for MVP; Elasticsearch can be added in Phase 2 |
| Tree structure | Adjacency list (parent_line_id) | Simple, PostgreSQL recursive CTEs handle well |

### Schema Statistics

| Metric | Value |
|--------|-------|
| Total tables | 22 |
| Custom ENUM types | 12 |
| Indexes | 85+ |
| Materialized views | 3 |
| Functions/triggers | 8 |

---

## 2. Entity Overview

### Core Entities

| Entity | Description | Estimated Records (Phase 1) |
|--------|-------------|----------------------------|
| `us_code_title` | Top-level titles (1-54) | 8 (Phase 1 titles) |
| `us_code_chapter` | Chapters within titles | ~500 |
| `us_code_section` | Individual sections of law | ~15,000 |
| `public_law` | Enacted legislation | ~5,000 (20 years) |
| `bill` | Proposed/failed legislation | ~50,000 |
| `law_change` | Diffs for enacted laws | ~100,000 |
| `us_code_line` | Line-level section structure | ~500,000 |
| `line_history` | Historical line versions | ~2,000,000 |
| `section_history` | Historical section snapshots | ~75,000 |

### Legislator Entities

| Entity | Description | Estimated Records |
|--------|-------------|-------------------|
| `legislator` | Congress members | ~15,000 (all time) |
| `legislator_term` | Individual terms served | ~40,000 |
| `sponsorship` | Law/bill sponsors | ~500,000 |
| `vote` | Aggregate vote records | ~20,000 |
| `individual_vote` | Per-legislator votes | ~10,000,000 |

### Supporting Entities

| Entity | Description |
|--------|-------------|
| `proposed_change` | Diffs for pending bills |
| `section_reference` | Cross-references between sections |
| `committee` | Congressional committees |
| `bill_committee_assignment` | Committee assignments |
| `amendment` | Bill amendments |
| `data_ingestion_log` | Pipeline audit trail |
| `data_correction` | Manual correction audit |

---

## 3. Entity-Relationship Diagram

### ASCII Entity-Relationship Diagram

```
                                    +------------------+
                                    |  us_code_title   |
                                    +------------------+
                                    | title_id (PK)    |
                                    | title_number     |
                                    | title_name       |
                                    | is_positive_law  |
                                    +--------+---------+
                                             |
                                             | 1:N
                                             v
+----------------+                  +------------------+                  +------------------+
|   public_law   |                  |  us_code_chapter |                  |   legislator     |
+----------------+                  +------------------+                  +------------------+
| law_id (PK)    |                  | chapter_id (PK)  |                  | legislator_id(PK)|
| law_number     |                  | title_id (FK)    |                  | bioguide_id      |
| congress       |                  | chapter_number   |                  | full_name        |
| popular_name   |                  | chapter_name     |                  | party            |
| enacted_date   |                  +--------+---------+                  | state            |
+-------+--------+                           |                            +--------+---------+
        |                                    | 1:N                                 |
        |                                    v                                     |
        |                           +------------------+                           |
        |                           | us_code_section  |                           |
        |                           +------------------+                           |
        |                           | section_id (PK)  |                           |
        |                           | title_id (FK)    |                           |
        |                           | chapter_id (FK)  |                           |
        |                           | section_number   |                           |
        |                           | heading          |                           |
        |                           | is_positive_law  |                           |
        |                           +--------+---------+                           |
        |                                    |                                     |
        |          +------------+------------+------------+                        |
        |          |            |                         |                        |
        |          | 1:N        | 1:N                     | 1:N                    |
        |          v            v                         v                        |
        |  +-------------+ +---------------+     +------------------+              |
        |  | law_change  | |section_history|     |   us_code_line   |              |
        |  +-------------+ +---------------+     +------------------+              |
        |  | change_id   | | history_id    |     | line_id (PK)     |              |
        +->| law_id (FK) | | section_id(FK)|     | section_id (FK)  |              |
        |  | section_id  | | law_id (FK)   |     | parent_line_id   |<---+         |
        |  | change_type | | version_number|     | line_number      |    |         |
        |  | old_text    | | text_content  |     | text_content     |    | self    |
        |  | new_text    | | effective_date|     | subsection_path  |    | ref     |
        |  +-------------+ +---------------+     | depth_level      |    |         |
        |                                        | created_by_law_id+----+---+     |
        |                                        | modified_by_law_id+---+   |     |
        |                                        | codified_by_law_id+---+   |     |
        |                                        +--------+---------+        |     |
        |                                                 |                  |     |
        |                                                 | 1:N              |     |
        |                                                 v                  |     |
        |                                        +------------------+        |     |
        |                                        |  line_history    |        |     |
        |                                        +------------------+        |     |
        |                                        | line_history_id  |        |     |
        |                                        | line_id (FK)     |        |     |
        |                                        | version_number   |        |     |
        |                                        | text_content     |        |     |
        +----------------------------------------| modified_by_law  |--------+     |
                                                 +------------------+              |
                                                                                   |
        +------------------+     +------------------+     +------------------+     |
        |   sponsorship    |     |      vote        |     | individual_vote  |     |
        +------------------+     +------------------+     +------------------+     |
        | sponsorship_id   |     | vote_id (PK)     |     | indiv_vote_id    |     |
        | law_id (FK)      |     | law_id (FK)      |     | vote_id (FK)     |     |
        | bill_id (FK)     |     | bill_id (FK)     |     | legislator_id(FK)+-----+
        | legislator_id(FK)+---->| chamber          |     | vote_cast        |
        | role             |     | vote_date        |     +------------------+
        +------------------+     +------------------+

        +------------------+     +------------------+
        |section_reference |     |      bill        |
        +------------------+     +------------------+
        | reference_id     |     | bill_id (PK)     |
        | source_section   |     | bill_number      |
        | target_section   |     | congress         |
        | reference_type   |     | status           |
        +------------------+     | related_law_id   |
                                 +------------------+
```

### Relationship Summary

```
us_code_title --(1:N)--> us_code_chapter
us_code_title --(1:N)--> us_code_section
us_code_chapter --(1:N)--> us_code_section
us_code_section --(1:N)--> us_code_line
us_code_section --(1:N)--> section_history
us_code_section --(1:N)--> law_change
us_code_section --(N:N via section_reference)--> us_code_section
us_code_line --(self-ref)--> us_code_line (parent/child tree)
us_code_line --(1:N)--> line_history
public_law --(1:N)--> law_change
public_law --(1:N)--> section_history
public_law --(1:N)--> us_code_line (via created_by, modified_by, codified_by)
public_law --(1:N)--> sponsorship
public_law --(1:N)--> vote
public_law --(1:1)--> bill (origin)
bill --(1:N)--> proposed_change
bill --(1:N)--> sponsorship
bill --(1:N)--> vote
bill --(1:N)--> bill_committee_assignment
bill --(1:N)--> amendment
legislator --(1:N)--> legislator_term
legislator --(1:N)--> sponsorship
legislator --(1:N)--> individual_vote
vote --(1:N)--> individual_vote
committee --(1:N)--> bill_committee_assignment
```

---

## 4. Detailed Table Specifications

### 4.1 US Code Tables

#### `us_code_title`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| title_id | SERIAL | PRIMARY KEY | Auto-increment ID |
| title_number | INTEGER | UNIQUE, NOT NULL | Title number (1-54) |
| title_name | VARCHAR(500) | NOT NULL | Title name |
| is_positive_law | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether enacted as positive law |
| positive_law_date | DATE | | Date of positive law enactment |
| positive_law_citation | VARCHAR(200) | | PL that enacted as positive law |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | |

#### `us_code_section`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| section_id | SERIAL | PRIMARY KEY | Auto-increment ID |
| title_id | INTEGER | FK, NOT NULL | Reference to title |
| chapter_id | INTEGER | FK | Reference to chapter |
| section_number | VARCHAR(50) | NOT NULL | Section number (e.g., "106", "512") |
| heading | VARCHAR(500) | NOT NULL | Section heading |
| full_citation | VARCHAR(200) | NOT NULL | Full citation (e.g., "17 U.S.C. § 106") |
| text_content | TEXT | | Current full text |
| enacted_date | DATE | | Original enactment date |
| last_modified_date | DATE | | Last modification date |
| effective_date | DATE | | Current effective date |
| is_positive_law | BOOLEAN | NOT NULL, DEFAULT FALSE | Inherited from title |
| title_positive_law_date | DATE | | When title became positive law |
| statutes_at_large_citation | VARCHAR(200) | | For non-positive law sections |
| is_repealed | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| repealed_date | DATE | | |
| repealed_by_law_id | INTEGER | FK | |
| notes | TEXT | | Editorial notes |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | For ordering |

#### `us_code_line`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| line_id | SERIAL | PRIMARY KEY | Auto-increment ID |
| section_id | INTEGER | FK, NOT NULL | Parent section |
| parent_line_id | INTEGER | FK (self) | Parent line (NULL for root) |
| line_number | INTEGER | NOT NULL | Sequential order (1, 2, 3...) |
| line_type | ENUM | NOT NULL | 'Heading', 'Prose', 'ListItem' |
| text_content | TEXT | NOT NULL | Line text |
| subsection_path | VARCHAR(100) | | Path like "(c)(1)(A)(ii)" |
| depth_level | INTEGER | NOT NULL, DEFAULT 0 | Tree depth (0=root) |
| created_by_law_id | INTEGER | FK | Law that created this line |
| last_modified_by_law_id | INTEGER | FK | Law that last modified |
| codified_by_law_id | INTEGER | FK | Positive law codification |
| effective_date | DATE | NOT NULL | When this version took effect |
| codification_date | DATE | | When codified as positive law |
| text_hash | VARCHAR(64) | NOT NULL | SHA-256 hash of text |
| is_current | BOOLEAN | NOT NULL, DEFAULT TRUE | False for superseded |

### 4.2 Public Law Tables

#### `public_law`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| law_id | SERIAL | PRIMARY KEY | Auto-increment ID |
| law_number | VARCHAR(20) | NOT NULL | e.g., "94-553" |
| congress | INTEGER | NOT NULL, CHECK(1-200) | Congress number |
| law_type | ENUM | NOT NULL, DEFAULT 'Public' | Public or Private |
| popular_name | VARCHAR(500) | | e.g., "Copyright Act of 1976" |
| official_title | TEXT | | Full official title |
| short_title | VARCHAR(500) | | Short title |
| summary | TEXT | | |
| purpose | TEXT | | |
| bill_number | VARCHAR(50) | | Origin bill (e.g., "S. 22") |
| bill_id | INTEGER | FK | Link to bill table |
| introduced_date | DATE | | |
| house_passed_date | DATE | | |
| senate_passed_date | DATE | | |
| presented_to_president_date | DATE | | |
| enacted_date | DATE | NOT NULL | Date of enactment |
| effective_date | DATE | | May differ from enacted_date |
| president | VARCHAR(100) | | Signing president |
| presidential_action | VARCHAR(50) | DEFAULT 'Signed' | Signed, Veto_Overridden |
| veto_date | DATE | | |
| veto_override_date | DATE | | |
| sections_affected | INTEGER | DEFAULT 0 | Computed |
| sections_added | INTEGER | DEFAULT 0 | Computed |
| sections_modified | INTEGER | DEFAULT 0 | Computed |
| sections_repealed | INTEGER | DEFAULT 0 | Computed |
| govinfo_url | VARCHAR(500) | | GovInfo.gov link |
| congress_url | VARCHAR(500) | | Congress.gov link |
| statutes_at_large_citation | VARCHAR(200) | | e.g., "90 Stat. 2541" |

### 4.3 Legislator Tables

#### `legislator`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| legislator_id | SERIAL | PRIMARY KEY | |
| bioguide_id | VARCHAR(20) | UNIQUE, NOT NULL | Official ID |
| thomas_id | VARCHAR(20) | | THOMAS ID |
| govtrack_id | INTEGER | | GovTrack ID |
| opensecrets_id | VARCHAR(20) | | OpenSecrets ID |
| fec_id | VARCHAR(20) | | FEC ID |
| first_name | VARCHAR(100) | NOT NULL | |
| middle_name | VARCHAR(100) | | |
| last_name | VARCHAR(100) | NOT NULL | |
| suffix | VARCHAR(20) | | Jr., Sr., III |
| nickname | VARCHAR(100) | | |
| full_name | VARCHAR(300) | NOT NULL | Display name |
| party | ENUM | | Current party |
| state | CHAR(2) | | Current state |
| district | VARCHAR(10) | | House district |
| current_chamber | ENUM | | House or Senate |
| is_current_member | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| first_served | DATE | | |
| last_served | DATE | | |
| photo_url | VARCHAR(500) | | |
| official_website | VARCHAR(500) | | |
| birth_date | DATE | | |
| death_date | DATE | | |
| gender | CHAR(1) | | M, F |
| biography | TEXT | | |

---

## 5. Relationships and Foreign Keys

### Primary Relationships

| Parent Table | Child Table | FK Column | Relationship | ON DELETE |
|--------------|-------------|-----------|--------------|-----------|
| us_code_title | us_code_chapter | title_id | 1:N | CASCADE |
| us_code_title | us_code_section | title_id | 1:N | RESTRICT |
| us_code_chapter | us_code_section | chapter_id | 1:N | SET NULL |
| us_code_section | us_code_line | section_id | 1:N | CASCADE |
| us_code_section | section_history | section_id | 1:N | CASCADE |
| us_code_section | law_change | section_id | 1:N | RESTRICT |
| us_code_line | us_code_line | parent_line_id | Self-ref | SET NULL |
| us_code_line | line_history | line_id | 1:N | CASCADE |
| public_law | law_change | law_id | 1:N | CASCADE |
| public_law | section_history | law_id | 1:N | RESTRICT |
| public_law | us_code_line (created) | created_by_law_id | 1:N | SET NULL |
| public_law | us_code_line (modified) | last_modified_by_law_id | 1:N | SET NULL |
| public_law | us_code_line (codified) | codified_by_law_id | 1:N | SET NULL |
| public_law | sponsorship | law_id | 1:N | CASCADE |
| public_law | vote | law_id | 1:N | CASCADE |
| bill | public_law | bill_id | 1:1 | SET NULL |
| bill | proposed_change | bill_id | 1:N | CASCADE |
| bill | sponsorship | bill_id | 1:N | CASCADE |
| bill | vote | bill_id | 1:N | CASCADE |
| legislator | sponsorship | legislator_id | 1:N | RESTRICT |
| legislator | individual_vote | legislator_id | 1:N | RESTRICT |
| legislator | legislator_term | legislator_id | 1:N | CASCADE |
| vote | individual_vote | vote_id | 1:N | CASCADE |

### Many-to-Many Relationships

| Relationship | Junction Table | Columns |
|--------------|----------------|---------|
| Section <-> Section (cross-reference) | section_reference | source_section_id, target_section_id |
| Law <-> Legislator (sponsorship) | sponsorship | law_id, legislator_id |
| Law <-> Legislator (voting) | individual_vote (via vote) | vote_id, legislator_id |
| Bill <-> Committee | bill_committee_assignment | bill_id, committee_id |

### Constraint Definitions

```sql
-- Unique constraints
UNIQUE (title_id, section_number)              -- One section number per title
UNIQUE (title_id, chapter_number)              -- One chapter number per title
UNIQUE (congress, law_number)                  -- One law number per Congress
UNIQUE (congress, bill_number)                 -- One bill number per Congress
UNIQUE (section_id, line_number)               -- Ordered lines per section
UNIQUE (section_id, version_number)            -- Ordered history per section
UNIQUE (line_id, version_number)               -- Ordered history per line
UNIQUE (source_section_id, target_section_id, reference_type, source_subsection_path)

-- Check constraints
CHECK (congress >= 1 AND congress <= 200)
CHECK (depth_level >= 0)
CHECK (likelihood_score IS NULL OR (likelihood_score >= 0 AND likelihood_score <= 1))
CHECK ((is_positive_law = FALSE AND positive_law_date IS NULL) OR
       (is_positive_law = TRUE AND positive_law_date IS NOT NULL))
CHECK ((is_repealed = FALSE AND repealed_date IS NULL) OR
       (is_repealed = TRUE AND repealed_date IS NOT NULL))
CHECK (superseded_date IS NULL OR superseded_date > effective_date)
CHECK (source_section_id != target_section_id)  -- No self-references
CHECK ((law_id IS NOT NULL AND bill_id IS NULL) OR
       (law_id IS NULL AND bill_id IS NOT NULL))  -- XOR for sponsorship
```

---

## 6. Indexing Strategy

### 6.1 Index Categories

The indexing strategy is organized by query pattern to ensure optimal performance for each core feature:

#### A. Code Browsing Indexes

```sql
-- Navigate by title/chapter/section
CREATE INDEX idx_section_title ON us_code_section(title_id);
CREATE INDEX idx_section_chapter ON us_code_section(chapter_id);
CREATE INDEX idx_section_number ON us_code_section(title_id, section_number);
CREATE INDEX idx_section_citation ON us_code_section(full_citation);

-- Get active (non-repealed) sections only
CREATE INDEX idx_section_active ON us_code_section(is_repealed) WHERE is_repealed = FALSE;

-- Order chapters and sections
CREATE INDEX idx_chapter_sort ON us_code_chapter(title_id, sort_order);
CREATE INDEX idx_section_sort ON us_code_section(chapter_id, sort_order);
```

#### B. Blame View Indexes (CRITICAL)

```sql
-- Get all lines in a section, ordered
CREATE INDEX idx_line_section ON us_code_line(section_id);
CREATE INDEX idx_line_section_order ON us_code_line(section_id, line_number);

-- Current lines only (most queries)
CREATE INDEX idx_line_current ON us_code_line(section_id, is_current) WHERE is_current = TRUE;

-- Attribution lookups
CREATE INDEX idx_line_created_by ON us_code_line(created_by_law_id);
CREATE INDEX idx_line_modified_by ON us_code_line(last_modified_by_law_id);
CREATE INDEX idx_line_codified_by ON us_code_line(codified_by_law_id);

-- Tree traversal
CREATE INDEX idx_line_parent ON us_code_line(parent_line_id);
CREATE INDEX idx_line_depth ON us_code_line(section_id, depth_level);

-- Change detection
CREATE INDEX idx_line_hash ON us_code_line(text_hash);
```

#### C. Law Viewer Indexes

```sql
-- Find laws by number
CREATE INDEX idx_law_number ON public_law(congress, law_number);
CREATE INDEX idx_law_congress ON public_law(congress);

-- Chronological browsing
CREATE INDEX idx_law_enacted ON public_law(enacted_date DESC);
CREATE INDEX idx_law_effective ON public_law(effective_date);

-- Popular name lookup
CREATE INDEX idx_law_popular_name ON public_law(popular_name);

-- Get changes for a law
CREATE INDEX idx_change_law ON law_change(law_id);
CREATE INDEX idx_change_section ON law_change(section_id);
CREATE INDEX idx_change_law_section ON law_change(law_id, section_id);
```

#### D. Time Travel Indexes

```sql
-- Get section as of specific date
CREATE INDEX idx_history_section ON section_history(section_id);
CREATE INDEX idx_history_section_date ON section_history(section_id, effective_date DESC);
CREATE INDEX idx_history_version ON section_history(section_id, version_number);

-- Line-level time travel
CREATE INDEX idx_line_history_line ON line_history(line_id);
CREATE INDEX idx_line_history_line_date ON line_history(line_id, effective_date DESC);
CREATE INDEX idx_line_history_version ON line_history(line_id, version_number);
```

#### E. Search Indexes

```sql
-- Full-text search on sections
CREATE INDEX idx_section_text_search ON us_code_section
    USING gin(to_tsvector('english', COALESCE(heading, '') || ' ' || COALESCE(text_content, '')));

-- Full-text search on laws
CREATE INDEX idx_law_text_search ON public_law
    USING gin(to_tsvector('english',
        COALESCE(popular_name, '') || ' ' ||
        COALESCE(official_title, '') || ' ' ||
        COALESCE(summary, '')));

-- Full-text search on legislator names
CREATE INDEX idx_legislator_name_search ON legislator
    USING gin(to_tsvector('english', full_name));
```

#### F. Analytics Indexes

```sql
-- Legislator activity
CREATE INDEX idx_sponsorship_legislator ON sponsorship(legislator_id);
CREATE INDEX idx_sponsorship_sponsor ON sponsorship(law_id, role) WHERE role = 'Sponsor';
CREATE INDEX idx_individual_vote_legislator ON individual_vote(legislator_id);

-- Congressional productivity
CREATE INDEX idx_law_president ON public_law(president);
CREATE INDEX idx_vote_chamber ON vote(chamber);
CREATE INDEX idx_vote_date ON vote(vote_date DESC);
```

#### G. Dependency Graph Indexes

```sql
-- Find what a section references
CREATE INDEX idx_ref_source ON section_reference(source_section_id);

-- Find what references a section
CREATE INDEX idx_ref_target ON section_reference(target_section_id);

-- Filter by reference type
CREATE INDEX idx_ref_type ON section_reference(reference_type);
```

### 6.2 Index Performance Projections

| Query Pattern | Without Index | With Index | Index Used |
|---------------|---------------|------------|------------|
| Get section by citation | ~15,000 rows scanned | 1 row | idx_section_citation |
| Get lines for section (blame) | ~500,000 rows scanned | ~33 rows avg | idx_line_section_order |
| Get section history at date | ~75,000 rows scanned | 1 row | idx_history_section_date |
| Full-text search "copyright" | Sequential scan | <100ms | idx_section_text_search |
| Laws by Congress | ~5,000 rows scanned | ~50 rows | idx_law_congress |

### 6.3 Partial Indexes

Partial indexes are used to optimize common query patterns:

```sql
-- Only query active sections (99%+ of queries)
CREATE INDEX idx_section_active ON us_code_section(is_repealed) WHERE is_repealed = FALSE;

-- Only query current lines (99%+ of queries)
CREATE INDEX idx_line_current ON us_code_line(section_id, is_current) WHERE is_current = TRUE;

-- Only query current legislators
CREATE INDEX idx_legislator_current ON legislator(is_current_member) WHERE is_current_member = TRUE;

-- Only query active bills
CREATE INDEX idx_bill_pending ON bill(status)
    WHERE status NOT IN ('Became_Law', 'Failed', 'Vetoed', 'Died_in_Committee');
```

---

## 7. Temporal Data Strategy

### 7.1 Version Tables Approach

CWLB uses **version tables** to track historical data:

| Current State Table | History Table | Strategy |
|---------------------|---------------|----------|
| us_code_section | section_history | Full snapshot per version |
| us_code_line | line_history | Full snapshot per version |

### 7.2 Section History

Each time a law modifies a section, a new `section_history` record is created:

```sql
INSERT INTO section_history (
    section_id,
    law_id,
    version_number,
    text_content,
    heading,
    effective_date,
    superseded_date
) VALUES (
    123,                                    -- section being modified
    456,                                    -- law making the modification
    (SELECT COALESCE(MAX(version_number), 0) + 1
     FROM section_history WHERE section_id = 123),
    'Full text at this version...',
    'Section heading',
    '2020-01-01',                          -- when this version took effect
    NULL                                    -- superseded when next version created
);

-- Update previous version's superseded_date
UPDATE section_history
SET superseded_date = '2020-01-01'
WHERE section_id = 123
  AND superseded_date IS NULL
  AND version_number < (SELECT MAX(version_number) FROM section_history WHERE section_id = 123);
```

### 7.3 Time Travel Query

To get a section as it existed on a specific date:

```sql
-- Get section as of 1990-01-01
SELECT
    sh.text_content,
    sh.heading,
    sh.effective_date,
    pl.law_number,
    pl.popular_name
FROM section_history sh
JOIN public_law pl ON sh.law_id = pl.law_id
WHERE sh.section_id = ?
  AND sh.effective_date <= '1990-01-01'::DATE
ORDER BY sh.effective_date DESC
LIMIT 1;
```

### 7.4 Line-Level History

For detailed blame view history, each line modification creates a `line_history` record:

```sql
-- Get line as it existed on a specific date
SELECT
    lh.text_content,
    lh.subsection_path,
    pl.law_number,
    pl.popular_name
FROM line_history lh
JOIN public_law pl ON lh.modified_by_law_id = pl.law_id
WHERE lh.line_id = ?
  AND lh.effective_date <= '1990-01-01'::DATE
ORDER BY lh.effective_date DESC
LIMIT 1;
```

### 7.5 Effective Date vs Enacted Date

The schema distinguishes between:

- **enacted_date**: When the law was signed by the President
- **effective_date**: When the law's changes take effect

This is critical because some laws have delayed effective dates:

```sql
-- Example: Law enacted in December but effective January 1
INSERT INTO public_law (law_number, congress, enacted_date, effective_date)
VALUES ('117-100', 117, '2022-12-15', '2023-01-01');

-- The law_change records use effective_date, not enacted_date
INSERT INTO law_change (law_id, section_id, effective_date, ...)
VALUES (?, ?, '2023-01-01', ...);  -- Use effective_date
```

---

## 8. Scalability Analysis

### 8.1 Data Volume Projections

#### Phase 1 (MVP) - 8 Titles, 20 Years

| Table | Records | Avg Record Size | Total Size |
|-------|---------|-----------------|------------|
| us_code_section | 15,000 | 5 KB | 75 MB |
| us_code_line | 500,000 | 500 B | 250 MB |
| line_history | 2,000,000 | 500 B | 1 GB |
| section_history | 75,000 | 10 KB | 750 MB |
| public_law | 5,000 | 2 KB | 10 MB |
| law_change | 100,000 | 2 KB | 200 MB |
| legislator | 15,000 | 1 KB | 15 MB |
| individual_vote | 10,000,000 | 100 B | 1 GB |
| **TOTAL** | | | **~3.5 GB** |

#### Phase 2 - All 54 Titles, Full History

| Table | Records | Total Size |
|-------|---------|------------|
| us_code_section | 60,000 | 300 MB |
| us_code_line | 2,000,000 | 1 GB |
| line_history | 15,000,000 | 7.5 GB |
| section_history | 500,000 | 5 GB |
| public_law | 25,000 | 50 MB |
| law_change | 500,000 | 1 GB |
| individual_vote | 50,000,000 | 5 GB |
| **TOTAL** | | **~20 GB** |

### 8.2 Query Performance Analysis

#### Critical Query: Blame View for Section

```sql
-- Benchmark: Get all lines with attribution for 17 USC § 512
-- Expected rows: ~150 lines
-- Without indexes: ~2-5 seconds (full scan of 500K+ rows)
-- With indexes: <50ms
EXPLAIN ANALYZE
SELECT l.*, pl.law_number, pl.popular_name, pl.enacted_date
FROM us_code_line l
LEFT JOIN public_law pl ON l.last_modified_by_law_id = pl.law_id
WHERE l.section_id = 512 AND l.is_current = TRUE
ORDER BY l.line_number;
```

#### Critical Query: Time Travel

```sql
-- Benchmark: Get section as of specific date
-- Expected: 1 row from ~75K section_history rows
-- With index on (section_id, effective_date DESC): <10ms
EXPLAIN ANALYZE
SELECT * FROM section_history
WHERE section_id = 512 AND effective_date <= '1998-10-28'
ORDER BY effective_date DESC
LIMIT 1;
```

#### Critical Query: Full-Text Search

```sql
-- Benchmark: Search for "copyright infringement"
-- With GIN index: <100ms for top 20 results
EXPLAIN ANALYZE
SELECT section_id, full_citation, heading,
       ts_rank(to_tsvector('english', heading || ' ' || text_content),
               plainto_tsquery('english', 'copyright infringement')) as rank
FROM us_code_section
WHERE to_tsvector('english', heading || ' ' || text_content)
      @@ plainto_tsquery('english', 'copyright infringement')
ORDER BY rank DESC
LIMIT 20;
```

### 8.3 Scaling Strategies

#### Horizontal Scaling (Read Replicas)

For read-heavy workloads (code browsing, search):

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Read       │    │  Read       │    │  Primary    │
│  Replica 1  │    │  Replica 2  │    │  (Write)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

#### Table Partitioning (Future)

For very large tables, partition by date range:

```sql
-- Partition line_history by effective_date
CREATE TABLE line_history_2020_2024 PARTITION OF line_history
    FOR VALUES FROM ('2020-01-01') TO ('2025-01-01');

CREATE TABLE line_history_2015_2019 PARTITION OF line_history
    FOR VALUES FROM ('2015-01-01') TO ('2020-01-01');

CREATE TABLE line_history_archive PARTITION OF line_history
    FOR VALUES FROM (MINVALUE) TO ('2015-01-01');
```

### 8.4 Memory Requirements

#### Recommended PostgreSQL Configuration

```ini
# postgresql.conf for CWLB

# Memory
shared_buffers = 4GB           # 25% of RAM
effective_cache_size = 12GB    # 75% of RAM
work_mem = 256MB               # For complex queries
maintenance_work_mem = 1GB     # For VACUUM, CREATE INDEX

# Connection Pooling
max_connections = 200

# Query Planning
random_page_cost = 1.1         # For SSD storage
effective_io_concurrency = 200 # For SSD storage

# Write Performance
wal_buffers = 64MB
checkpoint_completion_target = 0.9
```

---

## 9. Migration Tooling Recommendation

### 9.1 Recommended Tool: Alembic (Python)

Given the project's Python-based prototypes and data pipeline, **Alembic** is recommended:

| Criteria | Alembic | Prisma | Flyway |
|----------|---------|--------|--------|
| Language | Python | Node.js | Java/Any |
| Learning curve | Medium | Low | Low |
| Flexibility | High | Medium | High |
| Raw SQL support | Excellent | Limited | Excellent |
| Python integration | Native | N/A | Requires wrapper |
| Complex migrations | Excellent | Limited | Good |

### 9.2 Project Structure

```
cwlb/
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_materialized_views.py
│       ├── 003_add_indexes.py
│       └── ...
├── models/
│   ├── __init__.py
│   ├── us_code.py
│   ├── public_law.py
│   ├── legislator.py
│   └── ...
└── database/
    ├── __init__.py
    ├── connection.py
    └── queries/
        ├── blame_view.py
        ├── time_travel.py
        └── search.py
```

### 9.3 Sample Migration

```python
# alembic/versions/001_initial_schema.py
"""Initial schema creation

Revision ID: 001
Create Date: 2026-01-23
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Read and execute the full schema SQL
    with open('prototypes/database_schema.sql', 'r') as f:
        schema_sql = f.read()

    # Split into individual statements and execute
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            op.execute(statement)

def downgrade():
    # Drop all tables in reverse order
    tables = [
        'data_correction', 'data_ingestion_log',
        'amendment', 'bill_committee_assignment', 'committee',
        'section_reference', 'individual_vote', 'vote',
        'sponsorship', 'legislator_term', 'legislator',
        'line_history', 'us_code_line',
        'proposed_change', 'law_change',
        'section_history', 'us_code_section',
        'us_code_chapter', 'us_code_title',
        'bill', 'public_law'
    ]

    for table in tables:
        op.drop_table(table)
```

### 9.4 Migration Commands

```bash
# Initialize Alembic
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Add new column"

# Run migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

---

## 10. Performance Optimization Strategies

### 10.1 Materialized Views

Three materialized views are defined for common aggregations:

```sql
-- 1. Section blame summary (refresh daily)
CREATE MATERIALIZED VIEW mv_section_blame_summary AS
SELECT
    s.section_id, s.full_citation, s.is_positive_law,
    COUNT(l.line_id) as total_lines,
    COUNT(DISTINCT l.last_modified_by_law_id) as unique_modifying_laws
FROM us_code_section s
LEFT JOIN us_code_line l ON s.section_id = l.section_id AND l.is_current = TRUE
WHERE s.is_repealed = FALSE
GROUP BY s.section_id;

-- 2. Law impact summary (refresh after data ingestion)
CREATE MATERIALIZED VIEW mv_law_impact_summary AS
SELECT
    pl.law_id, pl.congress, pl.enacted_date,
    COUNT(DISTINCT lc.section_id) as sections_affected
FROM public_law pl
LEFT JOIN law_change lc ON pl.law_id = lc.law_id
GROUP BY pl.law_id;

-- 3. Legislator activity (refresh daily)
CREATE MATERIALIZED VIEW mv_legislator_activity AS
SELECT
    l.legislator_id, l.full_name,
    COUNT(DISTINCT sp.law_id) FILTER (WHERE sp.role = 'Sponsor') as laws_sponsored
FROM legislator l
LEFT JOIN sponsorship sp ON l.legislator_id = sp.legislator_id
GROUP BY l.legislator_id;
```

Refresh strategy:
```sql
-- Refresh concurrently (no lock, requires unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_section_blame_summary;
```

### 10.2 Caching Strategy

#### Redis Cache Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Redis Cache (L1)                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ Section Text  │  │ Blame View    │  │ Law Metadata  │       │
│  │ TTL: 1 hour   │  │ TTL: 1 hour   │  │ TTL: 24 hours │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL (L2)                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                 Materialized Views                         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Cache Keys

```
# Section text
section:{section_id}:current
section:{section_id}:at:{date}

# Blame view
blame:{section_id}:current
blame:{section_id}:at:{date}

# Law metadata
law:{law_id}
law:congress:{congress}:laws

# Search results
search:sections:{query_hash}
search:laws:{query_hash}
```

### 10.3 Query Optimization Patterns

#### Pagination for Large Results

```sql
-- Use keyset pagination instead of OFFSET
-- Bad (slow for large offsets):
SELECT * FROM us_code_section ORDER BY section_id LIMIT 20 OFFSET 10000;

-- Good (consistent performance):
SELECT * FROM us_code_section
WHERE section_id > :last_seen_id
ORDER BY section_id
LIMIT 20;
```

#### Batch Loading for Blame View

```sql
-- Load all attribution data in one query instead of N+1
SELECT
    l.line_id,
    l.line_number,
    l.text_content,
    pl.law_number,
    pl.popular_name,
    pl.president,
    pl.enacted_date
FROM us_code_line l
LEFT JOIN public_law pl ON l.last_modified_by_law_id = pl.law_id
WHERE l.section_id = :section_id AND l.is_current = TRUE
ORDER BY l.line_number;
```

---

## 11. Implementation Checklist

### Phase 1 Database Setup

- [ ] **Task 1.2a**: Create PostgreSQL database instance
- [ ] **Task 1.2b**: Execute initial schema (`database_schema.sql`)
- [ ] **Task 1.2c**: Configure Alembic for migrations
- [ ] **Task 1.2d**: Set up connection pooling (pgBouncer or built-in)
- [ ] **Task 1.2e**: Configure PostgreSQL for performance (see Section 8.4)

### Data Pipeline Integration

- [ ] **Task 1.6**: Implement `us_code_section` ingestion
- [ ] **Task 1.7**: Implement `public_law` ingestion
- [ ] **Task 1.8**: Implement `legislator` ingestion
- [ ] **Task 1.13**: Implement `us_code_line` parsing
- [ ] **Task 1.15**: Implement attribution (blame) population

### Optimization (Post-MVP)

- [ ] **Task 2.25a**: Analyze query patterns from production
- [ ] **Task 2.25b**: Add missing indexes based on slow query log
- [ ] **Task 2.25c**: Tune materialized view refresh schedules
- [ ] **Task 2.25d**: Implement Redis caching layer
- [ ] **Task 2.27**: Configure CDN for API responses

### Monitoring Setup

- [ ] Set up `pg_stat_statements` for query analysis
- [ ] Configure slow query logging (> 100ms)
- [ ] Set up connection pool monitoring
- [ ] Configure disk space alerts
- [ ] Set up replication lag monitoring (if using replicas)

---

## Appendix A: ENUM Type Definitions

```sql
-- All custom ENUM types used in the schema

CREATE TYPE law_type AS ENUM ('Public', 'Private');

CREATE TYPE bill_type AS ENUM (
    'HR', 'S', 'HJRES', 'SJRES', 'HCONRES', 'SCONRES', 'HRES', 'SRES'
);

CREATE TYPE bill_status AS ENUM (
    'Introduced', 'In_Committee', 'Reported_by_Committee',
    'Passed_House', 'Passed_Senate', 'Resolving_Differences',
    'To_President', 'Became_Law', 'Failed', 'Vetoed',
    'Veto_Overridden', 'Pocket_Vetoed', 'Died_in_Committee', 'Withdrawn'
);

CREATE TYPE change_type AS ENUM (
    'Add', 'Delete', 'Modify', 'Repeal', 'Redesignate', 'Transfer'
);

CREATE TYPE line_type AS ENUM ('Heading', 'Prose', 'ListItem');

CREATE TYPE chamber AS ENUM ('House', 'Senate');

CREATE TYPE vote_type AS ENUM (
    'Yea', 'Nay', 'Present', 'Not_Voting', 'Paired_Yea', 'Paired_Nay'
);

CREATE TYPE sponsorship_role AS ENUM ('Sponsor', 'Cosponsor');

CREATE TYPE reference_type AS ENUM (
    'Explicit_Citation', 'Cross_Reference', 'Subject_To',
    'Conditional', 'Exception', 'Incorporation'
);

CREATE TYPE political_party AS ENUM (
    'Democrat', 'Republican', 'Independent', 'Libertarian', 'Green', 'Other'
);
```

---

## Appendix B: Sample Data

### Sample US Code Title

```sql
INSERT INTO us_code_title (title_number, title_name, is_positive_law, positive_law_date)
VALUES (17, 'Copyrights', TRUE, '1976-10-19');
```

### Sample Public Law

```sql
INSERT INTO public_law (
    law_number, congress, law_type, popular_name,
    enacted_date, effective_date, president, bill_number
) VALUES (
    '94-553', 94, 'Public', 'Copyright Act of 1976',
    '1976-10-19', '1978-01-01', 'Gerald Ford', 'S. 22'
);
```

### Sample US Code Line (Blame View)

```sql
INSERT INTO us_code_line (
    section_id, parent_line_id, line_number, line_type,
    text_content, subsection_path, depth_level,
    created_by_law_id, last_modified_by_law_id,
    effective_date
) VALUES (
    106,           -- section_id for 17 USC § 106
    NULL,          -- root line (no parent)
    1,             -- first line
    'Heading',
    '§ 106. Exclusive rights in copyrighted works',
    NULL,          -- no subsection path for heading
    0,             -- depth 0 (root)
    1,             -- created by PL 94-553
    1,             -- last modified by PL 94-553
    '1978-01-01'   -- effective date
);
```

---

## Summary

Task 0.11 delivers a comprehensive database schema that:

1. **Supports all core features**: Code browsing, law viewing, blame view, time travel, search, and analytics
2. **Handles complex relationships**: Tree structures for lines, cross-references between sections, many-to-many for sponsorship/voting
3. **Optimizes for key queries**: 85+ indexes covering all critical query patterns
4. **Scales appropriately**: Handles Phase 1 (~3.5 GB) and Phase 2 (~20 GB) with room to grow
5. **Enables temporal queries**: Version tables for both section and line-level time travel
6. **Supports positive law complexity**: Three-tier attribution (created, modified, codified) per line

The schema is ready for implementation in Task 1.2 (PostgreSQL database setup).
