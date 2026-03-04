# PR2: Analyzer Core - Multi-Agent Architecture Foundation

**Branch:** `pr/02-analyzer-core`  
**Base:** `pr/01-scaffold-contracts-data`  
**Status:** ✅ Ready for Review

---

## Summary

This PR delivers the foundational multi-agent architecture for the Campaign Analyst system. It implements a unified Anthropic-style provider interface supporting both Kimi and MiniMax LLMs, a complete ContentBlock-based messaging system, session persistence, tool calling, and the core analyzer-validator-orchestrator flow.

**Scope Note:** This PR encompasses the originally planned PR2, PR3, and PR4 due to tight architectural coupling between the provider interface, session management, and multi-agent orchestration.

---

## What Changed

### 🆕 New Modules

#### 1. Unified Schema System (`src/schema/`)
```python
# Content blocks for all LLM interactions
ContentBlock = TextContent | ThinkingContent | ToolUseContent | 
               ToolResultContent | ImageContent | RedactedThinkingContent

# Standardized LLM response
LLMResponse(
    content: list[ContentBlock],
    usage: TokenUsage,
    cost: CostBreakdown,
    latency_ms: float,
    model: str,
    provider: str
)
```

**Files:**
- `src/schema/__init__.py` - Public exports
- `src/schema/content.py` - ContentBlock types
- `src/schema/llm.py` - LLMResponse, TokenUsage, CostBreakdown
- `src/schema/message.py` - Message with role constructors
- `src/schema/tool.py` - Tool, ToolInput, ToolResult

#### 2. Anthropic-Style Providers (`src/providers/`)

Unified interface for both Kimi and MiniMax using Anthropic Messages API format.

```python
# Factory function for model routing
provider = get_provider("k2p5")  # or "MiniMax-M2.5"

# Usage
response = provider.generate(
    messages=[Message.system("..."), Message.user("...")],
    tools=tool_schemas,
    max_tokens=4096,
    temperature=0.3,
    thinking=True  # Enable reasoning capture
)
```

**Files:**
- `src/providers/__init__.py` - Provider factory, model registry
- `src/providers/base.py` - `AnthropicStyleProvider` ABC (400 lines)
- `src/providers/kimi.py` - `KimiProvider` (api.kimi.com/coding)
- `src/providers/minimax_anthropic.py` - `MiniMaxAnthropicProvider`

**Supported Models:**
| Model | Provider | Cost (input/output per 1M) |
|-------|----------|---------------------------|
| k2p5 | Kimi | Free (beta) |
| MiniMax-M2.5 | MiniMax | $0.30 / $1.20 |
| MiniMax-M2.5-highspeed | MiniMax | $0.60 / $2.40 |

#### 3. Session Management (`src/session/`)

File-based session persistence with unlimited lifetime.

```python
manager = SessionManager(storage_path="./data/sessions")
session = manager.create(system_prompt="You are a campaign analyst...")
manager.add_message(session.id, Message.user("Analyze campaign X"))
history = manager.get_history(session.id)  # Full conversation
```

**Features:**
- JSON file storage (`{session_id}.json`)
- Automatic context compaction when budget exceeded
- Token estimation for budget management
- Full traceability for debugging

**Files:**
- `src/session/__init__.py`
- `src/session/models.py` - Session, SessionSummary
- `src/session/manager.py` - SessionManager

#### 4. Tool System (`src/tools/`)

Extensible tool framework with ContentBlock results.

```python
# Built-in tools
registry = ToolRegistry()
registry.register_all([ReadFileTool(), WriteFileTool()])

# Execute
result = registry.execute("read_file", path="./data/campaigns.json")
# Returns: ToolResult with content blocks (text, images, or errors)
```

**Files:**
- `src/tools/__init__.py`
- `src/tools/base.py` - Tool ABC
- `src/tools/registry.py` - ToolRegistry
- `src/tools/read_file.py` - ReadFileTool
- `src/tools/write_file.py` - WriteFileTool

#### 5. Multi-Agent System (`src/agents/`)

**AnalyzerAgent** - Generates campaign recommendations
- Anthropic-style provider interface
- ContentBlock parsing (text, thinking, tool_use)
- Metadata attachment (model, latency, cost, thinking)
- JSON response extraction with fallback regex

**ValidatorAgent** - Validates analyzer output
- LLM-based validation (not rule-based)
- Tool access for additional information
- Multi-step validation with tool loop
- Structured validation result

**Orchestrator** - Coordinates multi-step flow
```
User Request → Analyzer → Validator → Tools (if needed) → Final Response
                    ↓           ↓
              Session     Session
```

**Files:**
- `src/agents/__init__.py`
- `src/agents/analyzer.py` - Rewritten for ContentBlocks
- `src/agents/validator.py` - NEW
- `src/agents/orchestrator.py` - NEW

### 🔄 Modified Files

