# PR4: Evaluation Harness & Demo Scripts

**Branch:** `pr/04-evals-demo`  
**Base:** `pr/02-analyzer-core`  
**Status:** Ready for Review

---

## Summary

This PR provides offline evaluation capabilities and demo scripts for the Campaign Analyst system. It includes a mock provider for testing without API calls, comprehensive evaluation metrics, and interactive demos.

---

## What's Included

### 1. Evaluation Harness (`src/evals/run_eval.py`)

```python
# Run mock evaluation (no API keys needed)
python -m src.evals.run_eval --scenarios 50 --mock-accuracy 0.85

# Run live evaluation (requires API keys)
python -m src.evals.run_eval --scenarios 10 --live
```

**Features:**
- MockProvider for testing without API costs
- Accuracy tracking against labeled scenarios
- Human review rate metrics
- Cost and latency tracking
- JSON output for result analysis

### 2. Demo Scripts (`src/evals/demo.py`)

```bash
# Show sample API payload
python -m src.evals.demo --payload

# Run live analysis on synthetic scenario
export KIMI_API_KEY=sk-...
python -m src.evals.demo --scenario

# List available models
python -m src.evals.demo --models

# Show scenarios from dataset
python -m src.evals.demo --dataset
```

### 3. Mock Provider

The `MockProvider` simulates LLM responses for testing:
- Configurable accuracy rate
- Tracks call count
- Returns realistic action predictions
- No API costs for CI/testing

---

## Test Coverage

- 8 new tests in `tests/unit/test_evals.py`
- Mock provider tests
- Scenario loading tests
- Evaluation runner tests

---

## Usage Examples

### Evaluation

```bash
# Quick evaluation with 85% accuracy mock
python -m src.evals.run_eval --scenarios 20

# Full evaluation with output
python -m src.evals.run_eval --scenarios 100 --output results.json
```

### Demo

```bash
# Complete demo flow
python -m src.evals.demo --payload
export KIMI_API_KEY=sk-...
python -m src.evals.demo --scenario
python -m src.evals.demo --models
```

---

## Files Changed

- `src/evals/demo.py` - Updated for new architecture
- `src/evals/run_eval.py` - Complete rewrite with MockProvider
- `tests/unit/test_evals.py` - New test file

---

## Dependencies

- Works with existing architecture from PR2
- No new dependencies

---

## Checklist

- [x] Mock provider for testing
- [x] Evaluation harness with metrics
- [x] Demo scripts for all use cases
- [x] 8 unit tests passing
- [x] Updated for PR2 architecture
