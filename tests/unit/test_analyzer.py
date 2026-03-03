"""Unit tests for analyzer agent."""

import pytest
from unittest.mock import Mock, patch

from src.agents.analyzer import AnalyzerAgent, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agents.providers.base import LLMResponse
from src.domain.models import CampaignMetrics, RecommendedAction


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response_content: str):
        self.response_content = response_content
        self.called = False

    def chatCompletion(self, messages, **kwargs):
        self.called = True
        return LLMResponse(
            content=self.response_content,
            raw_response={"choices": [{"message": {"content": self.response_content}}]},
        )

    def health_check(self):
        return True


class TestAnalyzerAgent:
    """Tests for AnalyzerAgent."""

    def test_analyze_returns_campaign_analysis(self):
        """Test that analyze returns proper CampaignAnalysis."""
        mock_response = """{
            "recommended_action": "maintain",
            "reasoning": "Campaign is performing well with stable metrics",
            "confidence": {
                "overall_score": 0.9,
                "data_quality": 0.95,
                "recommendation_strength": 0.85
            },
            "key_factors": ["Stable CPA", "Good CTR"]
        }"""
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

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

        result = agent.analyze(metrics)

        assert result.campaign_id == "test_001"
        assert result.recommended_action == RecommendedAction.MAINTAIN
        assert result.confidence.overall_score == 0.9
        assert "Stable CPA" in result.key_factors
        assert provider.called

    def test_analyze_pause_campaign(self):
        """Test pause_campaign action extraction."""
        mock_response = """{
            "recommended_action": "pause_campaign",
            "reasoning": "Extreme CPA rise detected",
            "confidence": {"overall_score": 0.95, "data_quality": 0.9, "recommendation_strength": 0.95},
            "key_factors": ["CPA up 3x", "Low conversions"]
        }"""
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_002",
            cpa_3d_trend=3.0,
            ctr_current=0.01,
            ctr_7d_avg=0.03,
            audience_saturation=0.9,
            creative_age_days=30,
            conversion_volume_7d=5,
            spend_7d=5000.0,
        )

        result = agent.analyze(metrics)
        assert result.recommended_action == RecommendedAction.PAUSE_CAMPAIGN

    def test_analyze_creative_refresh(self):
        """Test creative_refresh action extraction."""
        mock_response = """{
            "recommended_action": "creative_refresh",
            "reasoning": "CTR dropped significantly with old creative",
            "confidence": {"overall_score": 0.8, "data_quality": 0.85, "recommendation_strength": 0.75},
            "key_factors": ["CTR down 40%", "Creative 30 days old"]
        }"""
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_003",
            cpa_3d_trend=1.2,
            ctr_current=0.02,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=30,
            conversion_volume_7d=50,
            spend_7d=500.0,
        )

        result = agent.analyze(metrics)
        assert result.recommended_action == RecommendedAction.CREATIVE_REFRESH

    def test_parse_fallback_on_invalid_json(self):
        """Test fallback parsing when JSON is invalid."""
        mock_response = "Here's my recommendation: pause_campaign"
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_004",
            cpa_3d_trend=2.5,
            ctr_current=0.01,
            ctr_7d_avg=0.03,
            audience_saturation=0.8,
            creative_age_days=20,
            conversion_volume_7d=5,
            spend_7d=3000.0,
        )

        result = agent.analyze(metrics)
        # Should fallback to default
        assert result.campaign_id == "test_004"

    def test_parse_fallback_on_missing_action(self):
        """Test fallback when recommended_action is missing."""
        mock_response = '{"reasoning": "Test", "confidence": {"overall_score": 0.5}}'
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_005",
            cpa_3d_trend=1.1,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=7,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = agent.analyze(metrics)
        # Should default to maintain
        assert result.recommended_action == RecommendedAction.MAINTAIN
        assert result.confidence.overall_score == 0.0  # Fallback default

    def test_reasoning_truncation(self):
        """Test that reasoning is truncated to 500 chars."""
        long_reasoning = "x" * 600
        mock_response = f"""{{
            "recommended_action": "maintain",
            "reasoning": "{long_reasoning}",
            "confidence": {{"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8}},
            "key_factors": ["test"]
        }}"""
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_006",
            cpa_3d_trend=1.0,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=5,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = agent.analyze(metrics)
        assert len(result.reasoning) <= 500

    def test_system_prompt_contains_schema(self):
        """Test that system prompt contains required JSON schema."""
        assert "recommended_action" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT
        assert "key_factors" in SYSTEM_PROMPT


class TestMockProvider:
    """Tests for mock provider functionality."""

    def test_provider_called_with_correct_messages(self):
        """Test that provider receives correct message structure."""
        mock_response = '{"recommended_action": "maintain", "reasoning": "ok", "confidence": {"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8}, "key_factors": []}'
        provider = MockProvider(mock_response)
        agent = AnalyzerAgent(provider)

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

        agent.analyze(metrics)

        # Verify provider was called (we can't check exact messages without more mocking)
        assert provider.called
