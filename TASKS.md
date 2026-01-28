# CWLB Implementation Tasks

This document translates the CWLB specification into an actionable backlog of implementation tasks, organized by phase and feature area.

---

## Phase 0: Research & Validation (2-3 months)

### Data Source Assessment
- [x] **Task 0.1**: Evaluate US House Office of Law Revision Counsel API/data formats ✅
  - Test XML/JSON structure for US Code sections
  - Assess completeness and update frequency
  - Document data schema and available metadata
  - **Completed**: See [research/TASK-0.1-OLRC-Data-Evaluation.md](research/TASK-0.1-OLRC-Data-Evaluation.md)

- [x] **Task 0.2**: Evaluate GovInfo.gov API for Public Laws ✅
  - Test API endpoints for Public Law documents
  - Assess historical coverage (how far back does structured data go?)
  - Document required API keys and rate limits
  - **Completed**: See [research/TASK-0.2-GovInfo-API-Evaluation.md](research/TASK-0.2-GovInfo-API-Evaluation.md)

- [x] **Task 0.3**: Evaluate Congress.gov API for bill information ✅
  - Test bill metadata endpoints
  - Assess legislator data availability
  - Document sponsor, co-sponsor, and vote record access
  - **Completed**: See [research/TASK-0.3-Congress-API-Evaluation.md](research/TASK-0.3-Congress-API-Evaluation.md)

- [x] **Task 0.4**: Research ProPublica Congress API for legislator details ✅
  - Test endpoints for legislator photos, party, state
  - Assess historical legislator data coverage
  - Document data freshness and update schedule
  - **Completed**: See [research/TASK-0.4-ProPublica-API-Evaluation.md](research/TASK-0.4-ProPublica-API-Evaluation.md)
  - **Note**: ProPublica API discontinued July 2024. Congress.gov API (Task 0.3) is superior alternative.

### Prototype Parser Development
- [x] **Task 0.5**: Build prototype parser for single Public Law (e.g., PL 94-553) ✅
  - Parse law metadata (number, date, sponsors)
  - Extract section changes from legal language
  - Generate diff between old and new text
  - **Completed**: See [research/TASK-0.5-Prototype-Parser.md](research/TASK-0.5-Prototype-Parser.md)
  - **Deliverables**: Jupyter notebook and Python script in `/prototypes` and `/notebooks`
  - **Key Finding**: Automated parsing feasible with 80% accuracy; recommend hybrid approach with manual review

- [x] **Task 0.6**: Build prototype line-level parser for one section (e.g., 17 USC § 106) ✅
  - Parse section into individual lines
  - Build parent/child tree structure
  - Extract subsection paths (e.g., "(1)", "(c)(1)(A)")
  - Calculate depth levels
  - **Completed**: See [research/TASK-0.6-0.7-Line-Level-Parser.md](research/TASK-0.6-0.7-Line-Level-Parser.md)
  - **Deliverables**: Python script in `/prototypes/line_level_parser_prototype.py`

- [x] **Task 0.7**: Test parser on complex nested section (e.g., 17 USC § 512(c)) ✅
  - Validate tree structure for deeply nested subsections
  - Test edge cases (multi-paragraph list items, ambiguous nesting)
  - Document parsing challenges and heuristics
  - **Completed**: See [research/TASK-0.6-0.7-Line-Level-Parser.md](research/TASK-0.6-0.7-Line-Level-Parser.md)
  - **Key Finding**: Parser correctly handles 4+ depth levels of nesting

### Title Selection
- [ ] **Task 0.8**: Finalize 5-10 titles for Phase 1 based on:
  - Public interest and relevance
  - Data availability and quality
  - Legislative activity volume (balance stable vs frequently updated)
  - Confirmed selection: Titles 10, 17, 18, 20, 22, 26, 42, 50

### User Research
- [ ] **Task 0.9**: Conduct user interviews with target audience segments
  - Citizens interested in civic engagement
  - Educators teaching civics or government
  - Journalists covering policy/legislation
  - Researchers studying legislative patterns

- [ ] **Task 0.10**: Create user personas and key user journeys
  - Document primary use cases and pain points
  - Prioritize features based on user needs
  - Define success criteria from user perspective

### Technical Architecture Design
- [x] **Task 0.11**: Design database schema (see Section 6 of spec) ✅
  - Define tables: USCodeSection, PublicLaw, LawChange, USCodeLine, etc.
  - Document relationships and foreign keys
  - Plan indexing strategy for performance
  - **Completed**: See [research/TASK-0.11-Database-Schema-Design.md](research/TASK-0.11-Database-Schema-Design.md)
  - **Deliverables**: SQL schema in `/prototypes/database_schema.sql` (22 tables, 85+ indexes, 3 materialized views)
  - **Key Decisions**: PostgreSQL 15+, Alembic migrations, version tables for temporal data

