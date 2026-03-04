# Campaign Analyst - Architecture & Data Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAMPAIGN ANALYST SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐        │
│   │   USER/API   │────▶│   API LAYER     │────▶│  ORCHESTRATOR    │        │
│   │   REQUEST    │     │   (FastAPI)     │     │  (Coordinator)   │        │
│   └──────────────┘     └─────────────────┘     └────────┬─────────┘        │
│                                                         │                    │
│                              ┌──────────────────────────┼────────────────┐  │
│                              │                          ▼                │  │
│                              │  ┌──────────────┐  ┌──────────────┐       │  │
│                              │  │   SESSION    │  │   ANALYZER   │       │  │
│                              │  │   MANAGER    │  │    AGENT     │       │  │
│                              │  │              │  │              │       │  │
│                              │  │ ┌──────────┐ │  │ ┌──────────┐ │       │  │
│                              │  │ │ Messages │ │  │ │  Kimi   │ │       │  │
│                              │  │ │  History │ │  │ │ k2.5    │ │       │  │
│                              │  │ └──────────┘ │  │ └──────────┘ │       │  │
│                              │  └──────────────┘  └──────┬───────┘       │  │
│                              │                           │               │  │
│                              │                           ▼               │  │
│                              │                    ┌──────────────┐       │  │
│                              │                    │  LLMResponse │       │  │
│                              │                    │ - Content[]  │       │  │
│                              │                    │ - Tokens     │       │  │
│                              │                    │ - Cost       │       │  │
│                              │                    └──────┬───────┘       │  │
│                              │                           │               │  │
│                              │                           ▼               │  │
│                              │  ┌──────────────┐  ┌──────────────┐       │  │
│                              │  │    TOOLS     │◀─│  VALIDATOR   │       │  │
│                              │  │   (Optional) │  │    AGENT     │       │  │
│                              │  │ ┌──────────┐ │  │ ┌──────────┐ │       │  │
│                              │  │ │read_file │ │  │ │ MiniMax │ │       │  │
│                              │  │ │write_file│ │  │ │ M2.5    │ │       │  │
│                              │  │ └──────────┘ │  │ └──────────┘ │       │  │
│                              │  └──────────────┘  └──────────────┘       │  │
│                              │                                           │  │
│                              └───────────────────────────────────────────┘  │
│                                                                             │
│                                                         │                    │
│                                                         ▼                    │
│                                               ┌──────────────────┐          │
│                                               │  FINAL RESPONSE  │          │
│                                               │  - Action        │          │
│                                               │  - Reasoning     │          │
│                                               │  - Confidence    │          │
│                                               │  - Metadata      │          │
│                                               └──────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Step by Step

### 1. Request Reception
```
┌──────────┐     POST /analyze      ┌──────────┐
│  Client  │ ──────────────────────▶ │ FastAPI  │
│          │  {campaign_metrics}     │  /main   │
└──────────┘                         └────┬─────┘
                                          │
                                          ▼
                                   Parse Request
                               Convert to CampaignMetrics
```

### 2. Session Initialization
```
┌──────────┐     Create/Load       ┌──────────────────┐
│   API    │ ─────────────────────▶ │ SessionManager   │
│          │                        │                  │
│          │ ◀───────────────────── │ - Session ID     │
│          │    Return Session      │ - Message History│
└──────────┘                        └──────────────────┘
```

### 3. Analyzer Agent Execution
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│   Analyzer   │────▶│    Kimi      │
│              │     │    Agent     │     │    k2.5      │
│              │     │              │     │              │
│              │     │ - System     │     │ - Analyze    │
│              │     │   Prompt     │     │ - Reasoning  │
│              │     │ - User       │     │ - Recommend  │
│              │     │   Metrics    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │ LLMResponse  │
                                        │ - Content[]  │
                                        │ - Thinking   │
                                        │ - Tokens     │
                                        └──────┬───────┘
                                               │
                                               ▼
                                        Parse JSON Result
