# The Code We Live By (CWLB) - Project Specification

## Executive Summary

**The Code We Live By** (CWLB) is a civic engagement platform that makes federal legislation accessible and understandable by treating the US Code as a software repository. By leveraging the familiar metaphors of version control (commits, pull requests, diffs, contributors), the platform enables citizens to explore how laws evolve over time, understand congressional activity patterns, and gain insights into the legislative process.

**Brand**: The Code We Live By | **Acronym**: CWLB | **Social**: @cwlb

**Mission**: Increase transparency and public understanding of how the nation's laws are created, modified, and maintained.

---

## Table of Contents

1. [Core Concept & Metaphor Mapping](#1-core-concept--metaphor-mapping)
   - [Repository Metaphor](#repository-metaphor)
   - [Understanding the US Code Structure](#understanding-the-us-code-structure)
   - [Repository Structure Mapping](#repository-structure-mapping)
2. [Target Audience](#2-target-audience)
3. [Phase 1 Scope](#3-phase-1-scope)
4. [Core Features](#4-core-features)
   - [Code Browsing ("Repository View")](#41-code-browsing-repository-view)
   - [Law Viewer ("Pull Request View")](#42-law-viewer-pull-request-view)
   - [Search & Discovery](#43-search--discovery)
   - [Analytics & Visualizations](#44-analytics--visualizations)
   - [Integration with Related Resources](#45-integration-with-related-resources)
5. [User Stories](#5-user-stories)
6. [Data Model](#6-data-model)
7. [Technical Architecture](#7-technical-architecture)
8. [User Interface & Experience](#8-user-interface--experience)
9. [Analytics: Key Metrics & Questions](#9-analytics-key-metrics--questions)
10. [Success Metrics](#10-success-metrics)
11. [Privacy & User Data](#11-privacy--user-data)
12. [Future Enhancements (Post-Phase 1)](#12-future-enhancements-post-phase-1)
13. [Technical Challenges & Mitigations](#13-technical-challenges--mitigations)
14. [Open Questions for Further Discussion](#14-open-questions-for-further-discussion)
15. [Development Roadmap](#15-development-roadmap)
16. [Conclusion](#16-conclusion)

**Appendices:**
- [Appendix A: Data Sources](#appendix-a-data-sources)
- [Appendix B: Technical Stack Recommendations](#appendix-b-technical-stack-recommendations)
- [Appendix C: Legal & Disclaimers](#appendix-c-legal--disclaimers)
- [Appendix D: Alternative Repository Structure Mappings](#appendix-d-alternative-repository-structure-mappings)

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

### Positive Law vs Non-Positive Law Titles

A critical distinction in understanding the US Code is that **not all titles carry the same legal authority**. The US Code consists of two types of titles:

**Positive Law Titles (Currently 29 of 54 titles)**
- These titles have been **formally enacted as statutes by Congress**
- They represent official restatements and codifications of federal law
- **The US Code text itself is the authoritative legal text**
- If a conflict exists between the US Code and original Statutes at Large, the US Code prevails
- Congress has designated these titles as "legal evidence" of the law
- Examples from Phase 1 scope:
  - **Title 10 (Armed Forces)** - Enacted as positive law in 1956
  - **Title 17 (Copyright)** - Enacted as positive law in 1976
  - **Title 18 (Crimes and Criminal Procedure)** - Enacted as positive law in 1948

**Non-Positive Law Titles (Currently 25 of 54 titles)**
- These are **editorial compilations** of individually enacted federal statutes
- They have NOT been enacted as a complete title by Congress
- **The Statutes at Large remains the authoritative legal text**
- The US Code text is "prima facie evidence" of the law, but not legally authoritative
- If conflicts exist between the US Code text and Statutes at Large, **Statutes at Large takes precedence**
- These titles are compiled by the Office of the Law Revision Counsel for convenience
- Examples from Phase 1 scope:
  - **Title 20 (Education)** - Not positive law (compilation only)
  - **Title 22 (Foreign Relations)** - Not positive law (compilation only)
  - **Title 26 (Internal Revenue Code)** - Not positive law as a complete title (though the IRC was enacted)
  - **Title 42 (Public Health and Social Welfare)** - Not positive law (compilation only)
  - **Title 50 (War and National Defense)** - Not positive law (compilation only)

**Why This Matters for CWLB:**

1. **Disclaimers**: Users must understand which titles are legally authoritative vs compilations
2. **Attribution**: For non-positive law titles, laws shown in "blame view" modified the Statutes at Large, not necessarily the US Code text directly
3. **UI Indicators**: Visual cues should distinguish positive law from non-positive law sections
4. **Legal Citations**: Lawyers citing non-positive law titles may need to verify against Statutes at Large
5. **Ongoing Codification**: Congress gradually enacts non-positive law titles into positive law (ongoing project since 1926)
6. **Authorship Complexity**: Positive law enactments create a "dual authorship" scenario:
   - **Original authorship**: The law that first created a provision (e.g., Copyright Act of 1909)
   - **Codification authorship**: The positive law enactment that made the US Code text authoritative (e.g., Copyright Act of 1976)
   - The blame view must track both to provide accurate historical context

**Display Recommendations:**
- Show a banner on non-positive law title pages: "This title is a compilation. For authoritative text, consult Statutes at Large."
- Mark positive law titles with a badge: "✓ Positive Law - Authoritative Text"
- Include metadata in section views indicating positive law status
- Link to official Statutes at Large citations for non-positive law provisions

**Authorship and Blame Attribution for Positive Law Titles:**

When a title is enacted as positive law, the blame view faces a dual attribution challenge. Consider Title 17 (Copyright), enacted as positive law in 1976:

*Scenario 1: Provision unchanged by codification*
- Original law: Copyright Act of 1909 created the text
- Codification: Copyright Act of 1976 (PL 94-553) enacted it as positive law
- **Attribution strategy**: Show codification law as primary (it made the text authoritative), with secondary note about original authorship

*Scenario 2: Provision modified during codification*
- Original law: Copyright Act of 1909
- Codification: Copyright Act of 1976 modified the text while codifying
- **Attribution strategy**: Show codification law as primary (it both modified AND codified)

*Scenario 3: Provision amended after codification*
- Original law: Copyright Act of 1909
- Codification: Copyright Act of 1976 (unchanged)
- Amendment: Digital Millennium Copyright Act of 1998 (PL 105-304)
- **Attribution strategy**: Show amendment law (standard blame view behavior), with note that title is positive law

**Recommended Blame View Display:**

```
┌─────────────────────────────────────────────────────────────┐
│ Before Positive Law Enactment (viewing as of 1970)          │
│                                                              │
│ PL 60-349   │ The owner of copyright under this Act shall  │
│ 62nd Cong   │ have the exclusive right to reproduce the    │
│ Taft 1909   │ copyrighted work...                           │
│ ⚠️ Non-PL   │                                               │
│             │ ↑ This title not yet positive law             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ After Positive Law Enactment (viewing as of 1980)           │
│ Text unchanged from 1909 version                            │
│                                                              │
│ PL 94-553   │ Subject to sections 107 through 122, the     │
│ 94th Cong   │ owner of copyright under this title has the  │
│ Ford 1976   │ exclusive rights to do and to authorize any  │
│ ✓ Codified  │ of the following:                             │
│             │                                               │
│             │ 📜 Originally enacted: PL 60-349 (1909)       │
│             │ [Click to view original version]              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ After Amendment to Positive Law (viewing as of 2000)        │
│                                                              │
│ PL 105-304  │ Subject to sections 107 through 122, the     │
│ 105th Cong  │ owner of copyright under this title has the  │
│ Clinton '98 │ exclusive rights to do and to authorize any  │
│ ✓ Positive  │ of the following:                             │
│             │                                               │
│             │ 📜 Title codified: PL 94-553 (1976)           │
│             │ 📜 Originally enacted: PL 60-349 (1909)       │
└─────────────────────────────────────────────────────────────┘
```

**For Non-Positive Law Titles:**
```
┌─────────────────────────────────────────────────────────────┐
│ Non-Positive Law Title (e.g., Title 42)                     │
│                                                              │
│ PL 111-148  │ Each applicable large employer shall...       │
│ 111th Cong  │                                               │
│ Obama 2010  │                                               │
│ ⚠️ Non-PL   │ Modified Statutes at Large (compiled)        │
│             │ [View authoritative Statutes at Large]        │
└─────────────────────────────────────────────────────────────┘
```

**Current Status (as of 2026):**
The Office of the Law Revision Counsel maintains an [official list of positive law titles](https://uscode.house.gov/codification/legislation.shtml). Positive law titles include: 1, 3, 4, 5, 9, 10, 11, 13, 14, 17, 18, 23, 28, 31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 44, 46, 49, 51, 52, 54, and others as they are enacted. The remaining titles are non-positive law compilations.

### Repository Structure Mapping

After evaluating multiple structural approaches (see [Appendix D](#appendix-d-alternative-repository-structure-mappings) for alternatives), we recommend **Section-as-File** mapping:

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

### Why Section-as-File?

1. **Matches legislative practice**: The section is the fundamental unit that Congress modifies (~80% of laws operate at this level)
2. **Optimal diff readability**: Typical laws modify 5-30 sections, producing clean "Files changed" lists
3. **Legal citation alignment**: "17 USC § 106" maps directly to a file path
4. **Scalability**: ~60,000 sections is manageable for modern systems
5. **Historical clarity**: Each section's evolution is tracked independently
6. **Balanced granularity**: Not too coarse (chapters) or too fine (subsections)

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
  - Title 10: Armed Forces ✓ *Positive Law*
  - Title 17: Copyright ✓ *Positive Law*
  - Title 18: Crimes and Criminal Procedure ✓ *Positive Law*
  - Title 20: Education ⚠️ *Non-Positive Law (compilation)*
  - Title 22: Foreign Relations and Intercourse ⚠️ *Non-Positive Law (compilation)*
  - Title 26: Internal Revenue Code (Tax) ⚠️ *Non-Positive Law (compilation)*
  - Title 42: Public Health and Social Welfare ⚠️ *Non-Positive Law (compilation)*
  - Title 50: War and National Defense ⚠️ *Non-Positive Law (compilation)*
  - Additional titles based on public interest and data availability

**Note on Legal Authority:**
- ✓ **Positive Law titles**: The US Code text is legally authoritative
- ⚠️ **Non-Positive Law titles**: The US Code is a compilation; Statutes at Large is authoritative
- See [Section 1: Positive Law vs Non-Positive Law Titles](#positive-law-vs-non-positive-law-titles) for detailed explanation

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
- **Positive law badge**: "✓ Positive Law" for authoritative titles
- **Non-positive law warning**: "⚠️ Compilation - See Statutes at Large" for non-positive law titles
- Banner disclaimers on title and section pages indicating legal authority status

**Legislative Blame View** ("Git Blame" for Laws)
- Line-by-line attribution showing which law last modified each provision
- Powered by **USCodeLine** entity with `last_modified_by_law_id` and `codified_by_law_id` tracking
- Display format for each line/paragraph:
  - **Public Law**: PL number and popular name (e.g., "PL 94-553: Copyright Act of 1976")
  - **Congress**: Which Congress passed it (e.g., "94th Congress")
  - **President**: Who signed it (e.g., "President Gerald Ford")
  - **Date**: When it became effective (e.g., "Oct 19, 1976")
  - **Visual indicator**: Color-coding or sidebar marker showing law attribution
  - **Positive Law badge**: "✓ Positive Law" or "✓ Codified" for positive law titles
  - **Original authorship note**: For codified provisions, secondary note showing original enactment
- Toggle between normal view and blame view
- Hover/click on any line to see:
  - Full metadata about the modifying law
  - Link to view the complete PR (law) that made the change
  - Preview of the diff showing what changed
  - Sponsors and vote counts
  - Hierarchical context (parent lines via tree structure)
- **Deep linking**: Each line has a unique URL for precise citation
  - Format: `https://cwlb.gov/17/106#line-3` or `https://cwlb.gov/17/106#(1)`
  - Share links to specific sentences or list items
- Multi-law sections: Some text may show multiple attributions if different subsections were modified by different laws
- Original enactment indicator: Special styling for text that dates to the section's original creation (via `created_by_law_id`)
- **Positive law attribution**: For positive law titles, show both the codification law and original authorship (see [Positive Law vs Non-Positive Law](#positive-law-vs-non-positive-law-titles) for detailed attribution model)
- **Non-positive law attribution**: Show clear disclaimer that law modified Statutes at Large, compiled into US Code
- User stories:
  - "I want to know when this copyright provision was added"
  - "Which Congress and President are responsible for this tax rule?"
  - "Has this criminal statute been modified since its original enactment?"
  - "When was this title codified as positive law, and what was the original source?"

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
- `is_positive_law`: Boolean (whether this section belongs to a positive law title)
- `title_positive_law_date`: Date (when the title was enacted as positive law, NULL if non-positive law)
- `statutes_at_large_citation`: String (authoritative citation for non-positive law sections)

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

**USCodeLine** (Fine-grained line structure with parent/child tree relationships)
- `line_id`: Primary key
- `section_id`: Foreign key to USCodeSection (which section this belongs to)
- `parent_line_id`: Foreign key to USCodeLine (NULL for root/section heading)
- `line_number`: Integer (sequential within section for ordering: 1, 2, 3...)
- `line_type`: Enum (Heading, Prose, ListItem)
- `text_content`: Text (the actual text of this line)
- `subsection_path`: String (e.g., "(c)(1)(A)(ii)" - for quick lookup and display)
- `depth_level`: Integer (computed from tree depth: 0=root, 1=child of root, etc.)
- `created_by_law_id`: Foreign key to PublicLaw (which law originally created this line)
- `last_modified_by_law_id`: Foreign key to PublicLaw (which law last modified this line)
- `codified_by_law_id`: Foreign key to PublicLaw (which positive law enactment codified this line, NULL if non-positive law or never codified)
- `codification_date`: Date (when this line became part of positive law, NULL if non-positive law)
- `effective_date`: Date (when this version took effect)
- `hash`: String (SHA-256 of text_content, for detecting identical text across versions)

**Note on Positive Law Attribution**: The `is_positive_law` status is inherited from the parent USCodeSection.

**Attribution Logic for Blame View:**
- **Non-positive law titles**: Display `last_modified_by_law_id` with disclaimer "Modified Statutes at Large (compiled into US Code)"
- **Positive law titles (unchanged during codification)**: Display `codified_by_law_id` as primary attribution with secondary note showing `created_by_law_id` as "Originally enacted by..."
- **Positive law titles (modified during codification)**: Display `codified_by_law_id` (serves as both modifier and codifier)
- **Positive law titles (amended after codification)**: Display `last_modified_by_law_id` with note that title is positive law and was codified by `codified_by_law_id`

**Example Queries for Blame View:**

```sql
-- Get blame view with positive law context
SELECT
  l.line_number,
  l.text_content,
  l.subsection_path,
  pl_modified.law_number as last_modified_law,
  pl_modified.popular_name as last_modified_name,
  pl_modified.enacted_date as last_modified_date,
  pl_modified.president as last_modified_president,
  pl_codified.law_number as codified_by_law,
  pl_codified.enacted_date as codification_date,
  pl_created.law_number as originally_created_by,
  pl_created.enacted_date as original_creation_date,
  s.is_positive_law
FROM USCodeLine l
JOIN USCodeSection s ON l.section_id = s.section_id
JOIN PublicLaw pl_modified ON l.last_modified_by_law_id = pl_modified.law_id
LEFT JOIN PublicLaw pl_codified ON l.codified_by_law_id = pl_codified.law_id
LEFT JOIN PublicLaw pl_created ON l.created_by_law_id = pl_created.law_id
WHERE l.section_id = ?
ORDER BY l.line_number;
```

**Why parent/child tree structure?**
- Handles arbitrary nesting depth (US Code can nest 5+ levels deep)
- Natural representation of legal document structure
- Enables precise blame attribution at line level
- Supports deep linking to any sentence or list item
- Simplifies queries for subtree navigation and context display

**Line Types:**
- **Heading**: Any level of heading (section title, subsection header, paragraph label)
- **Prose**: Regular paragraph text
- **ListItem**: Any enumerated item at any nesting level

The tree structure emerges from `parent_line_id`, eliminating the need for fixed "SubsectionHeading" types.

**Example: [17 USC § 106](https://www.law.cornell.edu/uscode/text/17/106)**

| line_id | parent_id | line_# | type | path | depth | text_content |
|---------|-----------|--------|------|------|-------|--------------|
| 100 | NULL | 1 | Heading | NULL | 0 | § 106. Exclusive rights in copyrighted works |
| 101 | 100 | 2 | Prose | NULL | 1 | Subject to sections 107 through 122, the owner of copyright under this title has the exclusive rights to do and to authorize any of the following: |
| 102 | 101 | 3 | ListItem | "(1)" | 2 | to reproduce the copyrighted work in copies or phonorecords; |
| 103 | 101 | 4 | ListItem | "(2)" | 2 | to prepare derivative works based upon the copyrighted work; |
| 104 | 101 | 5 | ListItem | "(3)" | 2 | to distribute copies or phonorecords of the copyrighted work to the public... |

Tree visualization:
```
§ 106 [Heading]
└── Subject to sections 107 through 122... [Prose]
    ├── (1) to reproduce... [ListItem]
    ├── (2) to prepare derivative works... [ListItem]
    ├── (3) to distribute copies... [ListItem]
    ├── (4) to perform publicly... [ListItem]
    ├── (5) to display publicly... [ListItem]
    └── (6) in the case of sound recordings... [ListItem]
```

**Example: [17 USC § 512(c)(1)](https://www.law.cornell.edu/uscode/text/17/512) - Deeply Nested**

| line_id | parent_id | line_# | type | path | depth | text_content |
|---------|-----------|--------|------|------|-------|--------------|
| 200 | NULL | 1 | Heading | NULL | 0 | § 512. Limitations on liability... |
| 201 | 200 | 2 | Heading | "(c)" | 1 | Information residing on systems... |
| 202 | 201 | 3 | Heading | "(c)(1)" | 2 | In general |
| 203 | 202 | 4 | Prose | "(c)(1)" | 3 | A service provider shall not be liable... if the service provider— |
| 204 | 203 | 5 | ListItem | "(c)(1)(A)" | 4 | (A) |
| 205 | 204 | 6 | ListItem | "(c)(1)(A)(i)" | 5 | (i) does not have actual knowledge... |
| 206 | 204 | 7 | ListItem | "(c)(1)(A)(ii)" | 5 | (ii) in the absence of such actual knowledge... |
| 207 | 204 | 8 | ListItem | "(c)(1)(A)(iii)" | 5 | (iii) upon obtaining such knowledge... |
| 208 | 203 | 9 | ListItem | "(c)(1)(B)" | 4 | (B) does not receive a financial benefit... |

Tree visualization:
```
§ 512 [Heading]
└── (c) Information residing... [Heading]
    └── (1) In general [Heading]
        └── A service provider shall not be liable... [Prose]
            ├── (A) [ListItem]
            │   ├── (i) does not have actual knowledge... [ListItem]
            │   ├── (ii) in the absence of... [ListItem]
            │   └── (iii) upon obtaining... [ListItem]
            └── (B) does not receive... [ListItem]
```

**LineHistory** (Historical versions of lines)
- `line_history_id`: Primary key
- `line_id`: Foreign key to USCodeLine
- `version_number`: Integer (1, 2, 3... for each time this line changed)
- `text_content`: Text (historical text at this version)
- `modified_by_law_id`: Foreign key to PublicLaw
- `effective_date`: Date
- `parent_line_id`: Foreign key (parent at this version, may differ from current)

**Key Query Patterns:**

```sql
-- Get all lines in a section (ordered for display)
SELECT * FROM USCodeLine
WHERE section_id = ?
ORDER BY line_number;

-- Get direct children of a line
SELECT * FROM USCodeLine
WHERE parent_line_id = ?
ORDER BY line_number;

-- Get entire subtree (recursive CTE)
WITH RECURSIVE subtree AS (
  SELECT * FROM USCodeLine WHERE line_id = ?
  UNION ALL
  SELECT l.* FROM USCodeLine l
  JOIN subtree s ON l.parent_line_id = s.line_id
)
SELECT * FROM subtree ORDER BY line_number;

-- Get path to root (breadcrumb trail)
WITH RECURSIVE path AS (
  SELECT * FROM USCodeLine WHERE line_id = ?
  UNION ALL
  SELECT l.* FROM USCodeLine l
  JOIN path p ON l.line_id = p.parent_line_id
)
SELECT * FROM path ORDER BY depth_level;

-- Blame view: lines with law attribution
SELECT l.line_number, l.text_content, l.subsection_path,
       pl.law_number, pl.popular_name, pl.enacted_date, pl.president,
       c.congress
FROM USCodeLine l
JOIN PublicLaw pl ON l.last_modified_by_law_id = pl.law_id
WHERE l.section_id = ?
ORDER BY l.line_number;
```

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
  - **Parse sections into USCodeLine tree structure**:
    - Identify headings, prose, and list items
    - Build parent/child relationships based on legal nesting
    - Extract subsection paths (e.g., "(c)(1)(A)(ii)")
    - Compute depth levels for rendering
    - Calculate line hashes for change detection
  - Build historical versions by applying changes chronologically
  - Track line-level attribution (created_by, last_modified_by)
  - Link legislators to sponsorship and votes

- **Challenges**:
  - Older laws may be in PDF/scanned format requiring OCR
  - Legal language parsing is complex (e.g., "Section 106 is amended by striking 'and' and inserting 'or'")
  - **Line parsing complexity**: Determining boundaries between lines (sentence vs. clause vs. list item)
  - **Tree structure inference**: Legal documents don't explicitly mark parent/child relationships
  - Effective dates may differ from enactment dates
  - Scale: Millions of USCodeLine records across ~60,000 sections

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
- Clear disclaimers about positive law vs non-positive law status (see [Appendix C](#appendix-c-legal--disclaimers))
- Users informed about which titles are legally authoritative vs compilations

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

### Challenge: Line-Level Parsing and Tree Structure
Breaking sections into individual lines with parent/child relationships requires sophisticated parsing that doesn't exist in source documents.

**Specific Challenges**:
- **Line boundaries**: What constitutes a "line"? Is "Subject to sections 107 through 122..." one line or multiple?
- **Nested list detection**: Recognizing that "(A)(i)" is a child of "(A)" which is a child of "(1)"
- **Prose vs. list items**: When a paragraph introduces a list with a colon, establishing the parent relationship
- **Multi-paragraph items**: Some list items span multiple paragraphs with complex internal structure
- **Inconsistent formatting**: Not all sections follow the same structural conventions
- **Subsection path extraction**: Parsing "(c)(1)(A)(ii)" from various formats

**Mitigation**:
- **Leverage XML structure**: Office of Law Revision Counsel provides XML with some hierarchical hints
- **Pattern recognition**: Build parser that recognizes common patterns:
  - Lines ending with ":" typically parent the following list
  - Numbered/lettered items are children of preceding prose
  - Indentation in source often indicates nesting depth
- **Heuristic rules**:
  - Complete sentences = Prose lines
  - Numbered items at same level = siblings
  - Items with deeper nesting = children
- **Manual correction interface**: Flag ambiguous cases for human review during ETL
- **Iterative refinement**: Parse simple sections first (like § 106), use as training data
- **Version control parsing rules**: Track parser logic changes to enable re-parsing if rules improve
- **Hash-based change detection**: Use line hashes to detect when text hasn't changed across versions

**Example parsing decision tree**:
```
Input: "(1) In general. A service provider shall not be liable..."

Decision:
- Starts with "(1)" → ListItem type
- Contains period after "general" → Has heading component
- Text after period is prose → Could split or keep together
- Decision: Keep as single ListItem with path "(1)"
- Create child Prose line for the text after "In general."
```

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
Full US Code is ~60,000 sections; with line-level granularity = **millions of USCodeLine records**. With 100+ years of history, LineHistory table could contain tens of millions of records.

**Specific Scale Concerns**:
- Average section has 20-50 lines → 1.2M - 3M current USCodeLine records
- Each line may have 5-10 historical versions → 10M - 30M LineHistory records
- Blame queries joining lines to laws across large datasets
- Deep tree traversals (recursive CTEs) for nested sections
- Full-text search across millions of line records

**Mitigation**:
- **Database optimization**:
  - Efficient indexing on section_id, parent_line_id, line_number
  - Materialized views for common queries (e.g., current section with all lines)
  - Partition LineHistory table by date ranges
  - Use PostgreSQL's recursive CTE optimization
- **Query strategies**:
  - Lazy loading: Load section headings first, expand on demand
  - Pagination for blame view (show first 100 lines)
  - Cache entire sections with line trees in Redis
  - Pre-compute depth_level and subsection_path during ETL
- **Storage optimization**:
  - Compress historical text (many lines unchanged across versions)
  - Use line hashes to detect duplicates
  - Archive very old versions to cold storage
- **CDN**: Serve pre-rendered section HTML for common sections
- **Horizontal scaling**: Partition database by Title for read replicas

### Challenge: Legal Accuracy
Displaying legal text requires precision; errors could mislead users.

**Mitigation**:
- Canonical source: Official US Code from House OLC
- Regular synchronization with official sources
- Clear disclaimers about unofficial nature
- Feedback mechanism for reporting errors

### Challenge: Positive Law Attribution and Codification Tracking

When a title is enacted as positive law, it creates complex attribution scenarios that must be accurately tracked and displayed.

**Specific Challenges**:
- **Dual authorship**: Text may have been originally enacted decades before positive law codification (e.g., 1909 Copyright Act provision codified in 1976 Copyright Act)
- **Text changes during codification**: Some provisions are modified, reorganized, or renumbered during positive law enactment, requiring tracking of both original and codified versions
- **Historical accuracy**: Before codification date, blame should show pre-positive law attribution; after codification, should show codification law
- **Mixed titles**: Phase 1 includes both positive law (10, 17, 18) and non-positive law (20, 22, 26, 42, 50) titles requiring different attribution strategies
- **Retroactive codification tracking**: Historical blame view must show correct attribution for dates before positive law enactment
- **Data source challenges**: Determining which provisions were unchanged vs modified during codification requires comparing original Statutes at Large with positive law enactment text

**Mitigation**:
- **Extended data model**: Add `codified_by_law_id` and `codification_date` to USCodeLine entity
- **Three-tier attribution tracking**:
  - `created_by_law_id`: Original law that first created the provision
  - `codified_by_law_id`: Positive law enactment (if applicable)
  - `last_modified_by_law_id`: Most recent modification
- **Historical versioning**: LineHistory table tracks full attribution context at each point in time
- **UI logic**: Display appropriate attribution based on:
  - Is title positive law? (check `is_positive_law`)
  - Has line been modified since codification? (compare `last_modified_by_law_id` vs `codified_by_law_id`)
  - Is user viewing historical version before codification? (check date vs `codification_date`)
- **Source verification**: Cross-reference Office of Law Revision Counsel's positive law enactment documentation to identify unchanged vs modified provisions
- **Clear UI indicators**: Use badges ("✓ Positive Law", "✓ Codified", "⚠️ Non-PL") and secondary notes ("Originally enacted by PL X") to communicate attribution complexity
- **Comprehensive testing**: Create test cases for all attribution scenarios using Title 17 (codified 1976) and Title 10 (codified 1956) as examples

**Example Scenarios to Handle:**

1. **Scenario**: User views 17 USC § 106 as of 1970 (before positive law)
   - **Display**: PL 60-349 (1909) with "⚠️ Non-PL" badge

2. **Scenario**: User views 17 USC § 106 as of 1980 (after codification, before DMCA)
   - **Display**: PL 94-553 (1976) with "✓ Codified" badge + note "Originally: PL 60-349 (1909)"

3. **Scenario**: User views 17 USC § 106 as of 2000 (after DMCA amendment)
   - **Display**: PL 105-304 (1998) with "✓ Positive Law" badge + secondary notes showing codification and original authorship

4. **Scenario**: User views 42 USC § 18001 (Affordable Care Act, non-positive law title)
   - **Display**: PL 111-148 (2010) with "⚠️ Non-PL" badge + "Modified Statutes at Large (compiled)"

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

**General Disclaimer:**
- This is an unofficial presentation of the US Code
- Official version is maintained by the Office of the Law Revision Counsel at uscode.house.gov
- This platform is not legal advice and should not be relied upon for legal decisions
- Always consult the official sources and a qualified attorney for legal matters

**Positive Law vs Non-Positive Law Titles:**

The US Code contains two types of titles with different legal authority:

1. **Positive Law Titles** (e.g., Titles 10, 17, 18):
   - The US Code text displayed here is the **legally authoritative source**
   - These titles have been enacted by Congress as statutes
   - In case of conflicts, the US Code text prevails over earlier Statutes at Large

2. **Non-Positive Law Titles** (e.g., Titles 20, 22, 26, 42, 50):
   - The US Code text displayed here is an **editorial compilation only**
   - These titles are "prima facie evidence" of the law, but **NOT legally authoritative**
   - The **Statutes at Large is the authoritative source** for these titles
   - In case of conflicts between US Code and Statutes at Large, **Statutes at Large prevails**
   - Users citing these provisions should verify against the original Statutes at Large

**Disclaimer Language for Platform:**

For Positive Law Title Pages:
> "This title has been enacted as positive law. The text displayed here represents the legally authoritative US Code. However, this is an unofficial presentation. For official citations, consult uscode.house.gov."

For Non-Positive Law Title Pages:
> "⚠️ This title is a non-positive law compilation. The text displayed is an editorial compilation and is NOT legally authoritative. For authoritative text, consult the Statutes at Large. This is an unofficial presentation for informational purposes only."

**Data Licensing:**
- All US Code text is in the public domain as government work
- Legislative data is sourced from official government APIs and databases
- This platform's presentation, analytics, and UI are subject to the project's open-source license
- Users may freely use, copy, and distribute the government data

## Appendix D: Alternative Repository Structure Mappings

This appendix presents alternative approaches to mapping the US Code structure to repository files. The main specification recommends **Section-as-File** (see Section 1), but these alternatives were considered during design.

### Option 2: Chapter-as-File

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

**Verdict**: Too coarse-grained for the use case. Would make diffs unwieldy and obscure the section-level changes that are fundamental to legislation.

---

### Option 3: Subsection-as-File

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

**Verdict**: Too fine-grained. Creates an overwhelming number of files and doesn't match how laws are typically cited or modified.

---

### Option 4: Hybrid Section-as-File with Subsection Anchors

**Structure:**
Same as recommended Section-as-File approach, but with enhanced deep linking:

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

**Verdict**: Strong alternative that could be adopted in Phase 2 for enhanced functionality. Maintains the benefits of Section-as-File while adding subsection-level precision through anchors rather than file structure.
