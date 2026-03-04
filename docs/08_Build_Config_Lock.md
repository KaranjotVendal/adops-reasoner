# Build Config Lock (Latest)

## Confirmed
- Python: **3.13**
- Primary LLM: **MiniMax**
- Kimi: test during implementation
- Deploy auth: **Workload Identity Federation** (GitHub Actions -> GCP)
- CI/CD scope:
  - lint
  - unit tests
  - integration tests
  - docker build
  - push to GHCR
  - deploy to Cloud Run
- Data: synthetic scenarios + deterministic labels

## Placeholders (fill during implementation)
- `GCP_PROJECT_ID=YOUR_PROJECT_ID`
- `GCP_REGION=YOUR_REGION` (suggest `us-central1`)
- `WIF_PROVIDER=projects/.../locations/global/workloadIdentityPools/.../providers/...`
- `WIF_SERVICE_ACCOUNT=...@...iam.gserviceaccount.com`
- `MINIMAX_API_KEY=...`
