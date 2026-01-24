-- ============================================================================
-- CWLB (The Code We Live By) - Database Schema
-- Version: 1.0.0
-- Task: 0.11 - Design Database Schema
--
-- This schema implements the data model defined in Section 6 of the CWLB
-- specification. It supports:
--   - US Code browsing with hierarchical structure
--   - Public Law tracking ("Merged PRs")
--   - Bill tracking ("Open/Closed PRs")
--   - Law change diffs
--   - Line-level attribution (blame view)
--   - Historical versioning (time travel)
--   - Legislator and voting data
--   - Cross-references between sections
--
-- Database: PostgreSQL 15+
-- ============================================================================

-- ============================================================================
-- EXTENSION REQUIREMENTS
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- For text similarity/search
CREATE EXTENSION IF NOT EXISTS "btree_gist";     -- For exclusion constraints

-- ============================================================================
-- CUSTOM TYPES (ENUMS)
-- ============================================================================

-- Law types: Public vs Private laws
CREATE TYPE law_type AS ENUM ('Public', 'Private');

-- Bill types: Originating chamber
CREATE TYPE bill_type AS ENUM (
    'HR',      -- House Bill
    'S',       -- Senate Bill
    'HJRES',   -- House Joint Resolution
    'SJRES',   -- Senate Joint Resolution
    'HCONRES', -- House Concurrent Resolution
    'SCONRES', -- Senate Concurrent Resolution
    'HRES',    -- House Simple Resolution
    'SRES'     -- Senate Simple Resolution
);

-- Bill status tracking
CREATE TYPE bill_status AS ENUM (
    'Introduced',
    'In_Committee',
    'Reported_by_Committee',
    'Passed_House',
    'Passed_Senate',
    'Resolving_Differences',
    'To_President',
    'Became_Law',
    'Failed',
    'Vetoed',
    'Veto_Overridden',
    'Pocket_Vetoed',
    'Died_in_Committee',
    'Withdrawn'
);

-- Change types for diffs
CREATE TYPE change_type AS ENUM (
    'Add',           -- New section/text added
    'Delete',        -- Section/text removed
    'Modify',        -- Existing text changed
    'Repeal',        -- Section formally repealed
    'Redesignate',   -- Section number changed
    'Transfer'       -- Section moved to different location
);

-- Line types in section structure
CREATE TYPE line_type AS ENUM (
    'Heading',       -- Section/subsection headings
    'Prose',         -- Regular paragraph text
    'ListItem'       -- Enumerated items (numbered, lettered)
);

-- Congressional chambers
CREATE TYPE chamber AS ENUM ('House', 'Senate');

-- Vote types
CREATE TYPE vote_type AS ENUM (
    'Yea',
    'Nay',
    'Present',
    'Not_Voting',
    'Paired_Yea',
    'Paired_Nay'
);

-- Sponsorship roles
CREATE TYPE sponsorship_role AS ENUM ('Sponsor', 'Cosponsor');

-- Reference types for cross-references
CREATE TYPE reference_type AS ENUM (
    'Explicit_Citation',    -- Direct citation (e.g., "pursuant to section 107")
    'Cross_Reference',      -- "See also" or "as defined in"
    'Subject_To',           -- "Subject to section X"
    'Conditional',          -- "If section X applies"
    'Exception',            -- "Except as provided in"
    'Incorporation'         -- "As amended by" or "as provided under"
);

