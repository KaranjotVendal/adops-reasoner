"""Synthetic scenario generator for campaign data."""

import json
import random
from pathlib import Path
from typing import Any

from ..domain.models import CampaignMetrics, RecommendedAction


# Deterministic labeling rules based on campaign metrics
def label_campaign(metrics: CampaignMetrics) -> RecommendedAction:
    """Apply deterministic labeling rules to a campaign.

    Rules (in order):
    1. pause_campaign: extreme CPA rise (>2.0x) AND low conversion volume
    2. creative_refresh: strong CTR drop (>30% decline) AND stale creative (>14 days)
    3. audience_expansion: high saturation (>0.8) AND stable/good CPA (<1.5x)
    4. bid_adjustment: CPA rise (1.3-2.0x) but CTR stable and creative not stale
    5. maintain: otherwise (healthy metrics)
    """
    cpa_trend = metrics.cpa_3d_trend
    ctr_ratio = metrics.ctr_current / max(metrics.ctr_7d_avg, 0.001)
    saturation = metrics.audience_saturation
    creative_age = metrics.creative_age_days
    conv_volume = metrics.conversion_volume_7d

    # Rule 1: pause_campaign - extreme CPA rise + low volume
    if cpa_trend > 2.0 and conv_volume < 10:
        return RecommendedAction.PAUSE_CAMPAIGN

    # Rule 2: creative_refresh - CTR drop + stale creative
    if ctr_ratio < 0.7 and creative_age > 14:
        return RecommendedAction.CREATIVE_REFRESH

    # Rule 3: audience_expansion - high saturation + stable CPA
    if saturation > 0.8 and cpa_trend < 1.5:
        return RecommendedAction.AUDIENCE_EXPANSION

    # Rule 4: bid_adjustment - moderate CPA rise without creative issues
    if 1.3 <= cpa_trend <= 2.0 and creative_age <= 14:
        return RecommendedAction.BID_ADJUSTMENT

    # Rule 5: maintain - healthy or unclear metrics
    return RecommendedAction.MAINTAIN


def generate_scenario(campaign_id: str, seed: int | None = None) -> dict[str, Any]:
    """Generate a single synthetic campaign scenario.

    Args:
        campaign_id: Unique identifier for this scenario
        seed: Random seed for reproducibility

    Returns:
        Dictionary with campaign metrics and expected action
    """
    if seed is not None:
        random.seed(seed)

    # Generate varied but realistic metrics
    cpa_3d_trend = round(random.uniform(0.8, 2.5), 2)
    ctr_current = round(random.uniform(0.01, 0.08), 4)
    ctr_7d_avg = round(ctr_current * random.uniform(0.9, 1.2), 4)
    audience_saturation = round(random.uniform(0.3, 0.95), 2)
    creative_age_days = random.randint(3, 60)
    conversion_volume_7d = random.randint(5, 500)
    spend_7d = round(random.uniform(100, 10000), 2)

    metrics = CampaignMetrics(
        campaign_id=campaign_id,
        cpa_3d_trend=cpa_3d_trend,
        ctr_current=ctr_current,
        ctr_7d_avg=ctr_7d_avg,
        audience_saturation=audience_saturation,
        creative_age_days=creative_age_days,
        conversion_volume_7d=conversion_volume_7d,
        spend_7d=spend_7d,
    )

    expected_action = label_campaign(metrics)

    return {
        "campaign_id": campaign_id,
        "metrics": metrics.model_dump(),
        "expected_action": expected_action.value,
        "notes": _generate_notes(metrics, expected_action),
    }


def _generate_notes(metrics: CampaignMetrics, action: RecommendedAction) -> str:
    """Generate brief explanation notes for the scenario."""
    notes = []
    safe_ctr_7d_avg = max(metrics.ctr_7d_avg, 0.001)

    if metrics.cpa_3d_trend > 2.0:
        notes.append(f"CPA trending up {metrics.cpa_3d_trend:.1f}x")
    if metrics.ctr_current / safe_ctr_7d_avg < 0.7:
        notes.append(f"CTR dropped {((1 - metrics.ctr_current / safe_ctr_7d_avg) * 100):.0f}%")
    if metrics.audience_saturation > 0.8:
        notes.append(f"High audience saturation {metrics.audience_saturation:.0%}")
    if metrics.creative_age_days > 14:
        notes.append(f"Creative is {metrics.creative_age_days} days old")

    if not notes:
        notes.append("Metrics within normal ranges")

    return "; ".join(notes)