- [x] **Task 0.12**: Design API architecture ✅
  - RESTful or GraphQL decision
  - Define key endpoints (browse code, view law, search, analytics)
  - Document request/response formats
  - **Completed**: See [research/TASK-0.12-API-Architecture-Design.md](research/TASK-0.12-API-Architecture-Design.md)
  - **Key Decisions**: RESTful API (better caching, simpler), 27 endpoints across 6 API areas, JSON responses
  - **Deliverables**: Full endpoint specifications with request/response examples, OpenAPI schema outline

- [x] **Task 0.13**: Select technology stack ✅
  - Frontend: React/Next.js vs alternatives
  - Backend: Node.js/Python decision
  - Database: PostgreSQL + Elasticsearch setup
  - Hosting platform: AWS/GCP/Azure decision
  - **Completed**: See [research/TASK-0.13-Technology-Stack-Selection.md](research/TASK-0.13-Technology-Stack-Selection.md)
  - **Key Decisions**: Monolith architecture, React + Python/FastAPI, PostgreSQL (Cloud SQL), GCP Cloud Run (scales to zero)
  - **Cost**: ~$10/month idle, ~$30-40/month with moderate traffic

- [x] **Task 0.14**: Design data pipeline architecture ✅
  - ETL process flow diagram
  - Ingestion frequency and update strategy
  - Error handling and data validation approach
  - **Completed**: See [research/TASK-0.14-Data-Pipeline-Architecture.md](research/TASK-0.14-Data-Pipeline-Architecture.md)

---

## Phase 1: MVP (6-9 months)

### Infrastructure Setup
- [ ] **Task 1.1**: Set up development environment
  - Initialize Git repository
  - Configure linting, formatting, testing tools
  - Set up CI/CD pipeline (GitHub Actions or equivalent)

- [ ] **Task 1.2**: Set up PostgreSQL database
  - Provision database instance
  - Create initial schema (core tables)
  - Set up migration tooling (e.g., Prisma, Alembic)

- [ ] **Task 1.3**: Set up Elasticsearch for full-text search
  - Provision Elasticsearch instance
  - Configure indices for sections and laws
  - Set up synchronization from PostgreSQL

- [ ] **Task 1.4**: Set up Redis for caching
  - Provision Redis instance
  - Configure caching strategy for frequently accessed sections

- [ ] **Task 1.5**: Set up hosting infrastructure
  - Provision cloud resources (compute, storage)
  - Configure CDN for static assets
  - Set up monitoring and logging (e.g., Datadog, Sentry)

### Data Pipeline - Core Implementation
- [ ] **Task 1.6**: Implement US Code section ingestion
  - Fetch current US Code data for selected titles
  - Parse XML/JSON into database format
  - Store in USCodeSection table

- [ ] **Task 1.7**: Implement Public Law ingestion
  - Fetch Public Law documents from GovInfo
  - Parse law metadata (number, date, sponsors, president)
  - Store in PublicLaw table

- [ ] **Task 1.8**: Implement legislator data ingestion
  - Fetch legislator data from ProPublica/Congress.gov
  - Parse legislator details (name, party, state, photo)
  - Store in Legislator table
  - Link sponsors to laws via Sponsorship table

- [ ] **Task 1.9**: Implement vote record ingestion
  - Fetch voting records for laws
  - Parse votes by legislator (Yea, Nay, Present, Not Voting)
  - Store in Vote table

### Data Pipeline - Law Change Parsing
- [ ] **Task 1.10**: Build legal language parser for common amendment patterns
  - "Section X is amended by striking Y and inserting Z"
  - "Section X is amended by adding at the end the following"
  - "Section X is repealed"
  - Document supported patterns and limitations

- [ ] **Task 1.11**: Implement diff generation for law changes
  - Compare old text vs new text for modified sections
  - Calculate line-by-line diffs
  - Store in LawChange table

- [ ] **Task 1.12**: Build manual review interface for complex amendments
  - Flag ambiguous legal language for human review
  - UI for reviewing and correcting parsed changes
  - Approval workflow before committing to database

### Data Pipeline - Line-Level Parsing
- [ ] **Task 1.13**: Implement line-level parser for sections
  - Parse section text into individual lines
  - Identify line types (Heading, Prose, ListItem)
  - Extract subsection paths (e.g., "(1)", "(c)(1)(A)")
  - Store in USCodeLine table

- [ ] **Task 1.14**: Build parent/child tree structure for lines
  - Detect nesting relationships using heuristics (indentation, numbering)
  - Set parent_line_id for each line
  - Calculate depth_level from tree structure
  - Validate tree integrity (no orphans, no cycles)

