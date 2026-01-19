# The Code We Live By (CWLB) - Project Specification

## Executive Summary

**The Code We Live By** (CWLB) is a civic engagement platform that makes federal legislation accessible and understandable by treating the US Code as a software repository. By leveraging the familiar metaphors of version control (commits, pull requests, diffs, contributors), the platform enables citizens to explore how laws evolve over time, understand congressional activity patterns, and gain insights into the legislative process.

**Brand**: The Code We Live By | **Acronym**: CWLB | **Social**: @cwlb

**Mission**: Increase transparency and public understanding of how the nation's laws are created, modified, and maintained.

---

## 1. Core Concept & Metaphor Mapping

### Repository Metaphor

| US Code Concept | Software Repository Equivalent |
|----------------|-------------------------------|
| US Code (current state) | Repository main branch |
| Individual sections (e.g., 17 USC § 106) | Source code files |
| Public Law / Statute | Merged Pull Request (PR) |
| Proposed bill | Open Pull Request |
| Failed/rejected bill | Closed/Rejected PR |
| Bill sponsor(s) | PR Author(s) |
| Co-sponsors | Co-authors |
| Congress members who voted | Reviewers |
| President's signature | Final approval/merge |
| Presidential veto | PR rejection |
| Veto override | Forced merge |
| Amendment to bill during passage | Commits to PR branch |
| Effective date | Merge timestamp |
| Historical versions of code | Git history / time travel |
| Titles (e.g., Title 17) | Repository directories/modules |
| Congressional debates/hearings | PR conversation/comments |
| Cross-references between sections | Code dependencies |

### Understanding the US Code Structure

The United States Code is the codification of federal statutory law, organized in a hierarchical structure:

**Structural Levels:**

1. **Titles** (54 total) - Broad subject areas
   - Example: Title 17 (Copyright), Title 26 (Internal Revenue Code)
   - Each title covers a major legal domain

2. **Chapters** - Major subdivisions within a title
   - Example: Title 17, Chapter 1 (Subject Matter and Scope of Copyright)
   - Typically 10-50+ chapters per title

3. **Sections** - The fundamental unit of law, indicated by the § symbol
   - Example: 17 USC § 106 (Exclusive rights in copyrighted works)
   - Full citation format: `[Title] USC § [Section]`
   - Most legislative changes happen at the section level
   - Typically hundreds to thousands of sections per title

4. **Subsections** - Numbered or lettered subdivisions within a section
   - Example: § 106(1), § 106(2), or § 106(a), § 106(b)
   - Contains the detailed provisions of the law

5. **Paragraphs, Subparagraphs, Clauses, Subclauses** - Deeper nesting
   - Example: § 101(a)(1)(A)(i)
   - Can nest several levels deep for complex provisions

**Example Hierarchy:**
```
Title 17 - Copyright
├── Chapter 1 - Subject Matter and Scope of Copyright
│   ├── § 101 - Definitions
│   ├── § 102 - Subject matter of copyright: In general
│   │   ├── (a) Copyright protection subsists...
│   │   └── (b) In no case does copyright protection...
│   ├── § 106 - Exclusive rights in copyrighted works
│   │   ├── (1) to reproduce the copyrighted work...
│   │   ├── (2) to prepare derivative works...
│   │   └── (6) in the case of sound recordings...
│   └── § 107 - Limitations on exclusive rights: Fair use
├── Chapter 2 - Copyright Ownership and Transfer
│   └── ...
└── Chapter 13 - Protection of Original Designs
    └── ...
```

### Repository Structure Mapping Options

#### Option 1: Section-as-File (Recommended ⭐)

**Structure:**
```
USC/
├── Title-17-Copyright/
│   ├── Chapter-01-Subject-Matter-and-Scope/
│   │   ├── Section-101-Definitions.md
│   │   ├── Section-102-Subject-Matter-In-General.md
│   │   ├── Section-106-Exclusive-Rights.md
│   │   └── Section-107-Fair-Use.md
│   ├── Chapter-02-Copyright-Ownership/
│   │   └── ...
│   └── README.md (Title overview)
├── Title-26-Internal-Revenue-Code/
│   └── ...
└── README.md (US Code overview)
```

**Mapping:**
- **Titles** → Top-level directories/modules
- **Chapters** → Subdirectories
- **Sections** → Individual files (e.g., `Section-106-Exclusive-Rights.md`)
- **Subsections** → Content within files (with anchor links for deep linking)
- **Paragraphs/clauses** → Nested content within files

**Rationale:**
- **Natural legislative granularity**: ~80% of laws modify at the section level
- **Meaningful diffs**: Most PRs (laws) change 1-50 sections, making diffs readable
- **Familiar citation pattern**: Aligns with how lawyers cite law ("17 USC § 106")
- **Balanced file count**: ~60,000 sections total = manageable but comprehensive
- **Clean PR visualization**: "Files changed: 23 sections" is intuitive
- **Historical tracking**: Each section has its own change history

**Example PR (Law) changing 3 sections:**
```
PL 105-304: Digital Millennium Copyright Act
Files changed: 3

Modified:
  ✏️ Title-17-Copyright/Chapter-01/Section-106-Exclusive-Rights.md
  ✏️ Title-17-Copyright/Chapter-05/Section-512-Limitations-on-Liability.md
Added:
  ➕ Title-17-Copyright/Chapter-12/Section-1201-Circumvention-of-Tech-Measures.md
```

