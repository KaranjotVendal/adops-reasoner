"""Demo script for running campaign analysis with new architecture."""

import json
import os
from pathlib import Path

from src.agents import Orchestrator
from src.data.scenario_generator import generate_scenario
from src.domain.models import CampaignMetrics


def create_orchestrator():
    """Create orchestrator with providers from environment."""
    return Orchestrator()


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

    # Check for API keys
    kimi_key = os.environ.get("KIMI_API_KEY")
    minimax_key = os.environ.get("MINIMAX_API_KEY")

    if not kimi_key and not minimax_key:
        print("\n(Requires KIMI_API_KEY or MINIMAX_API_KEY to run live)")
        print("Set one of: export KIMI_API_KEY=your_key")
        print("            export MINIMAX_API_KEY=your_key")
        return

    # Run with orchestrator
    print("\nRunning analysis...")
    orchestrator = create_orchestrator()

    metrics = CampaignMetrics(**scenario["metrics"])
    response = orchestrator.analyze(
        metrics=metrics,
        enable_validation=True,
        enable_thinking=False,
    )

    result = response.to_dict()
    print(f"\nRecommended Action: {result['recommended_action']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Confidence: {result['confidence']['overall_score']:.2f}")
    print(f"Validation: {result['validation']['decision'] if result['validation'] else 'N/A'}")
    print(f"\nMetadata:")
    print(f"  Models: {result['_metadata']['analyzer']['model']} / {result['_metadata']['validator']['model']}")
    print(f"  Latency: {result['_metadata']['total_latency_ms']:.0f}ms")
    print(f"  Cost: ${result['_metadata']['estimated_cost_usd']:.6f}")


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
        "validation": {
            "decision": "approve",
            "confidence": 0.92,
            "feedback": "Analysis aligns with metrics"
        },
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


def demo_model_switching():
    """Demo model switching capabilities."""
    print("\n" + "=" * 50)
    print("DEMO: Model Switching")
    print("=" * 50)

    from src.providers import get_provider, get_default_analyzer_model, get_default_validator_model

    print("\nAvailable models:")
    from src.providers import MODEL_REGISTRY
    for model, (provider, _) in MODEL_REGISTRY.items():
        print(f"  - {model} ({provider})")

    print(f"\nDefault analyzer model: {get_default_analyzer_model()}")
    print(f"Default validator model: {get_default_validator_model()}")

    print("\nOverride per request:")
    print('  orchestrator = Orchestrator(analyzer_model="MiniMax-M2.5")')


if __name__ == "__main__":
    import sys

    demos = {
        "--scenario": demo_with_synthetic_scenario,
        "--payload": demo_with_sample_payload,
        "--dataset": demo_scenarios_from_dataset,
        "--models": demo_model_switching,
    }

    if len(sys.argv) > 1 and sys.argv[1] in demos:
        demos[sys.argv[1]]()
    else:
        print("Campaign Analyst Demo")
        print("\nUsage: python -m src.evals.demo [OPTION]")
        print("\nOptions:")
        print("  --scenario  Run live analysis on synthetic scenario")
        print("  --payload   Show sample API request/response")
        print("  --dataset   List scenarios from dataset")
        print("  --models    Show available models and configuration")
        print("\nExample:")
        print("  export KIMI_API_KEY=sk-...")
        print("  python -m src.evals.demo --scenario")
