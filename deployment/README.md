# Deployment Guide

CWLB runs on **GCP Cloud Run** with **Cloud SQL** (PostgreSQL) and **Secret Manager**.

## Architecture

```
                    ┌─────────────────┐
                    │   Cloud Run     │
  Users ──────────► │  cwlb-frontend  │
                    │  (Next.js)      │
                    └────────┬────────┘
                             │ /api/* rewrites
                    ┌────────▼────────┐
                    │   Cloud Run     │
                    │  cwlb-backend   │
                    │  (FastAPI)      │
                    └────────┬────────┘
                             │ Cloud SQL Proxy
                    ┌────────▼────────┐
                    │   Cloud SQL     │
                    │  PostgreSQL 15  │
                    └─────────────────┘
```

Both Cloud Run services scale to zero when idle.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI) — install via `brew install --cask google-cloud-sdk` on macOS
- A GCP project with billing enabled

## GCP Project Setup

### 1. Set variables

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export AR_REPO=cwlb
export SQL_INSTANCE=cwlb-db
export DB_NAME=cwlb
export DB_USER=cwlb
```

### 2. Enable APIs

```bash
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    iam.googleapis.com \
    --project $PROJECT_ID
```

### 3. Create Artifact Registry repository

```bash
gcloud artifacts repositories create $AR_REPO \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID
```

### 4. Create Cloud SQL instance

```bash
gcloud sql instances create $SQL_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --project=$PROJECT_ID

gcloud sql databases create $DB_NAME \
    --instance=$SQL_INSTANCE \
    --project=$PROJECT_ID

read -s DB_PASSWORD
gcloud sql users create $DB_USER \
    --instance=$SQL_INSTANCE \
    --password=$DB_PASSWORD \
    --project=$PROJECT_ID
```

### 5. Store secrets in Secret Manager

```bash
# Database URL for Cloud SQL via Unix socket (uses $DB_PASSWORD from previous step)
echo -n "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${PROJECT_ID}:${REGION}:${SQL_INSTANCE}" \
    | gcloud secrets create DATABASE_URL --data-file=- --project=$PROJECT_ID

# Verify the secret version was created
gcloud secrets versions list DATABASE_URL --project=$PROJECT_ID
```

### 6. Set up Workload Identity Federation (for GitHub Actions)

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global \
    --display-name="GitHub Actions Pool" \
    --project=$PROJECT_ID

# Create a provider for GitHub (attribute-condition is required by GCP)
REPO_OWNER=SanthoshBala
REPO_NAME=code-we-live-by

gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="attribute.repository == '${REPO_OWNER}/${REPO_NAME}'" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --project=$PROJECT_ID

# Create a service account for CD
gcloud iam service-accounts create github-cd \
    --display-name="GitHub CD" \
    --project=$PROJECT_ID

# Grant necessary roles to the CD service account
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/cloudbuild.builds.editor"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:github-cd@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/storage.admin"

# Allow GitHub Actions to impersonate the service account
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding \
    "github-cd@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUM}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO_OWNER}/${REPO_NAME}" \
    --project=$PROJECT_ID
```

### 7. Configure GitHub repository variables

Set these in **Settings > Secrets and variables > Actions > Variables**:

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | `us-central1` |
| `AR_REPO` | `cwlb` |
| `CLOUD_SQL_INSTANCE` | `your-project-id:us-central1:cwlb-db` |
| `WIF_PROVIDER` | `projects/PROJECT_NUM/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `github-cd@your-project-id.iam.gserviceaccount.com` |

### 8. Grant Cloud Run access to secrets

```bash
# Grant the default compute service account (used by Cloud Run at runtime) access to read the DATABASE_URL secret
gcloud secrets add-iam-policy-binding DATABASE_URL \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
```

## GCS Cache Bucket

The pipeline cache bucket (`cwlb-pipeline-cache`) stores downloaded XML/HTM files from GovInfo and Congress.gov to avoid re-fetching on subsequent pipeline runs. A lifecycle policy auto-deletes objects after 180 days (see `gcs-cache-lifecycle.json`).

```bash
# Apply the lifecycle policy
gcloud storage buckets update gs://cwlb-pipeline-cache \
    --lifecycle-file=deployment/gcs-cache-lifecycle.json
```

## Running Migrations

Run Alembic migrations via Cloud Run Jobs or a one-off Cloud Run execution:

```bash
gcloud run jobs execute cwlb-migrate \
    --region $REGION \
    --project $PROJECT_ID
```

Or create the job first:

```bash
gcloud run jobs create cwlb-migrate \
    --image "$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/cwlb-backend:latest" \
    --region $REGION \
    --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
    --set-cloudsql-instances "$PROJECT_ID:$REGION:$SQL_INSTANCE" \
    --command "uv,run,alembic,upgrade,head" \
    --project $PROJECT_ID
```

## Updating Secrets

```bash
echo -n "new-value" | gcloud secrets versions add DATABASE_URL --data-file=- --project=$PROJECT_ID
```

Cloud Run picks up new secret versions on the next deployment (or service restart).

## Troubleshooting

### View logs

```bash
# Backend logs
gcloud run services logs read cwlb-backend --region $REGION --project $PROJECT_ID --limit 50

# Frontend logs
gcloud run services logs read cwlb-frontend --region $REGION --project $PROJECT_ID --limit 50
```

### Check service status

```bash
gcloud run services describe cwlb-backend --region $REGION --project $PROJECT_ID
gcloud run services describe cwlb-frontend --region $REGION --project $PROJECT_ID
```

### Common issues

- **502 Bad Gateway**: Service is starting up or crashed. Check logs for errors.
- **Connection refused to Cloud SQL**: Ensure `--add-cloudsql-instances` is set and the service account has `roles/cloudsql.client`.
- **Secret not found**: Verify the secret exists in Secret Manager and the service account has `roles/secretmanager.secretAccessor`.
