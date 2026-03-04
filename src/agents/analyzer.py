"""Analyzer agent - generates campaign recommendations via LLM.

Refactored to use unified Anthropic-style providers with ContentBlock support.
"""

import logging
from typing import Any

from src.domain.models import (
    AnalysisConfidence,
    CampaignAnalysis,
    CampaignMetrics,
    RecommendedAction,
)
from src.providers import AnthropicStyleProvider
from src.schema import ContentBlock, Message, TextContent, Tool, ToolUseContent

logger = logging.getLogger(__name__)

# Default system prompt for analyzer
DEFAULT_ANALYZER_SYSTEM_PROMPT = """You are a Campaign Analyst agent. Your role is to analyze marketing campaign metrics and recommend optimal actions.

You must respond with valid JSON only (no additional text). Use this exact schema:
{
  "recommended_action": "maintain" | "pause_campaign" | "creative_refresh" | "audience_expansion" | "bid_adjustment",
  "reasoning": "<your analysis in 1-2 sentences, max 500 chars>",
  "confidence": {
    "overall_score": <0.0-1.0>,
    "data_quality": <0.0-1.0>,
    "recommendation_strength": <0.0-1.0>
  },
  "key_factors": ["<factor1>", "<factor2>"]
}

Available actions:
- maintain: Campaign is performing well, no changes needed
- pause_campaign: Critical issues requiring immediate stop (extreme CPA, very low CTR, etc.)
- creative_refresh: CTR declining with old creative (>14 days)
- audience_expansion: High audience saturation, stable performance
- bid_adjustment: Moderate CPA changes without creative issues

Analyze the campaign metrics provided and return your recommendation."""


