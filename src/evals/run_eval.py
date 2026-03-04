"""Offline evaluation harness for campaign analyst.

Updated for new architecture with Anthropic-style providers.
"""

import json
import time
from pathlib import Path
from typing import Any

from src.agents import Orchestrator
from src.data.scenario_generator import generate_dataset
from src.domain.models import CampaignMetrics
from src.providers.base import AnthropicStyleProvider
from src.schema import ContentBlock, LLMResponse, Message, TextContent, TokenUsage


def load_scenarios(path: Path) -> list[dict]:
    """Load scenarios from JSONL file.

    Args:
        path: Path to JSONL file

    Returns:
        List of scenario dictionaries
    """
    scenarios = []
    with open(path) as f:
        for line in f:
            scenarios.append(json.loads(line))
    return scenarios


class MockProvider(AnthropicStyleProvider):
    """Mock provider for evaluation without API calls.

    Returns predetermined responses based on scenario difficulty.
    """

    def __init__(self, accuracy: float = 0.8):
        """Initialize mock provider.

        Args:
            accuracy: Target accuracy rate (0-1)
        """
        self.accuracy = accuracy
        self.call_count = 0
        self.calls: list[list[Message]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def api_version(self) -> str:
        return "2023-06-01"

    def _calculate_cost(self, usage: TokenUsage):
        from src.schema import CostBreakdown

        return CostBreakdown()

    def generate(
        self,
        messages: list[Message],
        tools=None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thinking: bool = False,
    ) -> LLMResponse:
        """Return mock response based on input analysis."""
        self.calls.append(messages)
        self.call_count += 1

        # Extract scenario info from messages
        content_str = str(messages)

        # Determine expected action from scenario patterns
        if "cpa_3d_trend" in content_str:
            # Parse metrics from content to make informed decision
            if "2.5" in content_str or "3.0" in content_str:
                action = "pause_campaign"
            elif "1.5" in content_str or "1.8" in content_str:
                action = "bid_adjustment"
            elif "creative_age_days\": 30" in content_str or "creative_age_days\": 25" in content_str:
                action = "creative_refresh"
            else:
                action = "maintain"
        else:
            action = "maintain"

        # Simulate some errors based on accuracy target
        import random

        random.seed(self.call_count)
        if random.random() > self.accuracy:
            # Return wrong action occasionally
            action = "maintain" if action != "maintain" else "bid_adjustment"

        response_text = json.dumps({
            "recommended_action": action,
            "reasoning": f"Mock analysis for evaluation (call #{self.call_count})",
            "confidence": {
                "overall_score": 0.8,
                "data_quality": 0.85,
                "recommendation_strength": 0.75,
            },
            "key_factors": ["Mock factor 1", "Mock factor 2"],
        })

        return LLMResponse(
            content=[TextContent(text=response_text)],
            model="mock",
            provider="mock",
            latency_ms=10.0,
        )


def run_eval(
    orchestrator: Orchestrator | None = None,
    num_scenarios: int = 50,
    use_mock: bool = True,
) -> dict[str, Any]:
    """Run offline evaluation on synthetic dataset.

    Args:
        orchestrator: Orchestrator instance (creates mock if None)
        num_scenarios: Number of scenarios to evaluate
        use_mock: Whether to use mock provider

    Returns:
        Evaluation results dictionary
    """
    # Generate or load dataset
    data_dir = Path(__file__).parent.parent.parent / "data"
    scenarios_path = data_dir / "scenarios_v1.jsonl"

    if scenarios_path.exists():
        all_scenarios = load_scenarios(scenarios_path)
        scenarios = all_scenarios[:num_scenarios]
    else:
        scenarios = generate_dataset(num_scenarios=num_scenarios)

    # Create orchestrator if not provided
    if orchestrator is None:
        if use_mock:
            # Create orchestrator with mock provider
            from src.providers import AnthropicStyleProvider

            mock_provider = MockProvider(accuracy=0.85)
            from src.agents import AnalyzerAgent

            analyzer = AnalyzerAgent(mock_provider)
            orchestrator = Orchestrator(
                analyzer_model="mock",
                validator_model="mock",
            )
            # Override the analyzer's provider
            orchestrator._analyzer = analyzer
        else:
            orchestrator = Orchestrator()

    results = []
    correct = 0
    total = 0
    human_review_triggered = 0
    total_latency = 0.0
    total_cost = 0.0

    start_time = time.time()

    for scenario in scenarios:
        metrics = CampaignMetrics(**scenario["metrics"])
        expected = scenario["expected_action"]

        try:
            # Run analysis
            response = orchestrator.analyze(
                metrics=metrics,
                enable_validation=True,
                enable_thinking=False,
            )

            result = response.to_dict()
            predicted = result["recommended_action"]

            # Track metrics
            total_latency += result["_metadata"]["total_latency_ms"]
            total_cost += result["_metadata"]["estimated_cost_usd"]

            if result["validation"] and result["validation"].get("requires_human_review"):
                human_review_triggered += 1

            # Count correct
            is_correct = predicted == expected
            if is_correct:
                correct += 1

            total += 1

            results.append({
                "campaign_id": scenario["campaign_id"],
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "latency_ms": result["_metadata"]["total_latency_ms"],
                "cost_usd": result["_metadata"]["estimated_cost_usd"],
            })

        except Exception as e:
            total += 1
            results.append({
                "campaign_id": scenario["campaign_id"],
                "expected": expected,
                "predicted": "error",
                "correct": False,
                "error": str(e),
            })

    eval_time = time.time() - start_time

    accuracy = correct / total if total > 0 else 0.0
    human_review_rate = human_review_triggered / total if total > 0 else 0.0
    avg_latency = total_latency / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "human_review_triggered": human_review_triggered,
        "human_review_rate": human_review_rate,
        "avg_latency_ms": avg_latency,
        "total_cost_usd": total_cost,
        "eval_time_seconds": eval_time,
        "results": results,
    }


