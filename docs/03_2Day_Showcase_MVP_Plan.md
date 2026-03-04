# 2-Day Showcase MVP Plan (Latest)

## Objective
Build a demo-ready **multi-agent Campaign Analyst** you can explain confidently in interviews.

## Locked scope
- FastAPI service (`/health`, `/analyze`)
- Analyzer agent + Validator agent
- Synthetic campaign dataset + offline evals
- Dockerized service
- GCP deploy on Cloud Run
- Terraform (minimal infra)
- GitHub Actions CI/CD:
  - lint + unit/integration tests
  - docker build
  - push image to GHCR
  - deploy Cloud Run (CD)

## Out of scope
- Cloud SQL/BigQuery pipelines
- Pub/Sub/Scheduler
- advanced observability platforms (Langfuse/LangSmith)
- multi-env promotion workflow

## Architecture
```text
Client -> FastAPI (/analyze) -> Analyzer -> Validator -> Final Decision
                                                  |
                                             requires_human_review

CI/CD: GitHub Actions -> GHCR -> Cloud Run
IaC : Terraform (Cloud Run + Secret Manager + IAM SA)
```

## LLM provider strategy
- Primary: **MiniMax**
- Secondary (candidate): **Kimi** after canary tests during implementation

## Success criteria
- Consistent structured output
- Multi-agent flow visible in response/logs
- Offline eval metric generated
- Cloud Run endpoint live
- CI/CD pipeline green