class AnalyzerAgent:
    """Agent that analyzes campaign metrics and generates recommendations.

    Uses Anthropic-style LLM providers (Kimi, MiniMax) with unified ContentBlock interface.
    Supports thinking/reasoning capture and tool use.
    """

    def __init__(
        self,
        provider: AnthropicStyleProvider,
        system_prompt: str | None = None,
        enable_thinking: bool = False,
    ):
        """Initialize analyzer with LLM provider.

        Args:
            provider: Anthropic-style LLM provider (Kimi or MiniMax)
            system_prompt: Custom system prompt (uses default if None)
            enable_thinking: Whether to capture model's reasoning/thinking
        """
        self.provider = provider
        self.system_prompt = system_prompt or DEFAULT_ANALYZER_SYSTEM_PROMPT
        self.enable_thinking = enable_thinking

    def analyze(
        self,
        metrics: CampaignMetrics,
        tools: list[Tool] | None = None,
    ) -> CampaignAnalysis:
        """Analyze campaign metrics and return recommendation.

        Args:
            metrics: Campaign metrics to analyze
            tools: Optional tools available to the model

        Returns:
            CampaignAnalysis with recommendation and reasoning
        """
        # Build conversation messages
        messages = self._build_messages(metrics)

        # Call LLM
        response = self.provider.generate(
            messages=messages,
            tools=tools,
            max_tokens=4096,
            temperature=0.3,
            thinking=self.enable_thinking,
        )

        # Parse response from content blocks
        parsed = self._parse_content_blocks(response.content)

        return self._build_analysis(metrics, parsed, response)

    def _build_messages(self, metrics: CampaignMetrics) -> list[Message]:
        """Build conversation messages for LLM.

        Args:
            metrics: Campaign metrics

        Returns:
            List of messages (system + user)
        """
        user_prompt = self._build_user_prompt(metrics)

        return [
            Message.system(self.system_prompt),
            Message.user(user_prompt),
        ]

    def _build_user_prompt(self, metrics: CampaignMetrics) -> str:
        """Build user prompt with campaign metrics.

        Args:
            metrics: Campaign metrics

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this campaign:

Campaign ID: {metrics.campaign_id}
CPA 3-day trend: {metrics.cpa_3d_trend}x
Current CTR: {metrics.ctr_current:.2%}
7-day avg CTR: {metrics.ctr_7d_avg:.2%}
Audience saturation: {metrics.audience_saturation:.0%}
Creative age: {metrics.creative_age_days} days
Conversions (7d): {metrics.conversion_volume_7d}
Spend (7d): ${metrics.spend_7d:.2f}

Provide your recommendation as JSON."""

    def _parse_content_blocks(self, content: list[ContentBlock]) -> dict[str, Any]:
        """Parse content blocks to extract analysis result.

        Handles:
        - Text blocks containing JSON
        - Thinking blocks (captured if enable_thinking=True)
        - Tool use blocks (future extension)

        Args:
            content: List of content blocks from LLM

        Returns:
            Parsed dict with recommended_action, reasoning, confidence, key_factors
        """
        import json

        # Extract text content (primary response)
        text_parts = []
        thinking_parts = []

        for block in content:
            if isinstance(block, TextContent):
                text_parts.append(block.text)
            elif hasattr(block, "thinking") and block.thinking:
                thinking_parts.append(block.thinking)
            elif isinstance(block, ToolUseContent):
                # Tool use not expected in analyzer, but handle gracefully
                logger.debug(f"Unexpected tool use in analyzer: {block.tool_use.name}")

        full_text = "\n".join(text_parts)

        # Try to parse JSON from text
        result = self._extract_json_from_text(full_text)

        # If we have thinking content and no explicit reasoning, prepend it
        if thinking_parts and result.get("reasoning"):
            thinking_summary = thinking_parts[0][:200] + "..." if len(thinking_parts[0]) > 200 else thinking_parts[0]
            result["_thinking"] = "\n".join(thinking_parts)

        return result

    def _extract_json_from_text(self, text: str) -> dict[str, Any]:
        """Extract JSON analysis from text response.

        Handles markdown fences and validates structure.

        Args:
            text: Raw text content

        Returns:
            Parsed dict or fallback defaults
        """
        import json
        import re

        cleaned = text.strip()

        # Remove markdown fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Find first and last fence
            start_idx = 0
            end_idx = len(lines) - 1

            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    if start_idx == 0 and i == 0:
                        start_idx = i + 1
                    elif end_idx == len(lines) - 1:
                        end_idx = i
                        break

            cleaned = "\n".join(lines[start_idx:end_idx]).strip()

        # Try to parse JSON
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "recommended_action" in data:
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to extract JSON from larger text
        json_pattern = re.compile(r'\{[^{}]*"recommended_action"[^{}]*\}', re.DOTALL)
        match = json_pattern.search(text)
        if match:
            try:
                data = json.loads(match.group())
                if "recommended_action" in data:
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: try to extract action via regex
        action_pattern = re.compile(
            r'"recommended_action"\s*:\s*"([^"]+)"',
            re.IGNORECASE,
        )
        action_match = action_pattern.search(text)

        if action_match:
            action = action_match.group(1)
            valid_actions = {a.value for a in RecommendedAction}
            if action not in valid_actions:
                action = "maintain"

            return {
                "recommended_action": action,
                "reasoning": "Analysis completed with default confidence due to parsing issue",
                "confidence": {
                    "overall_score": 0.5,
                    "data_quality": 0.5,
                    "recommendation_strength": 0.5,
                },
                "key_factors": ["Data parsed with fallback"],
            }

        # Complete fallback
        return {
            "recommended_action": "maintain",
            "reasoning": "Unable to analyze, defaulting to maintain",
            "confidence": {
                "overall_score": 0.0,
                "data_quality": 0.0,
                "recommendation_strength": 0.0,
            },
            "key_factors": ["Analysis failed"],
        }

    def _build_analysis(
        self,
        metrics: CampaignMetrics,
        parsed: dict[str, Any],
        response: Any,  # LLMResponse
    ) -> CampaignAnalysis:
        """Build CampaignAnalysis from parsed LLM response.

        Args:
            metrics: Original campaign metrics
            parsed: Parsed LLM response dict
            response: Full LLM response (for metadata)

        Returns:
            CampaignAnalysis instance
        """
        action_str = parsed.get("recommended_action", "maintain")

        # Map string to enum
        try:
            action = RecommendedAction(action_str)
        except ValueError:
            action = RecommendedAction.MAINTAIN

        conf = parsed.get("confidence", {})
        confidence = AnalysisConfidence(
            overall_score=conf.get("overall_score", 0.5),
            data_quality=conf.get("data_quality", 0.5),
            recommendation_strength=conf.get("recommendation_strength", 0.5),
        )

        reasoning = parsed.get("reasoning", "No reasoning provided")
        if len(reasoning) > 500:
            reasoning = reasoning[:497] + "..."

        key_factors = parsed.get("key_factors", [])
        if not isinstance(key_factors, list):
            key_factors = [str(key_factors)]

        analysis = CampaignAnalysis(
            campaign_id=metrics.campaign_id,
            recommended_action=action,
            reasoning=reasoning,
            confidence=confidence,
            key_factors=key_factors,
        )

        # Attach metadata for observability (not part of domain model)
        analysis._metadata = {
            "model": response.model,
            "provider": response.provider,
            "latency_ms": response.latency_ms,
            "usage": response.usage.model_dump() if response.usage else None,
            "cost": response.cost.model_dump() if response.cost else None,
            "thinking": parsed.get("_thinking"),  # Captured thinking if enabled
        }

        return analysis