# Targeted generators for each action type
def generate_for_pause_campaign(campaign_id: str, seed: int) -> dict:
    """Generate scenario that triggers pause_campaign."""
    random.seed(seed)
    return {
        "campaign_id": campaign_id,
        "metrics": {
            "campaign_id": campaign_id,
            "cpa_3d_trend": round(random.uniform(2.1, 3.5), 2),
            "ctr_current": round(random.uniform(0.005, 0.02), 4),
            "ctr_7d_avg": round(random.uniform(0.02, 0.05), 4),
            "audience_saturation": round(random.uniform(0.4, 0.9), 2),
            "creative_age_days": random.randint(5, 60),
            "conversion_volume_7d": random.randint(1, 9),
            "spend_7d": round(random.uniform(500, 8000), 2),
        },
        "expected_action": "pause_campaign",
        "notes": "Extreme CPA rise with low conversion volume",
    }


def generate_for_creative_refresh(campaign_id: str, seed: int) -> dict:
    """Generate scenario that triggers creative_refresh."""
    random.seed(seed)
    # Need CTR drop >30% and creative age >14
    ctr_current = round(random.uniform(0.01, 0.03), 4)
    ctr_7d_avg = round(ctr_current / random.uniform(0.5, 0.7), 4)  # 30-50% higher
    return {
        "campaign_id": campaign_id,
        "metrics": {
            "campaign_id": campaign_id,
            "cpa_3d_trend": round(random.uniform(0.9, 1.4), 2),
            "ctr_current": ctr_current,
            "ctr_7d_avg": ctr_7d_avg,
            "audience_saturation": round(random.uniform(0.3, 0.8), 2),
            "creative_age_days": random.randint(15, 60),
            "conversion_volume_7d": random.randint(20, 200),
            "spend_7d": round(random.uniform(300, 5000), 2),
        },
        "expected_action": "creative_refresh",
        "notes": "CTR dropped significantly with stale creative",
    }


def generate_for_audience_expansion(campaign_id: str, seed: int) -> dict:
    """Generate scenario that triggers audience_expansion."""
    random.seed(seed)
    # Need: saturation > 0.8 AND cpa_trend < 1.5
    # Must avoid: ctr_ratio < 0.7 AND creative_age > 14
    saturation = round(random.uniform(0.81, 0.98), 2)
    cpa_trend = round(random.uniform(0.8, 1.4), 2)
    # Ensure ctr_ratio >= 0.7 OR creative_age <= 14 to avoid creative_refresh
    ctr_current = round(random.uniform(0.03, 0.06), 4)
    ctr_7d_avg = round(ctr_current / random.uniform(0.7, 1.0), 4)  # Ensure ratio >= 0.7
    creative_age = random.randint(3, 14)  # <=14 to avoid creative_refresh
    
    return {
        "campaign_id": campaign_id,
        "metrics": {
            "campaign_id": campaign_id,
            "cpa_3d_trend": cpa_trend,
            "ctr_current": ctr_current,
            "ctr_7d_avg": ctr_7d_avg,
            "audience_saturation": saturation,
            "creative_age_days": creative_age,
            "conversion_volume_7d": random.randint(50, 300),
            "spend_7d": round(random.uniform(500, 8000), 2),
        },
        "expected_action": "audience_expansion",
        "notes": "High audience saturation with stable CPA",
    }


def generate_for_bid_adjustment(campaign_id: str, seed: int) -> dict:
    """Generate scenario that triggers bid_adjustment."""
    random.seed(seed)
    return {
        "campaign_id": campaign_id,
        "metrics": {
            "campaign_id": campaign_id,
            "cpa_3d_trend": round(random.uniform(1.31, 1.99), 2),
            "ctr_current": round(random.uniform(0.02, 0.05), 4),
            "ctr_7d_avg": round(random.uniform(0.02, 0.05), 4),
            "audience_saturation": round(random.uniform(0.3, 0.7), 2),
            "creative_age_days": random.randint(3, 14),
            "conversion_volume_7d": random.randint(20, 200),
            "spend_7d": round(random.uniform(300, 5000), 2),
        },
        "expected_action": "bid_adjustment",
        "notes": "Moderate CPA rise without creative issues",
    }