#### Option 2: Chapter-as-File

**Structure:**
```
USC/
├── Title-17-Copyright/
│   ├── Chapter-01-Subject-Matter-and-Scope.md
│   ├── Chapter-02-Copyright-Ownership.md
│   └── Chapter-13-Original-Designs.md
├── Title-26-Internal-Revenue-Code/
│   └── ...
└── README.md
```

**Mapping:**
- **Titles** → Directories
- **Chapters** → Files
- **Sections** → Major headings within files
- **Subsections** → Content under headings

**Pros:**
- Fewer total files (~500-1000 vs ~60,000)
- Easier to browse at high level
- Simpler file tree navigation

**Cons:**
- ❌ Very large files (some chapters have 100+ sections)
- ❌ Diffs are harder to read (entire chapter shows as changed even for 1-section amendments)
- ❌ Doesn't match legislative granularity (laws rarely touch whole chapters)
- ❌ Harder to link to specific provisions
- ❌ Section-level history is obscured

#### Option 3: Subsection-as-File

**Structure:**
```
USC/
├── Title-17-Copyright/
│   ├── Chapter-01/
│   │   ├── Section-106-Exclusive-Rights/
│   │   │   ├── Subsection-1-Reproduction.md
│   │   │   ├── Subsection-2-Derivative-Works.md
│   │   │   ├── Subsection-3-Distribution.md
│   │   │   └── ...
│   │   └── Section-107-Fair-Use/
│   │       └── ...
```

**Mapping:**
- **Titles** → Top-level directories
- **Chapters** → Directories
- **Sections** → Directories
- **Subsections** → Files
- **Paragraphs** → Content within files

**Pros:**
- Maximum granularity for tracking changes
- Very precise change attribution

**Cons:**
- ❌ Hundreds of thousands of files (overwhelming)
- ❌ Too granular for most use cases
- ❌ Many laws modify entire sections, not subsections
- ❌ Navigation becomes cumbersome
- ❌ Doesn't match typical legislative or legal citation patterns

#### Option 4: Hybrid Section-as-File with Subsection Anchors

**Structure:**
Same as Option 1 (Section-as-File), but with enhanced deep linking:

```
USC/
├── Title-17-Copyright/
│   └── Chapter-01/
│       └── Section-106-Exclusive-Rights.md
```

**File content with anchors:**
```markdown
# § 106 · Exclusive rights in copyrighted works

Subject to sections 107 through 122, the owner of copyright under this
title has the exclusive rights to do and to authorize any of the following:

## (1) Reproduction {#subsection-1}
to reproduce the copyrighted work in copies or phonorecords;

## (2) Derivative Works {#subsection-2}
to prepare derivative works based upon the copyrighted work;

...
```

**Enhanced features:**
- URLs can deep-link to subsections: `/Title-17/Chapter-01/Section-106#subsection-2`
- Diffs can highlight subsection-level changes within the file
- UI can show subsection-level change indicators
- Search can index and return subsections as results

**Pros:**
- ✅ Same benefits as Section-as-File
- ✅ Plus: subsection-level precision when needed
- ✅ Progressive disclosure: show section, expand to subsections
- ✅ Flexible for both coarse and fine-grained analysis

**Cons:**
- Slightly more complex implementation
- Requires anchor/bookmark parsing

### Recommended Approach: Option 1 (Section-as-File)

**Primary reasons:**

1. **Matches legislative practice**: The section is the fundamental unit that Congress modifies. When a law says "Section 106 is amended...", it's operating at this level.

2. **Optimal diff readability**: A typical law might modify 5-30 sections. This produces a clean "Files changed" list similar to a normal software PR.

3. **Legal citation alignment**: Lawyers, judges, and citizens reference laws as "17 USC § 106" – having this be a direct file path is intuitive.

4. **Scalability**: 60,000 files is large but manageable for modern systems. GitHub repositories regularly handle this scale.

5. **Historical clarity**: Each section's evolution is tracked independently, making time-travel intuitive.

6. **Balanced granularity**: Not too coarse (chapters) or too fine (subsections), but just right for the audience and use case.

**Implementation notes:**
- File naming: Use descriptive names like `Section-106-Exclusive-Rights.md` rather than just `106.md` for better discoverability
- Internal structure: Use markdown headers for subsections to enable deep linking
- Metadata: Include frontmatter with section number, heading, enactment date, last modified
- Cross-references: Automatically hyperlink citations to other sections (e.g., "section 107" → link to Section-107 file)

---

## 2. Target Audience

**Primary**: General public interested in civic engagement, transparency, and understanding government

**Characteristics**:
- May not have legal training
- Interested in understanding "how the sausage is made"
- Want to answer questions about legislative patterns and trends
- Value transparency and accessibility

**Design Principle**: Progressive disclosure - simple and accessible by default, with depth available for those who want it.

---

## 3. Phase 1 Scope

