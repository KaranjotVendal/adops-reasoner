# Campaign Analyst Agent — Mission & Success Criteria

## 1) Mission Statement
Build a **production-deployable Campaign Analyst Agent on GCP** that analyzes campaign context (CPA trend, CTR behavior, audience saturation, competitor activity) and recommends the most appropriate marketing workflow (e.g., creative refresh vs bid adjustment), with clear reasoning and confidence.

This system’s purpose is to reduce manual triage burden for marketing managers while preserving human control through reviewable, auditable recommendations.

---

## 2) Problem Definition
Current automation workflows execute actions but do not reason across context. When CPA rises, teams still manually inspect signals and choose the right intervention.

The agent solves this by:
1. Ingesting structured campaign snapshots
2. Producing a single recommended action + rationale
3. Logging decision traces for approval/rejection feedback
4. Enabling iterative quality improvement via evals

---

## 3) End Users
- **Primary:** Marketing Operations Managers / Channel Managers (internal users)
- **Secondary:** Data/AI Engineering team (maintains reliability, evals, and deployment)

---

## 4) Success Criteria (MVP → Production)

## Functional
- Agent returns exactly one action from controlled taxonomy:
  - `creative_refresh`
  - `bid_adjustment`
  - `audience_expansion`
  - `pause_campaign`
  - `maintain`
- Output always includes: `action`, `confidence`, `reasoning`, `key_signals`, `trace_id`

## Quality / ML-Eval
- Golden dataset action accuracy (offline): **>= 75%** initial target
- Human approval rate (online): **>= 70%** in first month pilot
- Confidence calibration gap: high-confidence bucket should outperform low-confidence bucket

## Reliability / Ops
- API P95 latency (single campaign analysis): **< 3s**
- Service availability target: **99.5%** (Cloud Run + managed services)
- Structured output validity: **> 99%** responses parse successfully

## Cost
- Mean inference cost per recommendation: **<= $0.03**
- Token and latency telemetry available per request

## Usability / Trust
- Recommendation includes concise plain-language rationale
- Every decision is traceable and queryable for audit/review

---

## 5) Non-Goals (for MVP)
- Fully autonomous workflow execution without human review
- Complex long-term memory or autonomous web browsing
- Multi-channel campaign optimization across all ad platforms

---

## 6) Engineering Principles
1. **Pragmatism over hype**: lightweight Python orchestration, no unnecessary frameworks
2. **Deterministic contracts**: strict schemas, explicit validation, idempotent APIs
3. **Observability-first**: trace every request, model call, and decision outcome
4. **Safe rollout**: offline eval gate before deployment and human-in-the-loop online
5. **Small PRs**: stacked, atomic, test-first development
