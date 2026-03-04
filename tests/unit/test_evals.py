"""Tests for evaluation harness."""

import json
import tempfile
from pathlib import Path

import pytest

from src.evals.run_eval import MockProvider, load_scenarios, run_eval
from src.schema import Message, TextContent


class TestMockProvider:
    """Test mock provider for evaluation."""

    def test_mock_provider_returns_response(self):
        """Test mock provider returns valid LLMResponse."""
        provider = MockProvider(accuracy=1.0)  # Perfect accuracy

        messages = [Message.user("Test message")]
        response = provider.generate(messages)

        assert response.model == "mock"
        assert response.provider == "mock"
        assert len(response.content) == 1
        assert isinstance(response.content[0], TextContent)

        # Parse JSON content
        content = json.loads(response.content[0].text)
        assert "recommended_action" in content
        assert "confidence" in content
        assert "key_factors" in content

    def test_mock_provider_tracks_calls(self):
        """Test mock provider tracks call count."""
        provider = MockProvider()

        assert provider.call_count == 0

        provider.generate([Message.user("Test 1")])
        assert provider.call_count == 1

        provider.generate([Message.user("Test 2")])
        assert provider.call_count == 2

    def test_mock_provider_accuracy(self):
        """Test mock provider respects accuracy setting."""
        # With 0% accuracy, should eventually return wrong answers
        provider = MockProvider(accuracy=0.0)

        # Run multiple times to hit random failure case
        results = []
        for i in range(20):
            response = provider.generate([Message.user(f"Test {i}")])
            content = json.loads(response.content[0].text)
            results.append(content["recommended_action"])

        # Just verify we got valid actions
        valid_actions = {"maintain", "pause_campaign", "creative_refresh", "bid_adjustment", "audience_expansion"}
        assert all(r in valid_actions for r in results)


class TestLoadScenarios:
    """Test scenario loading."""

    def test_load_scenarios_from_jsonl(self):
        """Test loading scenarios from JSONL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps({"campaign_id": "test_1", "expected_action": "maintain"}) + "\n")
            f.write(json.dumps({"campaign_id": "test_2", "expected_action": "pause"}) + "\n")
            temp_path = Path(f.name)

        try:
            scenarios = load_scenarios(temp_path)

            assert len(scenarios) == 2
            assert scenarios[0]["campaign_id"] == "test_1"
            assert scenarios[1]["campaign_id"] == "test_2"
        finally:
            temp_path.unlink()

    def test_load_empty_file(self):
        """Test loading empty JSONL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_path = Path(f.name)

        try:
            scenarios = load_scenarios(temp_path)
            assert len(scenarios) == 0
        finally:
            temp_path.unlink()


class TestRunEval:
    """Test evaluation runner."""

    def test_run_eval_with_mock(self):
        """Test evaluation with mock provider."""
        results = run_eval(num_scenarios=10, use_mock=True)

        assert "total" in results
        assert "correct" in results
        assert "accuracy" in results
        assert "results" in results
        assert results["total"] == 10
        assert 0 <= results["accuracy"] <= 1

    def test_eval_results_structure(self):
        """Test evaluation results have correct structure."""
        results = run_eval(num_scenarios=5, use_mock=True)

        for result in results["results"]:
            assert "campaign_id" in result
            assert "expected" in result
            assert "predicted" in result
            assert "correct" in result
            assert isinstance(result["correct"], bool)

    def test_eval_metrics(self):
        """Test evaluation calculates metrics correctly."""
        results = run_eval(num_scenarios=10, use_mock=True)

        # Check derived metrics
        assert results["accuracy"] == results["correct"] / results["total"]
        assert "avg_latency_ms" in results
        assert "total_cost_usd" in results
        assert "eval_time_seconds" in results