- [ ] **Task 1.15**: Implement line-level attribution (blame functionality)
  - For each line, determine which law created it (created_by_law_id)
  - For each line, determine which law last modified it (last_modified_by_law_id)
  - Handle edge cases (original enactment, multiple modifications)

- [ ] **Task 1.16**: Implement line hash calculation for change detection
  - Calculate SHA-256 hash of text_content for each line
  - Use hashes to detect unchanged lines across versions
  - Optimize storage by avoiding duplicate text

### Data Pipeline - Historical Depth
- [ ] **Task 1.17**: Ingest historical Public Laws (last 20 years as MVP scope)
  - Fetch laws from ~2004 to present for selected titles
  - Parse and store in chronological order
  - Build historical versions incrementally

- [ ] **Task 1.18**: Build SectionHistory records
  - For each law that modifies a section, create snapshot
  - Store full text at that point in time
  - Link to law_id and effective_date

- [ ] **Task 1.19**: Build LineHistory records
  - For each law that modifies specific lines, create version records
  - Store historical text_content, parent relationships
  - Enable time-travel at line granularity

### Backend API Development
- [ ] **Task 1.20**: Implement Code Browsing API endpoints
  - `GET /api/titles` - List all titles
  - `GET /api/titles/:title/chapters` - List chapters in a title
  - `GET /api/titles/:title/chapters/:chapter/sections` - List sections
  - `GET /api/sections/:title/:section` - Get full section content
  - `GET /api/sections/:title/:section/lines` - Get line-level structure

- [ ] **Task 1.21**: Implement Law Viewer API endpoints
  - `GET /api/laws/:lawId` - Get law metadata and summary
  - `GET /api/laws/:lawId/changes` - Get all section changes for a law
  - `GET /api/laws/:lawId/diff/:sectionId` - Get diff for specific section
  - `GET /api/laws/:lawId/sponsors` - Get sponsors and co-sponsors
  - `GET /api/laws/:lawId/votes` - Get vote records

- [ ] **Task 1.22**: Implement Search API endpoints
  - `GET /api/search/sections?q=query` - Full-text search within code
  - `GET /api/search/laws?q=query` - Search laws by name/number/keyword
  - Support filters (date range, title, sponsor)

- [ ] **Task 1.23**: Implement Time Travel API
  - `GET /api/sections/:title/:section/history` - Get all versions of section
  - `GET /api/sections/:title/:section/at/:date` - Get section as of specific date
  - `GET /api/sections/:title/:section/compare?from=date1&to=date2` - Compare versions

- [ ] **Task 1.24**: Implement Blame View API
  - `GET /api/sections/:title/:section/blame` - Get line-by-line attribution
  - Include law metadata (PL number, Congress, President, date) for each line
  - Support deep linking to specific lines

### Frontend Development - Core UI
- [ ] **Task 1.25**: Set up Next.js project structure
  - Initialize Next.js with TypeScript
  - Configure Tailwind CSS for styling
  - Set up component library structure

- [ ] **Task 1.26**: Build main navigation and layout
  - Header with logo and main nav (Explore Code, View Laws, Analytics, About)
  - Footer with disclaimers and links
  - Responsive design for mobile/tablet/desktop

- [ ] **Task 1.27**: Build Title/Chapter/Section navigation tree
  - Hierarchical navigation component (collapsible tree)
  - Breadcrumb trail showing current location
  - File path-style display (USC/Title-17/Chapter-1/Section-106)

### Frontend Development - Code Browser
- [ ] **Task 1.28**: Build Section Viewer component
  - Display section heading and full text
  - Clean, readable formatting with proper legal citations
  - "Last modified" timestamp and link to modifying law

- [ ] **Task 1.29**: Build Blame View component
  - Toggle between Normal and Blame views
  - Display law attribution for each line in sidebar
  - Format: PL number, Congress, President, date
  - Hover/click for full law details
  - Color-coding or visual indicators for different laws

- [ ] **Task 1.30**: Implement deep linking to specific lines
  - URL format: `/17/106#line-3` or `/17/106#(1)`
  - Scroll to line on page load
  - Highlight target line
  - Share button for copying line URLs

- [ ] **Task 1.31**: Build Time Travel UI
  - Date picker for selecting historical snapshot
  - Timeline scrubber for browsing over time
  - "What changed" summary when viewing historical version
  - Permalink to specific version (e.g., "Section 106 as of July 4, 1976")

### Frontend Development - Law Viewer
- [ ] **Task 1.32**: Build Law Details page
  - Display PL number, popular name, summary
  - Show metadata panel (sponsors, reviewers, timeline, impact)
  - Tabs for Conversation, Files Changed, Related Resources

