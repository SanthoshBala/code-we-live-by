# Cloud Run Job: Bootstrap Fan-out

This directory documents how to run the bootstrap pipeline as a distributed
Cloud Run Job, where each task processes one (or a few) US Code titles in
parallel rather than running all 54 titles in a single container.

## Why fan-out?

The single-container bootstrap uses `asyncio.gather` with a semaphore
(concurrency cap: 6). Fan-out breaks the work across independent Cloud Run Job
tasks, giving each title its own CPU and memory allocation and enabling
per-title retry on failure without re-running the whole job.

## How it works

Cloud Run Jobs sets two environment variables on every task:

| Variable | Description |
|---|---|
| `CLOUD_RUN_TASK_INDEX` | 0-based index of this task |
| `CLOUD_RUN_TASK_COUNT` | Total number of tasks in the job |

The `chrono-bootstrap` CLI reads these variables and partitions titles using
round-robin: task `i` processes `ALL_TITLES[i::task_count]`. With 54 tasks,
each task processes exactly one title.

**Coordination**: Task 0 creates the `OLRCReleasePoint` and `CodeRevision`
records in the database, then commits. Non-zero tasks poll for these records
(up to 120 s) before inserting snapshots, satisfying the FK constraint.

**Finalization**: Tasks exit after ingesting their titles. The revision remains
in `INGESTING` status. Run `chrono-bootstrap-finalize` after the job completes
to mark it `INGESTED`.

## Workflow

```
┌─────────────────────────────────────────────────────┐
│  Cloud Run Job (54 tasks, parallelism 54)           │
│                                                     │
│  Task 0: creates revision records, ingests title 1  │
│  Task 1: waits for records, ingests title 2         │
│  Task 2: waits for records, ingests title 3         │
│  ...                                                │
│  Task 53: waits for records, ingests title 54       │
└─────────────────────────────────────────────────────┘
                        ↓ job completes
  chrono-bootstrap-finalize 113-21   (marks INGESTED)
```

## Running the fan-out job

### Prerequisites

- Docker image built and pushed to Artifact Registry
- Cloud Run Job service account with Cloud SQL Client role
- `CLOUD_SQL_DATABASE_URL` secret in Secret Manager

### One-time: create the job

```bash
IMAGE="us-central1-docker.pkg.dev/YOUR_PROJECT/cwlb/backend:latest"
PROJECT="YOUR_PROJECT"
REGION="us-central1"
SQL_CONN="YOUR_PROJECT:us-central1:cwlb-db"
DB_URL_SECRET="projects/YOUR_PROJECT/secrets/CLOUD_SQL_DATABASE_URL/versions/latest"

gcloud run jobs create bootstrap-fanout \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --tasks 54 \
    --parallelism 54 \
    --max-retries 3 \
    --task-timeout 3600 \
    --memory 4Gi \
    --cpu 2 \
    --set-cloudsql-instances "$SQL_CONN" \
    --set-secrets "CLOUD_SQL_DATABASE_URL=$DB_URL_SECRET" \
    --command "uv" \
    --args "run,pipeline,chrono-bootstrap,113-21"
```

### Execute the job

```bash
gcloud run jobs execute bootstrap-fanout \
    --region "$REGION" \
    --project "$PROJECT" \
    --wait
```

### Finalize after the job completes

```bash
# Connect to a Cloud Run instance or run locally with DB access:
uv run pipeline chrono-bootstrap-finalize 113-21
```

### Or: override the release point at execute time

```bash
gcloud run jobs execute bootstrap-fanout \
    --region "$REGION" \
    --project "$PROJECT" \
    --update-args "run,pipeline,chrono-bootstrap,119-72not60" \
    --wait
```

## Local testing (single-task simulation)

Test a specific task without Cloud Run:

```bash
# Simulate task 3 of 54
CLOUD_RUN_TASK_INDEX=3 CLOUD_RUN_TASK_COUNT=54 \
    uv run pipeline chrono-bootstrap 113-21

# Or use CLI flags directly
uv run pipeline chrono-bootstrap 113-21 --task-index 3 --task-count 54
```

## Adjusting parallelism

To balance cost vs. speed, use fewer tasks (each processes more titles):

```bash
# 27 tasks, each handles 2 titles
gcloud run jobs update bootstrap-fanout \
    --tasks 27 --parallelism 27 ...
```

The CLI handles any `task_count` value via round-robin partitioning.

## Resource sizing

| Task count | Titles per task | Recommended memory | Recommended CPU |
|---|---|---|---|
| 54 | 1 | 2 Gi | 1 |
| 27 | 2 | 3 Gi | 2 |
| 18 | 3 | 4 Gi | 2 |
| 9 | 6 | 8 Gi | 4 |

Large titles (e.g., Title 26 / Internal Revenue Code) require more memory.
When using fewer tasks, size for the largest title in each group.
