# Architecture Foundation Plan

Based on thorough discussion, this document locks in the foundational decisions.

## Core Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Style | **Anthropic-only** | Supports both Kimi & MiniMax, single implementation |
| Model Switching | Server config + per-request override | Flexibility with sensible defaults |
| Response Schema | Unified `ContentBlock` system | Handles text/thinking/tool_use/redacted consistently |
| Streaming | **Disabled for MVP** | Add in PR5, not interview-critical |
| Session Lifetime | **Forever** | Full traceability, manual cleanup |
| Tools (MVP) | `read_file`, `write_file` | Foundation for agent actions |

## Unified Content Block Schema

```python
# All LLM responses normalized to this structure
class ContentBlock(BaseModel):
    type: Literal["text", "thinking", "tool_use", "redacted_thinking"]
    
    # Type: text
    text: str | None = None
    
    # Type: thinking
    thinking: str | None = None
    thinking_signature: str | None = None  # For multi-turn continuity
    
    # Type: tool_use  
    tool_use: ToolUseBlock | None = None
    
    # Type: redacted_thinking
    redacted_data: str | None = None  # Opaque payload for API continuity

class ToolUseBlock(BaseModel):
    id: str
    name: str  # "read_file", "write_file", etc.
    input: dict  # JSON arguments
```

## Provider Architecture

```
AnthropicStyleProvider (abstract)
    ├── KimiProvider
    │   └── base_url: https://api.kimi.com/coding/v1/messages
    │   └── models: k2p5, kimi-k2-thinking
    │
    └── MiniMaxProvider  
        └── base_url: https://api.minimax.io/anthropic/v1/messages
        └── models: MiniMax-M2.5, MiniMax-M2.5-highspeed
```

Both use identical Anthropic SDK pattern:
- Headers: `Authorization: Bearer {key}`, `anthropic-version: 2023-06-01`
- Payload: Anthropic Messages API format
- Response: Anthropic content block format

## Model Switching Strategy

### Default Configuration (environment)
```bash
ANALYZER_MODEL=k2p5                    # Kimi for analysis
VALIDATOR_MODEL=MiniMax-M2.5           # MiniMax for validation
FALLBACK_MODEL=MiniMax-M2.5            # If primary fails
```

### Per-Request Override
```json
POST /analyze
{
  "campaign_metrics": {...},
  "_options": {
    "analyzer_model": "MiniMax-M2.5",  // Override default
    "validator_model": "k2p5"
  }
}
```

### Runtime Provider Resolution
```python
def get_provider(model_id: str) -> AnthropicStyleProvider:
    if model_id in KIMI_MODELS:
        return KimiProvider(api_key=KIMI_API_KEY)
    elif model_id in MINIMAX_MODELS:
        return MiniMaxProvider(api_key=MINIMAX_API_KEY)
    else:
        raise ValueError(f"Unknown model: {model_id}")
```

## Multi-Step Agent Flow (PR3/4)

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION: sess_abc123                                        │
│  Messages: [user_request, analyzer_response,                │
│            validator_response, tool_results...]              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 1: Analyzer Agent                                      │
│  - Model: k2p5 (configured)                                 │
│  - Input: campaign_metrics + system_prompt                  │
│  - Output: ContentBlocks[thinking, text]                    │
│  - Decision: recommended_action + reasoning                 │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│  STEP 2: Validator Agent                                     │
│  - Model: MiniMax-M2.5 (configured)                         │
│  - Input: analyzer_output + original_metrics                │
│  - Output: ContentBlocks[thinking, text]                    │
│  - Decision: approve / request_tools / flag_human_review    │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
Approve           Tools Needed
    │                 │
    │    ┌────────────┴────────────┐
    │    │ TOOL EXECUTION           │
    │    │ - read_file              │
    │    │ - write_file             │
    │    │ - (extensible)           │
    │    └────────────┬─────────────┘
    │                 │
    │    ┌────────────┴────────────┐
    │    │ Validator Re-check       │
    │    │ (with tool results)      │
    │    └────────────┬─────────────┘
    │                 │
    └─────────────────┘
                      │
              ┌───────▼────────┐
              │ FINAL RESPONSE │
              │ with metadata  │
              └────────────────┘
```

## Session Persistence (pi-mono style)

```python
class SessionManager:
    """File-based session storage with unlimited lifetime."""
    
    def create(self, system_prompt: str) -> Session:
        session_id = generate_uuid()
        session = Session(
            id=session_id,
            created_at=datetime.now(),
            messages=[Message(role="system", content=system_prompt)],
            context_budget=16000,  # Compact when exceeded
            total_tokens_used=0
        )
        self._save_to_disk(session)
        return session
    
    def add_message(self, session_id: str, message: Message):
        session = self._load_from_disk(session_id)
        session.messages.append(message)
        
        # Compact if budget exceeded
        if self._estimate_tokens(session.messages) > session.context_budget:
            session = self._compact_history(session)
        
        self._save_to_disk(session)
    
    def get_history(self, session_id: str) -> list[Message]:
        """Retrieve full conversation history."""
        session = self._load_from_disk(session_id)
        return session.messages
    
    def _compact_history(self, session: Session) -> Session:
        """Summarize old messages when context budget exceeded."""
        # Find cut point (keep recent N messages)
        # Call LLM to summarize older messages
        # Replace old messages with summary
        return session
