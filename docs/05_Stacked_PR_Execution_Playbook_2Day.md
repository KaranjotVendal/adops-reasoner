# Stacked PR Execution Playbook (2-Day Showcase)

This is the **exact step-by-step PR plan** to execute the 2-day MVP with:
- multi-agent pipeline,
- synthetic evals,
- Terraform infra,
- GitHub Actions CI/CD (GHCR + Cloud Run deploy).

Use this as your runbook.

---

## 0) One-time setup (30 mins)

## 0.1 Create baseline commit on `main`
```bash
cd /home/childofprophecy/Desktop/Personal_projects/Machine_Learning/campaign_analyst

git checkout -b main
git add .
git commit -m "chore: initialize project planning docs"
```

## 0.2 Optional remote setup
```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

---

## 1) Stacking model you will follow

Each PR branch is created from previous PR branch:

```text
main
 └─ pr/01-scaffold-contracts-data
     └─ pr/02-analyzer-core
         └─ pr/03-validator-orchestration
             └─ pr/04-evals-demo
                 └─ pr/05-terraform-minimal
                     └─ pr/06-cicd-ghcr-cloudrun
```

When PR #1 merges, rebase PR #2 on `main`; repeat.

---

## 2) PR #1 — Scaffold + contracts + synthetic dataset

## Title
`PR #1: Scaffold service, typed contracts, synthetic scenario dataset`

## Goal
Set foundations: clean project structure, Pydantic contracts, and initial synthetic campaign data.

## Branch
```bash
git checkout -b pr/01-scaffold-contracts-data main
```

## Changes
- Create folders:
  - `src/api/`
  - `src/agent/`
  - `src/domain/`
  - `src/llm/`
  - `tests/`
  - `data/`
  - `scripts/`
- Add domain models and enums:
  - `src/domain/models.py`
  - `src/domain/enums.py`
- Add simple FastAPI app shell:
  - `src/api/main.py` with `/health`
- Add synthetic dataset and generator:
  - `data/scenarios_v1.jsonl`
  - `scripts/generate_scenarios.py`
- Add dev tooling:
  - `pyproject.toml` deps + test/lint config

## Tests required
- `tests/test_models.py`
- `tests/test_scenario_generation.py`

## Definition of done
- `pytest` passes
- `/health` endpoint runs locally
- At least 50 scenarios generated with `expected_action`

## Commit + push
```bash
git add .
git commit -m "feat: scaffold API contracts and synthetic scenario dataset"
git push -u origin pr/01-scaffold-contracts-data
```

## Interview tags
`[Pydantic] [Contract-First Design] [Synthetic Data Engineering]`

---

## 3) PR #2 — Analyzer core (single-agent baseline)

## Title
`PR #2: Implement analyzer agent with structured output`

## Goal
Build analyzer agent that produces deterministic JSON recommendation from campaign input.

## Branch
```bash
git checkout -b pr/02-analyzer-core pr/01-scaffold-contracts-data
```

## Changes
- Add prompt file:
  - `src/agent/prompts.py`
- Add provider abstraction + initial provider:
  - `src/llm/provider_interface.py`
  - `src/llm/openrouter_provider.py` (or vertex stub)
- Add analyzer:
  - `src/agent/analyzer.py`
- Add `/analyze` endpoint wired to analyzer

## Tests required
- `tests/test_analyzer.py` (mock model response)
- `tests/test_analyze_endpoint.py` (API contract)
- invalid JSON parse handling test

## Definition of done
- `/analyze` returns valid schema response
- Structured output parsing failure is handled cleanly
- Unit tests pass without real API dependency

## Commit + push
```bash
git add .
git commit -m "feat: add analyzer agent with structured recommendation output"
git push -u origin pr/02-analyzer-core
```

## Interview tags
`[Prompt Engineering] [Structured Output] [LLM Abstraction] [Async API Calls]`

---

## 4) PR #3 — Validator + multi-agent orchestration

## Title
`PR #3: Add validator agent and multi-agent decision policy`

## Goal
Convert single-agent flow into a robust two-agent pipeline.

## Branch
```bash
git checkout -b pr/03-validator-orchestration pr/02-analyzer-core
```

## Changes
- Add validator:
  - `src/agent/validator.py`
- Add pipeline orchestrator:
  - `src/agent/pipeline.py`
- Update `/analyze` to run Analyzer -> Validator -> Final policy
- Add `requires_human_review`
- Add `trace_id` in response/logs

## Tests required
- `tests/test_validator.py`
- `tests/test_pipeline.py`
- contradiction case test (validator rejects analyzer)
- low-confidence gating test

## Definition of done
- Multi-agent flow visible in logs/response
- `requires_human_review=true` triggers correctly
- Pipeline tests pass

## Commit + push
```bash
git add .
git commit -m "feat: implement validator and multi-agent orchestration pipeline"
git push -u origin pr/03-validator-orchestration
```

## Interview tags
`[Multi-Agent Systems] [Safety Guardrails] [Decision Policy] [Reliability]`

