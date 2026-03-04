# PR6: CI/CD Pipeline

**Branch:** `pr/06-cicd-ghcr-cloudrun`  
**Base:** `pr/05-terraform-minimal`  
**Status:** Ready for Review

---

## Summary

This PR provides a complete CI/CD pipeline with GitHub Actions for building, testing, and deploying the Campaign Analyst to GCP Cloud Run.

---

## Pipeline Stages

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Lint & Test    │────▶│  Build & Push   │────▶│  Test Deployment │ (PR branches)
│  (ruff, pytest) │     │  (GHCR)         │     │  (staging)       │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                                                          │
                                    ┌─────────────────────┘
                                    ▼
                            ┌──────────────────┐
                            │  Deploy Prod     │ (main branch only)
                            │  (Cloud Run)     │
                            └──────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │  Cleanup Staging │
                            └──────────────────┘
```

---

## Jobs

### 1. Lint & Test
- ruff lint check
- ruff format check
- pytest unit tests
- pytest integration tests

### 2. Build & Push
- Docker build with Buildx
- Push to GitHub Container Registry (GHCR)
- Multi-tag: branch, sha, latest
- Layer caching for fast builds

### 3. Test Deployment (PR branches)
- Deploy to `campaign-analyst-staging`
- Smoke test with `/health` endpoint
- Validates deployment before merge

### 4. Deploy Production (main only)
- Deploy to `campaign-analyst`
- Update with secrets from Secret Manager
- Production smoke test

### 5. Cleanup Staging
- Removes staging service after production deploy

---

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload identity federation |
| `GCP_SERVICE_ACCOUNT` | Service account for deployment |
| `GCP_REGION` | Cloud Run region |
| `GCP_PROJECT_ID` | GCP project ID |

---

## FastAPI Application

New `src/api/main.py` provides:

- `GET /health` - Health check for Cloud Run
- `POST /analyze` - Campaign analysis endpoint
- `GET /models` - List available models
- `GET /sessions/{id}` - Session replay

---

## Files Changed

- `.github/workflows/ci.yml` - Complete pipeline
- `src/api/main.py` - FastAPI application
- `pyproject.toml` - Added uvicorn dependency
- `tests/unit/test_ci.py` - Updated for new job names

---

## Test Coverage

- 4 CI tests passing
- Workflow validation
- Dockerfile validation

---

## Usage

### Automatic Deployment

- **PR branches**: Deploy to staging for testing
- **Main branch**: Deploy to production

### Manual Trigger

```bash
# Re-run workflow in GitHub Actions UI
# Or push to trigger
```

---

## Checklist

- [x] GitHub Actions workflow
- [x] Lint, test, build, deploy stages
- [x] Staging deployment for PRs
- [x] Production deployment for main
- [x] FastAPI application
- [x] Health check endpoints
- [x] Smoke tests
- [x] Tests passing
