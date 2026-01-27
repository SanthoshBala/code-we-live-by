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
| **Frontend** | Next.js (React) | 14.x |
| **Frontend Styling** | Tailwind CSS | 3.x |
| **Frontend State** | TanStack Query | 5.x |
| **Backend** | Python (FastAPI) | 3.11+ |
| **ORM** | SQLAlchemy | 2.x |
| **Database** | PostgreSQL | 15+ |
| **Search** | Elasticsearch | 8.x |
| **Cache** | Redis | 7.x |
| **Hosting** | AWS | - |
| **Containerization** | Docker | - |
| **Orchestration** | AWS ECS Fargate | - |
| **CI/CD** | GitHub Actions | - |
| **Monitoring** | Datadog | - |
| **Error Tracking** | Sentry | - |

### Key Decisions Summary

| Decision Area | Choice | Primary Rationale |
|---------------|--------|-------------------|
| Frontend Framework | **Next.js** | SSR/SSG for SEO, React ecosystem, App Router |
| Backend Language | **Python** | Existing prototypes, data processing strength, FastAPI performance |
| Database | **PostgreSQL** | Already decided in Task 0.11; best relational + full-text |
| Search | **Elasticsearch** | Superior full-text search, faceted navigation |
| Cache | **Redis** | Industry standard, versatile, excellent performance |
| Hosting | **AWS** | Mature ecosystem, government-friendly, cost-effective |

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

### 8.1 Candidates Evaluated

| Provider | Key Strengths | Key Weaknesses |
|----------|---------------|----------------|
| **AWS** | Mature, government-friendly, comprehensive | Complex, can be expensive |
| **GCP** | BigQuery, ML services, clean UI | Smaller ecosystem |
| **Azure** | Microsoft integration, enterprise | Complex pricing |
| **Vercel + Railway** | Simple, fast deployment | Limited control, vendor lock-in |
| **DigitalOcean** | Simple, affordable | Limited managed services |

### 8.2 Evaluation Matrix

| Criterion | AWS | GCP | Azure | Vercel+Railway |
|-----------|-----|-----|-------|----------------|
| Managed PostgreSQL | 10/10 | 9/10 | 8/10 | 7/10 |
| Managed Elasticsearch | 9/10 | 7/10 | 7/10 | 3/10 |
| Managed Redis | 10/10 | 8/10 | 8/10 | 6/10 |
| CDN | 10/10 | 9/10 | 8/10 | 10/10 |
| Container Orchestration | 10/10 | 10/10 | 9/10 | 5/10 |
| Government Compliance | 10/10 | 8/10 | 9/10 | 4/10 |
| Cost Efficiency | 7/10 | 8/10 | 6/10 | 8/10 |
| **Weighted Total** | **9.1** | **8.4** | **7.9** | **6.1** |

### 8.3 Decision: AWS

**Selected**: Amazon Web Services (AWS)

**Primary Reasons**:

1. **Government Readiness**:
   - FedRAMP authorized
   - GovCloud available if needed
   - Used by Congress.gov, many government sites
   - CWLB may eventually integrate with government systems

2. **Managed Services**:
   - **RDS PostgreSQL**: Automated backups, failover, read replicas
   - **OpenSearch**: Elasticsearch-compatible, managed
   - **ElastiCache**: Managed Redis
   - **CloudFront**: Global CDN with edge locations

3. **Mature Ecosystem**:
   - Extensive documentation
   - Large community
   - Proven at scale
   - Rich tooling (AWS CLI, SDKs, CDK)

4. **Cost Controls**:
   - Reserved instances for predictable workloads
   - Spot instances for batch processing (data pipeline)
   - Detailed cost explorer
   - AWS Nonprofit credits available

5. **Scalability Path**:
   - Easy to scale up as usage grows
   - Auto-scaling groups
   - Multi-AZ for high availability

### 8.4 AWS Architecture