### Coverage
- **Titles**: 5-10 most publicly relevant titles, including:
  - Title 17: Copyright
  - Title 26: Internal Revenue Code (Tax)
  - Title 18: Crimes and Criminal Procedure
  - Title 42: Public Health and Social Welfare
  - Title 20: Education
  - Additional titles based on public interest and data availability

### Historical Depth
- **Full legislative history** from original enactment to present
- Acknowledges that older records may require additional research/digitization effort

### Geographic Scope
- Federal law only (US Code)
- State laws excluded from Phase 1

---

## 4. Core Features

### 4.1 Code Browsing ("Repository View")

**Browse Current Code**
- Navigate US Code by Title > Chapter > Section hierarchy
- View verbatim text of current law
- Clean, readable formatting with proper legal citations
- Breadcrumb navigation showing location in hierarchy
- File path-style display (e.g., `USC/Title-17/Chapter-1/Section-106`)

**Time Travel**
- View any section as it existed at any point in history
- Date picker or timeline scrubber to select historical snapshots
- "What changed" summary when comparing dates
- Permalink to specific version (e.g., "Section 106 as of July 4, 1976")

**Visual Indicators**
- Color-coding for recently changed sections (e.g., changed in last 1yr, 5yr, 10yr)
- Activity heatmap showing which sections change frequently vs rarely
- "Last modified" timestamp for each section

**Legislative Blame View** ("Git Blame" for Laws)
- Line-by-line attribution showing which law last modified each provision
- Display format for each line/paragraph:
  - **Public Law**: PL number and popular name (e.g., "PL 94-553: Copyright Act of 1976")
  - **Congress**: Which Congress passed it (e.g., "94th Congress")
  - **President**: Who signed it (e.g., "President Gerald Ford")
  - **Date**: When it became effective (e.g., "Oct 19, 1976")
  - **Visual indicator**: Color-coding or sidebar marker showing law attribution
- Toggle between normal view and blame view
- Hover/click on any line to see:
  - Full metadata about the modifying law
  - Link to view the complete PR (law) that made the change
  - Preview of the diff showing what changed
  - Sponsors and vote counts
- Multi-law sections: Some text may show multiple attributions if different subsections were modified by different laws
- Original enactment indicator: Special styling for text that dates to the section's original creation
- User stories:
  - "I want to know when this copyright provision was added"
  - "Which Congress and President are responsible for this tax rule?"
  - "Has this criminal statute been modified since its original enactment?"

**Example Blame View:**
```
┌─────────────────────────────────────────────────────────────┐
│ § 106 · Exclusive rights in copyrighted works               │
│                                                              │
│ PL 94-553   Subject to sections 107 through 118, the owner  │
│ 94th Cong   of copyright under this title has the exclusive │
│ Ford        rights to do and to authorize any of the        │
│ 1976        following:                                       │
│                                                              │
│ PL 94-553   (1) to reproduce the copyrighted work in copies │
│ 94th Cong       or phonorecords;                            │
│ Ford                                                         │
│ 1976        (2) to prepare derivative works based upon the  │
│                 copyrighted work;                            │
│                                                              │
│ PL 101-650  (3) to distribute copies or phonorecords of the │
│ 101st Cong      copyrighted work to the public by sale or   │
│ Bush                                                         │
│ 1990        ...                                              │
└─────────────────────────────────────────────────────────────┘
         ↑
    Click any line to see full law details
```

### 4.2 Law Viewer ("Pull Request View")

**Individual Law Display**
- Public Law number and popular name (e.g., "PL 94-553: Copyright Act of 1976")
- Summary and purpose
- Diff view showing exact changes to US Code:
  - **Red/strikethrough**: Deleted text
  - **Green/highlight**: Added text
  - **Yellow**: Modified text (combined deletion + addition)
  - Line-by-line diff for precision
- Side-by-side or unified diff options

**Metadata Panel**
- **Authors**: Bill sponsors (with photos, party, state)
- **Co-authors**: Co-sponsors
- **Reviewers**:
  - House members (with vote: approve/reject/abstain)
  - Senate members (with vote)
  - President (signed/vetoed)
- Bill number(s) (e.g., H.R. 2223, S. 22)
- Date introduced, passed House, passed Senate, signed/enacted
- Effective date (when changes took effect)
- Related committee assignments

**Multi-Section Changes**
- If law affects multiple sections, show as "Files changed: 47"
- Collapsible list of all affected sections
- Navigation between changed sections within the law

**Legislative Journey Timeline**
- Visual timeline showing bill's progress:
  - Introduced → Committee → House vote → Senate vote → Presidential action → Effective
- Key dates and milestones

### 4.3 Search & Discovery

**Search Capabilities**
- **Full-text search**: Search within current or historical code text
- **Law search**: Find laws by name, number, keyword, sponsor
- **Advanced filters**:
  - Date range (e.g., laws from 101st-102nd Congress)
  - Sponsor/author
  - Affected Title or section
  - Vote margin (unanimous vs contested)
  - Bill type (appropriations, amendments, new law)

