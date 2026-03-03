"""Unit tests for validator agent."""

import pytest

from src.agents.validator import ValidatorAgent, CONFLICT_THRESHOLD, CONFIDENCE_THRESHOLD
from src.domain.models import (
    AnalysisConfidence,
    CampaignAnalysis,
    CampaignMetrics,
    RecommendedAction,
    ValidationResult,
)


class TestValidatorAgent:
    """Tests for ValidatorAgent."""

    def test_validate_approves_high_confidence(self):
        """Test that high confidence recommendation is approved."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_001",
            recommended_action=RecommendedAction.MAINTAIN,
            reasoning="All metrics stable",
            confidence=AnalysisConfidence(
                overall_score=0.9,
                data_quality=0.9,
                recommendation_strength=0.85,
            ),
            key_factors=["Stable metrics"],
        )

        metrics = CampaignMetrics(
            campaign_id="test_001",
            cpa_3d_trend=1.1,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.is_valid is True
        assert result.requires_human_review is False
        assert result.conflict_detected is False
        assert result.final_recommendation == RecommendedAction.MAINTAIN

    def test_validate_requires_human_review_low_confidence(self):
        """Test that low confidence triggers human review."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_002",
            recommended_action=RecommendedAction.BID_ADJUSTMENT,
            reasoning="Unclear metrics",
            confidence=AnalysisConfidence(
                overall_score=0.3,  # Below threshold
                data_quality=0.8,
                recommendation_strength=0.3,
            ),
            key_factors=[],
        )

        metrics = CampaignMetrics(
            campaign_id="test_002",
            cpa_3d_trend=1.5,
            ctr_current=0.03,
            ctr_7d_avg=0.03,
            audience_saturation=0.6,
            creative_age_days=10,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.is_valid is True
        assert result.requires_human_review is True
        assert result.final_recommendation == RecommendedAction.REQUIRES_HUMAN_REVIEW

    def test_validate_requires_human_review_low_data_quality(self):
        """Test that low data quality triggers human review."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_003",
            recommended_action=RecommendedAction.MAINTAIN,
            reasoning="Based on limited data",
            confidence=AnalysisConfidence(
                overall_score=0.7,
                data_quality=0.2,  # Below conflict threshold
                recommendation_strength=0.7,
            ),
            key_factors=[],
        )

        metrics = CampaignMetrics(
            campaign_id="test_003",
            cpa_3d_trend=1.1,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.requires_human_review is True
        assert "data quality" in result.conflict_details.lower()

    def test_validate_detects_conflict_pause_vs_improving_cpa(self):
        """Test conflict: pause_campaign but CPA improving and volume healthy."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_004",
            recommended_action=RecommendedAction.PAUSE_CAMPAIGN,
            reasoning="High CPA",
            confidence=AnalysisConfidence(
                overall_score=0.8,
                data_quality=0.9,
                recommendation_strength=0.8,
            ),
            key_factors=["CPA high"],
        )

        # CPA improving (trend < 1.0) and high volume
        metrics = CampaignMetrics(
            campaign_id="test_004",
            cpa_3d_trend=0.8,  # Improving
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=100,  # High
            spend_7d=1000.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.conflict_detected is True
        assert result.requires_human_review is True

    def test_validate_detects_conflict_maintain_vs_extreme_cpa(self):
        """Test conflict: maintain but extreme CPA rise."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_005",
            recommended_action=RecommendedAction.MAINTAIN,
            reasoning="Everything looks fine",
            confidence=AnalysisConfidence(
                overall_score=0.8,
                data_quality=0.9,
                recommendation_strength=0.8,
            ),
            key_factors=["Looking good"],
        )

        # Extreme CPA rise
        metrics = CampaignMetrics(
            campaign_id="test_005",
            cpa_3d_trend=3.5,  # Tripled
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.conflict_detected is True
        assert "CPA has tripled" in result.conflict_details

    def test_validate_passes_conflict_check(self):
        """Test that valid recommendations without conflicts pass."""
        validator = ValidatorAgent()

        analysis = CampaignAnalysis(
            campaign_id="test_006",
            recommended_action=RecommendedAction.CREATIVE_REFRESH,
            reasoning="CTR dropping with old creative",
            confidence=AnalysisConfidence(
                overall_score=0.85,
                data_quality=0.9,
                recommendation_strength=0.8,
            ),
            key_factors=["CTR down", "Old creative"],
        )

        # Valid: CTR drop + old creative
        metrics = CampaignMetrics(
            campaign_id="test_006",
            cpa_3d_trend=1.1,
            ctr_current=0.02,
            ctr_7d_avg=0.04,  # 50% drop
            audience_saturation=0.5,
            creative_age_days=30,  # Old
            conversion_volume_7d=50,
            spend_7d=500.0,
        )

        result = validator.validate(analysis, metrics)

        assert result.is_valid is True
        assert result.requires_human_review is False
        assert result.conflict_detected is False
        assert result.final_recommendation == RecommendedAction.CREATIVE_REFRESH


class TestValidatorThresholds:
    """Tests for validator threshold constants."""

    def test_confidence_threshold_value(self):
        """Test confidence threshold is set correctly."""
        assert CONFIDENCE_THRESHOLD == 0.5

    def test_conflict_threshold_value(self):
        """Test conflict threshold is set correctly."""
        assert CONFLICT_THRESHOLD == 0.3