---

## 5) PR #4 — Offline eval harness + demo scripts

## Title
`PR #4: Add offline eval harness and demo scenarios`

## Goal
Make the project measurable and demo-ready.

## Branch
```bash
git checkout -b pr/04-evals-demo pr/03-validator-orchestration
```

## Changes
- Add eval runner:
  - `evals/run_evals.py`
  - `evals/metrics.py`
- Add baseline output:
  - `evals/results_baseline.json`
- Add demo scripts:
  - `scripts/demo_requests.sh`
  - `scripts/demo_payloads/*.json`
- Optional `/analyze/batch`

## Tests required
- `tests/test_eval_metrics.py`
- deterministic eval regression test on fixed sample

## Definition of done
- Eval script prints accuracy summary
- Baseline result saved as artifact
- Demo script reproduces 3 representative scenarios

## Commit + push
```bash
git add .
git commit -m "feat: add eval harness and reproducible demo scripts"
git push -u origin pr/04-evals-demo
```

## Interview tags
`[Evals-as-a-Service] [Golden Dataset] [ML Quality Metrics] [Demo Engineering]`

---

## 6) PR #5 — Minimal Terraform infra

## Title
`PR #5: Provision Cloud Run + Secret Manager + IAM via Terraform`

## Goal
Provision minimal infra reproducibly (no over-engineering).

## Branch
```bash
git checkout -b pr/05-terraform-minimal pr/04-evals-demo
```

## Changes
- Add Terraform files:
  - `infra/terraform/main.tf`
  - `infra/terraform/variables.tf`
  - `infra/terraform/outputs.tf`
  - `infra/terraform/README.md`
- Provision only:
  - service account
  - IAM bindings
  - Secret Manager secret
  - Cloud Run service skeleton

## Tests required
- `terraform fmt -check`
- `terraform validate`

## Definition of done
- `terraform apply` succeeds in target project
- Outputs include Cloud Run service name and service account
- No manual IAM steps required beyond initial auth

## Commit + push
```bash
git add .
git commit -m "feat: add minimal terraform for cloud run, secrets, and iam"
git push -u origin pr/05-terraform-minimal
```

## Interview tags
`[Terraform] [GCP IaC] [IAM] [Secret Management] [Reproducibility]`

---

## 7) PR #6 — CI/CD with GHCR + Cloud Run deploy

## Title
`PR #6: Add GitHub Actions CI/CD (tests, GHCR push, Cloud Run deploy)`

## Goal
Automate quality gates + deployment.

## Branch
```bash
git checkout -b pr/06-cicd-ghcr-cloudrun pr/05-terraform-minimal
```

## Changes
- Add workflow:
  - `.github/workflows/ci_cd.yml`
- Steps in workflow:
  1. lint + unit tests + integration tests
  2. docker build
  3. push image to GHCR
  4. deploy to Cloud Run
- Add deploy helper script/docs:
  - `scripts/deploy_cloud_run.sh`
  - `docs/deployment_gcp_quickstart.md`
- README update with pipeline and required secrets

## Tests required
- CI workflow green on PR
- smoke test against deployed `/health`

## GCP/GitHub setup notes
- GitHub repo secrets for GCP auth
- GHCR package should be public for simplest Cloud Run pull path (or configure authenticated pull)

## Definition of done
- Merging to main triggers automated pipeline
- New image appears in GHCR
- Cloud Run revision updates automatically
- Smoke test passes

## Commit + push
```bash
git add .
git commit -m "feat: add github actions ci/cd with ghcr push and cloud run deploy"
git push -u origin pr/06-cicd-ghcr-cloudrun
```

## Interview tags
`[CI/CD] [GitHub Actions] [GHCR] [Cloud Run Deploy] [DevOps]`

---

## 8) Daily execution plan

## Day 1
- PR #1 (morning)
- PR #2 (afternoon)
- PR #3 (evening)

## Day 2
- PR #4 (early morning)
- PR #5 (midday)
- PR #6 (afternoon)
- Demo rehearsal + README polish (evening)

---

## 9) PR description template (copy/paste)

```md
## Goal
(One sentence)

## Why
(Why this change matters)

## Scope
- 
- 

## Tests
- [ ] unit tests added/updated
- [ ] integration/smoke checks run

## Demo
(curl command or screenshot)

## Interview tags
[Tag1] [Tag2] [Tag3]
```

---

## 10) Merge & rebase workflow for stacked PRs

When PR #1 merges:
```bash
git checkout pr/02-analyzer-core
git fetch origin
git rebase origin/main
git push --force-with-lease
```

Repeat for downstream branches.

---

## 11) Final showcase checklist

- [ ] Multi-agent flow works end-to-end
- [ ] Offline eval metric is generated
- [ ] Terraform provisions minimal infra
- [ ] CI runs tests + integration + image build
- [ ] GHCR image push works
- [ ] Cloud Run auto-deploy works
- [ ] 5-minute architecture walkthrough rehearsed

If these are true, you are interview-showcase ready.
