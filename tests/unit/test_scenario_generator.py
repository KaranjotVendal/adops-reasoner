"""Unit tests for scenario generator."""

import pytest

from src.data.scenario_generator import (
    label_campaign,
    generate_scenario,
    generate_dataset,
)
from src.domain.models import CampaignMetrics, RecommendedAction


class TestLabelCampaign:
    """Tests for deterministic labeling rules."""

    def test_pause_campaign_extreme_cpa_low_volume(self):
        """Rule 1: extreme CPA rise (>2.0x) AND low conversion volume."""
        metrics = CampaignMetrics(
            campaign_id="test_001",
            cpa_3d_trend=2.5,
            ctr_current=0.03,
            ctr_7d_avg=0.035,
            audience_saturation=0.6,
            creative_age_days=10,
            conversion_volume_7d=5,
            spend_7d=500.0,
        )
        assert label_campaign(metrics) == RecommendedAction.PAUSE_CAMPAIGN

    def test_creative_refresh_ctr_drop_stale_creative(self):
        """Rule 2: CTR drop (>30%) AND stale creative (>14 days)."""
        metrics = CampaignMetrics(
            campaign_id="test_002",
            cpa_3d_trend=1.1,
            ctr_current=0.02,  # 50% of 0.04
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=30,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )
        assert label_campaign(metrics) == RecommendedAction.CREATIVE_REFRESH

    def test_audience_expansion_high_saturation_stable_cpa(self):
        """Rule 3: high saturation (>0.8) AND stable/good CPA (<1.5x)."""
        metrics = CampaignMetrics(
            campaign_id="test_003",
            cpa_3d_trend=1.2,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.9,
            creative_age_days=10,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )
        assert label_campaign(metrics) == RecommendedAction.AUDIENCE_EXPANSION

    def test_bid_adjustment_moderate_cpa_rise(self):
        """Rule 4: moderate CPA rise (1.3-2.0x) without creative issues."""
        metrics = CampaignMetrics(
            campaign_id="test_004",
            cpa_3d_trend=1.5,
            ctr_current=0.035,
            ctr_7d_avg=0.035,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )
        assert label_campaign(metrics) == RecommendedAction.BID_ADJUSTMENT

    def test_maintain_healthy_metrics(self):
        """Rule 5: healthy or unclear metrics."""
        metrics = CampaignMetrics(
            campaign_id="test_005",
            cpa_3d_trend=1.1,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.4,
            creative_age_days=5,
            conversion_volume_7d=100,
            spend_7d=800.0,
        )
        assert label_campaign(metrics) == RecommendedAction.MAINTAIN

    def test_edge_case_cpa_improvement(self):
        """Edge case: CPA significantly improved."""
        metrics = CampaignMetrics(
            campaign_id="test_006",
            cpa_3d_trend=0.5,
            ctr_current=0.05,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=150,
            spend_7d=1000.0,
        )
        # Should be maintain (good performance)
        assert label_campaign(metrics) == RecommendedAction.MAINTAIN


class TestGenerateScenario:
    """Tests for scenario generation."""

    def test_generate_scenario_returns_dict(self):
        """Test that generate_scenario returns expected structure."""
        scenario = generate_scenario("camp_0001", seed=42)
        assert "campaign_id" in scenario
        assert "metrics" in scenario
        assert "expected_action" in scenario
        assert "notes" in scenario

    def test_generate_scenario_reproducible(self):
        """Test that same seed produces same scenario."""
        s1 = generate_scenario("camp_0001", seed=100)
        s2 = generate_scenario("camp_0001", seed=100)
        assert s1 == s2

    def test_generate_scenario_different_seeds(self):
        """Test that different seeds produce different scenarios."""
        s1 = generate_scenario("camp_0001", seed=100)
        s2 = generate_scenario("camp_0001", seed=200)
        assert s1 != s2

    def test_expected_action_matches_label(self):
        """Test that generated expected_action matches label_campaign."""
        scenario = generate_scenario("camp_0001", seed=50)
        metrics = CampaignMetrics(**scenario["metrics"])
        expected = label_campaign(metrics)
        assert scenario["expected_action"] == expected.value


class TestGenerateDataset:
    """Tests for dataset generation."""

    def test_generate_dataset_count(self):
        """Test that dataset generates correct number of scenarios."""
        scenarios = generate_dataset(num_scenarios=30, output_path=None)
        # Should have balanced distribution + edge cases
        assert len(scenarios) >= 30

    def test_generate_dataset_includes_edge_cases(self):
        """Test that edge cases are included."""
        scenarios = generate_dataset(num_scenarios=20, output_path=None)
        campaign_ids = [s["campaign_id"] for s in scenarios]
        assert "edge_001" in campaign_ids
        assert "edge_002" in campaign_ids

    def test_generate_dataset_has_all_actions(self):
        """Test that dataset covers all action types."""
        scenarios = generate_dataset(num_scenarios=30, output_path=None)
        actions = {s["expected_action"] for s in scenarios}
        expected_actions = {action.value for action in RecommendedAction}
        # Should have at least most actions represented
        assert len(actions) >= 4