- [ ] **Task 1.33**: Build Diff Viewer component
  - Line-by-line diff with color-coding (red=deleted, green=added, yellow=modified)
  - Side-by-side or unified diff toggle
  - Collapsible sections for multi-section changes

- [ ] **Task 1.34**: Build Sponsors & Reviewers panel
  - Display sponsor photos, names, party, state
  - Show co-sponsors (collapsible list)
  - Display vote counts and breakdown (House, Senate, President)

- [ ] **Task 1.35**: Build Legislative Journey Timeline
  - Visual timeline showing bill progress
  - Milestones: Introduced → Committee → House → Senate → President → Effective
  - Display key dates at each stage

### Frontend Development - Search
- [ ] **Task 1.36**: Build Search interface
  - Search bar with autocomplete suggestions
  - Tabs for searching Sections vs Laws
  - Results page with snippet previews and highlighting

- [ ] **Task 1.37**: Build Advanced Filters component
  - Date range picker
  - Title/Chapter selector
  - Sponsor selector (autocomplete)
  - Vote margin filter (unanimous vs contested)
  - Sort options (relevance, date, impact)

### Analytics - Basic Implementation
- [ ] **Task 1.38**: Implement basic analytics queries
  - Laws enacted per Congressional session
  - Sections modified per session
  - Lines added/removed per session

- [ ] **Task 1.39**: Build Legislative Activity Over Time chart
  - Line/bar chart showing laws enacted by Congress
  - X-axis: Congressional sessions
  - Y-axis: Count of laws, sections modified, or lines changed
  - Interactive tooltips with details

- [ ] **Task 1.40**: Build simple analytics dashboard page
  - Display 2-3 key visualizations
  - Filters for date range and Congress selection
  - Export data as CSV option

### Testing & Quality Assurance
- [ ] **Task 1.41**: Write unit tests for parser logic
  - Test legal language parsing patterns
  - Test line-level parsing and tree building
  - Test diff generation

- [ ] **Task 1.42**: Write integration tests for API endpoints
  - Test all GET endpoints
  - Test search functionality
  - Test time travel queries

- [ ] **Task 1.43**: Write E2E tests for critical user flows
  - Browse code navigation
  - View law and diff
  - Search and results
  - Time travel functionality

- [ ] **Task 1.44**: Conduct manual QA testing
  - Test across browsers (Chrome, Firefox, Safari)
  - Test on mobile devices
  - Test accessibility (screen readers, keyboard navigation)

- [ ] **Task 1.45**: Legal accuracy review
  - Compare displayed text to official US Code sources
  - Verify diff accuracy against Public Law documents
  - Document disclaimers about unofficial status

### Deployment & Launch
- [ ] **Task 1.46**: Set up production environment
  - Provision production database, cache, search instances
  - Configure production hosting and CDN
  - Set up SSL certificates

- [ ] **Task 1.47**: Perform load testing and optimization
  - Test with realistic traffic patterns
  - Identify and fix performance bottlenecks
  - Optimize database queries and caching

- [ ] **Task 1.48**: Create user documentation
  - Write "About" page explaining the project
  - Create glossary of legislative terms
  - Write FAQ

- [ ] **Task 1.49**: Public beta launch
  - Deploy to production
  - Announce to target user communities
  - Set up feedback collection mechanism (e.g., feedback form, GitHub issues)

---

## Phase 2: Enhancement (6-9 months)

### Time Travel - Full Implementation
- [ ] **Task 2.1**: Extend historical data ingestion to full depth
  - Ingest all historical Public Laws back to original enactment
  - Build complete SectionHistory for all covered titles
  - Handle pre-digital records (OCR, manual digitization)

- [ ] **Task 2.2**: Optimize time travel queries for performance
  - Index SectionHistory by effective_date
  - Cache common historical snapshots in Redis
  - Implement lazy loading for very old versions

- [ ] **Task 2.3**: Build enhanced Timeline Scrubber UI
  - Visual representation of modification frequency over time
  - Thumbnail previews of major changes
  - Keyboard shortcuts for navigation (arrow keys)

### Advanced Search
- [ ] **Task 2.4**: Implement advanced full-text search with Elasticsearch
  - Fuzzy matching and typo tolerance
  - Phrase search and proximity search
  - Boosting by relevance factors (recent, frequently accessed)

- [ ] **Task 2.5**: Build Saved Searches feature
  - User accounts for saving searches (optional login)
  - Store search criteria and rerun later
  - Alert notifications when new results match saved search

- [ ] **Task 2.6**: Build Search Results page enhancements
  - Faceted navigation (filter by Title, Congress, etc.)
  - Search within results
  - Export results to CSV/JSON

