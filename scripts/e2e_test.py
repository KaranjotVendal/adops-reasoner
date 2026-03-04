"""End-to-end test for Campaign Analyst system.

Tests the full multi-agent flow with real API calls.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import Orchestrator
from src.domain.models import CampaignMetrics, RecommendedAction


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, description: str):
    """Print a step indicator."""
    print(f"\n▶ Step {step_num}: {description}")
    print("-" * 50)


def test_simple_scenario():
    """Test with a simple scenario - CPA trend within normal range."""
    print_header("TEST 1: Simple Scenario (Maintain)")
    
    metrics = CampaignMetrics(
        campaign_id="test_maintain_001",
        cpa_3d_trend=1.1,  # Slight increase, still healthy
        ctr_current=0.04,
        ctr_7d_avg=0.04,
        audience_saturation=0.3,
        creative_age_days=5,
        conversion_volume_7d=100,
        spend_7d=1000.0,
    )
    
    print(f"\nInput Metrics:")
    print(f"  Campaign ID: {metrics.campaign_id}")
    print(f"  CPA Trend: {metrics.cpa_3d_trend}x (stable)")
    print(f"  CTR: {metrics.ctr_current:.2%}")
    print(f"  Creative Age: {metrics.creative_age_days} days (fresh)")
    print(f"  Conversions: {metrics.conversion_volume_7d}")
    
    run_analysis(metrics)


def test_pause_scenario():
    """Test with a critical scenario - extreme CPA increase."""
    print_header("TEST 2: Critical Scenario (Pause Campaign)")
    
    metrics = CampaignMetrics(
        campaign_id="test_pause_001",
        cpa_3d_trend=2.8,  # Extreme increase
        ctr_current=0.01,  # Very low CTR
        ctr_7d_avg=0.035,
        audience_saturation=0.85,
        creative_age_days=30,  # Old creative
        conversion_volume_7d=5,  # Very low volume
        spend_7d=5000.0,  # High spend with low results
    )
    
    print(f"\nInput Metrics:")
    print(f"  Campaign ID: {metrics.campaign_id}")
    print(f"  CPA Trend: {metrics.cpa_3d_trend}x (CRITICAL)")
    print(f"  CTR: {metrics.ctr_current:.2%} (very low)")
    print(f"  Creative Age: {metrics.creative_age_days} days (old)")
    print(f"  Conversions: {metrics.conversion_volume_7d} (very low)")
    print(f"  Spend: ${metrics.spend_7d:.2f}")
    
    run_analysis(metrics)


def test_creative_refresh_scenario():
    """Test with creative refresh scenario - declining CTR with old creative."""
    print_header("TEST 3: Creative Refresh Scenario")
    
    metrics = CampaignMetrics(
        campaign_id="test_creative_001",
        cpa_3d_trend=1.2,  # Slight increase
        ctr_current=0.025,  # Declining
        ctr_7d_avg=0.045,   # Was better
        audience_saturation=0.5,
        creative_age_days=22,  # Getting old
        conversion_volume_7d=80,
        spend_7d=1500.0,
    )
    
    print(f"\nInput Metrics:")
    print(f"  Campaign ID: {metrics.campaign_id}")
    print(f"  CTR Current: {metrics.ctr_current:.2%}")
    print(f"  CTR 7-day Avg: {metrics.ctr_7d_avg:.2%} (declining)")
    print(f"  Creative Age: {metrics.creative_age_days} days")
    print(f"  CPA Trend: {metrics.cpa_3d_trend}x")
    
    run_analysis(metrics)


def run_analysis(metrics: CampaignMetrics):
    """Run analysis with orchestrator and print results."""
    
    print_step(1, "Initialize Orchestrator")
    orchestrator = Orchestrator()
    print(f"  ✓ Orchestrator created")
    print(f"    Analyzer Model: {orchestrator.analyzer_model}")
    print(f"    Validator Model: {orchestrator.validator_model}")
    
    print_step(2, "Run Multi-Agent Analysis")
    print(f"  Sending to Analyzer ({orchestrator.analyzer_model})...")
    
    start_time = datetime.now()
    response = orchestrator.analyze(
        metrics=metrics,
        enable_validation=True,
        enable_thinking=True,  # Capture reasoning
    )
    elapsed = (datetime.now() - start_time).total_seconds()
    
    result = response.to_dict()
    
    print(f"  ✓ Analysis complete in {elapsed:.2f}s")
    
    print_step(3, "Analyzer Output")
    print(f"  Recommended Action: {result['recommended_action'].upper()}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Confidence: {result['confidence']['overall_score']:.2f}")
    print(f"  Key Factors:")
    for factor in result['key_factors']:
        print(f"    • {factor}")
    
    print_step(4, "Validator Output")
    if result['validation']:
        v = result['validation']
        print(f"  Decision: {v['decision'].upper()}")
        print(f"  Confidence: {v['confidence']:.2f}")
        print(f"  Feedback: {v['feedback']}")
    else:
        print("  (Validation disabled)")
    
    print_step(5, "Performance Metrics")
    meta = result['_metadata']
    print(f"  Session ID: {meta['session_id']}")
    print(f"  Trace ID: {meta['trace_id']}")
    print(f"\n  Analyzer Performance:")
    print(f"    Model: {meta['analyzer']['model']} ({meta['analyzer']['provider']})")
    print(f"    Latency: {meta['analyzer']['latency_ms']:.0f}ms")
    if meta['analyzer']['tokens']:
        t = meta['analyzer']['tokens']
        print(f"    Tokens: {t['input_tokens']} in / {t['output_tokens']} out")
    if meta['analyzer']['cost']:
        print(f"    Cost: ${meta['analyzer']['cost']['total_cost']:.6f}")
    if meta['analyzer'].get('thinking'):
        thinking = meta['analyzer']['thinking']
        print(f"    Thinking: {thinking[:200]}..." if len(thinking) > 200 else f"    Thinking: {thinking}")
    
    print(f"\n  Validator Performance:")
    if meta['validator']:
        v = meta['validator']
        print(f"    Model: {v['model']} ({v['provider']})")
        print(f"    Latency: {v['latency_ms']:.0f}ms")
        if v.get('tokens'):
            print(f"    Tokens: {v['tokens']['input_tokens']} in / {v['tokens']['output_tokens']} out")
        if v.get('cost'):
            print(f"    Cost: ${v['cost']['total_cost']:.6f}")
    
    print(f"\n  Total:")
    print(f"    Latency: {meta['total_latency_ms']:.0f}ms")
    print(f"    Cost: ${meta['estimated_cost_usd']:.6f}")
    
    return result


def test_provider_switching():
    """Test switching between providers."""
    print_header("TEST 4: Provider Switching")
    
    metrics = CampaignMetrics(
        campaign_id="test_switch_001",
        cpa_3d_trend=1.5,
        ctr_current=0.03,
        ctr_7d_avg=0.035,
        audience_saturation=0.4,
        creative_age_days=10,
        conversion_volume_7d=75,
        spend_7d=1200.0,
    )
    
    configs = [
        ("k2p5", "k2p5"),
        ("k2p5", "MiniMax-M2.5"),
        ("MiniMax-M2.5", "MiniMax-M2.5"),
    ]
    
    for analyzer_model, validator_model in configs:
        print(f"\n--- Configuration: {analyzer_model} → {validator_model} ---")
        orchestrator = Orchestrator(
            analyzer_model=analyzer_model,
            validator_model=validator_model,
        )
        
        response = orchestrator.analyze(metrics, enable_validation=True)
        result = response.to_dict()
        
        print(f"  Action: {result['recommended_action']}")
        print(f"  Validation: {result['validation']['decision'] if result['validation'] else 'N/A'}")
        print(f"  Total Latency: {result['_metadata']['total_latency_ms']:.0f}ms")
        print(f"  Total Cost: ${result['_metadata']['estimated_cost_usd']:.6f}")


def main():
    """Run all tests."""
    print_header("CAMPAIGN ANALYST - END-TO-END TEST")
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nThis will make REAL API calls to Kimi and MiniMax.")
    print(f"Estimated cost: ~$0.01-0.05 per test")
    
    try:
        # Run tests
        test_simple_scenario()
        test_pause_scenario()
        test_creative_refresh_scenario()
        # test_provider_switching()  # Optional - takes longer
        
        print_header("ALL TESTS COMPLETED SUCCESSFULLY ✓")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
