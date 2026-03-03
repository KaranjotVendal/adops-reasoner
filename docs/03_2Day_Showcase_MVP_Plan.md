# 2-Day Showcase MVP Plan (Pruned + IaC + CI/CD)

## Goal (for interview showcase, not full production)
In 2 days, build and deploy a **minimal multi-agent campaign analyst** on GCP that demonstrates:
1. Multi-agent orchestration (Analyzer + Validator)
2. Typed API contracts + tests
3. Containerized deployment on Cloud Run
4. Basic offline evaluation using synthetic scenarios
5. Lightweight IaC (Terraform) + CI/CD (GitHub Actions)

This is intentionally a **showcase system**: simple, explainable, reliable enough for demo.

---

## What to Cut (from full plan)
Do **not** do in this 2-day scope:
- Cloud SQL
- BigQuery ingestion pipeline
- Scheduler/PubSub
- Complex observability platform (Langfuse/LangSmith setup)
- Multi-environment release orchestration

Keep only what helps you confidently explain architecture + deployment.

---

## Minimal System Architecture

```text
                Demo Client / curl / Postman
                          |
                          v
                 FastAPI (Cloud Run)
                      /analyze
                          |
                ---------------------
                |                   |
                v                   v
       Agent 1: Analyzer      Agent 2: Validator
       (LLM recommendation)   (rule + optional LLM check)
                |                   |
                -----------+--------
                           |
                           v
                    Final Decision
      (action, confidence, rationale, requires_human_review)
                           |
                           v
               JSON response + structured logs
                (Cloud Logging in GCP)

GitHub Actions CI/CD:
  tests + docker build + push GHCR + deploy Cloud Run

Terraform:
  Cloud Run service + Secret Manager + Service Account/IAM
```

## Why this is enough
- Shows multi-agent design
- Shows deterministic safety gate (`requires_human_review`)
- Shows deployment competency on GCP
- Shows CI/CD and IaC maturity without over-building
- Shows evaluation thinking through golden scenarios

---

## Minimal Feature Set (must-have)

## API
- `GET /health`
- `POST /analyze`
- `POST /analyze/batch` (optional)

## Agent Pipeline
1. **Analyzer Agent**
   - Input: campaign snapshot
   - Output: action + confidence + reasoning + key_signals
2. **Validator Agent**
   - Checks consistency of analyzer output against input metrics
   - Flags low confidence or contradiction
3. **Final policy**
   - If validator fails or confidence < threshold => `requires_human_review = true`

## Data
- Synthetic scenario dataset (JSONL) with expected actions
- Offline eval script computes action accuracy on this dataset

## Deployment
- Dockerized app
- Terraform-provisioned Cloud Run + Secret Manager
- GitHub Actions workflow:
  - unit tests
  - integration tests
  - docker build
  - push to GHCR
  - deploy to Cloud Run (CD)

---

## Minimal Cloud/Platform Components

### GCP
1. **Cloud Run** — host API
2. **Secret Manager** — store model API key
3. **Cloud Logging** — request and decision traces
4. **IAM Service Account** — least privilege runtime identity

### GitHub
1. **GitHub Actions** — CI/CD
2. **GHCR** — container image registry

> Note: For fastest setup, keep GHCR image public or ensure Cloud Run can pull image with configured auth.

---

## 2-Day Execution Schedule

## Day 1 (Build core + tests)

### Block 1 (2 hrs)
- Scaffold project structure
- Add Pydantic models and enums
- Add synthetic dataset file (`data/scenarios_v1.jsonl`)

### Block 2 (3 hrs)
- Build Analyzer agent (LLM call + JSON parsing)
- Build Validator agent (simple rule + optional LLM check)
- Build orchestrator pipeline

### Block 3 (2 hrs)
- FastAPI endpoints (`/health`, `/analyze`)
- Unit + integration tests

### Block 4 (1 hr)
- Add offline eval script + run on synthetic scenarios
- Save baseline metrics in `evals/results_baseline.json`

## Day 2 (IaC + CI/CD + deploy + polish)

### Block 1 (2 hrs)
- Dockerfile + local container run
- Add structured logging with trace_id

### Block 2 (2 hrs)
- Add minimal Terraform for Cloud Run + Secret Manager + SA/IAM
- Apply infra

### Block 3 (2 hrs)
- Add GitHub Actions workflow:
  - tests
  - docker build
  - push GHCR
  - deploy Cloud Run

### Block 4 (2 hrs)
- Smoke test deployed endpoint
- Create demo script with 3 strong scenarios
- Write concise README + 5-minute architecture walkthrough

---

## Stacked PR Plan (2-day version)

## PR #1 — Scaffold + contracts + synthetic data
**Goal:** foundational project structure and data contracts.
- Files: `src/domain/*`, `src/api/schemas.py`, `data/scenarios_v1.jsonl`, tests
- Tests: model validation + schema tests
- GCP: none
- Tags: `[Pydantic] [API Contracts] [Data Modeling]`

## PR #2 — Analyzer agent (single-agent baseline)
**Goal:** get first recommendation working.
- Files: `src/agent/analyzer.py`, prompt file, provider adapter
- Tests: parser robustness + golden scenario unit tests
- GCP: none
- Tags: `[Prompt Engineering] [Structured Output] [Tool Calling]`

## PR #3 — Validator agent + multi-agent orchestration
**Goal:** convert baseline into multi-agent flow.
- Files: `src/agent/validator.py`, `src/agent/pipeline.py`, API route updates
- Tests: conflict detection + `requires_human_review` behavior
- GCP: none
- Tags: `[Multi-Agent Systems] [Safety Guardrails] [Decision Policy]`

## PR #4 — Evals + demo endpoint polish
**Goal:** measurable quality + cleaner demo.
- Files: `evals/run_evals.py`, `evals/metrics.py`, `scripts/demo_requests.sh`
- Tests: eval metric tests
- GCP: none
- Tags: `[Evals] [Golden Dataset] [Quality Measurement]`

## PR #5 — Minimal Terraform infra
**Goal:** provision cloud resources reproducibly.
- Files: `infra/terraform/main.tf`, `variables.tf`, `outputs.tf`
- Tests: `terraform fmt -check`, `terraform validate`
- GCP: Cloud Run, Secret Manager, service account/IAM
- Tags: `[Terraform] [GCP IaC] [IAM] [Secrets]`

## PR #6 — Docker + GHCR + GitHub Actions CD to Cloud Run
**Goal:** automated build/push/deploy pipeline.
- Files: `Dockerfile`, `.github/workflows/ci_cd.yml`, deploy script, README
- Tests: unit + integration + docker build + deployed `/health` smoke check
- GCP: Cloud Run deployment via CI
- Tags: `[CI/CD] [GitHub Actions] [GHCR] [Cloud Run Deploy]`

---

## Interview narrative from this MVP
"I built a two-agent recommendation service on GCP Cloud Run. The analyzer proposes an action from campaign context; the validator checks consistency and confidence before finalizing output. I used typed contracts, synthetic golden scenarios for eval, Terraform for reproducible cloud setup, and GitHub Actions CI/CD to run tests, push image to GHCR, and deploy to Cloud Run."

---

## Definition of Done (Showcase)
- [ ] `/analyze` returns valid structured response every call
- [ ] Multi-agent flow is visible in logs/output
- [ ] Offline eval script runs and reports metric summary
- [ ] Terraform provisions minimal infra successfully
- [ ] CI/CD pipeline runs tests + builds/pushes image + deploys Cloud Run
- [ ] Service deployed and callable
- [ ] README includes architecture and trade-offs

If all are done, you are showcase-ready.