```

### 4. Validator Agent Execution
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│   Validator  │────▶│   MiniMax    │
│              │     │    Agent     │     │    M2.5      │
│              │     │              │     │              │
│              │     │ - Original   │     │ - Validate   │
│              │     │   Metrics    │     │ - Review     │
│              │     │ - Analyzer   │     │ - Approve/   │
│              │     │   Result     │     │   Reject     │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │ValidationResult│
                                        │ - Decision   │
                                        │ - Confidence │
                                        │ - Feedback   │
                                        └──────────────┘
```

### 5. Tool Execution (Optional)
```
┌──────────────┐     Tool Call      ┌──────────────┐
│   Validator  │ ─────────────────▶ │   Tool       │
│   (if needed)│ {name, arguments}  │   Registry   │
└──────────────┘                    └──────┬───────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    ▼                    │
                    │  ┌──────────┐  ┌──────────┐            │
                    │  │read_file │  │write_file│            │
                    │  └─────┬────┘  └─────┬────┘            │
                    │        │             │                  │
                    └────────┼─────────────┼──────────────────┘
                             └──────┬──────┘
                                    │
                                    ▼
                           ┌────────────────┐
                           │  ToolResult    │
                           │ - Content[]    │
                           │ - is_error     │
                           └────────────────┘
```

### 6. Response Assembly
```
┌─────────────────────────────────────────────────────────────┐
│                      FINAL RESPONSE                          │
├─────────────────────────────────────────────────────────────┤
│ {                                                            │
│   "campaign_id": "camp_001",                                 │
│   "recommended_action": "pause_campaign",                    │
│   "reasoning": "CPA has increased 2.5x...",                  │
│   "confidence": {                                            │
│     "overall_score": 0.85,                                   │
│     "data_quality": 0.90,                                    │
│     "recommendation_strength": 0.80                          │
│   },                                                         │
│   "key_factors": ["CPA trend", "Low conversions"],           │
│   "validation": {                                            │
│     "decision": "approve",                                   │
│     "confidence": 0.92                                       │
│   },                                                         │
│   "_metadata": {                                             │
│     "session_id": "sess_abc123",                             │
│     "trace_id": "trace_xyz789",                              │
│     "analyzer": {                                            │
│       "model": "k2p5",                                       │
│       "provider": "kimi",                                    │
│       "latency_ms": 1877,                                    │
│       "tokens": {"input": 150, "output": 85},                │
│       "cost": {"total_cost": 0.00015}                        │
│     },                                                       │
│     "validator": {                                           │
│       "model": "MiniMax-M2.5",                               │
│       "provider": "minimax",                                 │
│       "latency_ms": 1234,                                    │
│       "tokens": {"input": 200, "output": 60},                │
│       "cost": {"total_cost": 0.00013}                        │
│     },                                                       │
│     "total_latency_ms": 3111,                                │
│     "estimated_cost_usd": 0.00028                            │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

## Provider Flow Detail

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANTHROPIC-STYLE PROVIDER                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                              │
│  │   Request    │                                              │
│  │ - Messages[] │                                              │
│  │ - Tools[]    │                                              │
│  │ - System     │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────┐                      │
│  │      CONVERT TO ANTHROPIC FORMAT     │                      │
│  │                                      │                      │
│  │  Messages:                           │                      │
│  │    [{"role": "user", "content": ...}] │                      │
│  │                                      │                      │
│  │  Tools:                              │                      │
│  │    [{"name": "...", "input_schema":}] │                      │
│  │                                      │                      │
│  └──────────────┬──────────────────────┘                      │
│                 │                                               │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                      │
│  │         HTTP POST /v1/messages       │                      │
│  │                                      │                      │
│  │  Headers:                            │                      │
│  │    Authorization: Bearer {key}       │                      │
│  │    anthropic-version: 2023-06-01     │                      │
│  │                                      │                      │
│  └──────────────┬──────────────────────┘                      │
│                 │                                               │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                      │
│  │      PARSE ANTHROPIC RESPONSE        │                      │
│  │                                      │                      │
│  │  Content Blocks:                     │                      │
│  │    - type: "text"                    │                      │
│  │    - type: "thinking"                │                      │
│  │    - type: "tool_use"                │                      │
│  │    - type: "redacted_thinking"       │                      │
│  │                                      │                      │
│  │  Usage:                              │                      │
│  │    input_tokens, output_tokens       │                      │
│  │                                      │                      │
│  └──────────────┬──────────────────────┘                      │
│                 │                                               │
│                 ▼                                               │
│  ┌──────────────────────────────────────┐                      │
│  │      CONVERT TO UNIFIED SCHEMA       │                      │
│  │                                      │                      │
│  │  LLMResponse:                        │                      │
│  │    content: ContentBlock[]           │                      │
│  │    usage: TokenUsage                 │                      │
│  │    cost: CostBreakdown               │                      │
│  │    latency_ms: float                 │                      │
│  │                                      │                      │
│  └──────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Session Persistence Flow

```
┌──────────────┐     Create/Load      ┌──────────────────┐
│   Request    │ ───────────────────▶ │  SessionManager  │
└──────────────┘                      └────────┬─────────┘
                                              │
                    ┌─────────────────────────┼────────────────────┐
                    │                         ▼                    │
                    │              ┌──────────────────┐            │
                    │              │   Session File   │            │
                    │              │                  │            │
                    │              │ {session_id}.json│            │
                    │              │                  │            │
                    │              │ {                │            │
                    │              │   "id": "...",   │            │
                    │              │   "messages": [],│            │
                    │              │   "metadata": {} │            │
                    │              │ }                │            │
                    │              └──────────────────┘            │
                    │                                              │
                    └──────────────────────────────────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Add Message     │
                                    │  - Update JSON   │
                                    │  - Sync to disk  │
                                    └──────────────────┘
