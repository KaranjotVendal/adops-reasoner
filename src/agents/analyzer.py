"""Analyzer agent - generates campaign recommendations via LLM."""

import json
import logging
import re

from src.agents.providers.base import ProviderInterface
from src.domain.models import (
    AnalysisConfidence,
    CampaignAnalysis,
    CampaignMetrics,
    RecommendedAction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Campaign Analyst agent. Your role is to analyze marketing campaign metrics and recommend optimal actions.

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

USER_PROMPT_TEMPLATE = """Analyze this campaign:

Campaign ID: {campaign_id}
CPA 3-day trend: {cpa_3d_trend}x
Current CTR: {ctr_current:.2%}
7-day avg CTR: {ctr_7d_avg:.2%}
Audience saturation: {audience_saturation:.0%}
Creative age: {creative_age_days} days
Conversions (7d): {conversion_volume_7d}
Spend (7d): ${spend_7d:.2f}

Provide your recommendation as JSON."""


class AnalyzerAgent:
    """Agent that analyzes campaign metrics and generates recommendations."""

    def __init__(self, provider: ProviderInterface):
        """Initialize analyzer with LLM provider.

        Args:
            provider: LLM provider instance (e.g., MiniMaxProvider)
        """
        self.provider = provider
        self._action_pattern = re.compile(
            r'"recommended_action"\s*:\s*"([^"]+)"',
            re.IGNORECASE,
        )
        self._json_pattern = re.compile(r'\{[^{}]*"recommended_action"[^{}]*\}', re.DOTALL)

    def analyze(self, metrics: CampaignMetrics) -> CampaignAnalysis:
        """Analyze campaign metrics and return recommendation.

        Args:
            metrics: Campaign metrics to analyze

        Returns:
            CampaignAnalysis with recommendation and reasoning
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            campaign_id=metrics.campaign_id,
            cpa_3d_trend=metrics.cpa_3d_trend,
            ctr_current=metrics.ctr_current,
            ctr_7d_avg=metrics.ctr_7d_avg,
            audience_saturation=metrics.audience_saturation,
            creative_age_days=metrics.creative_age_days,
            conversion_volume_7d=metrics.conversion_volume_7d,
            spend_7d=metrics.spend_7d,
        )

        response = self.provider.chatCompletion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        parsed = self._parse_response(response.content, response.raw_response)
        return self._build_analysis(metrics, parsed)

    def _parse_response(self, content: str | None, raw_response: dict | None = None) -> dict:
        """Parse LLM response into structured dict.

        Follows Mini-Agent patterns for robust handling:
        - content can be None or empty string
        - tool_calls may be present even with empty content
        - Multiple fallback strategies for parsing

        Args:
            content: Raw LLM response content (can be None)
            raw_response: Full API response for advanced parsing

        Returns:
            Parsed dict with recommended_action, reasoning, confidence, key_factors
        """
        # Handle None or non-string content (Mini-Agent pattern: message.content or "")
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = str(content) if content else ""

        # Check raw_response for tool_calls (Mini-Agent pattern)
        # Even with empty content, model might return tool_calls
        if raw_response:
            parsed_from_raw = self._try_parse_from_raw_response(raw_response)
            if parsed_from_raw:
                return parsed_from_raw

        # Try direct JSON parse first
        if content.strip():
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "recommended_action" in data:
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        # Try regex extraction for robustness (handles fenced markdown)
        cleaned = self._strip_markdown_fences(content)
        if cleaned.strip():
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict) and "recommended_action" in data:
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        # Try simpler regex fallback
        match = self._json_pattern.search(content)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, dict) and "recommended_action" in data:
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: extract action via regex, use defaults for rest
        action_match = self._action_pattern.search(content)
        if action_match:
            action = action_match.group(1)
            # Validate action
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

    def _try_parse_from_raw_response(self, raw_response: dict) -> dict | None:
        """Attempt to parse response from raw API response.

        Mini-Agent pattern: check message.content AND tool_calls in raw response.

        Args:
            raw_response: Full API response dict

        Returns:
            Parsed dict if successful, None otherwise
        """
        try:
            # Navigate typical OpenAI-compatible response structure
            # {"choices": [{"message": {"content": "...", "tool_calls": [...]}}]}
            choices = raw_response.get("choices", [])
            if not choices:
                return None

            message = choices[0].get("message", {})

            # Check for tool_calls first (even if content is empty)
            tool_calls = message.get("tool_calls")
            if tool_calls:
                # Tool calling mode - extract from first tool call
                logger.debug(f"Response contains {len(tool_calls)} tool calls")
                # For now, we don't handle tool calling in analyzer
                # But we could extract arguments from tool call if needed

            # Try content as before
            content = message.get("content")
            if content and isinstance(content, str):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "recommended_action" in data:
                        return data
                except (json.JSONDecodeError, TypeError):
                    pass

        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            logger.debug(f"Raw response parsing failed: {e}")

        return None

    def _strip_markdown_fences(self, content: str) -> str:
        """Strip markdown code fences from content.

        Handles:
        - ```json ... ```
        - ``` ... ```

        Args:
            content: Raw content possibly with markdown fences

        Returns:
            Content with fences stripped
        """
        # Remove ```json and ``` blocks
        lines = content.split("\n")
        result_lines = []
        in_fence = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    def _build_analysis(
        self, metrics: CampaignMetrics, parsed: dict
    ) -> CampaignAnalysis:
        """Build CampaignAnalysis from parsed LLM response.

        Args:
            metrics: Original campaign metrics
            parsed: Parsed LLM response

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

        return CampaignAnalysis(
            campaign_id=metrics.campaign_id,
            recommended_action=action,
            reasoning=reasoning,
            confidence=confidence,
            key_factors=key_factors,
        )