def print_eval_summary(results: dict[str, Any]) -> None:
    """Print evaluation summary.

    Args:
        results: Results from run_eval
    """
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total scenarios:      {results['total']}")
    print(f"Correct predictions:  {results['correct']}")
    print(f"Accuracy:             {results['accuracy']:.2%}")
    print(f"Human review rate:    {results['human_review_rate']:.2%}")
    print(f"Avg latency:          {results['avg_latency_ms']:.0f}ms")
    print(f"Total cost:           ${results['total_cost_usd']:.6f}")
    print(f"Eval time:            {results['eval_time_seconds']:.1f}s")
    print("=" * 60)

    # Show failures
    failures = [r for r in results["results"] if not r.get("correct", False)]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures[:5]:
            error = f.get("error", "")
            error_str = f" [ERROR: {error}]" if error else ""
            print(f"  {f['campaign_id']}: expected={f['expected']}, got={f['predicted']}{error_str}")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")


def save_eval_results(results: dict[str, Any], output_path: Path | None = None) -> Path:
    """Save evaluation results to file.

    Args:
        results: Evaluation results
        output_path: Optional output path (auto-generated if None)

    Returns:
        Path to saved results file
    """
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"eval_results_{timestamp}.json")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run offline evaluation")
    parser.add_argument(
        "--scenarios",
        type=int,
        default=50,
        help="Number of scenarios to evaluate (default: 50)",
    )
    parser.add_argument(
        "--mock-accuracy",
        type=float,
        default=0.85,
        help="Mock provider accuracy (default: 0.85)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live providers (requires API keys)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    if args.live:
        print("Running LIVE evaluation with real API calls...")
        print("Make sure KIMI_API_KEY and/or MINIMAX_API_KEY are set")
        orchestrator = Orchestrator()
        results = run_eval(orchestrator, num_scenarios=args.scenarios, use_mock=False)
    else:
        print(f"Running MOCK evaluation (accuracy target: {args.mock_accuracy:.0%})...")
        mock = MockProvider(accuracy=args.mock_accuracy)
        orchestrator = Orchestrator()
        # Note: This is a simplified version - in production would properly inject mock
        results = run_eval(None, num_scenarios=args.scenarios, use_mock=True)

    print_eval_summary(results)

    if args.output:
        save_eval_results(results, args.output)
