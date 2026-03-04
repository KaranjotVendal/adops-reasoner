# Adops Reasoner

A multi-agent LLM-powered system for marketing campaign analysis and recommendations.

## Overview

Campaign Analyst uses multiple LLM agents to analyze marketing campaign metrics and provide actionable recommendations:

- **Analyzer Agent** (Kimi k2.5): Analyzes metrics and generates recommendations
- **Validator Agent** (MiniMax M2.5): Validates recommendations for quality and consistency
- **Orchestrator**: Coordinates the multi-agent flow and tracks performance

## Features

- ✅ **Multi-Agent Architecture**: Analyzer → Validator → Tools → Response
- ✅ **Dual LLM Support**: Kimi (k2.5) and MiniMax (M2.5) providers
- ✅ **Session Persistence**: File-based conversation history
- ✅ **Cost Tracking**: Per-request token usage and cost breakdown
- ✅ **Tool System**: Extensible tool framework (read_file, write_file)
- ✅ **FastAPI**: RESTful API with auto-generated docs
- ✅ **Terraform**: GCP Cloud Run deployment ready

## Quick Start

### Prerequisites

- Python 3.13+
- API keys for at least one provider:
  - [Kimi API](https://platform.moonshot.cn/) (free during beta)
  - [MiniMax API](https://www.minimaxi.com/)

### Installation

```bash
# Clone repository
git clone https://github.com/KaranjotVendal/adops-reasoner.git
cd adops-reasoner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install uv
uv sync --all-extras
```

### Configuration

```bash
# Set API keys (at least one required)
export KIMI_API_KEY="sk-..."
export MINIMAX_API_KEY="sk-..."

# Optional: Model selection
export ANALYZER_MODEL="k2p5"              # Options: k2p5, MiniMax-M2.5
export VALIDATOR_MODEL="MiniMax-M2.5"     # Options: k2p5, MiniMax-M2.5
```

## Usage

### Demo Scripts

Run these scripts to test the system locally (no GCP required):

```bash
# Quick live test (30-45 seconds)
python scripts/test_live.py

# Comprehensive end-to-end test
python scripts/e2e_test.py

# Validate API connectivity
python scripts/test_kimi_api.py
python scripts/test_minimax_api.py
```

**Example output:**
```
============================================================
CAMPAIGN ANALYST - LIVE TEST
============================================================

1. Initializing orchestrator...
   Analyzer: k2p5
   Validator: MiniMax-M2.5

2. Creating test campaign...
   Campaign: live_test_001
   CPA Trend: 2.2x
   CTR: 2.50% (was 4.00%)

3. Running analysis...

4. Results:
   ✓ Action: CREATIVE_REFRESH
   ✓ Reasoning: CPA has spiked 2.2x over 3 days...
   ✓ Confidence: 85%
   ✓ Validation: APPROVE (80%)

5. Performance:
   Session: sess_d7a97104c5fc
   Latency: 35940ms
   Cost: $0.000225

============================================================
TEST PASSED ✓
============================================================
```

### Running Tests

```bash
# Run all tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_analyzer.py -v
```

### Running the API Server

```bash
# Start FastAPI server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Access API docs
open http://localhost:8000/docs
```

**API Endpoints:**
- `POST /analyze` - Analyze campaign metrics
- `GET /health` - Health check
- `GET /models` - List available models
- `GET /sessions/{id}` - Get session history

**Example API call:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_001",
    "cpa_3d_trend": 2.5,
    "ctr_current": 0.02,
    "ctr_7d_avg": 0.04,
    "audience_saturation": 0.8,
    "creative_age_days": 21,
    "conversion_volume_7d": 50,
    "spend_7d": 2000.0
  }'
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Client     │────▶│   FastAPI    │────▶│ Orchestrator │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                       ┌──────────────────────────┼────────────────┐
                       │                          ▼                │
              ┌────────▼────────┐      ┌──────────────┐          │
              │ Analyzer Agent  │      │   Validator  │          │
              │   (Kimi k2.5)   │      │ (MiniMax M2.5│          │
              └────────┬────────┘      └──────┬───────┘          │
                       │                      │                   │
              ┌────────▼────────┐      ┌──────▼───────┐          │
              │  Recommendation │      │  Validation  │          │
              └─────────────────┘      └──────────────┘          │
                       │                                         │
                       └──────────────────┬──────────────────────┘
                                          ▼
                               ┌──────────────────┐
                               │  Final Response  │
                               │  with metadata   │
                               └──────────────────┘
```

### Data Flow

1. **Request** → FastAPI validates input
2. **Session** → Created/stored via SessionManager
3. **Analyzer** → Kimi k2.5 analyzes metrics
4. **Parse** → Extract JSON from ContentBlocks
5. **Validator** → MiniMax M2.5 validates result
6. **Response** → Combined output with metadata

## Project Structure

```
adops-reasoner/
├── src/
│   ├── agents/           # Analyzer, Validator, Orchestrator
│   ├── api/              # FastAPI application
│   ├── evals/            # Demo scripts and evaluation
│   ├── providers/        # LLM provider implementations
│   ├── schema/           # ContentBlock, Message types
│   ├── session/          # Session management
│   └── tools/            # Tool system
├── infra/                # Terraform configuration
├── scripts/              # Demo and test scripts
├── tests/                # Unit tests
└── data/                 # Sessions and scenarios
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `KIMI_API_KEY` | — | Kimi API key |
| `MINIMAX_API_KEY` | — | MiniMax API key |
| `ANALYZER_MODEL` | `k2p5` | Model for analyzer |
| `VALIDATOR_MODEL` | `MiniMax-M2.5` | Model for validator |
| `SESSION_STORAGE_PATH` | `./data/sessions` | Session file location |
| `LOG_LEVEL` | `INFO` | Logging level |

## Deployment (Optional)

Deploy to GCP Cloud Run using Terraform:

```bash
cd infra/

# Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy
terraform init
terraform plan
terraform apply
```

**Resources created:**
- Cloud Run v2 service (auto-scaling 0-10 instances)
- Service account with minimal permissions
- Secret Manager for API keys
- IAM bindings for secure access

See `infra/README.md` for detailed deployment instructions.

## Performance

| Metric | Typical Value |
|--------|--------------|
| Full Analysis Latency | 30-45 seconds |
| Cost per Analysis | ~$0.0002-0.0003 |
| Kimi k2.5 Latency | ~15-25s |
| MiniMax M2.5 Latency | ~10-20s |
| Session Storage | File-based JSON |

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Provider Interface | Anthropic-style | Supports both Kimi & MiniMax |
| Response Format | ContentBlock union | Handles text/thinking/tools uniformly |
| Session Storage | File-based JSON | Unlimited lifetime, debuggable |
| Model Selection | Env vars + override | Runtime flexibility |
| Validation | LLM-based (not rules) | More nuanced, can use tools |

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Built for the MVF Campaign Analyst interview showcase.**
