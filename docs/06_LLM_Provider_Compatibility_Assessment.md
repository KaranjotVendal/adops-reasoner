# LLM Provider Compatibility Assessment (MiniMax + Kimi)

## Scope
Assess whether your **MiniMax Coding Plan** and **Kimi Coding Plan** are compatible with the 2-day Campaign Analyst MVP.

MVP requirements from agent side:
1. Chat completion API access from server-side Python
2. Stable structured output (JSON parseable)
3. Optional tool-calling / reasoning support
4. Acceptable latency/quota for demo

---

## Executive Verdict

## MiniMax Coding Plan: **Compatible (Strong Yes)**
- Clear server API docs for **OpenAI-compatible** and **Anthropic-compatible** endpoints
- Explicit support for tools and interleaved thinking
- Clear model names and SDK examples
- Best candidate for **primary provider** in this MVP

## Kimi Coding Plan: **Likely Compatible (Conditional Yes)**
- Docs show third-party integration with:
  - Anthropic-style base URL (`https://api.kimi.com/coding/`)
  - OpenAI-compatible entrypoint (`https://api.kimi.com/coding/v1`)
- But public docs are more integration-oriented than full API reference
- Use as **secondary/fallback** unless canary tests pass fully

---

## Evidence from docs

## MiniMax (strong API evidence)
From MiniMax docs:
- OpenAI-compatible base URL: `https://api.minimax.io/v1`
- Anthropic-compatible base URL: `https://api.minimax.io/anthropic`
- Supported models include `MiniMax-M2.5`, `MiniMax-M2.5-highspeed`, etc.
- Explicit note: supports tool usage; function_call deprecated, use `tools`
- Notes include interleaved thinking and preserving assistant/tool turns

Operational caveats:
- Coding plan key is separate from pay-as-you-go key
- usage limits in rolling window
- some OpenAI params ignored
- `temperature` expected in (0, 1]

## Kimi (good integration evidence, less API detail)
From Kimi docs:
- Claude Code integration via Anthropic env vars:
  - `ANTHROPIC_BASE_URL=https://api.kimi.com/coding/`
- Roo Code integration via OpenAI-compatible endpoint:
  - `https://api.kimi.com/coding/v1`
  - model: `kimi-for-coding`
  - uses legacy OpenAI API format
- Throughput claim and concurrency details provided

Gap:
- We did not find a full public API reference page confirming JSON schema mode/tool-call protocol details like OpenAI function calling semantics.

---

## Recommendation for this MVP

## Primary provider: MiniMax
Reason:
- lowest implementation risk in 2 days
- clear docs for server-side SDK use
- explicit tool/interleaved support

## Secondary provider: Kimi fallback
Reason:
- likely works, but uncertain protocol details for strict structured outputs
- useful as interview talking point for provider abstraction + failover

---

## Provider strategy for your code

Implement provider abstraction now:
- `ProviderInterface.complete(messages, ...) -> ProviderResponse`
- `MiniMaxProvider` (primary)
- `KimiProvider` (optional fallback)

Routing policy:
1. try primary provider once
2. retry with backoff once
3. fallback to secondary provider
4. if still fail, return `requires_human_review=true`

This gives reliability + strong system design narrative.

---

## 30-minute compatibility canary tests (do this before coding full pipeline)

## Test A — MiniMax OpenAI-compatible basic call
- Verify auth + model call works
- Check latency and response stability

## Test B — MiniMax structured JSON prompt
- Ask model to return strict JSON object
- Validate parse success across 20 runs
- Target: >95% parse success

## Test C — MiniMax tool-call sanity (optional)
- Provide one tool schema
- Verify tool call appears in response

## Test D — Kimi OpenAI-compatible basic call
- endpoint `https://api.kimi.com/coding/v1`
- model `kimi-for-coding`
- verify basic completion works

## Test E — Kimi structured JSON prompt
- same parse success test
- if parse reliability < MiniMax, keep Kimi as fallback only

---

## Decision Matrix (for this project)

| Capability | MiniMax | Kimi | MVP Decision |
|---|---|---|---|
| Server API docs clarity | High | Medium | MiniMax primary |
| OpenAI compatibility | Yes (documented) | Yes (integration docs) | both possible |
| Anthropic compatibility | Yes (documented) | Yes (Claude integration path) | both possible |
| Tool/interleaved docs | Explicit | Not explicit in fetched docs | MiniMax preferred |
| 2-day implementation risk | Low | Medium | MiniMax primary |

---

## Interview-ready explanation

"I evaluated two coding subscriptions as API backends. MiniMax had stronger public API compatibility docs for OpenAI/Anthropic formats and explicit tool/interleaved behavior, so I used it as primary for implementation reliability. I kept Kimi behind the same provider interface as fallback, which demonstrates vendor-agnostic architecture and resilience under quota or latency spikes."

---

## Final call
Proceed with:
- **MiniMax first** for analyzer + validator path
- **Kimi optional fallback** once canary tests pass

This gives you the best chance of shipping a solid demo in 2 days.
