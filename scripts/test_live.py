#!/usr/bin/env python3
"""Quick live test of Campaign Analyst system.

Usage:
    export KIMI_API_KEY=sk-...
    export MINIMAX_API_KEY=sk-...
    python scripts/test_live.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import Orchestrator
from src.domain.models import CampaignMetrics


def main():
    print("=" * 60)
    print("CAMPAIGN ANALYST - LIVE TEST")
    print("=" * 60)
    
    # Create orchestrator
    print("\n1. Initializing orchestrator...")
    orch = Orchestrator()
    print(f"   Analyzer: {orch.analyzer_model}")
    print(f"   Validator: {orch.validator_model}")
    
    # Create test campaign
    print("\n2. Creating test campaign...")
    metrics = CampaignMetrics(
        campaign_id="live_test_001",
        cpa_3d_trend=2.2,  # High CPA increase
        ctr_current=0.025,  # Declining
        ctr_7d_avg=0.04,
        audience_saturation=0.75,
        creative_age_days=18,
        conversion_volume_7d=25,
        spend_7d=3500.0,
    )
    print(f"   Campaign: {metrics.campaign_id}")
    print(f"   CPA Trend: {metrics.cpa_3d_trend}x")
    print(f"   CTR: {metrics.ctr_current:.2%} (was {metrics.ctr_7d_avg:.2%})")
    
    # Run analysis
    print("\n3. Running analysis (this may take 30-60 seconds)...")
    print("   Calling Analyzer (Kimi)...")
    
    try:
        response = orch.analyze(metrics, enable_validation=True)
        result = response.to_dict()
        
        print("\n4. Results:")
        print(f"   ✓ Action: {result['recommended_action'].upper()}")
        print(f"   ✓ Reasoning: {result['reasoning'][:80]}...")
        print(f"   ✓ Confidence: {result['confidence']['overall_score']:.0%}")
        
        if result['validation']:
            v = result['validation']
            print(f"   ✓ Validation: {v['decision'].upper()} ({v['confidence']:.0%})")
        
        print("\n5. Performance:")
        meta = result['_metadata']
        print(f"   Session: {meta['session_id']}")
        print(f"   Latency: {meta['total_latency_ms']:.0f}ms")
        print(f"   Cost: ${meta['estimated_cost_usd']:.6f}")
        
        print("\n" + "=" * 60)
        print("TEST PASSED ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