- `src/agents/__init__.py` - Updated exports
- `src/agents/analyzer.py` - Complete rewrite (~350 lines)
- `tests/unit/test_analyzer.py` - Updated for new architecture (~150 lines)

---

## Test Coverage

```
65 tests passing
├── test_models.py (14) - Domain model validation
├── test_analyzer.py (9) - Anthropic-style analyzer
├── test_session.py (9) - Session persistence
└── test_tools.py (28) - Tool system

Coverage: schema, providers (mocked), session, tools, analyzer
```

---

## Environment Configuration

```bash
# Required API keys
export KIMI_API_KEY="sk-..."
export MINIMAX_API_KEY="sk-..."

# Model selection (optional)
export ANALYZER_MODEL="k2p5"              # or "MiniMax-M2.5"
export VALIDATOR_MODEL="MiniMax-M2.5"     # or "k2p5"

# Session storage (optional)
export SESSION_STORAGE_PATH="./data/sessions"
export SESSION_CONTEXT_BUDGET="16000"
```

---

## API Usage Example

```python
from src.agents import Orchestrator
from src.domain.models import CampaignMetrics

# Initialize
orchestrator = Orchestrator()

# Analyze
metrics = CampaignMetrics(
    campaign_id="camp_001",
    cpa_3d_trend=2.5,
    ctr_current=0.02,
    ctr_7d_avg=0.04,
    audience_saturation=0.8,
    creative_age_days=20,
    conversion_volume_7d=10,
    spend_7d=2000.0
)

response = orchestrator.analyze(
    metrics=metrics,
    enable_validation=True,
    enable_thinking=True
)

# Response includes full metadata
print(response.to_dict())
# {
#   "campaign_id": "camp_001",
#   "recommended_action": "pause_campaign",
#   "reasoning": "CPA has increased 2.5x...",
#   "confidence": {...},
#   "validation": {"decision": "approve", ...},
#   "_metadata": {
#     "session_id": "sess_abc123",
#     "trace_id": "trace_xyz789",
#     "analyzer": {"model": "k2p5", "latency_ms": 1877, ...},
#     "validator": {"model": "MiniMax-M2.5", "latency_ms": 1234, ...},
#     "total_latency_ms": 3111,
#     "estimated_cost_usd": 0.00028
#   }
# }
```

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Provider Interface | Anthropic-style only | Supports both Kimi & MiniMax, single implementation |
| Content Format | ContentBlock union | Handles text/thinking/tool_use/redacted_thinking consistently |
| Session Storage | File-based JSON | Unlimited lifetime, simple, debuggable |
| Tool Results | ContentBlocks | Supports text, images, errors uniformly |
| Model Routing | Factory + env vars | Runtime flexibility without code changes |
| Validation | LLM-based | More nuanced than rule-based, can use tools |

---

## Files Added/Modified

```
# New directories (18 files)
src/schema/           (4 files)
src/providers/        (4 files)
src/session/          (3 files)
src/tools/            (5 files)

# Modified
src/agents/__init__.py
src/agents/analyzer.py

# Tests new
tests/unit/test_session.py
tests/unit/test_tools.py

# Tests modified
tests/unit/test_analyzer.py
```

---

## Migration Notes

The old `AnalyzerAgent` interface has changed:

```python
# Before (OpenAI-style)
from src.agents.providers.base import ProviderInterface
provider = MiniMaxProvider(api_key="...")
agent = AnalyzerAgent(provider)
response = agent.analyze(metrics)

# After (Anthropic-style)
from src.providers import get_provider
provider = get_provider("MiniMax-M2.5")  # or "k2p5"
agent = AnalyzerAgent(provider)
response = agent.analyze(metrics)
```

Or use the orchestrator for full multi-agent flow.

---

## Checklist

- [x] Unified Anthropic interface for both providers
- [x] ContentBlock system for all LLM interactions
- [x] Session persistence with file storage
- [x] Tool system with read_file, write_file
- [x] Analyzer agent with thinking capture
- [x] Validator agent with tool access
- [x] Orchestrator for multi-step flow
- [x] 65 unit tests passing
- [x] Token/cost tracking in responses
- [x] No secrets committed
- [ ] Terraform infrastructure (PR5)
- [ ] CI/CD pipeline (PR6)

---

## Related PRs

- **Base:** #1 (pr/01-scaffold-contracts-data)
- **Original PR3 superseded:** Validator + Orchestration (merged here)
- **Original PR4 superseded:** Multi-agent flow (merged here)
- **Next:** #5 (pr/05-terraform-minimal)
- **Following:** #6 (pr/06-cicd-ghcr-cloudrun)

---

## Review Notes

This PR is intentionally large due to the tight coupling between:
1. Provider interface (must support ContentBlocks)
2. Agent implementation (uses ContentBlocks)
3. Tool system (returns ContentBlocks)
4. Session storage (persists ContentBlocks)
5. Multi-agent flow (orchestrates ContentBlock exchanges)

Attempting to split these would result in intermediate states that don't compile or pass tests.
