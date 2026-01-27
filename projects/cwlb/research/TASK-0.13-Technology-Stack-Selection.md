# Task 0.13: Technology Stack Selection

**Status**: Complete
**Completed**: 2026-01-27
**Deliverables**:
- This documentation file

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Decision Framework](#2-decision-framework)
3. [Frontend Technology Selection](#3-frontend-technology-selection)
4. [Backend Technology Selection](#4-backend-technology-selection)
5. [Database Technology Selection](#5-database-technology-selection)
6. [Search Technology Selection](#6-search-technology-selection)
7. [Caching Technology Selection](#7-caching-technology-selection)
8. [Hosting Platform Selection](#8-hosting-platform-selection)
9. [DevOps and Infrastructure](#9-devops-and-infrastructure)
10. [Monitoring and Observability](#10-monitoring-and-observability)
11. [Complete Technology Stack Summary](#11-complete-technology-stack-summary)
12. [Cost Projections](#12-cost-projections)
13. [Implementation Roadmap](#13-implementation-roadmap)
14. [Risk Assessment](#14-risk-assessment)

---

## 1. Executive Summary

This document defines the complete technology stack for The Code We Live By (CWLB) platform. The stack has been selected to optimize for:

- **Developer productivity**: Familiar, well-documented technologies
- **Performance**: Sub-2-second page loads, efficient queries
- **Scalability**: Support 10,000+ concurrent users in Phase 2
- **Cost efficiency**: Reasonable hosting costs for a civic tech project
- **Maintainability**: Long-term support, active communities

### Technology Stack at a Glance

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | React (served by backend) | 18.x |
| **Frontend Styling** | Tailwind CSS | 3.x |
| **Backend** | Python (FastAPI) | 3.11+ |
| **ORM** | SQLAlchemy | 2.x |
| **Database** | PostgreSQL (Cloud SQL) | 15+ |
| **Search** | PostgreSQL Full-Text (MVP) | - |
| **Cache** | In-memory / Memorystore (if needed) | - |
| **Hosting** | Google Cloud Platform | - |
| **Compute** | Cloud Run (scales to zero) | - |
| **CI/CD** | GitHub Actions + Cloud Build | - |
| **Monitoring** | Cloud Monitoring (free tier) | - |

### Key Decisions Summary

| Decision Area | Choice | Primary Rationale |
|---------------|--------|-------------------|
| Architecture | **Monolith** | Simpler deployment, one service to manage |
| Frontend Framework | **React** | Served by FastAPI, no separate hosting needed |
| Backend Language | **Python** | Existing prototypes, data processing strength, FastAPI performance |
| Database | **PostgreSQL** | Already decided in Task 0.11; best relational + full-text |
| Search | **PostgreSQL FTS** | Built-in, no extra service for MVP (Elasticsearch later if needed) |
| Cache | **In-memory** | Start simple, add Redis/Memorystore only if needed |
| Hosting | **GCP Cloud Run** | Scales to zero = $0 when idle, familiar ecosystem |

---

## 2. Decision Framework

### 2.1 Evaluation Criteria

Each technology was evaluated against these criteria (weighted by importance):

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Performance** | 25% | Speed, efficiency, resource usage |
| **Developer Experience** | 20% | Learning curve, tooling, debugging |
| **Community & Support** | 20% | Documentation, ecosystem, long-term viability |
| **Cost** | 15% | Licensing, hosting, operational costs |
| **Scalability** | 10% | Horizontal scaling, performance under load |
| **Security** | 10% | Security track record, compliance features |

### 2.2 Team Assumptions

The technology choices assume:

- **Team size**: 3-5 developers (Phase 1)
- **Skill distribution**: Full-stack developers with Python/JavaScript experience
- **Timeline**: 6-9 months to MVP
- **Budget**: Moderate (civic tech, not enterprise)

### 2.3 Project Constraints

Constraints from prior decisions:

1. **PostgreSQL database** (Task 0.11) - Already designed schema
2. **RESTful API** (Task 0.12) - 27 endpoints designed
3. **Python prototypes** - Existing parsers in Python
4. **Read-heavy workload** - 95%+ read operations

---

## 3. Frontend Technology Selection

### 3.1 Candidates Evaluated

| Framework | Type | Key Strengths |
|-----------|------|---------------|
| **Next.js 14** | React meta-framework | SSR/SSG, App Router, React ecosystem |
| **Remix** | React meta-framework | Data loading patterns, web standards |
| **SvelteKit** | Svelte meta-framework | Performance, smaller bundles |
| **Nuxt 3** | Vue meta-framework | Vue ecosystem, auto-imports |

### 3.2 Evaluation Matrix

| Criterion | Next.js | Remix | SvelteKit | Nuxt 3 |
|-----------|---------|-------|-----------|--------|
| Performance | 9/10 | 9/10 | 10/10 | 8/10 |
| Developer Experience | 9/10 | 8/10 | 8/10 | 8/10 |
| Community & Support | 10/10 | 7/10 | 7/10 | 8/10 |
| React Ecosystem | 10/10 | 10/10 | 0/10 | 0/10 |
| SEO/SSR | 10/10 | 9/10 | 9/10 | 9/10 |
| Hiring Pool | 10/10 | 7/10 | 5/10 | 6/10 |
| **Weighted Total** | **9.3** | **8.3** | **7.5** | **7.2** |

### 3.3 Decision: Next.js 14

**Selected**: Next.js 14 with App Router

**Primary Reasons**:

1. **SEO Critical**: CWLB needs excellent SEO for legal citations to be discoverable. Next.js provides:
   - Static Site Generation (SSG) for US Code sections (rarely change)
   - Server-Side Rendering (SSR) for dynamic pages
   - Automatic metadata generation

2. **React Ecosystem**: Access to the largest ecosystem of components:
   - Syntax highlighting libraries (Prism, Shiki)
   - Diff viewers (react-diff-view)
   - Data visualization (Recharts, Visx)
   - Accessibility components (Radix UI)

3. **Performance Features**:
   - Automatic code splitting
   - Image optimization
   - Font optimization
   - Streaming SSR

4. **Developer Experience**:
   - Excellent TypeScript support
   - Fast Refresh for development
   - Built-in routing with App Router
   - Extensive documentation

5. **Vercel Integration** (optional):
   - Easy deployment path
   - Edge functions for global performance
   - Analytics built-in

**Trade-offs Accepted**:
- Larger initial bundle than SvelteKit
- More complex than Remix for data loading
- React learning curve (mitigated by team experience)

### 3.4 Frontend Architecture

```
src/
├── app/                          # Next.js App Router
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Home page
│   ├── titles/
│   │   ├── page.tsx             # Title listing
│   │   └── [titleNumber]/
│   │       ├── page.tsx         # Title detail
│   │       └── sections/
│   │           └── [sectionNumber]/
│   │               ├── page.tsx  # Section view
│   │               ├── blame/
│   │               │   └── page.tsx  # Blame view
│   │               └── history/
│   │                   └── page.tsx  # Time travel
│   ├── laws/
│   │   ├── page.tsx             # Law listing
│   │   └── [lawId]/
│   │       └── page.tsx         # Law detail with diff
│   ├── search/
│   │   └── page.tsx             # Search interface
│   └── analytics/
│       └── page.tsx             # Analytics dashboard
├── components/
│   ├── ui/                      # Base UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── ...
│   ├── code/                    # Code browsing components
│   │   ├── SectionViewer.tsx
│   │   ├── BlameView.tsx
│   │   ├── LineAttribution.tsx
│   │   └── NavigationTree.tsx
│   ├── law/                     # Law viewer components
│   │   ├── LawDetail.tsx
│   │   ├── DiffViewer.tsx
│   │   ├── SponsorPanel.tsx
│   │   └── VoteDisplay.tsx
│   └── analytics/               # Analytics components
│       ├── ProductivityChart.tsx
│       └── FocusAreaChart.tsx
├── lib/
│   ├── api/                     # API client
│   │   ├── client.ts
│   │   ├── sections.ts
│   │   ├── laws.ts
│   │   └── search.ts
│   └── utils/
│       ├── citations.ts
│       └── formatting.ts
├── hooks/                       # Custom React hooks
│   ├── useSection.ts
│   ├── useBlame.ts
│   └── useSearch.ts
└── styles/
    └── globals.css              # Tailwind imports
```

### 3.5 Frontend Dependencies

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-*": "^1.0.0",
    "recharts": "^2.10.0",
    "react-diff-view": "^3.0.0",
    "date-fns": "^3.0.0",
    "clsx": "^2.0.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.0.0",
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.0.0",
    "prettier": "^3.2.0",
    "vitest": "^1.2.0",
    "@testing-library/react": "^14.0.0",
    "playwright": "^1.40.0"
  }
}
```

---

## 4. Backend Technology Selection

### 4.1 Candidates Evaluated

| Language/Framework | Key Strengths |
|-------------------|---------------|
| **Python + FastAPI** | Async, type hints, OpenAPI auto-generation |
| **Python + Django** | Batteries included, ORM, admin |
| **Node.js + Express** | JavaScript everywhere, npm ecosystem |
| **Node.js + NestJS** | TypeScript, structured architecture |
| **Go + Gin** | Performance, concurrency, small binaries |

### 4.2 Evaluation Matrix

| Criterion | FastAPI | Django | Express | NestJS | Go/Gin |
|-----------|---------|--------|---------|--------|--------|
| Performance | 9/10 | 7/10 | 8/10 | 8/10 | 10/10 |
| Developer Experience | 9/10 | 9/10 | 7/10 | 8/10 | 7/10 |
| Type Safety | 9/10 | 6/10 | 5/10 | 9/10 | 10/10 |
| Data Processing | 10/10 | 9/10 | 6/10 | 6/10 | 7/10 |
| Ecosystem (Legal/Data) | 10/10 | 9/10 | 5/10 | 5/10 | 4/10 |
| Existing Code Reuse | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 |
| **Weighted Total** | **9.4** | **8.3** | **5.8** | **6.2** | **7.0** |

### 4.3 Decision: Python + FastAPI

**Selected**: Python 3.11+ with FastAPI

**Primary Reasons**:

1. **Existing Code Investment**:
   - All Phase 0 prototypes are in Python
   - Legal text parsers (Task 0.5-0.7) in Python
   - Data pipeline scripts in Python
   - Rewriting in another language = 2-3 months lost

2. **FastAPI Performance**:
   - Built on Starlette (ASGI) - async native
   - Performance comparable to Node.js/Go for I/O-bound workloads
   - Our workload is I/O-bound (database queries), not CPU-bound

3. **Data Processing Ecosystem**:
   - Pandas, NumPy for analytics calculations
   - BeautifulSoup, lxml for XML/HTML parsing
   - NLTK, spaCy for potential NLP features
   - No equivalent ecosystem in Node.js/Go

4. **Type Safety**:
   - Pydantic for runtime validation
   - mypy for static type checking
   - Auto-generated OpenAPI documentation

5. **SQLAlchemy 2.0**:
   - Best-in-class ORM for PostgreSQL
   - Async support with asyncpg
   - Matches our schema design from Task 0.11

**Trade-offs Accepted**:
- Slightly higher latency than Go (acceptable for our use case)
- GIL limitations (mitigated by async and process-based scaling)
- Two languages in codebase (TypeScript frontend, Python backend)

### 4.4 Backend Architecture

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry
│   ├── config.py                # Configuration management
│   ├── dependencies.py          # Dependency injection
│   │
│   ├── api/                     # API routes
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # API v1 router
│   │   │   ├── titles.py        # /titles endpoints
│   │   │   ├── sections.py      # /sections endpoints
│   │   │   ├── laws.py          # /laws endpoints
│   │   │   ├── search.py        # /search endpoints
│   │   │   ├── blame.py         # /blame endpoints
│   │   │   ├── history.py       # /history endpoints
│   │   │   └── analytics.py     # /analytics endpoints
│   │   └── deps.py              # Route dependencies
│   │
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── blame.py             # Blame view logic
│   │   ├── time_travel.py       # Historical queries
│   │   ├── diff.py              # Diff generation
│   │   └── search.py            # Search logic
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model class
│   │   ├── us_code.py           # Title, Chapter, Section, Line
│   │   ├── public_law.py        # Law, Change
│   │   ├── legislator.py        # Legislator, Vote
│   │   └── history.py           # SectionHistory, LineHistory
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── section.py           # Section request/response
│   │   ├── law.py               # Law request/response
│   │   ├── search.py            # Search request/response
│   │   └── common.py            # Pagination, errors
│   │
│   ├── crud/                    # Database operations
│   │   ├── __init__.py
│   │   ├── section.py
│   │   ├── law.py
│   │   ├── legislator.py
│   │   └── search.py
│   │
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── cache.py             # Redis caching
│       └── elasticsearch.py     # ES client
│
├── alembic/                     # Database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── api/                     # API tests
│   ├── core/                    # Unit tests
│   └── integration/             # Integration tests
│
├── pipeline/                    # Data ingestion pipeline
│   ├── __init__.py
│   ├── ingest_sections.py
│   ├── ingest_laws.py
│   ├── ingest_legislators.py
│   ├── parse_legal_text.py
│   └── calculate_blame.py
│
├── requirements.txt
├── pyproject.toml               # Poetry/pip config
└── Dockerfile
```

### 4.5 Backend Dependencies

```toml
# pyproject.toml
[project]
name = "cwlb-backend"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    # Web Framework
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "gunicorn>=21.2.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",

    # Validation
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",

    # Search
    "elasticsearch[async]>=8.12.0",

    # Cache
    "redis>=5.0.0",

    # Data Processing
    "pandas>=2.2.0",
    "lxml>=5.1.0",
    "beautifulsoup4>=4.12.0",

    # HTTP Client
    "httpx>=0.26.0",

    # Utilities
    "python-dateutil>=2.8.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "mypy>=1.8.0",
    "ruff>=0.1.0",
    "black>=24.1.0",
]
```

---

## 5. Database Technology Selection

### 5.1 Decision: PostgreSQL 15+ (Confirmed)

**Status**: Already decided in Task 0.11

**Confirmation**: PostgreSQL remains the optimal choice for CWLB.

**Key Capabilities Used**:

| Feature | CWLB Use Case |
|---------|---------------|
| **Recursive CTEs** | Line tree traversal for parent/child structure |
| **Window Functions** | Version numbering, ranking in analytics |
| **JSONB** | Flexible metadata storage |
| **Full-text Search** | Basic search (pg_trgm, tsvector) |
| **Partial Indexes** | Efficient queries on is_current, is_repealed |
| **Foreign Keys** | Referential integrity across 22 tables |

### 5.2 PostgreSQL Configuration

```ini
# postgresql.conf optimized for CWLB

# Memory (assuming 16GB RAM server)
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 256MB
maintenance_work_mem = 1GB
wal_buffers = 64MB

# Connections
max_connections = 200

# Query Planning (SSD storage)
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 200

# Parallel Queries
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Write Ahead Log
checkpoint_completion_target = 0.9
wal_compression = on
max_wal_size = 4GB

# Logging
log_min_duration_statement = 100  # Log queries > 100ms
log_statement = 'ddl'

# Extensions
shared_preload_libraries = 'pg_stat_statements'
```

### 5.3 PostgreSQL Extensions

```sql
-- Required extensions for CWLB
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- Fuzzy text matching
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- Query analysis
CREATE EXTENSION IF NOT EXISTS btree_gin;      -- GIN index support
CREATE EXTENSION IF NOT EXISTS unaccent;       -- Accent-insensitive search
```

---

## 6. Search Technology Selection

### 6.1 Candidates Evaluated

| Technology | Type | Key Strengths |
|------------|------|---------------|
| **PostgreSQL FTS** | Built-in | No additional infrastructure, tsvector |
| **Elasticsearch** | Dedicated search engine | Powerful, scalable, analytics |
| **OpenSearch** | ES fork | AWS-managed option, ES-compatible |
| **Meilisearch** | Lightweight search | Fast, simple, typo-tolerant |
| **Typesense** | Lightweight search | Fast, simple API |

### 6.2 Evaluation Matrix

| Criterion | PostgreSQL FTS | Elasticsearch | Meilisearch |
|-----------|----------------|---------------|-------------|
| Query Performance | 7/10 | 10/10 | 9/10 |
| Faceted Search | 4/10 | 10/10 | 8/10 |
| Highlighting | 6/10 | 10/10 | 9/10 |
| Typo Tolerance | 6/10 | 9/10 | 10/10 |
| Operational Complexity | 10/10 | 5/10 | 8/10 |
| Scalability | 6/10 | 10/10 | 7/10 |
| **Weighted Total** | **6.5** | **8.8** | **8.3** |

### 6.3 Decision: Elasticsearch 8.x

**Selected**: Elasticsearch 8.x (via AWS OpenSearch or self-hosted)

**Primary Reasons**:

1. **Full-text Search Quality**:
   - Legal text requires precise phrase matching
   - Proximity search ("copyright" NEAR "infringement")
   - Boosting by relevance factors

2. **Faceted Navigation**:
   - Filter by Title, Congress, date range
   - Aggregations for analytics
   - Fast facet counts for UI filters

3. **Highlighting**:
   - Show snippets with matching terms highlighted
   - Context around matches
   - Essential for search results UX

4. **Scalability**:
   - Handles millions of documents easily
   - Horizontal scaling when needed
   - Phase 2 will have ~60,000 sections + ~25,000 laws

5. **Analytics Aggregations**:
   - Time-series queries for productivity charts
   - Cardinality counts
   - Bucket aggregations for visualizations

**Implementation Strategy**:

- **Phase 1 (MVP)**: Use PostgreSQL full-text search initially (simpler)
- **Phase 1.5**: Add Elasticsearch when search quality becomes critical
- **Phase 2+**: Elasticsearch as primary search engine

### 6.4 Elasticsearch Index Design

```json
// Index: cwlb-sections
{
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "legal_text": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "english_stemmer", "legal_synonyms"]
        }
      },
      "filter": {
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "legal_synonyms": {
          "type": "synonym",
          "synonyms": [
            "sec, section",
            "subsec, subsection",
            "para, paragraph"
          ]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "section_id": { "type": "integer" },
      "title_number": { "type": "integer" },
      "title_name": { "type": "keyword" },
      "chapter_number": { "type": "keyword" },
      "section_number": { "type": "keyword" },
      "full_citation": { "type": "keyword" },
      "heading": {
        "type": "text",
        "analyzer": "legal_text",
        "fields": {
          "keyword": { "type": "keyword" }
        }
      },
      "text_content": {
        "type": "text",
        "analyzer": "legal_text"
      },
      "last_modified_date": { "type": "date" },
      "is_positive_law": { "type": "boolean" },
      "is_repealed": { "type": "boolean" }
    }
  }
}
```

```json
// Index: cwlb-laws
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "law_id": { "type": "integer" },
      "law_number": { "type": "keyword" },
      "congress": { "type": "integer" },
      "popular_name": {
        "type": "text",
        "fields": {
          "keyword": { "type": "keyword" }
        }
      },
      "official_title": { "type": "text" },
      "summary": { "type": "text" },
      "enacted_date": { "type": "date" },
      "president": { "type": "keyword" },
      "sections_affected": { "type": "integer" },
      "sponsor_names": { "type": "text" }
    }
  }
}
```

---

## 7. Caching Technology Selection

### 7.1 Decision: Redis 7.x

**Selected**: Redis 7.x (via AWS ElastiCache or self-hosted)

**Rationale**:

1. **Industry Standard**: Most proven caching solution
2. **Versatility**: Key-value, lists, sets, sorted sets, streams
3. **Performance**: Sub-millisecond latency
4. **Persistence Options**: RDB snapshots, AOF logging
5. **Cluster Support**: Horizontal scaling when needed

### 7.2 Redis Usage Patterns

| Use Case | Redis Data Structure | TTL |
|----------|---------------------|-----|
| Section text cache | STRING | 1 hour |
| Blame view cache | STRING (JSON) | 1 hour |
| Law metadata cache | STRING (JSON) | 24 hours |
| Historical section cache | STRING | 7 days (immutable) |
| Search results cache | STRING (JSON) | 5 minutes |
| Rate limiting | SORTED SET | Rolling window |
| Session storage | STRING | 24 hours |
| API response cache | STRING | Varies |

### 7.3 Cache Key Naming Convention

```
# Pattern: {prefix}:{entity}:{identifier}:{view}

# Section caches
section:17:106:current              # Current section text
section:17:106:at:1998-10-28        # Historical section
section:17:106:blame:current        # Blame view
section:17:106:blame:at:1998-10-28  # Historical blame
section:17:106:lines                # Line structure
section:17:106:history              # Version history

# Law caches
law:456                             # Law metadata
law:456:changes                     # Law changes
law:456:sponsors                    # Sponsors
law:456:votes                       # Vote records

# Search caches
search:sections:{query_hash}        # Section search results
search:laws:{query_hash}            # Law search results

# Analytics caches
analytics:productivity:117          # Congress 117 productivity
analytics:focus-areas:117           # Congress 117 focus areas

# Rate limiting
ratelimit:{client_id}:{minute}      # Per-minute rate limit counter
```

### 7.4 Redis Configuration

```conf
# redis.conf for CWLB

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (for cache warming after restart)
save 900 1
save 300 10
save 60 10000

# Append-only file
appendonly yes
appendfsync everysec

# Connection limits
maxclients 10000
timeout 300

# Security
requirepass ${REDIS_PASSWORD}
```

---

## 8. Hosting Platform Selection

### 8.1 Decision: Google Cloud Platform (Monolith)

**Selected**: Google Cloud Platform with Cloud Run

**Primary Reasons**:

1. **Scales to Zero**:
   - Cloud Run charges only when handling requests
   - $0/month during periods of no traffic
   - Perfect for a project with sporadic usage patterns

2. **Simplicity**:
   - One service to deploy (monolith)
   - No load balancer configuration needed
   - Automatic HTTPS
   - Built-in request routing

3. **Familiar Ecosystem**:
   - Similar to App Engine experience
   - Good documentation
   - gcloud CLI is straightforward

4. **Generous Free Tier**:
   - Cloud Run: 2 million requests/month free
   - Cloud SQL: No always-free tier, but minimal instance is ~$7/month
   - Cloud Storage: 5GB free
   - Cloud Build: 120 build-minutes/day free

### 8.2 GCP Architecture (Monolith)

```
                    ┌─────────────────────────────────┐
                    │         Cloud Run               │
                    │   ┌─────────────────────────┐   │
                    │   │   FastAPI (Python)      │   │
     HTTPS          │   │                         │   │
    Request ──────► │   │   - API endpoints       │   │
                    │   │   - Serves React build  │   │
                    │   │   - Static files        │   │
                    │   └───────────┬─────────────┘   │
                    └───────────────┼─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │      Cloud SQL (PostgreSQL)     │
                    │         db-f1-micro             │
                    │     (scales up if needed)       │
                    └─────────────────────────────────┘
```

**That's it.** Two services. No Redis, no Elasticsearch, no load balancer, no CDN configuration.

### 8.3 GCP Services Selection

| Service | GCP Service | Specification | Monthly Cost |
|---------|-------------|---------------|--------------|
| **Compute** | Cloud Run | 1 vCPU, 512MB RAM, scales to zero | ~$0 (idle) |
| **Database** | Cloud SQL PostgreSQL | db-f1-micro (shared vCPU, 614MB) | ~$7-10 |
| **Storage** | Cloud Storage | Static assets if needed | ~$0 (free tier) |
| **Secrets** | Secret Manager | API keys, DB credentials | ~$0 (free tier) |
| **DNS** | Cloud DNS | Optional (can use external) | ~$0.20/zone |
| **Monitoring** | Cloud Monitoring | Logs, metrics | ~$0 (free tier) |
| **CI/CD** | Cloud Build | Triggered by GitHub | ~$0 (free tier) |

### 8.4 Why Not Separate Services?

For MVP with low/sporadic traffic:

| Separate Service | Why Skip It |
|------------------|-------------|
| **Redis cache** | PostgreSQL is fast enough; add later if needed |
| **Elasticsearch** | PostgreSQL full-text search works for MVP |
| **CDN** | Cloud Run is already globally distributed |
| **Load balancer** | Cloud Run handles this automatically |
| **Separate frontend host** | FastAPI serves static files fine |

### 8.5 Scaling Path (If CWLB Takes Off)

| Traffic Level | Action |
|---------------|--------|
| **0-1K users/month** | Keep monolith, db-f1-micro |
| **1K-10K users/month** | Upgrade Cloud SQL to db-g1-small (~$25/month) |
| **10K-50K users/month** | Add Memorystore (Redis) for caching |
| **50K+ users/month** | Consider splitting frontend, add Elasticsearch |
| **100K+ users/month** | Evaluate migration to GKE or multi-region |

The architecture grows with demand. No need to pay for scale you don't have.

---

## 9. DevOps and Infrastructure

### 9.1 Containerization: Docker

Single Dockerfile for the monolith application:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Node.js for building React frontend
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build React frontend
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci

COPY frontend/ frontend/
RUN cd frontend && npm run build

# Copy backend code
COPY app/ app/

# Copy built frontend to static directory
RUN cp -r frontend/build app/static

# Expose port (Cloud Run uses 8080 by default)
ENV PORT=8080
EXPOSE 8080

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app.main:app -k uvicorn.workers.UvicornWorker
```

### 9.2 Project Structure (Monolith)

```
cwlb/
├── app/                      # FastAPI backend
│   ├── __init__.py
│   ├── main.py              # FastAPI app + static file serving
│   ├── api/                 # API routes
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── crud/                # Database operations
│   └── static/              # Built React app (generated)
│
├── frontend/                 # React frontend source
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   └── pages/
│   └── build/               # Build output (generated)
│
├── pipeline/                 # Data ingestion scripts
│   ├── ingest_sections.py
│   └── ingest_laws.py
│
├── alembic/                  # Database migrations
│   └── versions/
│
├── Dockerfile
├── requirements.txt
├── cloudbuild.yaml          # GCP Cloud Build config
└── .gcloudignore
```

### 9.3 GCP Deployment Commands

**One-time setup**:

```bash
# Create GCP project
gcloud projects create cwlb-app --name="The Code We Live By"
gcloud config set project cwlb-app

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com

# Create Cloud SQL instance
gcloud sql instances create cwlb-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create cwlb --instance=cwlb-db

# Store database password in Secret Manager
echo -n "your-secure-password" | \
  gcloud secrets create db-password --data-file=-
```

**Deploy**:

```bash
# Build and deploy to Cloud Run
gcloud run deploy cwlb \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances cwlb-app:us-central1:cwlb-db \
  --set-env-vars "DATABASE_URL=postgresql://postgres:PASSWORD@/cwlb?host=/cloudsql/cwlb-app:us-central1:cwlb-db"
```

### 9.4 CI/CD: GitHub Actions + Cloud Build

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy cwlb \
            --source . \
            --region us-central1 \
            --allow-unauthenticated \
            --quiet
```

**That's the entire CI/CD pipeline.** Push to main → deploys automatically.

---

## 10. Monitoring and Observability

### 10.1 Monitoring Stack (Simple)

For MVP, use GCP's built-in free monitoring:

| Component | Tool | Cost |
|-----------|------|------|
| **Metrics** | Cloud Monitoring | Free tier |
| **Logs** | Cloud Logging | Free tier (50GB/month) |
| **Errors** | Cloud Error Reporting | Free |
| **Uptime** | Cloud Monitoring Uptime Checks | Free (up to 10) |

No need for Datadog/Sentry unless traffic grows significantly.

### 10.2 Key Metrics to Track

| Metric | Where to Find | Alert If |
|--------|---------------|----------|
| Request latency | Cloud Run metrics | p99 > 2s |
| Error rate | Cloud Run metrics | > 1% |
| Instance count | Cloud Run metrics | Unexpectedly high |
| DB connections | Cloud SQL metrics | Near limit |
| DB CPU | Cloud SQL metrics | > 80% sustained |

### 10.3 Simple Alerting

```bash
# Create uptime check + alert via gcloud
gcloud monitoring uptime create cwlb-health \
  --display-name="CWLB Health Check" \
  --resource-type="cloud-run-revision" \
  --resource-labels="service_name=cwlb,location=us-central1"
```

### 10.4 Logging

Cloud Run automatically captures stdout/stderr. Use structured logging:

```python
# app/core/logging.py
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })

logging.basicConfig(level=logging.INFO)
logging.getLogger().handlers[0].setFormatter(JSONFormatter())
```

Logs are automatically available in Cloud Logging console.

---

## 11. Complete Technology Stack Summary

### 11.1 Full Stack Overview (Monolith)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  React 18          │  Tailwind CSS      │  TypeScript       │  Recharts    │
│  (Components)      │  (Styling)         │  (Types)          │  (Charts)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (built & served by backend)
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLICATION LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI           │  Pydantic          │  SQLAlchemy 2.0   │  Python 3.11 │
│  (API + Static)    │  (Validation)      │  (ORM)            │  (Runtime)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL 15 (Cloud SQL)               │  Full-text search (built-in)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE (GCP)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Cloud Run         │  Cloud SQL         │  Cloud Build      │  Secret Mgr  │
│  (Compute)         │  (PostgreSQL)      │  (CI/CD)          │  (Secrets)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Technology Versions

| Category | Technology | Version | Notes |
|----------|------------|---------|-------|
| **Frontend** | React | 18.x | Served by FastAPI |
| | TypeScript | 5.x | |
| | Tailwind CSS | 3.x | |
| | Recharts | 2.x | Charts/visualizations |
| **Backend** | Python | 3.11+ | |
| | FastAPI | 0.109+ | |
| | SQLAlchemy | 2.0+ | |
| | Pydantic | 2.x | |
| | Alembic | 1.13+ | Migrations |
| **Database** | PostgreSQL | 15+ | Cloud SQL |
| **Search** | PostgreSQL FTS | - | Built-in, add ES later if needed |
| **Infrastructure** | Cloud Run | - | Scales to zero |
| | Cloud SQL | - | Managed PostgreSQL |
| | Cloud Build | - | CI/CD |
| **Monitoring** | Cloud Monitoring | - | Free tier |

---

## 12. Cost Projections

### 12.1 Idle Month (No Traffic)

| Service | Specification | Monthly Cost |
|---------|---------------|--------------|
| **Cloud Run** | Scales to zero | **$0** |
| **Cloud SQL** | db-f1-micro (always on) | ~$7-10 |
| **Cloud Storage** | < 5GB (free tier) | $0 |
| **Cloud Build** | < 120 min/day (free tier) | $0 |
| **Secret Manager** | < 6 secrets (free tier) | $0 |
| **Cloud Monitoring** | Free tier | $0 |
| **Domain** | Annual / 12 | ~$1 |
| **TOTAL (Idle)** | | **~$8-11/month** |

### 12.2 Light Usage (~1,000 requests/day)

| Service | Specification | Monthly Cost |
|---------|---------------|--------------|
| **Cloud Run** | ~30K requests/month, minimal CPU | ~$0-2 |
| **Cloud SQL** | db-f1-micro | ~$7-10 |
| **Egress** | ~1GB/month | ~$0.12 |
| **TOTAL (Light)** | | **~$10-15/month** |

### 12.3 Moderate Usage (~10,000 requests/day)

| Service | Specification | Monthly Cost |
|---------|---------------|--------------|
| **Cloud Run** | ~300K requests/month | ~$5-10 |
| **Cloud SQL** | db-g1-small (upgrade) | ~$25 |
| **Egress** | ~10GB/month | ~$1.20 |
| **TOTAL (Moderate)** | | **~$30-40/month** |

### 12.4 Scaling Costs

| Traffic Level | Cloud SQL Tier | Est. Monthly Cost |
|---------------|----------------|-------------------|
| 0-1K req/day | db-f1-micro | ~$10 |
| 1K-10K req/day | db-g1-small | ~$35 |
| 10K-50K req/day | db-custom-2-4096 | ~$80 |
| 50K+ req/day | db-custom-4-8192 + Memorystore | ~$200+ |

### 12.5 Cost Comparison

| Scenario | GCP (This Plan) | AWS (Original) |
|----------|-----------------|----------------|
| Idle month | ~$10 | ~$500+ |
| Light usage | ~$15 | ~$600+ |
| Moderate usage | ~$40 | ~$800+ |

**Key advantage**: GCP Cloud Run's scale-to-zero means you only pay for actual usage. No minimum costs for compute.

---

## 13. Implementation Roadmap

### 13.1 Infrastructure Setup (Day 1)

```bash
# Everything you need to set up (1-2 hours)

# 1. Create GCP project
gcloud projects create cwlb-app
gcloud config set project cwlb-app

# 2. Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com

# 3. Create Cloud SQL instance
gcloud sql instances create cwlb-db --database-version=POSTGRES_15 --tier=db-f1-micro --region=us-central1

# 4. Create database and user
gcloud sql databases create cwlb --instance=cwlb-db

# 5. Done! Deploy when ready
```

### 13.2 Application Setup (Week 1)

```
Day 1-2:
├── Initialize FastAPI project structure
├── Set up SQLAlchemy models (from Task 0.11 schema)
├── Configure Alembic migrations
└── Create Dockerfile

Day 3-4:
├── Initialize React frontend (create-react-app or Vite)
├── Configure Tailwind CSS
├── Set up basic routing
└── Integrate with FastAPI static serving

Day 5:
├── Set up GitHub Actions deploy workflow
├── First deploy to Cloud Run
└── Verify everything works
```

### 13.3 Integration with Phase 1 Tasks

| Task ID | Task Name | Technology Used |
|---------|-----------|-----------------|
| 1.1 | Development environment | Docker, GitHub |
| 1.2 | PostgreSQL setup | Cloud SQL, Alembic |
| 1.3 | Elasticsearch setup | PostgreSQL FTS (MVP), ES later |
| 1.4 | Redis setup | Skip for MVP, add Memorystore if needed |
| 1.5 | Hosting infrastructure | Cloud Run (1 command deploy) |
| 1.20-1.24 | Backend API | FastAPI, SQLAlchemy |
| 1.25-1.37 | Frontend UI | React, Tailwind (served by FastAPI) |
| 1.46 | Production deployment | GitHub Actions → Cloud Run |

---

## 14. Risk Assessment

### 14.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cold start latency | Medium | Low | Keep min instances=1 if needed (~$25/mo) |
| PostgreSQL FTS limitations | Medium | Medium | Upgrade to Elasticsearch later if search quality suffers |
| Cloud SQL connection limits | Low | Medium | Connection pooling, upgrade tier if needed |
| React bundle size | Low | Low | Code splitting, lazy loading |

### 14.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cloud SQL downtime | Very Low | High | Automated backups, point-in-time recovery |
| Data loss | Very Low | Critical | Daily backups enabled by default |
| Cost spike | Low | Low | Budget alerts, scale-to-zero protects against runaway costs |

### 14.3 Organizational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | High | Medium | Strict MVP scope, resist adding complexity |
| Over-engineering | Medium | Medium | Keep monolith simple, resist premature optimization |

**Note**: The simplified architecture significantly reduces operational risk compared to a multi-service setup.

---

## Appendix A: Alternative Considered - AWS (Full Stack)

**Why AWS was considered**:
- Government-ready (FedRAMP)
- Comprehensive managed services
- Proven at scale

**Why AWS was not selected for MVP**:
- Minimum monthly cost ~$500+ even with no traffic
- More complex to set up and maintain
- Overkill for a project with sporadic usage

**Recommendation**: Migrate to AWS if CWLB reaches 50K+ monthly users and needs enterprise-grade reliability.

---

## Appendix B: Alternative Considered - Vercel + Supabase

**Why it was considered**:
- Even simpler than GCP
- Excellent free tiers
- Great developer experience

**Why GCP was selected instead**:
- More familiar (similar to App Engine)
- Better PostgreSQL control via Cloud SQL
- Clearer scaling path
- Single vendor simplicity

**Either would work** - GCP chosen for familiarity.

---

## Appendix C: Development Environment Setup

### Local Development Prerequisites

```bash
# Required software
- Docker Desktop 4.x
- Node.js 20.x (via nvm)
- Python 3.11+ (via pyenv)
- PostgreSQL 15 client (psql)
- Google Cloud SDK (gcloud)

# Recommended IDE
- VS Code with extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
```

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: cwlb
      POSTGRES_USER: cwlb
      POSTGRES_PASSWORD: localdev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./app:/app/app
      - ./frontend:/app/frontend
    environment:
      - DATABASE_URL=postgresql://cwlb:localdev@postgres:5432/cwlb
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

## Summary

Task 0.13 establishes a **simple, cost-effective technology stack** for CWLB:

| Layer | Selection | Key Rationale |
|-------|-----------|---------------|
| **Architecture** | Monolith | One service to deploy and manage |
| **Frontend** | React + Tailwind | Served by backend, no separate hosting |
| **Backend** | Python + FastAPI | Existing prototypes, data processing strength |
| **Database** | PostgreSQL (Cloud SQL) | Already designed schema, built-in FTS |
| **Search** | PostgreSQL FTS | Good enough for MVP, add Elasticsearch later |
| **Cache** | None (MVP) | Add Memorystore only if needed |
| **Hosting** | GCP Cloud Run | Scales to zero = ~$0 when idle |
| **CI/CD** | GitHub Actions | Simple, free for public repos |

### Cost Summary

| Traffic | Monthly Cost |
|---------|--------------|
| Idle (no traffic) | ~$8-11 |
| Light (1K req/day) | ~$10-15 |
| Moderate (10K req/day) | ~$30-40 |

### Key Principles

1. **Start simple** - Monolith over microservices
2. **Pay for what you use** - Cloud Run scales to zero
3. **Add complexity only when needed** - Skip Redis/Elasticsearch for MVP
4. **Familiar tools** - GCP is similar to App Engine experience

The technology stack is ready for implementation in Phase 1 Tasks 1.1-1.5 (Infrastructure Setup).
