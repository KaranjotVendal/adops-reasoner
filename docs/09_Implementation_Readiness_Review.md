# Implementation Readiness Review

Date: current

## Overall status
You are ready to implement.
No architecture blockers remain.

## Confirmed decisions
- 2-day showcase scope locked
- Multi-agent pipeline locked (Analyzer + Validator)
- MiniMax primary provider locked
- Kimi compatibility test deferred to implementation phase
- Terraform included (minimal)
- CI/CD included (GitHub Actions + GHCR + Cloud Run)
- WIF chosen for deploy auth
- Python 3.13 locked

## What still needs placeholders filled
1. GCP project setup values
2. WIF provider resource name
3. service account email for deployment
4. GitHub repository secrets

## Required GitHub secrets checklist
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `MINIMAX_API_KEY`

## Required implementation order
Follow stacked PRs in this order:
1. PR #1 scaffold/contracts/data
2. PR #2 analyzer
3. PR #3 validator/orchestration
4. PR #4 evals/demo
5. PR #5 terraform
6. PR #6 ci/cd deploy

## Risk watchlist
- GHCR pull permissions from Cloud Run (keep image public initially if needed)
- WIF setup friction (validate early with a minimal auth test)
- JSON output truncation due to max tokens (set safe max and validate parser)
- provider rate limits during demo (add retries and graceful fallback)

## Fast preflight before coding
- [ ] `uv --version`
- [ ] `python --version` is 3.13
- [ ] MiniMax key exported locally and one test call works
- [ ] repo branch strategy confirmed
- [ ] placeholders documented for GCP/WIF

## Definition of “showcase ready”
- API deployed on Cloud Run
- multi-agent response includes `requires_human_review`
- eval metric artifact generated from synthetic dataset
- CI/CD pipeline visible in repo actions
- can explain architecture + trade-offs in 5 minutes
