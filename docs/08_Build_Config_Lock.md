# Build Config Lock (Confirmed Decisions)

This file freezes key decisions to avoid churn during 2-day implementation.

## Confirmed
- **Primary LLM provider:** MiniMax
- **Secondary candidate:** Kimi (evaluate during implementation)
- **Python version:** 3.13
- **Deploy auth strategy:** Workload Identity Federation (GitHub Actions -> GCP)
- **CI/CD scope:**
  - lint
  - unit tests
  - integration tests
  - docker image build
  - push to GHCR
  - deploy to Cloud Run
- **Data strategy:** synthetic scenarios + deterministic labeling rules

## Deferred / Placeholder (to fill at implementation)
- `GCP_PROJECT_ID=YOUR_PROJECT_ID`
- `GCP_REGION=YOUR_REGION` (recommended: `us-central1`)
- `GCP_WORKLOAD_IDENTITY_PROVIDER=projects/.../locations/global/workloadIdentityPools/.../providers/...`
- `GCP_SERVICE_ACCOUNT_EMAIL=...@...iam.gserviceaccount.com`

## Notes
- Keep MiniMax as primary for execution reliability under timeline constraints.
- Promote Kimi only after canary checks pass (auth + JSON mode + tool-call sanity + latency).
