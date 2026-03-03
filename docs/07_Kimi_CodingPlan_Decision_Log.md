# Kimi Coding Plan — Decision Log, Assumptions, and Test Plan

## Status (Current Decision)
- **Primary provider for implementation:** MiniMax
- **Kimi status:** Candidate provider, pending compatibility test with your current coding-plan key
- **When to test:** During implementation (PR #2 / provider adapter stage)

Reason: we have clear implementation certainty with MiniMax right now and a 2-day deadline.

---

## Why this doc exists
Kimi has multiple docs/surfaces (Kimi Code docs and Moonshot Open Platform docs). This can cause confusion about:
- which endpoint to call,
- which API key works where,
- whether tool calling and JSON mode are available for your exact plan.

This document centralizes all assumptions so implementation stays clean.

---

## Known endpoints from docs

## Kimi Code docs (coding-plan integrations)
- Anthropic-style base URL shown: `https://api.kimi.com/coding/`
- OpenAI-compatible style shown in third-party tools: `https://api.kimi.com/coding/v1`
- Model examples include: `kimi-for-coding`

## Moonshot Open Platform docs (full API docs)
- OpenAI-compatible base URL: `https://api.moonshot.ai/v1`
- Endpoint: `POST /v1/chat/completions`
- Features documented:
  - `tools` / tool calling
  - `response_format={"type":"json_object"}`
  - model family: `kimi-k2.5`, `kimi-k2-thinking`, etc.

---

## Key uncertainty to resolve
**Does your existing Kimi coding-plan key authenticate and authorize calls to `https://api.moonshot.ai/v1` for the features we need (chat + JSON mode + tool use)?**

Until this is verified, Kimi remains secondary.

---

## MVP-required capabilities (for any provider)
1. Basic chat completion
2. Stable structured JSON output (`response_format=json_object` or equivalent)
3. Optional tool calling support
4. Reliable latency / rate-limit behavior for demo load

---

## Canary Test Plan (run during implementation)

## Test A — Auth + basic completion
- Call chat completion once
- Pass criteria: HTTP 200 and valid assistant message

## Test B — JSON mode stability
- 20 repeated calls with strict schema prompt
- Pass criteria: >=95% valid JSON parse success

## Test C — Tool-calling sanity
- Single function/tool schema
- Pass criteria: at least one valid tool-call response shape

## Test D — latency quick check
- 20 calls; measure p50/p95
- Pass criteria: usable for demo (<~5s p95 acceptable for showcase)

## Decision rule after canary
- If all tests pass on Kimi: can promote Kimi to primary
- If any critical test fails: keep MiniMax primary, Kimi fallback only

---

## Implementation policy (current)
- Keep provider abstraction (`ProviderInterface`)
- Implement `MiniMaxProvider` first
- Add `KimiProvider` behind feature flag/env switch
- Add fallback routing only after Kimi canary passes

Environment example:
- `LLM_PROVIDER=minimax` (default)
- `LLM_FALLBACK_PROVIDER=kimi` (optional)

---

## Interview-ready explanation
"I separated provider choice from business logic using a provider interface. We selected MiniMax as primary for implementation certainty under a 2-day deadline. Kimi remained a candidate and we defined explicit compatibility canary tests (auth, JSON mode stability, tool-call shape, latency) before promoting it to primary. This keeps delivery risk low while preserving vendor flexibility."

---

## Final note
This is a delivery-first decision, not a model-quality judgment. We can switch primary provider in minutes once compatibility is proven.