### Analytics - Comprehensive Dashboard
- [ ] **Task 2.7**: Implement Focus Area Analysis queries
  - Calculate legislative activity by Title over time
  - Identify "hot zones" of change
  - Compare focus areas across different Congresses

- [ ] **Task 2.8**: Build Focus Area visualizations
  - Stacked area chart showing Title modifications over time
  - Pie chart of activity by Title for selected Congress
  - Heatmap of US Code structure colored by change frequency

- [ ] **Task 2.9**: Implement Law Scope Metrics
  - Calculate breadth (sections affected) for each law
  - Calculate depth (lines changed) for each law
  - Calculate focus score: narrow vs broad laws

- [ ] **Task 2.10**: Build Law Scope visualizations
  - Distribution histogram (X=sections affected, Y=count of laws)
  - Identify and highlight omnibus bills vs targeted amendments
  - Examples of narrowest and broadest laws

- [ ] **Task 2.11**: Implement Congressional Productivity Comparison
  - Aggregate metrics by Congress (total laws, sections, lines, time to passage)
  - Calculate bipartisan vs party-line vote percentages
  - Identify most productive vs least productive Congresses

- [ ] **Task 2.12**: Build Congressional Productivity visualizations
  - Sortable comparison table
  - Bar charts comparing key metrics
  - Control for unified vs divided government context

- [ ] **Task 2.13**: Implement Contributor Statistics
  - Most active sponsors (by law count, by impact)
  - Collaboration networks (who co-sponsors together)
  - Bipartisan index for each legislator

- [ ] **Task 2.14**: Build Contributor visualizations
  - Network graph showing sponsor collaboration
  - Leaderboards for most active legislators
  - Specialization charts (which Titles each legislator focuses on)

- [ ] **Task 2.15**: Build comprehensive Analytics Dashboard
  - Multiple tabs for different analysis types
  - Interactive filters (date range, Congress, Title, sponsor)
  - Export all visualizations as images or data files
  - Embeddable widgets for external sites

### Integration with External Resources
- [ ] **Task 2.16**: Implement links to Congress.gov
  - Link to bill text, reports, debates for each law
  - Fetch and cache relevant URLs during ingestion
  - Display as "View on Congress.gov" button

- [ ] **Task 2.17**: Implement links to GovInfo
  - Link to official Public Law PDF documents
  - Display as "Official document (PDF)" link

- [ ] **Task 2.18**: Implement links to Supreme Court cases
  - Identify cases citing specific sections (via Courtlistener or similar)
  - Display "Cited by X Supreme Court cases" with links

- [ ] **Task 2.19**: Implement links to CFR (Code of Federal Regulations)
  - Identify regulations implementing specific statutes
  - Display "Related regulations" section

- [ ] **Task 2.20**: Build Citation Tools
  - Generate properly formatted legal citations (Bluebook format)
  - Export to citation managers (BibTeX, Zotero)
  - Copy citation to clipboard

### User Accounts & Personalization
- [ ] **Task 2.21**: Implement optional user authentication
  - OAuth or email/password login
  - Store minimal user data (email, preferences)
  - Privacy-focused: no tracking, no data selling

- [ ] **Task 2.22**: Implement Bookmarks feature
  - Save favorite sections or laws
  - Organize bookmarks into collections
  - Sync across devices via user account

- [ ] **Task 2.23**: Implement Annotations feature (private)
  - Add personal notes to specific sections or lines
  - Tag and organize notes
  - Search within personal annotations

- [ ] **Task 2.24**: Build user dashboard
  - View saved searches, bookmarks, annotations
  - Activity feed of recently viewed content
  - Personalized recommendations

### Performance Optimization
- [ ] **Task 2.25**: Optimize database queries
  - Add missing indices based on production query patterns
  - Create materialized views for expensive aggregations
  - Implement query result caching with smart invalidation

- [ ] **Task 2.26**: Optimize frontend bundle size
  - Code splitting for large visualizations
  - Lazy loading of non-critical components
  - Image and asset optimization

- [ ] **Task 2.27**: Implement CDN caching strategy
  - Cache static sections that rarely change
  - Cache-control headers for different content types
  - Purge cache on data updates

- [ ] **Task 2.28**: Implement API rate limiting and throttling
  - Protect against abuse
  - Fair usage quotas for anonymous vs authenticated users
  - Monitor and alert on unusual traffic patterns

### Educational Resources
- [ ] **Task 2.29**: Create "How a Bill Becomes a Law" explainer
  - Interactive diagram with examples from CWLB data
  - Glossary of legislative terms (introduced, enacted, vetoed, etc.)
  - Link from Law Viewer pages

- [ ] **Task 2.30**: Create guided tours
  - "The journey of the ADA" - follow ADA through history
  - "How copyright law evolved" - see changes over decades
  - "Understanding tax code changes" - explore Title 26