```
                                    ┌─────────────────────┐
                                    │     CloudFront      │
                                    │        (CDN)        │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   Application       │
                                    │   Load Balancer     │
                                    └──────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
           ┌────────▼────────┐       ┌────────▼────────┐       ┌────────▼────────┐
           │   ECS Fargate   │       │   ECS Fargate   │       │   ECS Fargate   │
           │   (Frontend)    │       │    (Backend)    │       │   (Backend)     │
           │   Next.js       │       │    FastAPI      │       │   FastAPI       │
           └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
                    │                         │                          │
                    │                         │                          │
                    │              ┌──────────▼──────────────────────────┘
                    │              │
                    │    ┌─────────▼─────────┐    ┌─────────────────────┐
                    │    │   ElastiCache     │    │    OpenSearch       │
                    │    │     (Redis)       │    │   (Elasticsearch)   │
                    │    └───────────────────┘    └─────────────────────┘
                    │              │                         │
                    │              │                         │
                    │    ┌─────────▼─────────────────────────▼─────────┐
                    │    │              RDS PostgreSQL                  │
                    │    │          (Multi-AZ, Read Replica)           │
                    └────┤                                             │
                         └─────────────────────────────────────────────┘
```

### 8.5 AWS Services Selection

| Service | AWS Service | Specification |
|---------|-------------|---------------|
| Compute (Frontend) | ECS Fargate | 0.5 vCPU, 1GB RAM per task |
| Compute (Backend) | ECS Fargate | 1 vCPU, 2GB RAM per task |
| Database | RDS PostgreSQL | db.r6g.large (2 vCPU, 16GB RAM) |
| Search | OpenSearch | t3.medium.search (2 nodes) |
| Cache | ElastiCache Redis | cache.r6g.large (2 nodes) |
| CDN | CloudFront | Standard distribution |
| Object Storage | S3 | Standard tier |
| DNS | Route 53 | Hosted zone |
| Secrets | Secrets Manager | API keys, DB credentials |
| Monitoring | CloudWatch | Logs, metrics, alarms |
| CI/CD | CodePipeline + CodeBuild | Or GitHub Actions |

---

## 9. DevOps and Infrastructure

### 9.1 Containerization: Docker

All services containerized for consistency across environments.

**Frontend Dockerfile**:

```dockerfile
# Dockerfile.frontend
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

**Backend Dockerfile**:

```dockerfile
# Dockerfile.backend
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS builder
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

FROM base AS runner
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY ./app ./app
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### 9.2 Infrastructure as Code: Terraform

```hcl
# main.tf (simplified)

provider "aws" {
  region = var.aws_region
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "cwlb-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
}

# RDS PostgreSQL
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.0.0"

  identifier = "cwlb-postgres"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.r6g.large"

  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = "cwlb"
  username = var.db_username
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.security_group.security_group_id]

  backup_retention_period = 7
  skip_final_snapshot     = false
  deletion_protection     = true
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "cwlb-redis"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
}

# OpenSearch
resource "aws_opensearch_domain" "search" {
  domain_name    = "cwlb-search"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type  = "t3.medium.search"
    instance_count = 2
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 100
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "cwlb-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

### 9.3 CI/CD: GitHub Actions

```yaml
# .github/workflows/deploy.yml

name: Deploy CWLB

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY_BACKEND: cwlb-backend
  ECR_REPOSITORY_FRONTEND: cwlb-frontend
  ECS_CLUSTER: cwlb-cluster

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          cd backend
          pytest --cov=app tests/

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci

      - name: Run frontend tests
        run: |
          cd frontend
          npm run test

      - name: Build frontend
        run: |
          cd frontend
          npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push backend image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          cd backend
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:$IMAGE_TAG

      - name: Build and push frontend image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          cd frontend
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:$IMAGE_TAG

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster $ECS_CLUSTER --service cwlb-backend --force-new-deployment
          aws ecs update-service --cluster $ECS_CLUSTER --service cwlb-frontend --force-new-deployment