def generate_for_maintain(campaign_id: str, seed: int) -> dict:
    """Generate scenario that triggers maintain."""
    random.seed(seed)
    # Need: cpa_trend <1.3 OR creative_age <=14, but NOT both triggers for other rules
    # Must avoid: ctr_ratio < 0.7 AND creative_age > 14
    # Must avoid: saturation > 0.8 AND cpa_trend < 1.5
    # Must avoid: 1.3 <= cpa_trend <= 2.0 AND creative_age <= 14
    cpa_trend = round(random.uniform(0.85, 1.29), 2)
    ctr_current = round(random.uniform(0.03, 0.06), 4)
    ctr_7d_avg = round(ctr_current * random.uniform(1.0, 1.1), 4)  # slight variation but not big drop
    creative_age = random.randint(3, 13)  # <=14 to avoid creative_refresh
    saturation = round(random.uniform(0.3, 0.75), 2)  # <0.8 to avoid audience_expansion
    
    return {
        "campaign_id": campaign_id,
        "metrics": {
            "campaign_id": campaign_id,
            "cpa_3d_trend": cpa_trend,
            "ctr_current": ctr_current,
            "ctr_7d_avg": ctr_7d_avg,
            "audience_saturation": saturation,
            "creative_age_days": creative_age,
            "conversion_volume_7d": random.randint(30, 300),
            "spend_7d": round(random.uniform(300, 6000), 2),
        },
        "expected_action": "maintain",
        "notes": "Healthy metrics within normal ranges",
    }


# Map actions to generators
ACTION_GENERATORS = {
    RecommendedAction.PAUSE_CAMPAIGN: generate_for_pause_campaign,
    RecommendedAction.CREATIVE_REFRESH: generate_for_creative_refresh,
    RecommendedAction.AUDIENCE_EXPANSION: generate_for_audience_expansion,
    RecommendedAction.BID_ADJUSTMENT: generate_for_bid_adjustment,
    RecommendedAction.MAINTAIN: generate_for_maintain,
}


def generate_dataset(num_scenarios: int = 50, output_path: Path | None = None) -> list[dict]:
    """Generate a balanced dataset of campaign scenarios.

    The returned list size is exactly ``num_scenarios`` (including edge cases).

    Args:
        num_scenarios: Exact number of scenarios to generate
        output_path: Optional path to write JSONL file

    Returns:
        List of scenario dictionaries
    """
    scenarios = []

    # Ensure balanced distribution across actions
    actions = list(RecommendedAction)
    # Remove REQUIRES_HUMAN_REVIEW from generation (it's a validator output, not a labeled action)
    actions_to_generate = [a for a in actions if a != RecommendedAction.REQUIRES_HUMAN_REVIEW]

    edge_cases = [
        {
            "campaign_id": "edge_001",
            "metrics": {
                "campaign_id": "edge_001",
                "cpa_3d_trend": 3.5,
                "ctr_current": 0.005,
                "ctr_7d_avg": 0.04,
                "audience_saturation": 0.95,
                "creative_age_days": 45,
                "conversion_volume_7d": 3,
                "spend_7d": 5000.0,
            },
            "expected_action": "pause_campaign",
            "notes": "Extreme case: very high CPA, very low CTR, low volume",
        },
        {
            "campaign_id": "edge_002",
            "metrics": {
                "campaign_id": "edge_002",
                "cpa_3d_trend": 0.95,
                "ctr_current": 0.075,
                "ctr_7d_avg": 0.072,
                "audience_saturation": 0.35,
                "creative_age_days": 5,
                "conversion_volume_7d": 250,
                "spend_7d": 1500.0,
            },
            "expected_action": "maintain",
            "notes": "Healthy campaign: stable CPA, good CTR, low saturation",
        },
    ]

    edge_case_count = min(len(edge_cases), max(num_scenarios, 0))
    base_scenarios = max(num_scenarios - edge_case_count, 0)

    # Spread remaining scenarios approximately evenly across action types
    scenarios_per_action = base_scenarios // len(actions_to_generate)
    remainder = base_scenarios % len(actions_to_generate)

    campaign_counter = 1

    for idx, action in enumerate(actions_to_generate):
        generator = ACTION_GENERATORS[action]
        target_count = scenarios_per_action + (1 if idx < remainder else 0)

        for _ in range(target_count):
            scenario = generator(f"camp_{campaign_counter:04d}", seed=campaign_counter)
            # Validate the generated scenario produces expected action
            metrics = CampaignMetrics(**scenario["metrics"])
            actual_action = label_campaign(metrics)
            assert actual_action == action, f"Generated {actual_action}, expected {action}"
            scenarios.append(scenario)
            campaign_counter += 1

    # Add edge cases up to requested total
    scenarios.extend(edge_cases[:edge_case_count])

    # Final safeguard to exact requested size
    scenarios = scenarios[:num_scenarios]

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for scenario in scenarios:
                f.write(json.dumps(scenario) + "\n")

    return scenarios


if __name__ == "__main__":
    # Generate default dataset
    data_dir = Path(__file__).parent.parent.parent / "data"
    scenarios = generate_dataset(num_scenarios=50, output_path=data_dir / "scenarios_v1.jsonl")
    print(f"Generated {len(scenarios)} scenarios -> {data_dir / 'scenarios_v1.jsonl'}")