- [ ] **Task 2.31**: Build educator resources
  - Lesson plans for civics classes
  - Student activities using CWLB
  - Links to curriculum standards

---

## Phase 3: Scale & Engage (Ongoing)

### Expanded Coverage
- [ ] **Task 3.1**: Ingest all 54 US Code titles
  - Extend data pipeline to cover remaining titles
  - Prioritize based on public interest and legislative activity
  - Monitor storage and performance impact

- [ ] **Task 3.2**: Backfill complete historical depth for all titles
  - Continue historical data ingestion (pre-2004)
  - Handle pre-digital sources (OCR, manual review)
  - Partner with libraries or legal tech companies for digitization

### Proposed Bills ("Open PRs") - Priority Future Feature
- [ ] **Task 3.3**: Implement Bill entity and ingestion
  - Fetch current bills from Congress.gov
  - Store in Bill table with status (Introduced, In Committee, etc.)
  - Track bill amendments as the bill progresses

- [ ] **Task 3.4**: Implement ProposedChange entity
  - Calculate proposed diffs (what would change if bill passes)
  - Store in ProposedChange table
  - Handle cases where bill targets new sections (additions)

- [ ] **Task 3.5**: Build "Open PRs" view
  - List current bills awaiting action
  - Display as PRs with status badges (In Committee, Scheduled for Vote, etc.)
  - Show proposed diffs

- [ ] **Task 3.6**: Implement real-time status updates
  - Set up webhooks or polling for Congress.gov updates
  - Update bill status automatically
  - Notify users watching specific bills

### Failed Legislation ("Closed/Rejected PRs")
- [ ] **Task 3.7**: Ingest historical failed bills
  - Fetch bills that died in committee, failed votes, or were vetoed
  - Store with status (Failed, Vetoed, Died in Committee)
  - Link to related_law_id if eventually reintroduced and passed

- [ ] **Task 3.8**: Build "Closed/Rejected PRs" view
  - Display failed bills with context (why they failed)
  - Show voting records for failed votes
  - Compare similar bills across sessions

- [ ] **Task 3.9**: Build success/failure analytics
  - Calculate pass rate by topic, sponsor, Congress
  - Visualize "bill graveyard" - common failure points
  - Identify bills that were repeatedly attempted

### Dependency Graph
- [ ] **Task 3.10**: Implement SectionReference entity and detection
  - Parse section text to detect citations to other sections
  - Extract reference text and target section
  - Store in SectionReference table with type (Explicit, Cross-reference, etc.)

- [ ] **Task 3.11**: Build Section Dependency API
  - `GET /api/sections/:title/:section/references` - Sections this one references
  - `GET /api/sections/:title/:section/referenced-by` - Sections referencing this one
  - Calculate reference counts and rank by importance

- [ ] **Task 3.12**: Build Dependency Graph visualization
  - Interactive network graph using D3.js force-directed layout
  - Nodes = sections, edges = references
  - Color-code by Title, size by reference count
  - Zoom and pan controls
  - Click node to navigate to that section

- [ ] **Task 3.13**: Build Impact Analysis feature
  - "If this section changes, these X sections might be affected"
  - Highlight downstream dependencies
  - Use case: assess impact of proposed amendments

### Conversation Tab (for Laws)
- [ ] **Task 3.14**: Ingest congressional debate excerpts
  - Fetch floor debate transcripts from Congress.gov
  - Parse and extract relevant excerpts for each law
  - Store as conversation entries linked to law

- [ ] **Task 3.15**: Ingest committee hearing summaries
  - Fetch hearing transcripts and testimony
  - Summarize key points
  - Link to law timeline (pre-passage stage)

- [ ] **Task 3.16**: Build Conversation tab UI
  - Chronological display of debates, hearings, amendments
  - Searchable and filterable
  - Link to external sources for full transcripts

- [ ] **Task 3.17**: Integrate media coverage and expert analysis
  - Curate links to news articles about major laws
  - Aggregate expert commentary from think tanks, legal scholars
  - Display as "Related commentary" section

### Community Features
- [ ] **Task 3.18**: Implement public annotations (moderated)
  - Allow users to submit annotations on sections
  - Moderation queue for reviewing before publication
  - Voting/ranking system for helpful annotations

- [ ] **Task 3.19**: Implement discussion forums
  - Per-section discussion threads
  - Per-law discussion threads
  - Moderation tools

- [ ] **Task 3.20**: Implement crowdsourced plain-language summaries
  - Users can submit ELI5 explanations of complex sections
  - Community voting for best summaries
  - Editorial review for accuracy