```

---

## 10. Monitoring and Observability

### 10.1 Monitoring Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **Metrics** | Datadog | Infrastructure and application metrics |
| **Logs** | Datadog / CloudWatch | Centralized logging |
| **Traces** | Datadog APM | Distributed tracing |
| **Errors** | Sentry | Error tracking and alerting |
| **Uptime** | Datadog Synthetics | Uptime monitoring |

### 10.2 Key Metrics to Track

**Application Metrics**:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API response time (p50) | < 100ms | > 200ms |
| API response time (p99) | < 500ms | > 1000ms |
| Error rate | < 0.1% | > 1% |
| Request throughput | Monitor | Spike > 3x baseline |

**Infrastructure Metrics**:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| CPU utilization | < 70% | > 85% |
| Memory utilization | < 80% | > 90% |
| Database connections | < 80% max | > 90% max |
| Cache hit rate | > 90% | < 70% |

**Database Metrics**:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Query time (p99) | < 100ms | > 500ms |
| Connection count | < 150 | > 180 |
| Replication lag | < 10s | > 60s |
| Disk usage | < 70% | > 85% |

### 10.3 Alerting Strategy

```yaml
# Datadog monitors (simplified)

monitors:
  - name: "High API Error Rate"
    type: metric
    query: "avg(last_5m):sum:cwlb.api.errors{*} / sum:cwlb.api.requests{*} > 0.01"
    message: "Error rate exceeded 1%"
    priority: P1

  - name: "Slow API Response"
    type: metric
    query: "avg(last_5m):p99:cwlb.api.response_time{*} > 1000"
    message: "P99 response time > 1 second"
    priority: P2

  - name: "Database Connection Pool Exhausted"
    type: metric
    query: "avg(last_5m):cwlb.db.connections{*} > 180"
    message: "Database connections near limit"
    priority: P1

  - name: "Low Cache Hit Rate"
    type: metric
    query: "avg(last_15m):cwlb.cache.hit_rate{*} < 0.7"
    message: "Cache hit rate below 70%"
    priority: P3
```

### 10.4 Logging Configuration

**Backend Logging (Python)**:

```python
# app/core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

