# Kimi Coding Plan Decision Log (Latest)

## Current decision
- Keep **MiniMax** as primary API (implementation certainty).
- Test **Kimi** during implementation.
- If canary passes, Kimi can become primary later.

## Why
- 2-day deadline favors lowest integration risk.
- MiniMax docs are explicit for OpenAI/Anthropic-compatible API, JSON mode, tool use.
- Kimi appears compatible but key compatibility with your exact coding plan must be validated.

## Kimi canary checks
1. Auth/basic chat call
2. JSON mode parse success across 20 runs
3. tool_call sanity response
4. latency p95 check

If all pass -> promote Kimi.
If any fail -> keep MiniMax primary and Kimi fallback.
