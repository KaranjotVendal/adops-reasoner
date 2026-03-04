"""Unit tests for analyzer agent (Anthropic-style provider version)."""

import pytest

from src.agents.analyzer import AnalyzerAgent, DEFAULT_ANALYZER_SYSTEM_PROMPT
from src.domain.models import CampaignMetrics, RecommendedAction
from src.providers.base import AnthropicStyleProvider
from src.schema import ContentBlock, LLMResponse, Message, StopReason, TextContent, TokenUsage


class MockAnthropicProvider(AnthropicStyleProvider):
    """Mock Anthropic-style provider for testing."""

    def __init__(self, response_content: str | list[ContentBlock]):
        """Initialize with mock response."""
        self._response_content = response_content
        self.calls: list[list[Message]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def api_version(self) -> str:
        return "2023-06-01"

    def _calculate_cost(self, usage: TokenUsage):
        from src.schema import CostBreakdown

        return CostBreakdown()

    def generate(
        self,
        messages: list[Message],
        tools=None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thinking: bool = False,
    ) -> LLMResponse:
        """Return mock response."""
        self.calls.append(messages)

        if isinstance(self._response_content, str):
            content = [TextContent(text=self._response_content)]
        else:
            content = self._response_content

        return LLMResponse(
            content=content,
            model="mock-model",
            provider="mock",
            stop_reason="stop",
        )


class TestAnalyzerAgent:
    """Tests for AnalyzerAgent with Anthropic-style providers."""

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
        provider = MockAnthropicProvider(mock_response)
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
        assert len(provider.calls) == 1

    def test_analyze_pause_campaign(self):
        """Test pause_campaign action extraction."""
        mock_response = """{
            "recommended_action": "pause_campaign",
            "reasoning": "Extreme CPA rise detected",
            "confidence": {"overall_score": 0.95, "data_quality": 0.9, "recommendation_strength": 0.95},
            "key_factors": ["CPA up 3x", "Low conversions"]
        }"""
        provider = MockAnthropicProvider(mock_response)
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
        provider = MockAnthropicProvider(mock_response)
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
        mock_response = 'Here is my recommendation: "recommended_action": "pause_campaign"'
        provider = MockAnthropicProvider(mock_response)
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
        # Should fallback to default with action extracted via regex
        assert result.campaign_id == "test_004"
        assert result.recommended_action == RecommendedAction.PAUSE_CAMPAIGN

    def test_parse_fallback_on_missing_action(self):
        """Test fallback when recommended_action is missing."""
        mock_response = '{"reasoning": "Test", "confidence": {"overall_score": 0.5}}'
        provider = MockAnthropicProvider(mock_response)
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

    def test_reasoning_truncation(self):
        """Test that reasoning is truncated to 500 chars."""
        long_reasoning = "x" * 600
        mock_response = f"""{{
            "recommended_action": "maintain",
            "reasoning": "{long_reasoning}",
            "confidence": {{"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8}},
            "key_factors": ["test"]
        }}"""
        provider = MockAnthropicProvider(mock_response)
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
        assert "recommended_action" in DEFAULT_ANALYZER_SYSTEM_PROMPT
        assert "confidence" in DEFAULT_ANALYZER_SYSTEM_PROMPT
        assert "key_factors" in DEFAULT_ANALYZER_SYSTEM_PROMPT

    def test_custom_system_prompt(self):
        """Test that custom system prompt can be provided."""
        provider = MockAnthropicProvider('{"recommended_action": "maintain"}')
        custom_prompt = "Custom system prompt for testing"
        agent = AnalyzerAgent(provider, system_prompt=custom_prompt)

        assert agent.system_prompt == custom_prompt

    def test_metadata_attached_to_result(self):
        """Test that LLM metadata is attached to analysis result."""
        mock_response = """{
            "recommended_action": "maintain",
            "reasoning": "Test",
            "confidence": {"overall_score": 0.8, "data_quality": 0.8, "recommendation_strength": 0.8},
            "key_factors": ["test"]
        }"""
        provider = MockAnthropicProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_007",
            cpa_3d_trend=1.0,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=5,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        result = agent.analyze(metrics)

        # Check metadata is attached
        assert hasattr(result, "_metadata")
        assert result._metadata is not None
        assert result._metadata.get("model") == "mock-model"
        assert result._metadata.get("provider") == "mock"

    def test_messages_structure(self):
        """Test that correct message structure is sent to provider."""
        mock_response = '{"recommended_action": "maintain"}'
        provider = MockAnthropicProvider(mock_response)
        agent = AnalyzerAgent(provider)

        metrics = CampaignMetrics(
            campaign_id="test_008",
            cpa_3d_trend=1.0,
            ctr_current=0.04,
            ctr_7d_avg=0.04,
            audience_saturation=0.5,
            creative_age_days=5,
            conversion_volume_7d=100,
            spend_7d=1000.0,
        )

        agent.analyze(metrics)

        # Check provider was called with correct messages
        assert len(provider.calls) == 1
        messages = provider.calls[0]
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "test_008" in str(messages[1].content)