```

## Multi-Agent Collaboration

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT COLLABORATION                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   STEP 1: ANALYSIS                                               │
│   ┌─────────────┐    Analyze     ┌─────────────┐               │
│   │   Kimi      │ ◀──────────────│  Campaign   │               │
│   │   k2.5      │   Metrics      │   Metrics   │               │
│   │  (Analyzer) │                │  (Input)    │               │
│   └──────┬──────┘                └─────────────┘               │
│          │                                                      │
│          │ {"action": "pause", "reasoning": "..."}               │
│          ▼                                                      │
│   ┌─────────────┐                                               │
│   │   Result    │                                               │
│   └──────┬──────┘                                               │
│          │                                                      │
│   STEP 2: VALIDATION                                             │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐    Validate    ┌─────────────┐               │
│   │  MiniMax    │ ◀──────────────│   Result    │               │
│   │   M2.5      │   + Metrics    │  (Analyzer) │               │
│   │ (Validator) │                │             │               │
│   └──────┬──────┘                └─────────────┘               │
│          │                                                      │
│          │ {"decision": "approve", "confidence": 0.92}          │
│          ▼                                                      │
│   ┌─────────────┐                                               │
│   │  Validation │                                               │
│   │   Result    │                                               │
│   └──────┬──────┘                                               │
│          │                                                      │
│   STEP 3: TOOLS (if needed)                                      │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐    Request     ┌─────────────┐               │
│   │  Validator  │ ──────────────▶│    Tools    │               │
│   │             │   read_file    │             │               │
│   └─────────────┘                └─────────────┘               │
│                                         │                       │
│                                         ▼                       │
│                                  ┌─────────────┐               │
│                                  │   Result    │               │
│                                  │   Content   │               │
│                                  └──────┬──────┘               │
│                                         │                       │
│   STEP 4: FINAL OUTPUT                    │                       │
│                                         ▼                       │
│                                  ┌─────────────┐               │
│                                  │  Re-check   │               │
│                                  │  Validator  │               │
│                                  └──────┬──────┘               │
│                                         │                       │
│                                         ▼                       │
│   ┌──────────────────────────────────────────────────────┐     │
│   │                    FINAL RESPONSE                     │     │
│   │  - Action: pause_campaign                            │     │
│   │  - Reasoning: CPA increased 2.5x...                  │     │
│   │  - Confidence: 0.85                                  │     │
│   │  - Validation: approved                              │     │
│   │  - Models: k2p5 → MiniMax-M2.5                       │     │
│   └──────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
