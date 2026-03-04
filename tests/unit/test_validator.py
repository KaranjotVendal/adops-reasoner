"""Unit tests for validator agent (new LLM-based implementation)."""

import pytest

from src.agents.validator import ValidatorAgent, ValidationResult, DEFAULT_VALIDATOR_SYSTEM_PROMPT
from src.domain.models import (
    CampaignMetrics,
)


class MockProvider:
    """Mock provider for testing validator."""

    def __init__(self, response_content: str):
        self.response_content = response_content

    def generate(self, messages, tools=None, max_tokens=4096, temperature=0.2, thinking=False):
        from src.schema import LLMResponse, TextContent

        return LLMResponse(
            content=[TextContent(text=self.response_content)],
            model="mock",
            provider="mock",
            latency_ms=10.0,
        )


class TestValidatorAgent:
    """Tests for ValidatorAgent with LLM-based validation."""

    def test_validate_returns_validation_result(self):
        """Test that validate returns a ValidationResult."""
        mock_response = """{
            "decision": "approve",
            "confidence": 0.92,
            "feedback": "Analysis aligns with metrics",
            "suggested_changes": [],
            "requires_human_review": false
        }"""
        provider = MockProvider(mock_response)
        validator = ValidatorAgent(provider)

        analysis_result = {
            "recommended_action": "maintain",
            "reasoning": "Campaign is stable",
            "confidence": {"overall_score": 0.85, "data_quality": 0.9, "recommendation_strength": 0.8},
            "key_factors": ["Stable metrics"],
        }

        result = validator.validate(
            campaign_id="test_001",
            analysis_result=analysis_result,
            original_metrics=None,
        )

        assert isinstance(result, ValidationResult)
        assert result.decision == "approve"
        assert result.confidence == 0.92
        assert result.requires_human_review is False

    def test_validate_rejects_invalid_analysis(self):
        """Test validator can reject analysis."""
        mock_response = """{
            "decision": "reject",
            "confidence": 0.75,
            "feedback": "Reasoning doesn't match metrics",
            "suggested_changes": ["Check CPA trend again"],
            "requires_human_review": true
        }"""
        provider = MockProvider(mock_response)
        validator = ValidatorAgent(provider)

        analysis_result = {
            "recommended_action": "maintain",
            "reasoning": "Everything looks good",
            "confidence": {"overall_score": 0.9},
            "key_factors": [],
        }

        result = validator.validate(
            campaign_id="test_002",
            analysis_result=analysis_result,
        )

        assert result.decision == "reject"
        assert result.requires_human_review is True
        assert len(result.suggested_changes) > 0

    def test_validate_needs_info(self):
        """Test validator can request more information."""
        mock_response = """{
            "decision": "needs_info",
            "confidence": 0.6,
            "feedback": "Need historical data to validate",
            "suggested_changes": [],
            "requires_human_review": false
        }"""
        provider = MockProvider(mock_response)
        validator = ValidatorAgent(provider)

        analysis_result = {
            "recommended_action": "bid_adjustment",
            "reasoning": "CPA increasing",
            "confidence": {"overall_score": 0.7},
            "key_factors": ["CPA up"],
        }

        result = validator.validate(
            campaign_id="test_003",
            analysis_result=analysis_result,
        )

        assert result.decision == "needs_info"

    def test_validate_with_metrics(self):
        """Test validator with original metrics provided."""
        mock_response = """{
            "decision": "approve",
            "confidence": 0.88,
            "feedback": "Action matches data",
            "suggested_changes": [],
            "requires_human_review": false
        }"""
        provider = MockProvider(mock_response)
        validator = ValidatorAgent(provider)

        analysis_result = {
            "recommended_action": "pause_campaign",
            "reasoning": "CPA has tripled",
            "confidence": {"overall_score": 0.9},
            "key_factors": ["CPA 3x"],
        }

        metrics = CampaignMetrics(
            campaign_id="test_004",
            cpa_3d_trend=3.0,
            ctr_current=0.01,
            ctr_7d_avg=0.03,
            audience_saturation=0.8,
            creative_age_days=25,
            conversion_volume_7d=10,
            spend_7d=3000.0,
        )

        result = validator.validate(
            campaign_id="test_004",
            analysis_result=analysis_result,
            original_metrics=metrics.model_dump(),
        )

        assert result.decision == "approve"
        assert result.is_approved() is True

    def test_fallback_parsing_on_invalid_json(self):
        """Test fallback when LLM returns invalid JSON."""
        mock_response = "I think this looks good, decision: approve"
        provider = MockProvider(mock_response)
        validator = ValidatorAgent(provider)

        analysis_result = {
            "recommended_action": "maintain",
            "reasoning": "Stable",
            "confidence": {"overall_score": 0.8},
            "key_factors": [],
        }

        result = validator.validate(
            campaign_id="test_005",
            analysis_result=analysis_result,
        )

        # Should fallback to reject with low confidence
        assert result.decision == "reject"
        assert result.requires_human_review is True


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_is_approved(self):
        """Test is_approved method."""
        result = ValidationResult(
            decision="approve",
            confidence=0.9,
            feedback="Looks good",
            suggested_changes=[],
            requires_human_review=False,
        )
        assert result.is_approved() is True

        result2 = ValidationResult(
            decision="reject",
            confidence=0.5,
            feedback="Issues found",
            suggested_changes=["Fix this"],
            requires_human_review=True,
        )
        assert result2.is_approved() is False

    def test_to_dict(self):
        """Test to_dict serialization."""
        result = ValidationResult(
            decision="approve",
            confidence=0.85,
            feedback="Valid analysis",
            suggested_changes=[],
            requires_human_review=False,
        )

        data = result.to_dict()

        assert data["decision"] == "approve"
        assert data["confidence"] == 0.85
        assert data["requires_human_review"] is False


class TestValidatorSystemPrompt:
    """Tests for validator system prompt."""

    def test_system_prompt_contains_required_elements(self):
        """Test that system prompt has required instructions."""
        assert "decision" in DEFAULT_VALIDATOR_SYSTEM_PROMPT
        assert "confidence" in DEFAULT_VALIDATOR_SYSTEM_PROMPT
        assert "feedback" in DEFAULT_VALIDATOR_SYSTEM_PROMPT
        assert "approve" in DEFAULT_VALIDATOR_SYSTEM_PROMPT
        assert "reject" in DEFAULT_VALIDATOR_SYSTEM_PROMPT