- [ ] **Task 3.21**: Build reputation system
  - Points for contributions (annotations, summaries, reports)
  - Badges for milestones (100 helpful annotations, etc.)
  - Leaderboard of top contributors

### API for Researchers
- [ ] **Task 3.22**: Build comprehensive public API
  - Document all endpoints with OpenAPI/Swagger
  - Provide API keys for authenticated access
  - Set usage quotas (free tier, research tier, commercial tier)

- [ ] **Task 3.23**: Implement bulk data export
  - Download entire datasets as CSV/JSON/SQL dumps
  - Regular snapshots (monthly or quarterly)
  - Versioned exports for reproducibility

- [ ] **Task 3.24**: Build API documentation site
  - Interactive API explorer
  - Code examples in multiple languages (Python, JavaScript, R)
  - Use case tutorials for researchers

### Mobile Optimization
- [ ] **Task 3.25**: Improve responsive design for mobile
  - Optimize navigation for small screens
  - Touch-friendly controls for timeline scrubber
  - Simplified visualizations for mobile

- [ ] **Task 3.26**: Implement Progressive Web App (PWA)
  - Service worker for offline access
  - Install prompt for add-to-home-screen
  - Push notifications for alerts (if user opts in)

- [ ] **Task 3.27**: Consider native mobile apps (iOS/Android)
  - Evaluate need based on user demand
  - Design mobile-specific features (e.g., barcode scan for US Code citations)

### Advanced Features - Future Exploration
- [ ] **Task 3.28**: Natural Language Query interface
  - "Show me all environmental laws passed in the 1970s"
  - Use NLP to parse intent and execute appropriate queries
  - Display results as conversational responses

- [ ] **Task 3.29**: Predictive Analytics
  - Identify sections likely to be modified soon based on patterns
  - Predict bill passage likelihood using ML models
  - Alert users to emerging legislative trends

- [ ] **Task 3.30**: Alert System
  - Subscribe to notifications for specific sections, titles, or topics
  - Email or in-app alerts when changes occur
  - Digest options (daily, weekly, monthly)

- [ ] **Task 3.31**: Comparison Tool for multi-state laws
  - Expand beyond federal to include state laws
  - Side-by-side comparison of similar statutes across states
  - Visualize regional differences in legislation

- [ ] **Task 3.32**: Causality Tracking
  - Link laws to the events/problems that prompted them
  - "In response to X disaster, Congress passed Y law"
  - Historical context enrichment

---

## Ongoing Maintenance & Operations

### Data Pipeline Maintenance
- [ ] **Task M.1**: Set up automated data ingestion schedule
  - Daily sync for new Public Laws
  - Weekly sync for bill status updates
  - Monthly full reconciliation with official sources

- [ ] **Task M.2**: Monitor data quality and accuracy
  - Automated tests for parser accuracy
  - Regular spot-checks against official sources
  - User-reported error tracking and resolution

- [ ] **Task M.3**: Handle data corrections and updates
  - Process errata from official sources
  - Reprocess affected sections when parser improvements are made
  - Maintain change log of data corrections

### System Monitoring & Operations
- [ ] **Task M.4**: Set up monitoring and alerting
  - Application performance monitoring (response times, error rates)
  - Database performance monitoring (query times, connection pools)
  - Infrastructure monitoring (CPU, memory, disk usage)
  - Alert on-call team for critical issues

- [ ] **Task M.5**: Regular security updates
  - Patch dependencies regularly
  - Security audits (automated and manual)
  - Penetration testing annually

- [ ] **Task M.6**: Database maintenance
  - Regular backups (daily with point-in-time recovery)
  - Periodic VACUUM and REINDEX operations
  - Monitor and optimize slow queries
  - Capacity planning as data grows

### User Support & Community
- [ ] **Task M.7**: User support system
  - Set up help desk or support email
  - Document common issues and solutions (knowledge base)
  - Respond to user inquiries within SLA

- [ ] **Task M.8**: Collect and act on user feedback
  - Regular user surveys
  - Analyze usage metrics to identify pain points
  - Prioritize feature requests from community

- [ ] **Task M.9**: Community engagement
  - Blog posts about interesting findings from data
  - Social media presence (@cwlb)
  - Partnerships with educators, journalists, researchers

### Continuous Improvement
- [ ] **Task M.10**: Regular retrospectives
  - Monthly team retrospectives
  - Review metrics, incidents, user feedback
  - Identify process improvements

- [ ] **Task M.11**: Performance optimization reviews
  - Quarterly performance audits
  - Identify and address bottlenecks
  - Optimize costs (infrastructure, API usage)

- [ ] **Task M.12**: Legal compliance reviews
  - Ensure disclaimers are up-to-date
  - Review privacy policy and terms of service
  - Stay compliant with accessibility standards (WCAG 2.1 AA)