# Configure logging
def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )
```

---

## 11. Complete Technology Stack Summary

### 11.1 Full Stack Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Next.js 14        │  React 18          │  Tailwind CSS     │  TypeScript  │
│  (App Router)      │  (Components)      │  (Styling)        │  (Types)     │
├─────────────────────────────────────────────────────────────────────────────┤
│  TanStack Query    │  Radix UI          │  Recharts         │  react-diff  │
│  (Data fetching)   │  (Accessibility)   │  (Charts)         │  (Diffs)     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               API LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI           │  Pydantic          │  SQLAlchemy 2.0   │  Python 3.11 │
│  (Framework)       │  (Validation)      │  (ORM)            │  (Runtime)   │
├─────────────────────────────────────────────────────────────────────────────┤
│  httpx             │  pytest            │  Alembic          │  Gunicorn    │
│  (HTTP client)     │  (Testing)         │  (Migrations)     │  (Server)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL 15     │  Elasticsearch 8   │  Redis 7          │              │
│  (Primary DB)      │  (Search)          │  (Cache)          │              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  AWS ECS Fargate   │  AWS RDS           │  AWS OpenSearch   │  ElastiCache │
│  (Compute)         │  (PostgreSQL)      │  (Search)         │  (Redis)     │
├─────────────────────────────────────────────────────────────────────────────┤
│  CloudFront        │  Route 53          │  S3               │  ECR         │
│  (CDN)             │  (DNS)             │  (Storage)        │  (Registry)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEVOPS LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Docker            │  Terraform         │  GitHub Actions   │  Datadog     │
│  (Containers)      │  (IaC)             │  (CI/CD)          │  (Monitoring)│
├─────────────────────────────────────────────────────────────────────────────┤
│  Sentry            │  Git               │  GitHub           │              │
│  (Errors)          │  (Version Control) │  (Code hosting)   │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Technology Versions

| Category | Technology | Version | Notes |
|----------|------------|---------|-------|
| **Frontend** | Next.js | 14.x | App Router |
| | React | 18.x | |
| | TypeScript | 5.x | |
| | Tailwind CSS | 3.x | |
| | TanStack Query | 5.x | Data fetching |
| **Backend** | Python | 3.11+ | |
| | FastAPI | 0.109+ | |
| | SQLAlchemy | 2.0+ | Async support |
| | Pydantic | 2.x | |
| | Alembic | 1.13+ | |
| **Database** | PostgreSQL | 15+ | |
| **Search** | Elasticsearch | 8.x | Or OpenSearch 2.x |
| **Cache** | Redis | 7.x | |
| **Infrastructure** | Docker | Latest | |
| | Terraform | 1.6+ | |
| **Monitoring** | Datadog | SaaS | |
| | Sentry | SaaS | |

---

## 12. Cost Projections

### 12.1 Phase 1 (MVP) Monthly Costs

| Service | Specification | Monthly Cost |
|---------|---------------|--------------|
| **ECS Fargate (Frontend)** | 2 tasks × 0.5 vCPU × 1GB | ~$30 |
| **ECS Fargate (Backend)** | 2 tasks × 1 vCPU × 2GB | ~$60 |
| **RDS PostgreSQL** | db.r6g.large, Multi-AZ | ~$350 |
| **OpenSearch** | t3.medium.search × 2 | ~$150 |
| **ElastiCache Redis** | cache.r6g.large | ~$130 |
| **CloudFront** | 100GB transfer | ~$20 |
| **S3** | 10GB storage | ~$1 |
| **Route 53** | Hosted zone + queries | ~$5 |
| **Secrets Manager** | 10 secrets | ~$5 |
| **CloudWatch** | Logs + metrics | ~$30 |
| **Data transfer** | 200GB outbound | ~$20 |
| **Datadog** | Pro plan (3 hosts) | ~$75 |
| **Sentry** | Team plan | ~$26 |
| **Domain** | Annual / 12 | ~$2 |
| **TOTAL (Phase 1)** | | **~$900/month** |

### 12.2 Phase 2 (Scale) Monthly Costs

| Service | Specification | Monthly Cost |
|---------|---------------|--------------|
| **ECS Fargate (Frontend)** | 4 tasks × 1 vCPU × 2GB | ~$120 |
| **ECS Fargate (Backend)** | 6 tasks × 1 vCPU × 2GB | ~$180 |
| **RDS PostgreSQL** | db.r6g.xlarge, Multi-AZ + Read Replica | ~$700 |
| **OpenSearch** | m6g.large.search × 3 | ~$400 |
| **ElastiCache Redis** | cache.r6g.large × 2 (cluster) | ~$260 |
| **CloudFront** | 500GB transfer | ~$50 |
| **Other services** | | ~$150 |
| **Monitoring (Datadog)** | Pro plan (10 hosts) | ~$250 |
| **TOTAL (Phase 2)** | | **~$2,100/month** |

### 12.3 Cost Optimization Strategies

1. **Reserved Instances**: 30-40% savings on RDS, ElastiCache with 1-year commitment
2. **Spot Instances**: Use for data pipeline batch jobs (70% savings)
3. **Right-sizing**: Start small, scale based on actual usage
4. **Caching**: Aggressive caching reduces database load
5. **AWS Nonprofit Credits**: Apply for credits (if applicable)
6. **CloudFront Caching**: Reduces origin requests

---

## 13. Implementation Roadmap

### 13.1 Infrastructure Setup (Week 1-2)

```
Week 1:
├── Day 1-2: Set up AWS account, IAM roles, VPC
├── Day 3-4: Provision RDS PostgreSQL, run schema
├── Day 5: Set up ElastiCache Redis
└── Weekend: Set up OpenSearch (can run parallel)

Week 2:
├── Day 1-2: Set up ECS cluster, ECR repositories
├── Day 3: Configure ALB, SSL certificates
├── Day 4: Set up CloudFront distribution
├── Day 5: Configure DNS in Route 53
└── Weekend: Terraform modules for reproducibility
```

### 13.2 Application Setup (Week 3-4)

```
Week 3:
├── Day 1-2: Initialize Next.js project, configure Tailwind
├── Day 3-4: Initialize FastAPI project, configure SQLAlchemy
├── Day 5: Set up Alembic migrations, run initial migration
└── Weekend: Docker containers for both services

