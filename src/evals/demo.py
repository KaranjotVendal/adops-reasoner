"""Demo script for running campaign analysis."""

import json
from pathlib import Path

from src.agents.analyzer import AnalyzerAgent
from src.agents.orchestrator import CampaignOrchestrator
from src.agents.providers.minimax import MiniMaxProvider
from src.agents.validator import ValidatorAgent
from src.data.scenario_generator import generate_scenario


def create_orchestrator() -> CampaignOrchestrator:
    """Create orchestrator with MiniMax provider.

    Returns:
        Configured CampaignOrchestrator
    """
    provider = MiniMaxProvider()
    analyzer = AnalyzerAgent(provider)
    validator = ValidatorAgent()
    return CampaignOrchestrator(analyzer, validator)


def demo_with_synthetic_scenario():
    """Run demo with a single synthetic scenario."""
    print("\n" + "=" * 50)
    print("DEMO: Single Synthetic Scenario")
    print("=" * 50)

    # Generate a scenario
    scenario = generate_scenario("demo_001", seed=42)
    print(f"\nInput Campaign: {scenario['campaign_id']}")
    print(f"Expected Action: {scenario['expected_action']}")
    print(f"Notes: {scenario['notes']}")

    # Note: This would require actual API key
    print("\n(Requires MINIMAX_API_KEY to run live)")
    print("Run with: export MINIMAX_API_KEY=your_key")


def demo_with_sample_payload():
    """Show sample API payload."""
    print("\n" + "=" * 50)
    print("DEMO: Sample API Payload")
    print("=" * 50)

    sample = {
        "campaign_metrics": {
            "campaign_id": "camp_0001",
            "cpa_3d_trend": 2.5,
            "ctr_current": 0.01,
            "ctr_7d_avg": 0.04,
            "audience_saturation": 0.9,
            "creative_age_days": 30,
            "conversion_volume_7d": 5,
            "spend_7d": 5000.0,
        }
    }

    print("\nPOST /analyze")
    print(json.dumps(sample, indent=2))

    # Show expected response
    expected_response = {
        "campaign_id": "camp_0001",
        "recommended_action": "pause_campaign",
        "requires_human_review": True,
        "reasoning": "Extreme CPA rise with low conversion volume",
        "confidence": {
            "overall_score": 0.85,
            "data_quality": 0.9,
            "recommendation_strength": 0.8,
        },
        "key_factors": ["CPA up 2.5x", "Low conversion volume"],
        "validation_notes": "Passed all validation checks",
    }

    print("\nExpected Response:")
    print(json.dumps(expected_response, indent=2))


def demo_scenarios_from_dataset():
    """Load and display scenarios from dataset."""
    print("\n" + "=" * 50)
    print("DEMO: Scenarios from Dataset")
    print("=" * 50)

    data_dir = Path(__file__).parent.parent.parent / "data"
    dataset_path = data_dir / "scenarios_v1.jsonl"

    if not dataset_path.exists():
        print("Dataset not found. Run: python -m src.data.scenario_generator")
        return

    scenarios = []
    with open(dataset_path) as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            scenarios.append(json.loads(line))

    print(f"\nFirst {len(scenarios)} scenarios from {dataset_path}:")
    for s in scenarios:
        print(f"  {s['campaign_id']}: {s['expected_action']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scenario":
            demo_with_synthetic_scenario()
        elif sys.argv[1] == "--payload":
            demo_with_sample_payload()
        elif sys.argv[1] == "--dataset":
            demo_scenarios_from_dataset()
        else:
            print("Usage: python -m src.evals.demo [--scenario|--payload|--dataset]")
    else:
        demo_with_sample_payload()