```

## Observability (Interview-Ready)

### Structured Logging
```python
# Every LLM call logged
{
    "timestamp": "2025-03-03T22:56:00Z",
    "session_id": "sess_abc123",
    "trace_id": "trace_xyz789",
    "event": "llm_request",
    "agent": "analyzer",  # or "validator"
    "model": "k2p5",
    "provider": "kimi",
    "input_tokens": 150,
    "output_tokens": 85,
    "thinking_tokens": 45,
    "latency_ms": 1877,
    "cost_usd": 0.00015
}

# Every tool execution logged
{
    "timestamp": "2025-03-03T22:56:02Z",
    "session_id": "sess_abc123",
    "trace_id": "trace_xyz789",
    "event": "tool_execution",
    "tool_name": "read_file",
    "input": {"path": "/data/campaigns.json"},
    "success": True,
    "latency_ms": 45
}
```

### API Response Metadata
```json
{
  "campaign_id": "camp_0001",
  "recommended_action": "pause_campaign",
  "reasoning": "CPA has tripled in 3 days...",
  "confidence": 0.92,
  "requires_human_review": false,
  "_metadata": {
    "session_id": "sess_abc123",
    "trace_id": "trace_xyz789",
    "analyzer": {
      "model": "k2p5",
      "provider": "kimi",
      "latency_ms": 1877,
      "tokens": {"input": 150, "output": 85, "thinking": 45}
    },
    "validator": {
      "model": "MiniMax-M2.5",
      "provider": "minimax",
      "latency_ms": 1234,
      "tokens": {"input": 200, "output": 60}
    },
    "total_latency_ms": 3111,
    "estimated_cost_usd": 0.00028
  }
}
```

## PR Breakdown

### PR2: Anthropic Foundation ✅ COMPLETED
- [x] Replace OpenAI provider with Anthropic-style
- [x] Implement `AnthropicStyleProvider` base class
- [x] Implement `KimiProvider` and `MiniMaxProvider`
- [x] Unified `ContentBlock` schema
- [x] Model routing based on config + request override
- [x] Update `AnalyzerAgent` to use new provider interface
- [x] Tests: both providers, model switching

### PR3: Session + Tool Foundation ✅ COMPLETED
- [x] `SessionManager` with file persistence
- [x] `Tool` base class + registry
- [x] `ReadFileTool`, `WriteFileTool`
- [x] Context compaction (basic)
- [ ] Session endpoints: `POST /sessions`, `GET /sessions/{id}` (API layer)

### PR4: LLM Validator + Multi-Step ✅ COMPLETED
- [x] `ValidatorAgent` as LLM with tool access
- [x] Agent loop: Analyzer → Validator → Tools → Response
- [x] Tool execution in loop
- [x] Final response assembly (via Orchestrator)

### PR5: Observability + Polish 🔄 PENDING
- [ ] Structured logging (JSON)
- [x] Token/cost tracking (implemented in providers)
- [x] Response metadata (via Orchestrator)
- [ ] Session replay endpoint
- [ ] (Optional) Streaming support

## Key Files to Create/Modify

```
src/
├── providers/
│   ├── __init__.py
│   ├── base.py                    # AnthropicStyleProvider (ABC)
│   ├── schema.py                  # ContentBlock, LLMResponse, ToolUseBlock
│   ├── kimi.py                    # KimiProvider
│   └── minimax.py                 # MiniMaxProvider (Anthropic-style)
│
├── schema/
│   ├── __init__.py
│   └── content.py                 # Unified content block types
│
├── session/
│   ├── __init__.py
│   ├── manager.py                 # SessionManager
│   └── models.py                  # Session, Message
│
├── tools/
│   ├── __init__.py
│   ├── base.py                    # Tool ABC
│   ├── registry.py                # Tool registry
│   ├── read_file.py               # ReadFileTool
│   └── write_file.py              # WriteFileTool
│
├── observability/
│   ├── __init__.py
│   ├── logger.py                  # Structured logger
│   └── models.py                  # LogEntry types
│
└── agents/
    ├── __init__.py
    ├── analyzer.py                # Updated for Anthropic-style
    ├── validator.py               # NEW: LLM-based validator
    └── orchestrator.py            # NEW: Multi-step orchestrator
```

## Configuration (Environment)

```bash
# Required
KIMI_API_KEY=sk-...
MINIMAX_API_KEY=sk-...

# Optional (defaults shown)
ANALYZER_MODEL=k2p5
VALIDATOR_MODEL=MiniMax-M2.5
FALLBACK_MODEL=MiniMax-M2.5

# Session storage
SESSION_STORAGE_PATH=./data/sessions
SESSION_CONTEXT_BUDGET=16000

# Observability
LOG_LEVEL=INFO
LOG_FORMAT=json  # or text
```

## Implementation Status

### ✅ Completed
- **Unified Anthropic Interface**: Both Kimi and MiniMax through `AnthropicStyleProvider`
- **Model Switching**: Server config (`ANALYZER_MODEL`, `VALIDATOR_MODEL`) + per-request override capability
- **Content Block System**: Full support for text, thinking, tool_use, redacted_thinking
- **Session Persistence**: File-based with unlimited lifetime, context compaction
- **Tool System**: Registry, read_file, write_file with ContentBlock results
- **Multi-Agent Flow**: Analyzer → Validator → Tools → Response via Orchestrator
- **Token/Cost Tracking**: Implemented in providers, exposed in metadata

### 🔄 Remaining for PR5
- Structured JSON logging (interview-ready format)
- Session replay endpoint
- Streaming support (optional)

### Test Coverage
- 65 unit tests passing
- Schema validation
- Provider mocks
- Session management
- Tool execution
- Analyzer agent with ContentBlock parsing