Week 4:
├── Day 1-2: GitHub Actions CI pipeline
├── Day 3: GitHub Actions CD pipeline
├── Day 4: Datadog agent setup
├── Day 5: Sentry integration
└── Weekend: Documentation, runbooks
```

### 13.3 Integration with Phase 1 Tasks

| Task ID | Task Name | Technology Used |
|---------|-----------|-----------------|
| 1.1 | Development environment | Docker, GitHub |
| 1.2 | PostgreSQL setup | RDS PostgreSQL, Alembic |
| 1.3 | Elasticsearch setup | OpenSearch |
| 1.4 | Redis setup | ElastiCache |
| 1.5 | Hosting infrastructure | ECS, CloudFront, ALB |
| 1.20-1.24 | Backend API | FastAPI, SQLAlchemy |
| 1.25-1.37 | Frontend UI | Next.js, Tailwind, React |
| 1.46 | Production deployment | Terraform, GitHub Actions |

---

## 14. Risk Assessment

### 14.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Next.js complexity | Medium | Medium | Team training, start with Pages Router fallback |
| FastAPI async issues | Low | Medium | Comprehensive testing, sync fallbacks |
| PostgreSQL performance | Low | High | Monitoring, query optimization, read replicas |
| Elasticsearch sync issues | Medium | Medium | Transaction outbox pattern, monitoring |
| AWS cost overruns | Medium | Medium | Budget alerts, reserved instances, right-sizing |

### 14.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Service outage | Low | High | Multi-AZ, health checks, auto-recovery |
| Data loss | Very Low | Critical | Automated backups, point-in-time recovery |
| Security breach | Low | Critical | WAF, security groups, secrets management |
| Scaling issues | Medium | Medium | Load testing, auto-scaling policies |

### 14.3 Organizational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Key person dependency | Medium | High | Documentation, pair programming, cross-training |
| Scope creep | High | Medium | Clear MVP scope, backlog discipline |
| Budget constraints | Medium | Medium | Phased rollout, cost monitoring |

---

## Appendix A: Alternative Considered - Go Backend

**Why Go was seriously considered**:
- Superior performance for high-throughput scenarios
- Excellent concurrency model
- Single binary deployment
- Strong typing

**Why Go was not selected**:
- Would require rewriting all Python prototypes
- Smaller ecosystem for legal/data processing
- Team more experienced with Python
- Performance difference not critical for CWLB's I/O-bound workload

**Recommendation**: Consider Go for specific high-performance microservices in Phase 3 if needed.

---

## Appendix B: Alternative Considered - Vercel + Railway

**Why Vercel + Railway was considered**:
- Simpler deployment
- Excellent developer experience
- Lower operational overhead
- Cost-effective for small scale

**Why it was not selected**:
- Less control over infrastructure
- Vendor lock-in concerns
- Government compliance uncertainty
- Limited managed database options
- May not scale as cost-effectively

**Recommendation**: Acceptable for a prototype or proof-of-concept, but AWS better for production civic tech platform.

---

## Appendix C: Development Environment Setup

### Local Development Prerequisites

```bash
# Required software
- Docker Desktop 4.x
- Node.js 20.x (via nvm)
- Python 3.11+ (via pyenv)
- PostgreSQL 15 client (psql)
- Redis CLI
- AWS CLI v2
- Terraform 1.6+

# Recommended IDE
- VS Code with extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
  - Docker
  - Remote - Containers
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

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://cwlb:localdev@postgres:5432/cwlb
      - REDIS_URL=redis://redis:6379
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - postgres
      - redis
      - elasticsearch

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

volumes:
  postgres_data:
  es_data:
```

---

## Summary

Task 0.13 establishes the complete technology stack for CWLB:

| Layer | Selection | Key Rationale |
|-------|-----------|---------------|
| **Frontend** | Next.js 14 + React | SEO, ecosystem, performance |
| **Backend** | Python + FastAPI | Existing code, data processing |
| **Database** | PostgreSQL 15 | Already designed, best relational |
| **Search** | Elasticsearch 8 | Full-text, facets, analytics |
| **Cache** | Redis 7 | Industry standard, versatile |
| **Hosting** | AWS | Government-ready, mature |
| **DevOps** | Docker + Terraform + GitHub Actions | Reproducibility, automation |

The stack optimizes for:
- **Developer productivity** with familiar, well-documented tools
- **Performance** with async Python, SSR, and aggressive caching
- **Scalability** with containerized services and managed databases
- **Cost efficiency** with right-sized resources and optimization paths
- **Maintainability** with long-term supported technologies

The technology stack is ready for implementation in Phase 1 Tasks 1.1-1.5 (Infrastructure Setup).