**Search Results**
- Snippet preview with matched text highlighted
- Sort by relevance, date, or impact (# of sections changed)
- Save searches for later

### 4.4 Analytics & Visualizations

**Purpose**: Enable users to answer questions about legislative patterns and congressional activity.

**Congressional Activity Dashboard**

*Questions to Answer*:
- "What were the legislative focus areas of the 102nd Congress?"
- "How do Congressional terms differ in terms of legislative productivity?"
- "How focused are individual laws?"

*Visualizations*:

1. **Legislative Activity Over Time**
   - Line/bar chart: Laws enacted per Congressional session
   - Metric: Total laws, total sections modified, lines added/removed
   - Granularity: By session, year, or month

2. **Focus Area Analysis**
   - Stacked area chart showing which Titles were modified over time
   - Pie chart of legislative activity by Title for a given Congress
   - Identify "hot zones" of legislative change

3. **Congressional Productivity Comparison**
   - Compare metrics across different Congresses:
     - Total laws passed
     - Sections modified
     - Average time from introduction to enactment
     - Bipartisan vs party-line votes
   - Sortable table and visual charts

4. **Law Scope Metrics**
   - For each law, calculate:
     - **Breadth**: Number of distinct sections modified
     - **Depth**: Total lines changed
     - **Focus Score**: Narrow (1-2 sections) vs Broad (100+ sections)
   - Distribution chart: How many laws are narrow vs broad?
   - Identify omnibus bills vs targeted amendments

5. **Contributor Statistics**
   - Most active sponsors (by number of laws, impact)
   - Collaboration networks (who co-sponsors together)
   - Bipartisan index (single-party vs cross-party sponsorship)

6. **Code Change Heatmap**
   - Visual heatmap of US Code structure
   - Color intensity = frequency of change
   - Identify stable vs volatile sections

7. **Timeline Visualizations**
   - Swim lane diagram showing parallel legislative efforts
   - Commit-style activity graph (à la GitHub contributions)

**Export & Sharing**
- Export data as CSV/JSON for further analysis
- Share permalinks to specific visualizations
- Embed visualizations in articles/reports

### 4.5 Integration with Related Resources

**External Links**
- Link to source documents:
  - Congress.gov for bill text, reports, debates
  - GovInfo for official Public Law documents
  - Supreme Court cases citing specific sections
  - CFR (Code of Federal Regulations) for related regulations
  - Congressional committee reports

**Citation Tools**
- Generate properly formatted legal citations
- Export to citation managers (BibTeX, Zotero)

**Educational Resources**
- "Learn more" links explaining legal concepts
- Glossary of legislative terms
- Process diagrams (how a bill becomes a law)

---

## 5. User Stories

### As a citizen, I want to...
1. See how copyright law has changed since the internet was invented
2. Understand who authored the laws that affect my daily life
3. Discover whether my representative is an active legislator
4. See which areas of law are most actively debated and changed
5. **Use blame view to see which President and Congress are responsible for specific tax provisions I care about**
6. **Click on any line of law to understand when and why it was added**

### As an educator, I want to...
1. Show students real examples of legislative change over time
2. Compare how different Congresses approached specific issues
3. Demonstrate the collaborative nature of lawmaking through co-sponsorship data
4. **Use blame view to teach students about legislative authorship and accountability**
5. **Show students how a single section evolved through multiple Congresses**

### As a journalist, I want to...
1. Quickly identify when a specific section was last modified and why
2. Analyze voting patterns on consequential legislation
3. Track which legislators are most influential in specific policy areas
4. **Use blame view to attribute specific provisions to specific administrations for fact-checking**
5. **Trace contentious legal language back to the exact law and legislators responsible**

### As a researcher, I want to...
1. Export data about legislative activity for statistical analysis
2. Identify trends in legislative focus over decades
3. Study the evolution of specific legal concepts through amendments
4. **Analyze patterns in which Congresses and Presidents modified which sections**
5. **Study legislative persistence by identifying which provisions remain unchanged for decades**

---

## 6. Data Model

### Core Entities

**USCodeSection**
- `title`: Integer (e.g., 17)
- `chapter`: String (e.g., "1")
- `section`: String (e.g., "106")
- `heading`: String (e.g., "Exclusive rights in copyrighted works")
- `text`: Text (current verbatim text)
- `last_modified`: Date
- `enacted_date`: Date (when section was originally created)

**PublicLaw** (Enacted legislation - "Merged PR")
- `law_number`: String (e.g., "94-553")
- `congress`: Integer (e.g., 94)
- `law_type`: Enum (Public, Private)
- `popular_name`: String (e.g., "Copyright Act of 1976")
- `summary`: Text
- `bill_number`: String (e.g., "S. 22")
- `introduced_date`: Date
- `house_passed_date`: Date
- `senate_passed_date`: Date
- `enacted_date`: Date
- `effective_date`: Date
- `president`: String
- `status`: Enum (Enacted) - always "Enacted" for this table

**Bill** (Proposed or failed legislation - "Open or Closed PR")
- `bill_number`: String (e.g., "H.R. 1234")
- `congress`: Integer
- `bill_type`: Enum (House, Senate)
- `popular_name`: String
- `summary`: Text
- `introduced_date`: Date
- `status`: Enum (Introduced, In Committee, Passed House, Passed Senate, Failed, Vetoed)
- `current_chamber`: String
- `current_committee`: String
- `last_action_date`: Date
- `last_action_description`: Text
- `likelihood_score`: Float (optional - probability of passage)
- `related_law_id`: Foreign key to PublicLaw (if eventually enacted)

**LawChange** (The "Diff" for enacted laws)
- `law_id`: Foreign key to PublicLaw
- `section_id`: Foreign key to USCodeSection
- `change_type`: Enum (Add, Delete, Modify, Repeal)
- `old_text`: Text
- `new_text`: Text
- `line_number_start`: Integer
- `line_number_end`: Integer

**ProposedChange** (The "Diff" for bills not yet enacted)
- `bill_id`: Foreign key to Bill
- `section_id`: Foreign key to USCodeSection (proposed target)
- `change_type`: Enum (Add, Delete, Modify, Repeal)
- `current_text`: Text (current code text)
- `proposed_text`: Text (what it would become)
- `line_number_start`: Integer
- `line_number_end`: Integer

**SectionHistory**
- `section_id`: Foreign key
- `law_id`: Foreign key (which law caused this version)
- `text`: Text (full text at this point in time)
- `effective_date`: Date
- `version_number`: Integer

**Legislator**
- `bioguide_id`: String (official ID)
- `name`: String
- `party`: String
- `state`: String
- `chamber`: Enum (House, Senate)
- `photo_url`: String
- `served_from`: Date
- `served_to`: Date

**Sponsorship**
- `law_id`: Foreign key
- `legislator_id`: Foreign key
- `role`: Enum (Sponsor, Co-sponsor)
- `sponsored_date`: Date

**Vote**
- `law_id`: Foreign key
- `legislator_id`: Foreign key
- `vote_type`: Enum (Yea, Nay, Present, Not Voting)
- `chamber`: Enum (House, Senate)
- `vote_date`: Date

**SectionReference** (For dependency graphs)
- `source_section_id`: Foreign key to USCodeSection (the section doing the referencing)
- `target_section_id`: Foreign key to USCodeSection (the section being referenced)
- `reference_type`: Enum (Explicit citation, Cross-reference, "Subject to", Conditional)
- `reference_text`: Text (the actual text that makes the reference)
- `discovered_date`: Date (when this reference was identified)

**LineAttribution** (For "git blame" style attribution - tracks which law created each line)
- `section_id`: Foreign key to USCodeSection
- `law_id`: Foreign key to PublicLaw (which law last modified this text)
- `line_number_start`: Integer (starting line number)
- `line_number_end`: Integer (ending line number, for multi-line provisions)
- `text_content`: Text (the actual text content for this range)
- `subsection_identifier`: String (e.g., "(a)", "(1)", "(A)(i)" - helps map to legal structure)
- `attribution_type`: Enum (Original enactment, Amendment, Addition, Renumbering)
- `effective_date`: Date (when this version of the text took effect)
- `created_at`: Timestamp (when this attribution record was created)
- Note: When a law modifies text, old LineAttribution records are preserved for historical blame views

**Alternative/Optimization**: Instead of storing line-by-line attribution, could compute blame dynamically by:
1. Starting with section's original enactment law
2. Applying LawChange records chronologically
3. Tracking which law last touched each portion of text
This approach saves storage but increases computation time for blame views.

---

## 7. Technical Architecture

### Frontend
- **Framework**: React or Next.js for interactive UI
- **Visualization**: D3.js or Observable for charts and graphs
- **Diff Display**: react-diff-viewer or custom diff component
- **Routing**: Support deep linking to sections, laws, time periods
- **State Management**: Context API or Redux for complex state

### Backend
- **API**: RESTful or GraphQL API
- **Database**: PostgreSQL for relational data, with full-text search
- **Caching**: Redis for frequently accessed sections/laws
- **Search**: Elasticsearch for advanced full-text search

### Data Pipeline
- **Sources**:
  - US House Office of Law Revision Counsel (official US Code source)
  - GovInfo API (GPO - Government Publishing Office)
  - Congress.gov API
  - ProPublica Congress API (for legislator data)
  - Historical sources for pre-digital records

- **ETL Process**:
  - Ingest Public Laws in structured format (XML/JSON)
  - Parse legal language to extract section changes
  - Build historical versions by applying changes chronologically
  - Link legislators to sponsorship and votes

- **Challenges**:
  - Older laws may be in PDF/scanned format requiring OCR
  - Legal language parsing is complex (e.g., "Section 106 is amended by striking 'and' and inserting 'or'")
  - Effective dates may differ from enactment dates

### Infrastructure
- **Hosting**: Cloud platform (AWS, GCP, or Azure)
- **CDN**: For static assets and performance
- **Authentication**: Optional user accounts for saved searches, annotations

---

## 8. User Interface & Experience

### Key Principles
1. **Clarity over complexity**: Use plain language, avoid legal jargon where possible
2. **Progressive disclosure**: Show essentials first, details on demand
3. **Visual hierarchy**: Use familiar GitHub-style UI patterns where applicable
4. **Accessibility**: WCAG 2.1 AA compliance, screen reader friendly

### Main Navigation
- **Explore Code**: Browse current US Code structure
- **View Laws**: Search and browse individual laws (PRs)
- **Analytics**: Dashboard for insights and trends
- **About**: Educational content, methodology, data sources

### Code Browser Page
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] The Code We Live By       [Search] [Analytics] [?]   │
├─────────────────────────────────────────────────────────────┤
│ USC > Title 17 > Chapter 1 > § 106                          │
│                                                              │
│ Time Travel: [◄] Jan 1, 2024 [Date Picker] [►]             │
│ View: [Normal] [🔍 Blame]                                    │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ § 106 · Exclusive rights in copyrighted works           │ │
│ │                                                          │ │
│ │ Subject to sections 107 through 122, the owner of       │ │
│ │ copyright under this title has the exclusive rights     │ │
│ │ to do and to authorize any of the following:            │ │
│ │                                                          │ │
│ │ (1) to reproduce the copyrighted work in copies or      │ │
│ │     phonorecords;                                        │ │
│ │ ...                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Last modified: Oct 28, 1998 by PL 105-304                   │
│ [View change history] [View full law] [Legislative blame]   │
└─────────────────────────────────────────────────────────────┘
```

**With Blame View Enabled:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] The Code We Live By       [Search] [Analytics] [?]   │
├─────────────────────────────────────────────────────────────┤
│ USC > Title 17 > Chapter 1 > § 106                          │
│                                                              │
│ Time Travel: [◄] Jan 1, 2024 [Date Picker] [►]             │
│ View: [Normal] [🔍 Blame] ← Active                           │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ § 106 · Exclusive rights in copyrighted works           │ │
│ │                                                          │ │
│ │ PL 94-553 │ Subject to sections 107 through 122, the    │ │
│ │ 94th Cong │ owner of copyright under this title has the │ │
│ │ Ford 1976 │ exclusive rights to do and to authorize any │ │
│ │           │ of the following:                            │ │
│ │              ↑ Hover for details                         │ │
│ │ PL 94-553 │ (1) to reproduce the copyrighted work in    │ │
│ │ 94th Cong │     copies or phonorecords;                  │ │
│ │ Ford 1976 │                                              │ │
│ │           │ (2) to prepare derivative works based upon  │ │
│ │           │     the copyrighted work;                    │ │
│ │                                                          │ │
│ │ PL 101-650│ (3) to distribute copies or phonorecords of │ │
│ │ 101st Cong│     the copyrighted work to the public...   │ │
│ │ Bush 1990 │                                              │ │
│ │ ...                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ 💡 Tip: Click any line to see the full law that created it  │
└─────────────────────────────────────────────────────────────┘
```

