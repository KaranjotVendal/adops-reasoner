# System Design Document (SDD) — Campaign Analyst Agent on GCP

## 1) Scope
This SDD defines the MVP production architecture for a marketing recommendation agent deployed on **Google Cloud Platform**.

Design goal: **simple first**, production-safe, observable, and easy to explain in interviews.

---

## 2) High-Level Architecture Summary

- **Serving layer:** FastAPI on Cloud Run
- **Model access:** Vertex AI (Gemini) via provider adapter
- **Data in:** Campaign snapshots from BigQuery (or API payload)
- **Data out:** Recommendations + traces stored in Cloud SQL (Postgres) and BigQuery analytics table
- **Security:** IAM, Secret Manager, VPC connector (if needed), least-privilege service accounts
- **Ops:** Cloud Build CI/CD, Cloud Logging, Cloud Monitoring, Error Reporting

### ASCII Architecture

```text
                        ┌──────────────────────────┐
                        │   Marketing User / UI    │
                        └──────────────┬───────────┘
                                       │ HTTPS
                                       ▼
                           ┌────────────────────────┐
                           │ Cloud Run (FastAPI)    │
                           │ campaign-analyst-api   │
                           └───────┬──────┬────────┘
                                   │      │
                    Read snapshots │      │ Write decisions
                                   │      │
                                   ▼      ▼
                           ┌──────────┐  ┌──────────────┐
                           │ BigQuery │  │ Cloud SQL     │
                           │ campaign │  │ Postgres      │
                           │ features │  │ decisions/log │
                           └────┬─────┘  └──────┬───────┘
                                │               │
                                │               │
                                ▼               ▼
                       ┌────────────────────────────────┐
                       │ Cloud Logging + Monitoring     │
                       │ traces, latency, cost, errors │
                       └────────────────────────────────┘

                                   │
                                   ▼
                         ┌─────────────────────┐
                         │ Vertex AI (Gemini)  │
                         │ structured output    │
                         └─────────────────────┘

Secrets: Secret Manager (API keys/config)
CI/CD : GitHub -> Cloud Build -> Artifact Registry -> Cloud Run
```

---

## 3) Why These Technology Choices

## FastAPI + Cloud Run
- **Why FastAPI:** typed contracts (Pydantic), async, clear APIs
- **Why Cloud Run:** easiest production container deployment on GCP, autoscaling, no cluster ops
- **Why not GKE (now):** operational overhead, overkill for MVP

## Vertex AI over custom model host
- Managed auth, observability integration, simpler governance
- Supports structured JSON output workflows
- Avoids standing up model infrastructure

## Cloud SQL + BigQuery split
- **Cloud SQL (Postgres):** transactional records (decision lifecycle, approvals)
- **BigQuery:** analytics/evaluation queries at scale
- **Why not only one DB:** single DB can work initially, but this split preserves clean OLTP vs analytics boundaries

## Direct API calls first, Pub/Sub later
- **MVP:** direct synchronous API calls (fewer moving parts)
- **When Pub/Sub is added:** scheduled/batch volume, retries, decoupled producers/consumers
- This preserves simplicity while leaving a clear scale path

---

## 4) Core Components

1. **API Service (`campaign-analyst-api`)**
   - Endpoints: `/health`, `/analyze`, `/batch/analyze`, `/decisions/{campaign_id}`
   - Validates request schema and idempotency key
   - Calls analyzer + validator pipeline

2. **Analyzer Engine**
   - Prompt + structured output schema
   - Returns recommended action, confidence, key signals, rationale

3. **Validator Layer**
   - Rule checks + optional second model pass
   - Flags low-confidence or conflicting outputs for human review

4. **Storage Layer**
   - Cloud SQL table: decisions, request metadata, model info, user feedback
   - BigQuery table: flattened event stream for eval dashboards

5. **Evaluation Runner**
   - Offline golden dataset tests in CI
   - Regression checks on prompt/model changes

---

## 5) Data Contracts (MVP)

## Request
```json
{
  "request_id": "optional-client-id",
  "campaign": {
    "campaign_id": "abc123",
    "cpa_3d_trend": 30.0,
    "cpa_7d_trend": 40.0,
    "ctr_current": 0.8,
    "ctr_7d_avg": 2.1,
    "audience_saturation": 90.0,
    "days_since_creative_refresh": 25,
    "competitor_activity_score": 7.0,
    "current_spend_3d": 8000.0
  },
  "context": "optional context"
}
```

## Response
```json
{
  "trace_id": "uuid",
  "analysis": {
    "recommended_action": "creative_refresh",
    "confidence": 0.87,
    "reasoning": "CTR dropped while creative stale",
    "key_signals": ["ctr_drop", "creative_age", "cpa_rise"],
    "requires_human_review": false
  }
}
```

---

## 6) Security Strategy

1. **Identity & access**
   - Dedicated Cloud Run service account
   - Least privilege IAM (BigQuery read, Cloud SQL write, Secret Manager access)

2. **Secrets**
   - No secrets in repo or env files in production
   - All model/API credentials in Secret Manager

3. **Network**
   - Public ingress for MVP with auth token
   - Optional internal ingress + IAP for internal-only mode
   - VPC connector if private DB access is required

4. **Data protection**
   - Avoid storing sensitive user identifiers in prompts/logs
   - Redact logs for PII fields

---

## 7) Observability Strategy

1. **Structured logs** (JSON)
   - trace_id, campaign_id, model_name, latency_ms, token_counts, cost_estimate, action

2. **Metrics**
   - p50/p95 latency
   - error rate by endpoint
   - structured-output parse failure rate
   - action distribution and confidence distribution

3. **Dashboards + alerts**
   - Alert if error rate > threshold
   - Alert if parse failures spike
   - Alert if cost/request drifts above budget

4. **Tracing**
   - request -> model call -> validation -> DB write span chain

---

## 8) Error Handling & Reliability

- Retries with backoff for transient model errors
- Timeouts on external calls
- Fallback response for low confidence / schema failure:
  - return `requires_human_review=true`
- Idempotency key to prevent duplicate writes
- Dead-letter pattern deferred until Pub/Sub phase

---

## 9) Deployment Strategy on GCP

## Environments
- `dev` (cheap, permissive)
- `staging` (production-like)
- `prod` (guarded rollout)

## CI/CD
1. GitHub PR checks (lint, unit, integration, eval subset)
2. Cloud Build on main merge
3. Build container -> Artifact Registry
4. Deploy to Cloud Run (staging)
5. Smoke tests
6. Manual approval gate -> prod deploy

---

## 10) MVP vs Phase-2 Boundary

## MVP includes
- Single service FastAPI
- Direct sync analyze endpoint
- Cloud Run deployment
- Cloud SQL logging + BigQuery analytics export
- CI + offline eval baseline

## Phase-2 includes
- Pub/Sub async pipeline
- Scheduled batch analysis
- richer validator / multi-agent orchestration
- online approval UI integration

---

## 11) Open Decisions (Document Before Build)

1. Gemini model tier (cost vs quality)
2. Approval workflow surface (simple API vs lightweight UI)
3. Whether Cloud SQL alone is sufficient for first 2 weeks
4. Whether to add Langfuse/LangSmith now or after MVP telemetry baseline

---

## 12) Why This Design is Interview-Strong

- Demonstrates pragmatic cloud choices (Cloud Run, Secret Manager, Logging)
- Shows you understand evals, observability, and reliability
- Avoids over-engineering while preserving scale path
- Maps directly to AI engineering expectations in the JD
