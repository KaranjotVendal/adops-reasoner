"""Unit tests for eval harness."""

import pytest
from unittest.mock import Mock

from src.agents.providers.base import LLMResponse
from src.evals.run_eval import load_scenarios, run_eval, print_eval_summary
from src.data.scenario_generator import generate_dataset


class MockProvider:
    """Mock provider that returns specified action."""

    def __init__(self, action: str = "maintain"):
        self.action = action
        self.called = False

    def generate(self, messages, tools=None, max_tokens=4096, temperature=0.7, thinking=False):
        """New interface matching AnthropicStyleProvider."""
        from src.schema import LLMResponse, TextContent, TokenUsage, CostBreakdown

        self.called = True
        content = '{"recommended_action": "' + self.action + '", "reasoning": "test", "confidence": {"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8}, "key_factors": ["test"]}'

        return LLMResponse(
            content=[TextContent(text=content)],
            model="mock",
            provider="mock",
            latency_ms=10.0,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=CostBreakdown(total_cost=0.0001),
        )


class TestLoadScenarios:
    """Tests for load_scenarios."""

    def test_load_scenarios_from_file(self, tmp_path):
        """Test loading scenarios from JSONL file."""
        # Create test file
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"campaign_id": "test_001", "metrics": {"campaign_id": "test_001"}, "expected_action": "maintain"}\n'
            '{"campaign_id": "test_002", "metrics": {"campaign_id": "test_002"}, "expected_action": "pause_campaign"}\n'
        )

        scenarios = load_scenarios(test_file)
        assert len(scenarios) == 2
        assert scenarios[0]["campaign_id"] == "test_001"


class TestRunEval:
    """Tests for run_eval."""

    def test_run_eval_with_mock_provider_always_maintain(self):
        """Test eval with mock provider that always returns maintain."""
        provider = MockProvider("maintain")
        from src.agents.analyzer import AnalyzerAgent

        analyzer = AnalyzerAgent(provider)

        results = run_eval(analyzer, validator=None)

        assert results["total"] > 0
        assert results["correct"] >= 0
        assert "accuracy" in results
        assert "results" in results

    def test_run_eval_tracks_human_review(self):
        """Test that human review is tracked."""
        from src.agents.analyzer import AnalyzerAgent
        from src.agents.validator import ValidatorAgent

        analyzer = AnalyzerAgent(MockProvider("maintain"))
        validator = ValidatorAgent(MockProvider("approve"))

        results = run_eval(analyzer, validator)

        assert "human_review_triggered" in results
        assert "human_review_rate" in results


class TestPrintEvalSummary:
    """Tests for print_eval_summary."""

    def test_print_summary_does_not_raise(self):
        """Test that print_eval_summary handles all cases."""
        results = {
            "total": 10,
            "correct": 8,
            "accuracy": 0.8,
            "human_review_triggered": 2,
            "human_review_rate": 0.2,
            "results": [
                {"campaign_id": "c1", "expected": "maintain", "predicted": "maintain", "correct": True},
                {"campaign_id": "c2", "expected": "pause_campaign", "predicted": "maintain", "correct": False},
            ],
        }
        # Should not raise
        print_eval_summary(results)