-- Political parties (simplified)
CREATE TYPE political_party AS ENUM (
    'Democrat',
    'Republican',
    'Independent',
    'Libertarian',
    'Green',
    'Other'
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- USCodeTitle: Top-level organization of US Code
-- ----------------------------------------------------------------------------
CREATE TABLE us_code_title (
    title_id SERIAL PRIMARY KEY,
    title_number INTEGER NOT NULL UNIQUE,
    title_name VARCHAR(500) NOT NULL,
    is_positive_law BOOLEAN NOT NULL DEFAULT FALSE,
    positive_law_date DATE,                              -- When enacted as positive law (NULL if not)
    positive_law_citation VARCHAR(200),                  -- Public Law that enacted positive law
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_positive_law_date CHECK (
        (is_positive_law = FALSE AND positive_law_date IS NULL) OR
        (is_positive_law = TRUE AND positive_law_date IS NOT NULL)
    )
);

COMMENT ON TABLE us_code_title IS 'Top-level titles of the US Code (1-54)';
COMMENT ON COLUMN us_code_title.is_positive_law IS 'True if this title has been enacted as positive law by Congress';
COMMENT ON COLUMN us_code_title.positive_law_date IS 'Date the title was enacted as positive law';

-- ----------------------------------------------------------------------------
-- USCodeChapter: Chapter-level organization within titles
-- ----------------------------------------------------------------------------
CREATE TABLE us_code_chapter (
    chapter_id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL REFERENCES us_code_title(title_id) ON DELETE CASCADE,
    chapter_number VARCHAR(50) NOT NULL,                 -- Can be "1", "1A", "1-A", etc.
    chapter_name VARCHAR(500) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,               -- For proper ordering
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_chapter_per_title UNIQUE (title_id, chapter_number)
);

COMMENT ON TABLE us_code_chapter IS 'Chapters within US Code titles';

-- ----------------------------------------------------------------------------
-- USCodeSection: The fundamental unit of US Code
-- ----------------------------------------------------------------------------
CREATE TABLE us_code_section (
    section_id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL REFERENCES us_code_title(title_id),
    chapter_id INTEGER REFERENCES us_code_chapter(chapter_id),

    -- Section identifiers
    section_number VARCHAR(50) NOT NULL,                 -- e.g., "106", "512", "106A"
    heading VARCHAR(500) NOT NULL,                       -- e.g., "Exclusive rights in copyrighted works"
    full_citation VARCHAR(200) NOT NULL,                 -- e.g., "17 U.S.C. § 106"

    -- Current text (for quick access; line-level detail in us_code_line)
    text_content TEXT,

    -- Temporal data
    enacted_date DATE,                                   -- When section was originally created
    last_modified_date DATE,                             -- When section was last changed
    effective_date DATE,                                 -- Current effective date

    -- Positive law attribution
    is_positive_law BOOLEAN NOT NULL DEFAULT FALSE,      -- Inherited from title
    title_positive_law_date DATE,                        -- When title became positive law
    statutes_at_large_citation VARCHAR(200),             -- For non-positive law sections

    -- Status
    is_repealed BOOLEAN NOT NULL DEFAULT FALSE,
    repealed_date DATE,
    repealed_by_law_id INTEGER,                          -- FK added after public_law table

    -- Metadata
    notes TEXT,                                          -- Editorial notes
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_section_per_title UNIQUE (title_id, section_number),
    CONSTRAINT valid_repeal_data CHECK (
        (is_repealed = FALSE AND repealed_date IS NULL) OR
        (is_repealed = TRUE AND repealed_date IS NOT NULL)
    )
);

COMMENT ON TABLE us_code_section IS 'Individual sections of US Code - the fundamental unit of law';
COMMENT ON COLUMN us_code_section.is_positive_law IS 'Whether this section is part of a positive law title';
COMMENT ON COLUMN us_code_section.statutes_at_large_citation IS 'Authoritative source citation for non-positive law sections';

-- ----------------------------------------------------------------------------
-- PublicLaw: Enacted legislation ("Merged Pull Requests")
-- ----------------------------------------------------------------------------
CREATE TABLE public_law (
    law_id SERIAL PRIMARY KEY,

    -- Law identifiers
    law_number VARCHAR(20) NOT NULL,                     -- e.g., "94-553"
    congress INTEGER NOT NULL,                           -- e.g., 94
    law_type law_type NOT NULL DEFAULT 'Public',

    -- Names
    popular_name VARCHAR(500),                           -- e.g., "Copyright Act of 1976"
    official_title TEXT,                                 -- Full official title
    short_title VARCHAR(500),                            -- Short title if different

    -- Summary
    summary TEXT,
    purpose TEXT,

    -- Bill origin
    bill_number VARCHAR(50),                             -- e.g., "S. 22", "H.R. 1234"
    bill_id INTEGER,                                     -- FK added after bill table

    -- Timeline
    introduced_date DATE,
    house_passed_date DATE,
    senate_passed_date DATE,
    presented_to_president_date DATE,
    enacted_date DATE NOT NULL,
    effective_date DATE,                                 -- May differ from enacted_date

    -- Presidential action
    president VARCHAR(100),                              -- President who signed
    presidential_action VARCHAR(50) DEFAULT 'Signed',    -- Signed, Veto_Overridden, etc.
    veto_date DATE,
    veto_override_date DATE,

    -- Impact metrics (computed)
    sections_affected INTEGER DEFAULT 0,
    sections_added INTEGER DEFAULT 0,
    sections_modified INTEGER DEFAULT 0,
    sections_repealed INTEGER DEFAULT 0,

    -- External references
    govinfo_url VARCHAR(500),                            -- Link to GovInfo.gov
    congress_url VARCHAR(500),                           -- Link to Congress.gov
    statutes_at_large_citation VARCHAR(200),             -- e.g., "90 Stat. 2541"

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_law_number UNIQUE (congress, law_number),
    CONSTRAINT valid_congress CHECK (congress >= 1 AND congress <= 200)
);

COMMENT ON TABLE public_law IS 'Enacted Public Laws - equivalent to merged pull requests';
COMMENT ON COLUMN public_law.law_number IS 'Public Law number (e.g., "94-553" for PL 94-553)';
COMMENT ON COLUMN public_law.effective_date IS 'When the law takes effect (may differ from enactment)';

-- Add FK for repealed_by in us_code_section
ALTER TABLE us_code_section
    ADD CONSTRAINT fk_repealed_by_law
    FOREIGN KEY (repealed_by_law_id)
    REFERENCES public_law(law_id);

-- ----------------------------------------------------------------------------
-- Bill: Proposed legislation ("Open/Closed Pull Requests")
-- ----------------------------------------------------------------------------
CREATE TABLE bill (
    bill_id SERIAL PRIMARY KEY,

    -- Bill identifiers
    bill_number VARCHAR(50) NOT NULL,                    -- e.g., "H.R. 1234", "S. 567"
    congress INTEGER NOT NULL,
    bill_type bill_type NOT NULL,

    -- Names
    popular_name VARCHAR(500),
    official_title TEXT,
    short_title VARCHAR(500),

    -- Summary
    summary TEXT,
    purpose TEXT,

    -- Status tracking
    status bill_status NOT NULL DEFAULT 'Introduced',
    current_chamber chamber,
    current_committee VARCHAR(200),

    -- Timeline
    introduced_date DATE NOT NULL,
    last_action_date DATE,
    last_action_description TEXT,

    -- Outcome
    became_law BOOLEAN NOT NULL DEFAULT FALSE,
    related_law_id INTEGER REFERENCES public_law(law_id),  -- If enacted
    failed_date DATE,
    failure_reason TEXT,

    -- Predictions (optional)
    likelihood_score NUMERIC(5,4),                       -- 0.0000 to 1.0000
    likelihood_updated_at TIMESTAMP WITH TIME ZONE,

    -- External references
    congress_url VARCHAR(500),
    govtrack_url VARCHAR(500),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_bill_number UNIQUE (congress, bill_number),
    CONSTRAINT valid_likelihood CHECK (likelihood_score IS NULL OR (likelihood_score >= 0 AND likelihood_score <= 1))
);

COMMENT ON TABLE bill IS 'Bills under consideration - equivalent to open/closed pull requests';
COMMENT ON COLUMN bill.likelihood_score IS 'Predicted probability of passage (ML-based, optional)';

-- Add FK for bill_id in public_law
ALTER TABLE public_law
    ADD CONSTRAINT fk_origin_bill
    FOREIGN KEY (bill_id)
    REFERENCES bill(bill_id);

-- ----------------------------------------------------------------------------
-- LawChange: Diffs for enacted laws
-- ----------------------------------------------------------------------------
CREATE TABLE law_change (
    change_id SERIAL PRIMARY KEY,
    law_id INTEGER NOT NULL REFERENCES public_law(law_id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES us_code_section(section_id),

    -- Change details
    change_type change_type NOT NULL,
    change_description TEXT,                             -- Human-readable description

    -- Text diffs
    old_text TEXT,                                       -- Original text (NULL for Add)
    new_text TEXT,                                       -- New text (NULL for Delete/Repeal)

    -- Location within section
    line_number_start INTEGER,
    line_number_end INTEGER,
    subsection_path VARCHAR(100),                        -- e.g., "(c)(1)(A)"

    -- Effective date (may differ from law's enacted_date)
    effective_date DATE NOT NULL,

    -- Parsing metadata
    parsed_automatically BOOLEAN DEFAULT TRUE,
    manually_reviewed BOOLEAN DEFAULT FALSE,
    reviewer_notes TEXT,
    confidence_score NUMERIC(5,4),                       -- Parser confidence

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE law_change IS 'Individual changes made by laws to US Code sections';
COMMENT ON COLUMN law_change.subsection_path IS 'Path to affected subsection (e.g., "(c)(1)(A)")';

-- ----------------------------------------------------------------------------
-- ProposedChange: Diffs for bills (not yet enacted)
-- ----------------------------------------------------------------------------
CREATE TABLE proposed_change (
    proposed_change_id SERIAL PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES bill(bill_id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES us_code_section(section_id),  -- NULL for new sections

    -- Change details
    change_type change_type NOT NULL,
    change_description TEXT,

    -- Text diffs
    current_text TEXT,                                   -- Current US Code text
    proposed_text TEXT,                                  -- What it would become

    -- Location
    line_number_start INTEGER,
    line_number_end INTEGER,
    subsection_path VARCHAR(100),

    -- For new sections
    proposed_section_number VARCHAR(50),
    proposed_title_id INTEGER REFERENCES us_code_title(title_id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE proposed_change IS 'Proposed changes from bills not yet enacted';

-- ----------------------------------------------------------------------------
-- SectionHistory: Historical versions of sections
-- ----------------------------------------------------------------------------
CREATE TABLE section_history (
    history_id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES us_code_section(section_id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES public_law(law_id),

    -- Version tracking
    version_number INTEGER NOT NULL,                     -- 1, 2, 3...

    -- Full text at this version
    text_content TEXT NOT NULL,
    heading VARCHAR(500),

    -- Temporal data
    effective_date DATE NOT NULL,
    superseded_date DATE,                                -- When next version took effect

    -- Change summary
    change_summary TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_section_version UNIQUE (section_id, version_number),
    CONSTRAINT valid_version_dates CHECK (
        superseded_date IS NULL OR superseded_date > effective_date
    )
);

COMMENT ON TABLE section_history IS 'Historical versions of sections for time travel feature';

-- ============================================================================
-- LINE-LEVEL TABLES (For Blame View)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- USCodeLine: Fine-grained line structure with parent/child tree
-- ----------------------------------------------------------------------------
CREATE TABLE us_code_line (
    line_id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES us_code_section(section_id) ON DELETE CASCADE,

    -- Tree structure
    parent_line_id INTEGER REFERENCES us_code_line(line_id),
    line_number INTEGER NOT NULL,                        -- Sequential within section (1, 2, 3...)

    -- Line content
    line_type line_type NOT NULL,
    text_content TEXT NOT NULL,

    -- Subsection identification
    subsection_path VARCHAR(100),                        -- e.g., "(c)(1)(A)(ii)"
    depth_level INTEGER NOT NULL DEFAULT 0,              -- 0=root, 1=child of root, etc.

    -- Attribution (blame view)
    created_by_law_id INTEGER REFERENCES public_law(law_id),
    last_modified_by_law_id INTEGER REFERENCES public_law(law_id),
    codified_by_law_id INTEGER REFERENCES public_law(law_id),  -- For positive law titles

    -- Temporal data
    effective_date DATE NOT NULL,
    codification_date DATE,                              -- When line became positive law

    -- Change detection
    text_hash VARCHAR(64) NOT NULL,                      -- SHA-256 of text_content

    -- Status
    is_current BOOLEAN NOT NULL DEFAULT TRUE,            -- False for superseded lines

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_line_in_section UNIQUE (section_id, line_number),
    CONSTRAINT valid_depth CHECK (depth_level >= 0),
    CONSTRAINT valid_parent CHECK (
        (parent_line_id IS NULL AND depth_level = 0) OR
        (parent_line_id IS NOT NULL AND depth_level > 0)
    )
);

COMMENT ON TABLE us_code_line IS 'Line-level structure of sections for blame view';
COMMENT ON COLUMN us_code_line.parent_line_id IS 'Parent line (NULL for root/section heading)';
COMMENT ON COLUMN us_code_line.subsection_path IS 'Path notation like (c)(1)(A)(ii)';
COMMENT ON COLUMN us_code_line.created_by_law_id IS 'Law that originally created this line';
COMMENT ON COLUMN us_code_line.last_modified_by_law_id IS 'Law that last modified this line';
COMMENT ON COLUMN us_code_line.codified_by_law_id IS 'Positive law enactment that codified this line';
COMMENT ON COLUMN us_code_line.text_hash IS 'SHA-256 hash for change detection';

-- ----------------------------------------------------------------------------
-- LineHistory: Historical versions of individual lines
-- ----------------------------------------------------------------------------
CREATE TABLE line_history (
    line_history_id SERIAL PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES us_code_line(line_id) ON DELETE CASCADE,

    -- Version tracking
    version_number INTEGER NOT NULL,

    -- Historical content
    text_content TEXT NOT NULL,
    text_hash VARCHAR(64) NOT NULL,

    -- Attribution at this version
    modified_by_law_id INTEGER NOT NULL REFERENCES public_law(law_id),

    -- Tree structure at this version (may differ from current)
    parent_line_id INTEGER,
    subsection_path VARCHAR(100),
    depth_level INTEGER,

    -- Temporal data
    effective_date DATE NOT NULL,
    superseded_date DATE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_line_version UNIQUE (line_id, version_number)
);

COMMENT ON TABLE line_history IS 'Historical versions of individual lines for detailed time travel';

-- ============================================================================
-- LEGISLATOR TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Legislator: Congress members
-- ----------------------------------------------------------------------------
CREATE TABLE legislator (
    legislator_id SERIAL PRIMARY KEY,

    -- Official identifiers
    bioguide_id VARCHAR(20) UNIQUE NOT NULL,             -- Official Biographical Directory ID
    thomas_id VARCHAR(20),                               -- Library of Congress THOMAS ID
    govtrack_id INTEGER,                                 -- GovTrack.us ID
    opensecrets_id VARCHAR(20),                          -- OpenSecrets.org ID
    fec_id VARCHAR(20),                                  -- FEC candidate ID

    -- Personal info
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    suffix VARCHAR(20),                                  -- Jr., Sr., III, etc.
    nickname VARCHAR(100),
    full_name VARCHAR(300) NOT NULL,                     -- Computed/stored for display

    -- Current status
    party political_party,
    state CHAR(2),                                       -- State abbreviation
    district VARCHAR(10),                                -- House district (NULL for Senators)
    current_chamber chamber,
    is_current_member BOOLEAN NOT NULL DEFAULT FALSE,

    -- Service dates
    first_served DATE,
    last_served DATE,

    -- Media
    photo_url VARCHAR(500),
    official_website VARCHAR(500),

    -- Biography
    birth_date DATE,
    death_date DATE,
    gender CHAR(1),                                      -- M, F, or NULL
    biography TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE legislator IS 'Members of Congress (current and historical)';
COMMENT ON COLUMN legislator.bioguide_id IS 'Official Congressional Biographical Directory ID';

-- ----------------------------------------------------------------------------
-- LegislatorTerm: Individual terms served
-- ----------------------------------------------------------------------------
CREATE TABLE legislator_term (
    term_id SERIAL PRIMARY KEY,
    legislator_id INTEGER NOT NULL REFERENCES legislator(legislator_id) ON DELETE CASCADE,

    -- Term details
    chamber chamber NOT NULL,
    state CHAR(2) NOT NULL,
    district VARCHAR(10),
    party political_party NOT NULL,

    -- Congress numbers covered
    congress_start INTEGER NOT NULL,
    congress_end INTEGER NOT NULL,

    -- Dates
    start_date DATE NOT NULL,
    end_date DATE,                                       -- NULL if current

    -- Leadership positions (if any)
    leadership_positions TEXT[],                         -- Array of positions held
    committee_assignments TEXT[],                        -- Array of committees

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_congress_range CHECK (congress_end >= congress_start)
);

COMMENT ON TABLE legislator_term IS 'Individual terms served by legislators';

-- ----------------------------------------------------------------------------
-- Sponsorship: Law sponsors and co-sponsors
-- ----------------------------------------------------------------------------
CREATE TABLE sponsorship (
    sponsorship_id SERIAL PRIMARY KEY,
    law_id INTEGER REFERENCES public_law(law_id) ON DELETE CASCADE,
    bill_id INTEGER REFERENCES bill(bill_id) ON DELETE CASCADE,
    legislator_id INTEGER NOT NULL REFERENCES legislator(legislator_id),

    -- Role
    role sponsorship_role NOT NULL,
    sponsored_date DATE,
    withdrawn_date DATE,                                 -- If co-sponsor withdrew

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT law_or_bill CHECK (
        (law_id IS NOT NULL AND bill_id IS NULL) OR
        (law_id IS NULL AND bill_id IS NOT NULL)
    ),
    CONSTRAINT unique_sponsorship_law UNIQUE (law_id, legislator_id, role),
    CONSTRAINT unique_sponsorship_bill UNIQUE (bill_id, legislator_id, role)
);

COMMENT ON TABLE sponsorship IS 'Sponsors and co-sponsors of laws and bills';

-- ----------------------------------------------------------------------------
-- Vote: Voting records
-- ----------------------------------------------------------------------------
CREATE TABLE vote (
    vote_id SERIAL PRIMARY KEY,

    -- What was voted on
    law_id INTEGER REFERENCES public_law(law_id) ON DELETE CASCADE,
    bill_id INTEGER REFERENCES bill(bill_id) ON DELETE CASCADE,

    -- Vote session info
    chamber chamber NOT NULL,
    vote_date DATE NOT NULL,
    vote_number INTEGER,                                 -- Roll call number
    congress INTEGER NOT NULL,
    session INTEGER,                                     -- 1 or 2

    -- Vote description
    vote_question TEXT,                                  -- e.g., "On Passage"
    vote_result VARCHAR(50),                             -- e.g., "Passed", "Failed"

    -- Aggregate counts
    yea_count INTEGER,
    nay_count INTEGER,
    present_count INTEGER,
    not_voting_count INTEGER,

    -- Required threshold
    required_majority VARCHAR(50),                       -- e.g., "1/2", "2/3", "3/5"

    -- External references
    congress_url VARCHAR(500),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT law_or_bill_vote CHECK (
        (law_id IS NOT NULL) OR (bill_id IS NOT NULL)
    )
);

COMMENT ON TABLE vote IS 'Aggregate vote information for laws and bills';

-- ----------------------------------------------------------------------------
-- IndividualVote: How each legislator voted
-- ----------------------------------------------------------------------------
CREATE TABLE individual_vote (
    individual_vote_id SERIAL PRIMARY KEY,
    vote_id INTEGER NOT NULL REFERENCES vote(vote_id) ON DELETE CASCADE,
    legislator_id INTEGER NOT NULL REFERENCES legislator(legislator_id),

    -- How they voted
    vote_cast vote_type NOT NULL,

    -- Pairing info (if paired)
    paired_with_legislator_id INTEGER REFERENCES legislator(legislator_id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_individual_vote UNIQUE (vote_id, legislator_id)
);

COMMENT ON TABLE individual_vote IS 'Individual legislator votes on laws and bills';

-- ============================================================================
-- CROSS-REFERENCE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- SectionReference: Cross-references between sections (dependency graph)
-- ----------------------------------------------------------------------------
CREATE TABLE section_reference (
    reference_id SERIAL PRIMARY KEY,
    source_section_id INTEGER NOT NULL REFERENCES us_code_section(section_id) ON DELETE CASCADE,
    target_section_id INTEGER NOT NULL REFERENCES us_code_section(section_id) ON DELETE CASCADE,

    -- Reference details
    reference_type reference_type NOT NULL,
    reference_text TEXT,                                 -- The actual text making the reference

    -- Location in source
    source_line_id INTEGER REFERENCES us_code_line(line_id),
    source_subsection_path VARCHAR(100),

    -- Discovery metadata
    discovered_date DATE NOT NULL DEFAULT CURRENT_DATE,
    discovered_method VARCHAR(50),                       -- 'automated', 'manual', etc.
    confidence_score NUMERIC(5,4),                       -- Parser confidence

    -- Status
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_date DATE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT no_self_reference CHECK (source_section_id != target_section_id),
    CONSTRAINT unique_reference UNIQUE (source_section_id, target_section_id, reference_type, source_subsection_path)
);

COMMENT ON TABLE section_reference IS 'Cross-references between US Code sections for dependency graph';
COMMENT ON COLUMN section_reference.source_section_id IS 'Section containing the reference';
COMMENT ON COLUMN section_reference.target_section_id IS 'Section being referenced';

-- ============================================================================
-- SUPPORTING TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Committee: Congressional committees
-- ----------------------------------------------------------------------------
CREATE TABLE committee (
    committee_id SERIAL PRIMARY KEY,
    chamber chamber NOT NULL,
    committee_code VARCHAR(20) NOT NULL,                 -- e.g., "HSJU", "SSJU"
    committee_name VARCHAR(200) NOT NULL,
    parent_committee_id INTEGER REFERENCES committee(committee_id),  -- For subcommittees
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    jurisdiction TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_committee_code UNIQUE (committee_code)
);

COMMENT ON TABLE committee IS 'Congressional committees and subcommittees';

-- ----------------------------------------------------------------------------
-- BillCommitteeAssignment: Bills assigned to committees
-- ----------------------------------------------------------------------------
CREATE TABLE bill_committee_assignment (
    assignment_id SERIAL PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES bill(bill_id) ON DELETE CASCADE,
    committee_id INTEGER NOT NULL REFERENCES committee(committee_id),

    assigned_date DATE NOT NULL,
    discharged_date DATE,                                -- If discharged from committee
    reported_date DATE,                                  -- If reported out
    report_number VARCHAR(50),                           -- Committee report number

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_bill_committee UNIQUE (bill_id, committee_id)
);

COMMENT ON TABLE bill_committee_assignment IS 'Committee assignments for bills';

-- ----------------------------------------------------------------------------
-- Amendment: Amendments to bills
-- ----------------------------------------------------------------------------
CREATE TABLE amendment (
    amendment_id SERIAL PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES bill(bill_id) ON DELETE CASCADE,

    -- Amendment identifiers
    amendment_number VARCHAR(50) NOT NULL,               -- e.g., "H.AMDT.123"
    chamber chamber NOT NULL,

    -- Sponsor
    sponsor_legislator_id INTEGER REFERENCES legislator(legislator_id),

    -- Content
    purpose TEXT,
    description TEXT,

    -- Status
    offered_date DATE,
    status VARCHAR(50),                                  -- Agreed, Rejected, Withdrawn, etc.
    agreed_date DATE,

    -- If rolled into another amendment
    rolled_into_amendment_id INTEGER REFERENCES amendment(amendment_id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE amendment IS 'Amendments proposed to bills';

-- ============================================================================
-- AUDIT AND METADATA TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DataIngestionLog: Track data pipeline runs
-- ----------------------------------------------------------------------------
CREATE TABLE data_ingestion_log (
    log_id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,                        -- 'govinfo', 'congress_api', 'olrc', etc.
    ingestion_type VARCHAR(50) NOT NULL,                 -- 'full', 'incremental', 'correction'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'running',       -- running, completed, failed
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB                                       -- Additional run details
);

COMMENT ON TABLE data_ingestion_log IS 'Log of data pipeline ingestion runs';

-- ----------------------------------------------------------------------------
-- DataCorrection: Track manual corrections to parsed data
-- ----------------------------------------------------------------------------
CREATE TABLE data_correction (
    correction_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    correction_reason TEXT,
    corrected_by VARCHAR(100),
    corrected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE data_correction IS 'Audit trail of manual data corrections';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- US Code Title indexes
CREATE INDEX idx_title_number ON us_code_title(title_number);
CREATE INDEX idx_title_positive_law ON us_code_title(is_positive_law);

-- US Code Chapter indexes
CREATE INDEX idx_chapter_title ON us_code_chapter(title_id);
CREATE INDEX idx_chapter_sort ON us_code_chapter(title_id, sort_order);

-- US Code Section indexes (CRITICAL for code browsing)
CREATE INDEX idx_section_title ON us_code_section(title_id);
CREATE INDEX idx_section_chapter ON us_code_section(chapter_id);
CREATE INDEX idx_section_number ON us_code_section(title_id, section_number);
CREATE INDEX idx_section_citation ON us_code_section(full_citation);
CREATE INDEX idx_section_modified ON us_code_section(last_modified_date DESC);
CREATE INDEX idx_section_positive_law ON us_code_section(is_positive_law);
CREATE INDEX idx_section_active ON us_code_section(is_repealed) WHERE is_repealed = FALSE;

-- Full-text search on sections
CREATE INDEX idx_section_text_search ON us_code_section
    USING gin(to_tsvector('english', COALESCE(heading, '') || ' ' || COALESCE(text_content, '')));

-- Public Law indexes (CRITICAL for law viewing)
CREATE INDEX idx_law_number ON public_law(congress, law_number);
CREATE INDEX idx_law_congress ON public_law(congress);
CREATE INDEX idx_law_enacted ON public_law(enacted_date DESC);
CREATE INDEX idx_law_effective ON public_law(effective_date);
CREATE INDEX idx_law_popular_name ON public_law(popular_name);
CREATE INDEX idx_law_president ON public_law(president);

-- Full-text search on laws
CREATE INDEX idx_law_text_search ON public_law
    USING gin(to_tsvector('english',
        COALESCE(popular_name, '') || ' ' ||
        COALESCE(official_title, '') || ' ' ||
        COALESCE(summary, '')));

-- Bill indexes
CREATE INDEX idx_bill_number ON bill(congress, bill_number);
CREATE INDEX idx_bill_congress ON bill(congress);
CREATE INDEX idx_bill_status ON bill(status);
CREATE INDEX idx_bill_introduced ON bill(introduced_date DESC);
CREATE INDEX idx_bill_pending ON bill(status) WHERE status NOT IN ('Became_Law', 'Failed', 'Vetoed', 'Died_in_Committee');

-- Law Change indexes (CRITICAL for diff view)
CREATE INDEX idx_change_law ON law_change(law_id);
CREATE INDEX idx_change_section ON law_change(section_id);
CREATE INDEX idx_change_law_section ON law_change(law_id, section_id);
CREATE INDEX idx_change_effective ON law_change(effective_date);
CREATE INDEX idx_change_type ON law_change(change_type);

-- Section History indexes (CRITICAL for time travel)
CREATE INDEX idx_history_section ON section_history(section_id);
CREATE INDEX idx_history_section_date ON section_history(section_id, effective_date DESC);
CREATE INDEX idx_history_law ON section_history(law_id);
CREATE INDEX idx_history_version ON section_history(section_id, version_number);

-- US Code Line indexes (CRITICAL for blame view)
CREATE INDEX idx_line_section ON us_code_line(section_id);
CREATE INDEX idx_line_section_order ON us_code_line(section_id, line_number);
CREATE INDEX idx_line_parent ON us_code_line(parent_line_id);
CREATE INDEX idx_line_path ON us_code_line(subsection_path);
CREATE INDEX idx_line_created_by ON us_code_line(created_by_law_id);
CREATE INDEX idx_line_modified_by ON us_code_line(last_modified_by_law_id);
CREATE INDEX idx_line_codified_by ON us_code_line(codified_by_law_id);
CREATE INDEX idx_line_hash ON us_code_line(text_hash);
CREATE INDEX idx_line_current ON us_code_line(section_id, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_line_depth ON us_code_line(section_id, depth_level);

-- Line History indexes (for detailed time travel)
CREATE INDEX idx_line_history_line ON line_history(line_id);
CREATE INDEX idx_line_history_line_date ON line_history(line_id, effective_date DESC);
CREATE INDEX idx_line_history_law ON line_history(modified_by_law_id);
CREATE INDEX idx_line_history_version ON line_history(line_id, version_number);

-- Legislator indexes
CREATE INDEX idx_legislator_bioguide ON legislator(bioguide_id);
CREATE INDEX idx_legislator_name ON legislator(last_name, first_name);
CREATE INDEX idx_legislator_state ON legislator(state);
CREATE INDEX idx_legislator_party ON legislator(party);
CREATE INDEX idx_legislator_current ON legislator(is_current_member) WHERE is_current_member = TRUE;

-- Full-text search on legislators
CREATE INDEX idx_legislator_name_search ON legislator
    USING gin(to_tsvector('english', full_name));

-- Legislator Term indexes
CREATE INDEX idx_term_legislator ON legislator_term(legislator_id);
CREATE INDEX idx_term_congress ON legislator_term(congress_start, congress_end);
CREATE INDEX idx_term_chamber_state ON legislator_term(chamber, state);

-- Sponsorship indexes
CREATE INDEX idx_sponsorship_law ON sponsorship(law_id);
CREATE INDEX idx_sponsorship_bill ON sponsorship(bill_id);
CREATE INDEX idx_sponsorship_legislator ON sponsorship(legislator_id);
CREATE INDEX idx_sponsorship_sponsor ON sponsorship(law_id, role) WHERE role = 'Sponsor';

-- Vote indexes
CREATE INDEX idx_vote_law ON vote(law_id);
CREATE INDEX idx_vote_bill ON vote(bill_id);
CREATE INDEX idx_vote_date ON vote(vote_date DESC);
CREATE INDEX idx_vote_chamber ON vote(chamber);

-- Individual Vote indexes
CREATE INDEX idx_individual_vote_vote ON individual_vote(vote_id);
CREATE INDEX idx_individual_vote_legislator ON individual_vote(legislator_id);
CREATE INDEX idx_individual_vote_cast ON individual_vote(vote_id, vote_cast);

-- Section Reference indexes (for dependency graph)
CREATE INDEX idx_ref_source ON section_reference(source_section_id);
CREATE INDEX idx_ref_target ON section_reference(target_section_id);
CREATE INDEX idx_ref_type ON section_reference(reference_type);
CREATE INDEX idx_ref_verified ON section_reference(is_verified);

-- Committee indexes
CREATE INDEX idx_committee_chamber ON committee(chamber);
CREATE INDEX idx_committee_active ON committee(is_active) WHERE is_active = TRUE;

-- Bill Committee Assignment indexes
CREATE INDEX idx_bill_committee_bill ON bill_committee_assignment(bill_id);
CREATE INDEX idx_bill_committee_committee ON bill_committee_assignment(committee_id);

-- Amendment indexes
CREATE INDEX idx_amendment_bill ON amendment(bill_id);
CREATE INDEX idx_amendment_sponsor ON amendment(sponsor_legislator_id);

-- Data Ingestion Log indexes
CREATE INDEX idx_ingestion_source ON data_ingestion_log(source);
CREATE INDEX idx_ingestion_status ON data_ingestion_log(status);
CREATE INDEX idx_ingestion_date ON data_ingestion_log(started_at DESC);

-- ============================================================================
-- MATERIALIZED VIEWS (for performance optimization)
-- ============================================================================

-- Materialized view for section blame summary
CREATE MATERIALIZED VIEW mv_section_blame_summary AS
SELECT
    s.section_id,
    s.title_id,
    s.section_number,
    s.heading,
    s.full_citation,
    s.is_positive_law,
    COUNT(l.line_id) as total_lines,
    COUNT(DISTINCT l.last_modified_by_law_id) as unique_modifying_laws,
    MIN(pl.enacted_date) as oldest_line_date,
    MAX(pl.enacted_date) as newest_line_date
FROM us_code_section s
LEFT JOIN us_code_line l ON s.section_id = l.section_id AND l.is_current = TRUE
LEFT JOIN public_law pl ON l.last_modified_by_law_id = pl.law_id
WHERE s.is_repealed = FALSE
GROUP BY s.section_id, s.title_id, s.section_number, s.heading, s.full_citation, s.is_positive_law;

CREATE UNIQUE INDEX idx_mv_blame_section ON mv_section_blame_summary(section_id);
CREATE INDEX idx_mv_blame_title ON mv_section_blame_summary(title_id);
CREATE INDEX idx_mv_blame_citation ON mv_section_blame_summary(full_citation);

-- Materialized view for law impact summary
CREATE MATERIALIZED VIEW mv_law_impact_summary AS
SELECT
    pl.law_id,
    pl.law_number,
    pl.congress,
    pl.popular_name,
    pl.enacted_date,
    COUNT(DISTINCT lc.section_id) as sections_affected,
    SUM(CASE WHEN lc.change_type = 'Add' THEN 1 ELSE 0 END) as sections_added,
    SUM(CASE WHEN lc.change_type = 'Modify' THEN 1 ELSE 0 END) as sections_modified,
    SUM(CASE WHEN lc.change_type IN ('Delete', 'Repeal') THEN 1 ELSE 0 END) as sections_removed,
    COUNT(DISTINCT s.title_id) as titles_affected
FROM public_law pl
LEFT JOIN law_change lc ON pl.law_id = lc.law_id
LEFT JOIN us_code_section s ON lc.section_id = s.section_id
GROUP BY pl.law_id, pl.law_number, pl.congress, pl.popular_name, pl.enacted_date;

CREATE UNIQUE INDEX idx_mv_impact_law ON mv_law_impact_summary(law_id);
CREATE INDEX idx_mv_impact_congress ON mv_law_impact_summary(congress);
CREATE INDEX idx_mv_impact_date ON mv_law_impact_summary(enacted_date DESC);

-- Materialized view for legislator activity
CREATE MATERIALIZED VIEW mv_legislator_activity AS
SELECT
    l.legislator_id,
    l.full_name,
    l.party,
    l.state,
    COUNT(DISTINCT CASE WHEN sp.role = 'Sponsor' THEN sp.law_id END) as laws_sponsored,
    COUNT(DISTINCT CASE WHEN sp.role = 'Cosponsor' THEN sp.law_id END) as laws_cosponsored,
    COUNT(DISTINCT iv.vote_id) as votes_cast,
    SUM(CASE WHEN iv.vote_cast = 'Yea' THEN 1 ELSE 0 END) as yea_votes,
    SUM(CASE WHEN iv.vote_cast = 'Nay' THEN 1 ELSE 0 END) as nay_votes
FROM legislator l
LEFT JOIN sponsorship sp ON l.legislator_id = sp.legislator_id
LEFT JOIN individual_vote iv ON l.legislator_id = iv.legislator_id
GROUP BY l.legislator_id, l.full_name, l.party, l.state;

CREATE UNIQUE INDEX idx_mv_activity_legislator ON mv_legislator_activity(legislator_id);
CREATE INDEX idx_mv_activity_sponsored ON mv_legislator_activity(laws_sponsored DESC);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_us_code_title_updated_at BEFORE UPDATE ON us_code_title
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_us_code_chapter_updated_at BEFORE UPDATE ON us_code_chapter
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_us_code_section_updated_at BEFORE UPDATE ON us_code_section
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_public_law_updated_at BEFORE UPDATE ON public_law
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_bill_updated_at BEFORE UPDATE ON bill
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_law_change_updated_at BEFORE UPDATE ON law_change
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_us_code_line_updated_at BEFORE UPDATE ON us_code_line
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_section_reference_updated_at BEFORE UPDATE ON section_reference
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to compute text hash
CREATE OR REPLACE FUNCTION compute_text_hash(text_input TEXT)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(sha256(text_input::bytea), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-compute hash on line insert/update
CREATE OR REPLACE FUNCTION set_line_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.text_hash = compute_text_hash(NEW.text_content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_us_code_line_hash BEFORE INSERT OR UPDATE OF text_content ON us_code_line
    FOR EACH ROW EXECUTE FUNCTION set_line_hash();

CREATE TRIGGER set_line_history_hash BEFORE INSERT OR UPDATE OF text_content ON line_history
    FOR EACH ROW EXECUTE FUNCTION set_line_hash();

-- Function to refresh materialized views (call periodically)
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_section_blame_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_law_impact_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_legislator_activity;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- These are commented out but provided for reference during implementation

/*
-- ============================================================================
-- BLAME VIEW QUERY: Get all lines in a section with attribution
-- ============================================================================
SELECT
    l.line_number,
    l.text_content,
    l.subsection_path,
    l.line_type,
    l.depth_level,
    -- Last modification
    pl_mod.law_number as last_modified_law,
    pl_mod.popular_name as last_modified_name,
    pl_mod.enacted_date as last_modified_date,
    pl_mod.president as last_modified_president,
    pl_mod.congress as last_modified_congress,
    -- Codification (for positive law)
    pl_cod.law_number as codified_by_law,
    pl_cod.enacted_date as codification_date,
    -- Original creation
    pl_cre.law_number as created_by_law,
    pl_cre.enacted_date as created_date,
    -- Positive law status
    s.is_positive_law
FROM us_code_line l
JOIN us_code_section s ON l.section_id = s.section_id
LEFT JOIN public_law pl_mod ON l.last_modified_by_law_id = pl_mod.law_id
LEFT JOIN public_law pl_cod ON l.codified_by_law_id = pl_cod.law_id
LEFT JOIN public_law pl_cre ON l.created_by_law_id = pl_cre.law_id
WHERE l.section_id = ? AND l.is_current = TRUE
ORDER BY l.line_number;

-- ============================================================================
-- TIME TRAVEL QUERY: Get section as it existed on a specific date
-- ============================================================================
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

-- ============================================================================
-- TREE TRAVERSAL: Get entire subtree of a line (recursive CTE)
-- ============================================================================
WITH RECURSIVE subtree AS (
    SELECT * FROM us_code_line WHERE line_id = ?
    UNION ALL
    SELECT l.* FROM us_code_line l
    JOIN subtree s ON l.parent_line_id = s.line_id
)
SELECT * FROM subtree ORDER BY line_number;

-- ============================================================================
-- PATH TO ROOT: Get breadcrumb trail for a line (recursive CTE)
-- ============================================================================
WITH RECURSIVE path AS (
    SELECT * FROM us_code_line WHERE line_id = ?
    UNION ALL
    SELECT l.* FROM us_code_line l
    JOIN path p ON l.line_id = p.parent_line_id
)
SELECT * FROM path ORDER BY depth_level;

-- ============================================================================
-- LAW IMPACT: Get all changes made by a law
-- ============================================================================
SELECT
    lc.change_type,
    s.full_citation,
    s.heading,
    lc.old_text,
    lc.new_text,
    lc.effective_date
FROM law_change lc
JOIN us_code_section s ON lc.section_id = s.section_id
WHERE lc.law_id = ?
ORDER BY s.title_id, s.section_number;

-- ============================================================================
-- DEPENDENCY GRAPH: Get sections referenced by a section
-- ============================================================================
SELECT
    sr.reference_type,
    sr.reference_text,
    target.full_citation as referenced_section,
    target.heading
FROM section_reference sr
JOIN us_code_section target ON sr.target_section_id = target.section_id
WHERE sr.source_section_id = ?
ORDER BY target.title_id, target.section_number;

-- ============================================================================
-- SEARCH: Full-text search for sections
-- ============================================================================
SELECT
    s.section_id,
    s.full_citation,
    s.heading,
    ts_rank(to_tsvector('english', COALESCE(s.heading, '') || ' ' || COALESCE(s.text_content, '')),
            plainto_tsquery('english', 'copyright fair use')) as rank
FROM us_code_section s
WHERE to_tsvector('english', COALESCE(s.heading, '') || ' ' || COALESCE(s.text_content, ''))
      @@ plainto_tsquery('english', 'copyright fair use')
ORDER BY rank DESC
LIMIT 20;

-- ============================================================================
-- ANALYTICS: Legislative productivity by Congress
-- ============================================================================
SELECT
    congress,
    COUNT(*) as laws_enacted,
    SUM(sections_affected) as total_sections_changed,
    AVG(sections_affected) as avg_sections_per_law,
    COUNT(CASE WHEN sections_affected >= 50 THEN 1 END) as omnibus_bills
FROM mv_law_impact_summary
GROUP BY congress
ORDER BY congress DESC;

*/

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