### Law Viewer Page (Pull Request Style)
```
┌─────────────────────────────────────────────────────────────┐
│ PL 94-553: Copyright Act of 1976                            │
│                                                              │
│ ⚡ Merged on Oct 19, 1976 by President Gerald Ford          │
│                                                              │
│ ┌────────────┬──────────────────────────────────────────┐   │
│ │ Authors    │ [Photo] Sen. John McClellan (D-AR)       │   │
│ │            │ + 25 co-sponsors [show all]              │   │
│ ├────────────┼──────────────────────────────────────────┤   │
│ │ Reviewers  │ ✓ House: 316-7                           │   │
│ │            │ ✓ Senate: Voice vote                     │   │
│ │            │ ✓ President: Signed                      │   │
│ ├────────────┼──────────────────────────────────────────┤   │
│ │ Timeline   │ [●══●══●══●] Introduced → ... → Enacted  │   │
│ ├────────────┼──────────────────────────────────────────┤   │
│ │ Impact     │ Files changed: 84 sections               │   │
│ │            │ +12,450 lines, -3,200 lines              │   │
│ └────────────┴──────────────────────────────────────────┘   │
│                                                              │
│ [Conversation] [Files changed 84] [Related resources]       │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Title 17 / Chapter 1 / § 106                            │ │
│ │                                                          │ │
│ │ -  Subject to sections 107 through 118, the owner of    │ │
│ │ +  Subject to sections 107 through 122, the owner of    │ │
│ │    copyright under this title has the exclusive rights  │ │
│ │    to do and to authorize any of the following:         │ │
│ │                                                          │ │
│ │    (1) to reproduce the copyrighted work in copies or   │ │
│ │        phonorecords;                                    │ │
│ │                                                          │ │
│ │ +  (2) to prepare derivative works based upon the       │ │
│ │ +      copyrighted work;                                │ │
│ │    ...                                                   │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Analytics Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│ Legislative Analytics                                        │
│                                                              │
│ [Congress Comparison] [Focus Areas] [Contributors] [Trends] │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Productivity by Congress                                │ │
│ │                                                          │ │
│ │ Laws Enacted                                             │ │
│ │  600 ┤        ╭╮                                         │ │
│ │  400 ┤     ╭╮ ││  ╭╮                                     │ │
│ │  200 ┤  ╭╮ │╰╮│╰╮╭╯│                                     │ │
│ │    0 ┴──┴──┴─┴┴─┴┴─┴──                                   │ │
│ │      101st 102nd 103rd 104th 105th                       │ │
│ │                                                          │ │
│ │ [Compare selected Congresses]                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Legislative Focus: 102nd Congress (1991-1993)           │ │
│ │                                                          │ │
│ │  ██████████████ Title 42 (Health & Welfare) - 89 laws   │ │
│ │  ███████████ Title 26 (Tax) - 67 laws                   │ │
│ │  ████████ Title 16 (Conservation) - 54 laws             │ │
│ │  ██████ Title 10 (Armed Forces) - 41 laws               │ │
│ │  ████ Title 20 (Education) - 28 laws                    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Analytics: Key Metrics & Questions

### Legislative Productivity Metrics

**Per Congress**:
- Total Public Laws enacted
- Total sections created/modified/repealed
- Total lines added/removed
- Average days from introduction to enactment
- Percentage of bipartisan bills
- Most active committees

**Per Law**:
- Breadth (sections affected)
- Depth (total text changed)
- Focus score: `log(1 + sections_affected)`
- Time to passage
- Vote margins (unanimous vs narrow)

**Per Section**:
- Modification frequency
- Total times amended
- Stability score (time since last change)
- Number of laws that touched this section

**Per Legislator**:
- Laws sponsored (primary sponsor)
- Laws co-sponsored
- Success rate (sponsored bills that became law)
- Specialization score (concentration in specific Titles)
- Bipartisan collaboration index

### Answering Key Questions

**"What were the legislative focus areas of the 102nd Congress?"**
- Aggregate all laws from 102nd Congress
- Group by Title affected
- Visualize as bar chart or pie chart
- Drill down to see specific laws in each category

**"How do Congressional terms differ in productivity?"**
- Compare metrics across Congresses:
  - Total laws enacted
  - Sections modified
  - Lines of code changed
  - Distribution of narrow vs broad laws
- Control for unified vs divided government
- Show trends over time

**"How focused are individual laws?"**
- Calculate focus score for each law
- Create distribution: X-axis = sections affected, Y-axis = number of laws
- Identify outliers (omnibus bills with 500+ sections vs targeted 1-section amendments)
- Show examples of narrow vs broad laws

---

## 10. Success Metrics

### Engagement Metrics
- Monthly active users
- Average session duration
- Pages per visit
- Return visitor rate

### Learning Metrics
- "Time travel" feature usage (indicates exploration)
- Analytics dashboard views
- Search query diversity

### Impact Metrics
- External citations (media, research papers)
- Educational adoption (classroom use)
- Data export usage (indicates research value)
- Social sharing of specific laws/sections

---

## 11. Privacy & User Data

### No Login Required
- Default experience is fully open and anonymous
- No tracking beyond basic analytics (page views, referrers)

### Optional Accounts
- Save searches, bookmarks, annotations (local-first, with optional sync)
- No personally identifiable data required
- No selling of user data

### Data Transparency
- All source data is public domain (government data)
- Methodology and data sources clearly documented
- Open API for researchers

---

## 12. Future Enhancements (Post-Phase 1)

### Legislative Process Features (Priority Backlog)

**Proposed Bills ("Open Pull Requests")** ⭐ Priority
- Show bills currently under consideration in Congress
- Display as "Open PRs" awaiting merge (enactment)
- Real-time status updates (in committee, scheduled for vote, etc.)
- Show proposed diffs (what would change if bill passes)
- Filter by chamber, committee, likelihood of passage
- Track bill amendments as commits to the PR
- User story: "I want to see what changes to copyright law are being proposed right now"

**Failed Legislation ("Closed/Rejected PRs")**
- Show bills that failed to pass (died in committee, rejected, vetoed without override)
- Display as closed/rejected PRs
- Include voting records showing why it failed
- Compare similar bills across sessions (was it reintroduced?)
- Analytics: success/failure rates by topic, sponsor, Congress
- User story: "I want to see how many times healthcare reform was attempted before the ACA passed"

**Conversation Tab**
- Congressional floor debates excerpts
- Committee hearing summaries and testimony
- Bill markup session notes
- Public comments (if applicable)
- Media coverage and analysis links
- Expert commentary
- Design challenges: What format? How much detail? Chronological or topical?
- User story: "I want to understand the debates that shaped this law"

**Dependency Graph**
- Visual network showing which sections reference each other
- "This section is referenced by 47 other sections"
- "This section references 12 other sections"
- Identify critical hub sections (highly referenced)
- Impact analysis: "If this section changes, these others might be affected"
- Interactive graph visualization (D3.js force-directed graph)
- User story: "I want to see what other laws depend on this privacy statute"

### Expanded Coverage
- All 54 titles of US Code
- State laws (multi-state comparison)
- Regulations (CFR) linked to statutes
- Historical statutes at large (pre-codification)

### Advanced Features
- **Annotations & Discussions**: Community commentary on specific sections
- **Alert System**: Notify users when specific sections are modified
- **Impact Analysis**: "What laws depend on this section?"
- **Predictive Analytics**: Identify sections likely to be modified soon based on patterns
- **Natural Language Queries**: "Show me all environmental laws passed in the 1970s"
- **API Access**: Full programmatic access for researchers
- **Comparison Tool**: Side-by-side comparison of similar sections across states
- **Causality Tracking**: Link laws to the events/problems that prompted them

### Collaboration Features
- User-submitted annotations (moderated)
- Crowdsourced plain-language summaries
- Educational lesson plans built around specific laws

### Mobile App
- Responsive web design initially
- Native mobile apps for deeper engagement

---

## 13. Technical Challenges & Mitigations

### Challenge: Parsing Legal Language
Legal statutes often describe changes indirectly:
> "Section 106 is amended by striking paragraph (3) and inserting the following..."

**Mitigation**:
- Use Office of Law Revision Counsel's XML format (structured amendments)
- Build parser for common amendment patterns
- Manual review for complex cases
- Display both original bill language AND resulting code change

### Challenge: Historical Data Availability
Pre-1990s laws may lack structured digital format.

**Mitigation**:
- Partner with legal tech companies or academic institutions
- Phased approach: recent history first, backfill over time
- OCR and manual correction for critical historical laws
- Community contribution model for digitization

### Challenge: Effective Dates vs Enactment Dates
Some laws take effect immediately; others have delayed effective dates or phase-in periods.

**Mitigation**:
- Track both enactment and effective dates
- Time travel defaults to effective date
- Show annotation if dates differ significantly

### Challenge: Scale
Full US Code is ~60,000 sections; 100+ years of history = millions of changes.

**Mitigation**:
- Efficient database schema with indexing
- Lazy loading and pagination
- Pre-compute common queries (e.g., "current version")
- CDN for static content

### Challenge: Legal Accuracy
Displaying legal text requires precision; errors could mislead users.

**Mitigation**:
- Canonical source: Official US Code from House OLC
- Regular synchronization with official sources
- Clear disclaimers about unofficial nature
- Feedback mechanism for reporting errors

---

## 14. Open Questions for Further Discussion

1. **Monetization**: Should this be:
   - Fully free (grant-funded or nonprofit)
   - Freemium (advanced features require subscription)
   - Ad-supported (with ethical ad standards)

2. **Governance**: Who maintains this? Options:
   - Nonprofit organization
   - Open-source community
   - Academic institution
   - Government partnership

3. **Amendments to Bills**: Should we show:
   - Amendments proposed during bill passage as "commits to PR branch"?
   - Failed amendments as "rejected commits"?

4. **Cross-References**: How deeply should we link related sections?
   - Inline links to other sections mentioned?
   - Auto-detect citations and hyperlink them?

5. **International Expansion**: Could this model extend to other countries' legal codes?

6. **Educational Materials**: Should we create:
   - Video tutorials?
   - Guided tours (e.g., "The journey of the ADA")?
   - Curriculum for high school civics classes?

---

## 15. Development Roadmap

### Phase 0: Research & Validation (2-3 months)
- [ ] Data source assessment and API testing
- [ ] Build prototype parser for 1-2 sample laws
- [ ] User research with target audience
- [ ] Technical architecture design
- [ ] Select initial 5-10 titles

### Phase 1: MVP (6-9 months)
- [ ] Core data pipeline (ingest, parse, store)
- [ ] Basic code browser (current version only)
- [ ] Law viewer with diff display
- [ ] Simple search functionality
- [ ] 5-10 titles, last 20 years of history
- [ ] Basic analytics (activity over time)
- [ ] Public beta launch

### Phase 2: Enhancement (6-9 months)
- [ ] Time travel functionality
- [ ] Advanced search and filters
- [ ] Comprehensive analytics dashboard
- [ ] Integration with external resources
- [ ] Expand to full historical depth
- [ ] User accounts and saved searches
- [ ] Performance optimization

### Phase 3: Scale & Engage (ongoing)
- [ ] Expand to all US Code titles
- [ ] Community features (annotations, discussions)
- [ ] Educational partnerships
- [ ] API for researchers
- [ ] Mobile optimization
- [ ] Continuous data updates

---

## 16. Conclusion

**The Code We Live By** (CWLB) transforms how citizens understand and engage with federal law. By applying the familiar metaphor of software development to the legislative process, we make the US Code accessible, explorable, and analytically rich.

**Key Differentiators**:
- **Transparency**: See exactly what changed, when, and by whom
- **Historical Depth**: Time-travel through decades of legal evolution
- **Analytical Power**: Answer questions about legislative patterns and productivity
- **Civic Engagement**: Empower citizens to understand the laws that govern them
- **Familiarity**: Leverage intuitive software development metaphors

This platform has the potential to become an essential tool for civic education, journalism, legal research, and public understanding of government.

---

## Appendix A: Data Sources

- **US Code**: Office of the Law Revision Counsel (https://uscode.house.gov)
- **Public Laws**: GovInfo.gov (GPO)
- **Bill Information**: Congress.gov API
- **Legislator Data**: ProPublica Congress API, Bioguide
- **Vote Records**: Congress.gov, GovTrack
- **Historical Documents**: HathiTrust, Internet Archive

## Appendix B: Technical Stack Recommendations

**Frontend**: Next.js (React), TypeScript, Tailwind CSS, D3.js
**Backend**: Node.js/Express or Python/FastAPI
**Database**: PostgreSQL + Elasticsearch
**Infrastructure**: Vercel/AWS/GCP
**Version Control**: Git (meta!)

## Appendix C: Legal & Disclaimers

- This is an unofficial presentation of the US Code
- Official version is at uscode.house.gov
- Not legal advice
- Open data license for all content
