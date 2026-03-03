"""Unit tests for domain models."""

import pytest
from pydantic import ValidationError

from src.domain.models import (
    CampaignMetrics,
    CampaignAnalysis,
    AnalysisConfidence,
    RecommendedAction,
    AnalyzeRequest,
    AnalyzeResponse,
    ValidationResult,
)


class TestCampaignMetrics:
    """Tests for CampaignMetrics model."""

    def test_valid_metrics(self):
        """Test creating valid campaign metrics."""
        metrics = CampaignMetrics(
            campaign_id="test_001",
            cpa_3d_trend=1.5,
            ctr_current=0.03,
            ctr_7d_avg=0.035,
            audience_saturation=0.6,
            creative_age_days=10,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )
        assert metrics.campaign_id == "test_001"
        assert metrics.cpa_3d_trend == 1.5

    def test_invalid_ctr_range(self):
        """Test that CTR outside 0-1 range fails validation."""
        with pytest.raises(ValidationError):
            CampaignMetrics(
                campaign_id="test_002",
                cpa_3d_trend=1.5,
                ctr_current=1.5,  # Invalid: > 1.0
                ctr_7d_avg=0.035,
                audience_saturation=0.6,
                creative_age_days=10,
                conversion_volume_7d=50,
                spend_7d=500.0,
            )

    def test_negative_cpa_trend(self):
        """Test that lower CPA trend values are allowed (improvement)."""
        metrics = CampaignMetrics(
            campaign_id="test_003",
            cpa_3d_trend=0.5,
            ctr_current=0.03,
            ctr_7d_avg=0.035,
            audience_saturation=0.6,
            creative_age_days=10,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )
        assert metrics.cpa_3d_trend == 0.5

    def test_invalid_audience_saturation_range(self):
        """Test that audience saturation outside 0-1 fails validation."""
        with pytest.raises(ValidationError):
            CampaignMetrics(
                campaign_id="test_004",
                cpa_3d_trend=1.1,
                ctr_current=0.03,
                ctr_7d_avg=0.035,
                audience_saturation=1.2,
                creative_age_days=10,
                conversion_volume_7d=50,
                spend_7d=500.0,
            )

    def test_negative_spend_fails(self):
        """Test that negative spend fails validation."""
        with pytest.raises(ValidationError):
            CampaignMetrics(
                campaign_id="test_005",
                cpa_3d_trend=1.1,
                ctr_current=0.03,
                ctr_7d_avg=0.035,
                audience_saturation=0.6,
                creative_age_days=10,
                conversion_volume_7d=50,
                spend_7d=-1.0,
            )


class TestRecommendedAction:
    """Tests for RecommendedAction enum."""

    def test_all_actions_defined(self):
        """Test all expected actions are available."""
        expected = {
            "maintain",
            "pause_campaign",
            "creative_refresh",
            "audience_expansion",
            "bid_adjustment",
            "requires_human_review",
        }
        actual = {action.value for action in RecommendedAction}
        assert expected == actual


class TestAnalysisConfidence:
    """Tests for AnalysisConfidence model."""

    def test_valid_confidence(self):
        """Test creating valid confidence scores."""
        confidence = AnalysisConfidence(
            overall_score=0.85,
            data_quality=0.9,
            recommendation_strength=0.8,
        )
        assert confidence.overall_score == 0.85

    def test_confidence_out_of_range(self):
        """Test that confidence > 1.0 fails."""
        with pytest.raises(ValidationError):
            AnalysisConfidence(
                overall_score=1.5,
                data_quality=0.9,
                recommendation_strength=0.8,
            )

    def test_confidence_negative(self):
        """Test that negative confidence fails."""
        with pytest.raises(ValidationError):
            AnalysisConfidence(
                overall_score=-0.1,
                data_quality=0.9,
                recommendation_strength=0.8,
            )


class TestAnalyzeRequest:
    """Tests for AnalyzeRequest model."""

    def test_valid_request(self):
        """Test creating valid analyze request."""
        request = AnalyzeRequest(
            campaign_metrics=CampaignMetrics(
                campaign_id="test_001",
                cpa_3d_trend=1.5,
                ctr_current=0.03,
                ctr_7d_avg=0.035,
                audience_saturation=0.6,
                creative_age_days=10,
                conversion_volume_7d=50,
                spend_7d=500.0,
            )
        )
        assert request.campaign_metrics.campaign_id == "test_001"


class TestAnalyzeResponse:
    """Tests for AnalyzeResponse model."""

    def test_valid_response(self):
        """Test creating valid analyze response."""
        response = AnalyzeResponse(
            campaign_id="test_001",
            recommended_action=RecommendedAction.MAINTAIN,
            requires_human_review=False,
            reasoning="All metrics within normal ranges",
            confidence=AnalysisConfidence(
                overall_score=0.85,
                data_quality=0.9,
                recommendation_strength=0.8,
            ),
            key_factors=["Stable CPA", "Good CTR"],
        )
        assert response.recommended_action == RecommendedAction.MAINTAIN
        assert response.requires_human_review is False

    def test_response_with_validation_notes(self):
        """Test response includes validation notes."""
        response = AnalyzeResponse(
            campaign_id="test_002",
            recommended_action=RecommendedAction.BID_ADJUSTMENT,
            requires_human_review=False,
            reasoning="Moderate CPA rise detected",
            confidence=AnalysisConfidence(
                overall_score=0.7,
                data_quality=0.8,
                recommendation_strength=0.65,
            ),
            key_factors=["CPA trending up"],
            validation_notes="Passed all validation checks",
        )
        assert response.validation_notes == "Passed all validation checks"


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result(self):
        """Test creating valid validation result."""
        result = ValidationResult(
            is_valid=True,
            requires_human_review=False,
            conflict_detected=False,
            final_recommendation=RecommendedAction.MAINTAIN,
        )
        assert result.is_valid is True

    def test_conflict_result(self):
        """Test validation result with conflict."""
        result = ValidationResult(
            is_valid=True,
            requires_human_review=True,
            conflict_detected=True,
            conflict_details="Analyzer and validator disagree on action",
            final_recommendation=RecommendedAction.REQUIRES_HUMAN_REVIEW,
        )
        assert result.conflict_detected is True
        assert result.requires_human_review is True
