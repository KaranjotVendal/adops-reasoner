# Stacked PR Roadmap — Campaign Analyst on GCP

This roadmap is intentionally **sequential, atomic, and review-friendly**. Each PR is scoped to one purpose and can be merged independently.

---

## Branching Strategy (Mandatory)

- Base branch: `main`
- Create stacked branches:
  - `pr-01-scaffold`
  - `pr-02-domain-models` (from pr-01)
  - `pr-03-analyzer-core` (from pr-02)
  - ... and so on
- Keep each PR under ~300 changed lines where possible
- Each PR includes tests and updates docs/changelog

---

## PR #1: Project scaffolding, tooling, and code quality baseline

**Goal**
Create a clean Python service skeleton with linting, formatting, test runner, and pre-commit.

**Key files/modules changed**
- `pyproject.toml`
- `src/` package skeleton
- `tests/` skeleton
- `.pre-commit-config.yaml`
- `Makefile`
- `README.md` (dev setup)

**Tests required**
- `pytest -q` placeholder smoke test
- Lint/format checks in CI (ruff, black, mypy)

**GCP resources provisioned**
- None

**Interview tags**
`[Engineering Hygiene] [Python Tooling] [CI Foundations] [Maintainability]`

---

## PR #2: Domain contracts and schema-first API models

**Goal**
Define strict Pydantic contracts for requests/responses and action taxonomy.

**Key files/modules changed**
- `src/domain/models.py`
- `src/domain/enums.py`
- `src/api/schemas.py`
- `tests/domain/test_models.py`

**Tests required**
- Validation tests (ranges, required fields, enum constraints)
- Serialization/deserialization tests

**GCP resources provisioned**
- None

**Interview tags**
`[Pydantic Validation] [API Contracts] [Schema Design] [Determinism]`

---

## PR #3: Analyzer core (provider-agnostic) + deterministic parsing

**Goal**
Implement analyzer service with prompt template + structured output parser, using a mock provider for deterministic tests.

**Key files/modules changed**
- `src/agent/analyzer.py`
- `src/agent/prompts/analyzer_prompt.md`
- `src/llm/provider_interface.py`
- `src/llm/mock_provider.py`
- `tests/agent/test_analyzer_core.py`

**Tests required**
- Golden unit tests for known campaign scenarios
- Parser robustness tests (malformed JSON, missing fields)

**GCP resources provisioned**
- None

**Interview tags**
`[Prompt Engineering] [Structured Output] [Tool Calling Basics] [Testability]`

---

## PR #4: Vertex AI provider adapter (Gemini) with retries/timeouts

**Goal**
Replace mock in runtime path with Vertex AI adapter while preserving provider interface.

**Key files/modules changed**
- `src/llm/vertex_provider.py`
- `src/config/settings.py`
- `src/agent/analyzer_service.py`
- `tests/llm/test_vertex_provider_contract.py` (mocked network)

**Tests required**
- Contract tests for provider interface
- Retry/timeout behavior tests

**GCP resources provisioned**
- Vertex AI API enablement (documented, not automated yet)

**Interview tags**
`[Cloud ML APIs] [Async I/O] [Resilience] [Adapter Pattern]`

---

## PR #5: Persistence layer (Cloud SQL-compatible Postgres + migrations)

**Goal**
Add decision logging repository with migration-based schema management.

**Key files/modules changed**
- `src/storage/models.py`
- `src/storage/repository.py`
- `migrations/` (Alembic)
- `tests/storage/test_repository.py`

**Tests required**
- CRUD repository tests against local Postgres test container
- Idempotent write tests using request IDs

**GCP resources provisioned**
- None yet (local Postgres for dev)

**Interview tags**
`[Data Modeling] [Idempotency] [Repository Pattern] [Transactional Integrity]`

---

## PR #6: FastAPI endpoints + idempotency + error contracts

**Goal**
Expose `/analyze`, `/health`, `/decisions/{campaign_id}` with clean HTTP errors and trace IDs.

**Key files/modules changed**
- `src/api/main.py`
- `src/api/routes.py`
- `src/api/error_handlers.py`
- `tests/api/test_endpoints.py`

**Tests required**
- API integration tests (happy path + validation errors)
- Idempotency behavior test (`Idempotency-Key` header)

**GCP resources provisioned**
- None

**Interview tags**
`[FastAPI] [REST Design] [Idempotency] [Error Handling]`

---

## PR #7: Validator stage + human-review gating

**Goal**
Add validator logic that flags low-confidence or conflicting recommendations.

**Key files/modules changed**
- `src/agent/validator.py`
- `src/agent/pipeline.py`
- `src/domain/decision_status.py`
- `tests/agent/test_validator.py`

**Tests required**
- Rule-based validator tests
- End-to-end test for `requires_human_review=true`

**GCP resources provisioned**
- None

**Interview tags**
`[Multi-step Reasoning] [Safety Guards] [Human-in-the-loop] [Risk Controls]`

