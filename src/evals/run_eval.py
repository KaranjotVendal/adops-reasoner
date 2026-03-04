"""Offline evaluation harness for campaign analyst."""

import json
from pathlib import Path

from src.data.scenario_generator import generate_dataset
from src.domain.models import CampaignMetrics


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


def run_eval(analyzer, validator=None) -> dict:
    """Run offline evaluation on synthetic dataset.

    Args:
        analyzer: AnalyzerAgent instance
        validator: ValidatorAgent instance (optional)

    Returns:
        Evaluation results dictionary
    """
    # Generate or load dataset
    data_dir = Path(__file__).parent.parent.parent / "data"
    scenarios_path = data_dir / "scenarios_v1.jsonl"

    if scenarios_path.exists():
        scenarios = load_scenarios(scenarios_path)
    else:
        scenarios = generate_dataset(num_scenarios=50)

    results = []
    correct = 0
    total = 0
    human_review_triggered = 0

    for scenario in scenarios:
        metrics = CampaignMetrics(**scenario["metrics"])
        expected = scenario["expected_action"]

        # Run analysis
        analysis = analyzer.analyze(metrics)

        # Run validation if provided
        if validator:
            analysis_result = {
                "recommended_action": analysis.recommended_action.value,
                "reasoning": analysis.reasoning,
                "confidence": analysis.confidence.model_dump(),
                "key_factors": analysis.key_factors,
            }
            validation = validator.validate(
                campaign_id=metrics.campaign_id,
                analysis_result=analysis_result,
                original_metrics=metrics.model_dump(),
            )
            if validation.requires_human_review:
                human_review_triggered += 1

        predicted = analysis.recommended_action.value

        # Count correct
        if predicted == expected:
            correct += 1

        total += 1
        results.append({
            "campaign_id": scenario["campaign_id"],
            "expected": expected,
            "predicted": predicted,
            "correct": predicted == expected,
        })

    accuracy = correct / total if total > 0 else 0.0
    human_review_rate = human_review_triggered / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "human_review_triggered": human_review_triggered,
        "human_review_rate": human_review_rate,
        "results": results,
    }


def print_eval_summary(results: dict) -> None:
    """Print evaluation summary.

    Args:
        results: Results from run_eval
    """
    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total scenarios: {results['total']}")
    print(f"Correct predictions: {results['correct']}")
    print(f"Accuracy: {results['accuracy']:.2%}")
    print(f"Human review triggered: {results['human_review_triggered']}")
    print(f"Human review rate: {results['human_review_rate']:.2%}")
    print("=" * 50)

    # Show failures
    failures = [r for r in results["results"] if not r["correct"]]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures[:5]:
            print(f"  {f['campaign_id']}: expected={f['expected']}, got={f['predicted']}")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")


if __name__ == "__main__":
    # Quick demo without actual LLM (mock-based)

    from src.agents.providers.base import LLMResponse

    # Create mock provider that returns maintain
    class MockProvider:
        def chatCompletion(self, messages, **kwargs):
            return LLMResponse(
                content='{"recommended_action": "maintain", "reasoning": "mock", "confidence": {"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8}, "key_factors": ["test"]}',
                raw_response={},
            )

    from src.agents.analyzer import AnalyzerAgent
    from src.agents.validator import ValidatorAgent

    analyzer = AnalyzerAgent(MockProvider())
    validator = ValidatorAgent()

    print("Running offline evaluation (mock LLM)...")
    results = run_eval(analyzer, validator)
    print_eval_summary(results)
