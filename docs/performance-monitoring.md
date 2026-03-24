# Performance Monitoring

This guide covers how to monitor API performance locally and in production (Cloud Run).

## Built-in Instrumentation

The backend includes two performance features added in PR #126:

1. **Server-Timing header** — Every API response includes `Server-Timing: total;dur=<ms>`, visible in browser DevTools.
2. **Slow request logging** — Any request taking >500ms is logged at WARNING level with the prefix `SLOW`.

## Local Development

### Browser DevTools

1. Open DevTools → **Network** tab
2. Click any `/api/` request
3. Check **Response Headers** → `Server-Timing: total;dur=142.5`
4. Chrome also shows Server-Timing entries in the **Timing** tab

### Identifying Slow Endpoints

With the dev server running (`uv run uvicorn app.main:app --reload --port 8000`), watch the terminal for WARNING lines:

```
WARNING - SLOW /api/v1/titles/26/sections 1243ms
```

### Key Endpoints to Profile

| Route | What to watch for |
|-------|-------------------|
| `/api/v1/titles/{id}/sections` | Title structure load time (column projection keeps this fast) |
| `/api/v1/sections/{title}/{section}` | Section lookup (CTE + chain threading, should be ~2 queries) |
| `/api/v1/laws/{congress}/{number}/text?format=metadata` | Metadata-only load (no file I/O) |
| `/api/v1/laws/{congress}/{number}/text?format=htm` | HTM content fetch |
| `/api/v1/laws/{congress}/{number}/diffs` | Diff computation (batch section fetching) |

## Production Monitoring (Cloud Run)

### Searching Logs with gcloud CLI

**Find all slow requests (last hour):**

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND textPayload=~"SLOW"' \
    --project=<your-project-id> \
    --freshness=1h \
    --format="table(timestamp, textPayload)"
```

**Filter to a specific endpoint:**

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND textPayload=~"SLOW" AND textPayload=~"/api/v1/titles"' \
    --project=<your-project-id> \
    --freshness=24h
```

**See all request timings (not just slow ones):**

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND textPayload=~"completed in"' \
    --project=<your-project-id> \
    --freshness=1h \
    --format="table(timestamp, textPayload)"
```

### Using the Cloud Console

1. Go to **console.cloud.google.com** → **Cloud Run** → select the service
2. Click the **Logs** tab (pre-filtered to the service)
3. Use the filter bar:
    - `SLOW` — all slow requests
    - `severity>=WARNING` — same result (slow requests log at WARNING)
    - `/api/v1/titles` — filter to title page requests
    - `completed in` — all request timings

### Extracting Response Time Data

Parse timings from logs for analysis:

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND textPayload=~"completed in"' \
    --project=<your-project-id> \
    --freshness=24h \
    --format=json \
    | jq -r '.[].textPayload' \
    | grep -oP '\d+ms' \
    | sort -n
```

### Setting Up Alerts

Create a log-based metric to trigger alerts on slow requests:

```bash
# Create the metric
gcloud logging metrics create slow_api_requests \
    --project=<your-project-id> \
    --description="API requests taking >500ms" \
    --log-filter='resource.type="cloud_run_revision" AND textPayload=~"SLOW"'
```

Then in **Cloud Console** → **Monitoring** → **Alerting**, create an alert policy on the `slow_api_requests` metric.

## Cache Behavior

The `CacheControlMiddleware` in `backend/app/core/cache_middleware.py` behaves differently by environment:

- **Development** (`DEBUG=true`): Sends `Cache-Control: no-store` — no caching, so content changes are always reflected immediately.
- **Production**: Sends `Cache-Control: public, max-age=300, stale-while-revalidate=3600` — browsers and CDNs cache responses for 5 minutes, with stale content served for up to 1 hour while revalidating in the background.

Cache is automatically bypassed on new deployments since Cloud Run assigns new revision URLs.

## Frontend Performance

React Query is configured in `frontend/src/components/QueryProvider.tsx` with:

- **gcTime**: 30 minutes (keeps unused data in memory for fast re-navigation)
- **refetchOnWindowFocus**: disabled (prevents unnecessary refetches when switching tabs)

The law page (`/laws/[congress]/[lawNumber]`) uses a three-stage loading pattern:

1. **Immediate**: Fetch metadata only (`?format=metadata`) — fast, single DB query
2. **Background prefetch**: After metadata renders, prefetch HTM and XML content
3. **On tab click**: Display already-cached content instantly