---

## PR #8: Observability baseline (logs, metrics, traces)

**Goal**
Instrument structured logging and key service metrics.

**Key files/modules changed**
- `src/observability/logging.py`
- `src/observability/metrics.py`
- middleware for trace IDs
- `docs/observability.md`
- `tests/observability/test_trace_propagation.py`

**Tests required**
- Trace ID propagation test
- Metric emission unit tests

**GCP resources provisioned**
- Cloud Logging & Cloud Monitoring (documented configs)

**Interview tags**
`[Observability] [SRE Basics] [Traceability] [Prod Readiness]`

---

## PR #9: Offline evaluation harness + golden dataset

**Goal**
Add repeatable eval suite for recommendation quality and regression protection.

**Key files/modules changed**
- `evals/golden_dataset.jsonl`
- `evals/run_evals.py`
- `evals/metrics.py`
- `tests/evals/test_eval_metrics.py`

**Tests required**
- Eval metric calculation correctness
- CI gate: fail if quality drops below threshold

**GCP resources provisioned**
- Optional BigQuery dataset for storing eval runs (deferred or documented)

**Interview tags**
`[Evals-as-a-Service] [ML Quality] [Regression Testing] [Data-driven Iteration]`

---

## PR #10: Containerization + local reproducibility

**Goal**
Production-like container runtime for local and CI environments.

**Key files/modules changed**
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `.dockerignore`
- `tests/smoke/test_container_health.py`

**Tests required**
- Docker image build smoke test
- `/health` endpoint smoke test in container

**GCP resources provisioned**
- None

**Interview tags**
`[Docker] [Reproducibility] [Environment Parity] [DevEx]`

---

## PR #11: GCP IaC bootstrap (minimal Terraform)

**Goal**
Provision minimal cloud foundation: Artifact Registry, Cloud Run service, Secret Manager, service accounts/IAM.

**Key files/modules changed**
- `infra/terraform/main.tf`
- `infra/terraform/variables.tf`
- `infra/terraform/outputs.tf`
- `infra/terraform/README.md`

**Tests required**
- `terraform fmt -check`
- `terraform validate`

**GCP resources provisioned**
- Artifact Registry
- Cloud Run service (initial)
- Secret Manager secrets
- IAM roles for runtime service account

**Interview tags**
`[GCP IaC] [Cloud IAM] [Secret Management] [Least Privilege]`

---

## PR #12: CI/CD pipeline (GitHub Actions + Cloud Build deploy staging)

**Goal**
Automate test/build/deploy to staging Cloud Run.

**Key files/modules changed**
- `.github/workflows/ci.yml`
- `cloudbuild.yaml`
- deployment scripts under `scripts/`
- `docs/release_process.md`

**Tests required**
- CI must run lint + tests + eval subset
- Staging deploy smoke test script

**GCP resources provisioned**
- Cloud Build trigger
- Workload identity / deploy credentials

**Interview tags**
`[CI/CD] [Cloud Build] [Release Engineering] [Staging Gates]`

---

## PR #13: BigQuery ingestion path + scheduled batch mode

**Goal**
Add optional batch analysis from BigQuery snapshots, triggered by Cloud Scheduler.

**Key files/modules changed**
- `src/jobs/batch_runner.py`
- `src/data/bigquery_reader.py`
- `src/api/routes_batch.py`
- `tests/jobs/test_batch_runner.py`

**Tests required**
- Batch runner unit tests
- BigQuery reader contract tests (mock client)

**GCP resources provisioned**
- BigQuery dataset/table (if not already existing)
- Cloud Scheduler job calling batch endpoint

**Interview tags**
`[BigQuery] [Batch Processing] [Scheduler] [Scalability Path]`

---

## PR #14: Production hardening + runbooks + prod deploy

**Goal**
Finalize production readiness: SLOs, alert policies, rollback guide, security checklist.

**Key files/modules changed**
- `docs/runbook.md`
- `docs/slo_sla.md`
- `docs/security_checklist.md`
- `docs/incident_response.md`
- minor runtime config for prod

**Tests required**
- End-to-end smoke test against staging before prod promotion
- Alert policy dry-run checks

**GCP resources provisioned**
- Monitoring alert policies
- Production Cloud Run revision
- Optional Error Reporting sink

**Interview tags**
`[Production Readiness] [SLO/SLI] [Incident Response] [Operational Excellence]`

---

## Definition of Done per PR (non-negotiable)

A PR is mergeable only if:
1. Single clear purpose
2. Tests included and passing
3. CI green
4. Docs updated (what/why/how)
5. No secrets committed
6. Reviewer can explain diff in under 3 minutes

---

## Suggested Cadence

- PRs 1–6: core service MVP (week 1)
- PRs 7–10: quality + reliability (week 2)
- PRs 11–14: cloud productionization (week 3)

This cadence gives a realistic interview-ready demo by end of week 2 and production deployment by week 3.