---

## Priority & Sequencing Notes

### Critical Path (Must complete for MVP)
1. Tasks 0.1-0.14 (Phase 0 foundation)
2. Tasks 1.1-1.19 (Infrastructure and data pipeline)
3. Tasks 1.20-1.24 (Core APIs)
4. Tasks 1.25-1.35 (Core UI)
5. Tasks 1.46-1.49 (Deployment)

### High Priority (MVP-adjacent)
- Task 1.36-1.37 (Search)
- Task 1.38-1.40 (Basic analytics)
- Tasks 1.41-1.45 (Testing & QA)

### Medium Priority (Phase 2)
- Tasks 2.1-2.6 (Enhanced time travel and search)
- Tasks 2.7-2.15 (Comprehensive analytics)
- Tasks 2.16-2.20 (External integrations)

### Lower Priority (Phase 3 or Later)
- Tasks 3.3-3.9 (Proposed and failed bills)
- Tasks 3.10-3.13 (Dependency graph)
- Tasks 3.18-3.21 (Community features)
- Tasks 3.28-3.32 (Advanced features)

### Dependencies
- Line-level parsing (Task 1.13-1.16) is prerequisite for blame view (Task 1.29-1.30)
- Historical data (Task 1.17-1.19) is prerequisite for time travel (Task 1.23, 1.31)
- Core APIs (Task 1.20-1.24) must be complete before frontend work (Task 1.25+)
- Analytics queries (Task 2.7, 2.9, 2.11, 2.13) must be complete before visualizations (Task 2.8, 2.10, 2.12, 2.14)

---

## Success Criteria by Phase

### Phase 0 Success
- [ ] Confirmed data availability for 5-10 selected titles
- [ ] Working prototype parser for at least 2 Public Laws
- [ ] Validated technical architecture with stakeholders
- [ ] User research completed with key findings documented

### Phase 1 (MVP) Success
- [ ] 5-10 titles ingested with 20 years of history
- [ ] Code browsing with navigation and line-level view functional
- [ ] Law viewer with diffs and metadata functional
- [ ] Blame view showing line-by-line attribution functional
- [ ] Basic search operational
- [ ] Basic analytics (1-2 visualizations) operational
- [ ] Public beta launched with 100+ users
- [ ] <2s average page load time
- [ ] <1% error rate

### Phase 2 Success
- [ ] Full historical depth for covered titles
- [ ] Time travel fully optimized and intuitive
- [ ] Comprehensive analytics dashboard with 5+ visualizations
- [ ] Advanced search with filters and saved searches
- [ ] Integration with Congress.gov, GovInfo, CFR
- [ ] 10,000+ monthly active users
- [ ] Positive user feedback (>4/5 average rating)
- [ ] Featured in at least one major media outlet

### Phase 3 Success
- [ ] All 54 titles covered
- [ ] Proposed bills ("Open PRs") feature launched
- [ ] Dependency graph operational
- [ ] Public API with 100+ registered users
- [ ] 100,000+ monthly active users
- [ ] Used in at least 10 educational institutions
- [ ] Cited in at least 10 research papers or major journalism pieces

---

## Risk Mitigation

### Data Quality Risks
- **Risk**: Parser incorrectly interprets legal language
- **Mitigation**: Manual review process, user reporting, regular spot-checks

### Performance Risks
- **Risk**: Slow queries on large historical datasets
- **Mitigation**: Aggressive caching, database optimization, pagination

### Scalability Risks
- **Risk**: Traffic spike overwhelms infrastructure
- **Mitigation**: Auto-scaling, CDN, rate limiting, load testing

### User Adoption Risks
- **Risk**: Users find UI confusing or overwhelming
- **Mitigation**: User testing, progressive disclosure, onboarding tutorials, iterate based on feedback

### Legal/Accuracy Risks
- **Risk**: Displaying incorrect law text damages credibility
- **Mitigation**: Clear disclaimers, canonical source links, accuracy verification, user error reporting

---

## Estimated Effort (Person-Months)

**Phase 0**: 2-3 months (1-2 people)
- Research, prototyping, architecture design

**Phase 1 (MVP)**: 6-9 months (3-5 people)
- Backend: 3-4 months (2 engineers)
- Frontend: 3-4 months (2 engineers)
- Data pipeline: 3-4 months (1-2 engineers, can overlap with backend)
- QA/Testing: 1-2 months (1 engineer + all team)

**Phase 2**: 6-9 months (3-5 people)
- Feature development, analytics, optimization

**Phase 3**: Ongoing (2-4 people)
- Expansion, maintenance, community engagement

**Note**: Estimates assume team has relevant expertise (legal tech, data engineering, full-stack web development). Adjust based on team composition and experience level.
