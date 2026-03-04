"""Validator agent - validates campaign analysis with tool access.

LLM-based validator that reviews analyzer output and can request
additional information via tools before final approval.
"""

import logging
from typing import Any

from src.providers import AnthropicStyleProvider
from src.schema import (
    ContentBlock,
    LLMResponse,
    Message,
    TextContent,
    Tool,
    ToolUseBlock,
)
from src.tools import ToolRegistry

logger = logging.getLogger(__name__)

# Default system prompt for validator
DEFAULT_VALIDATOR_SYSTEM_PROMPT = """You are a Campaign Analysis Validator. Your role is to review and validate campaign recommendations.

You must respond with valid JSON only (no additional text). Use this exact schema:
{
  "decision": "approve" | "reject" | "needs_info",
  "confidence": <0.0-1.0>,
  "feedback": "<validation feedback, max 300 chars>",
  "suggested_changes": ["<change1>", "<change2>"],
  "requires_human_review": <true|false>
}

Decisions:
- approve: Recommendation is sound and complete
- reject: Critical flaws found, needs revision
- needs_info: Need additional data (use tools if available)

Use tools to gather information when needed:
- read_file: Read data files for context
- write_file: Save validation notes

Review criteria:
1. Does the action match the data?
2. Is the confidence justified?
3. Are there missing factors?
4. Would you approve this for production?"""


class ValidationResult:
    """Result of validation with metadata."""

    def __init__(
        self,
        decision: str,
        confidence: float,
        feedback: str,
        suggested_changes: list[str],
        requires_human_review: bool,
        raw_response: dict[str, Any] | None = None,
        llm_response: LLMResponse | None = None,
    ):
        self.decision = decision
        self.confidence = confidence
        self.feedback = feedback
        self.suggested_changes = suggested_changes
        self.requires_human_review = requires_human_review
        self.raw_response = raw_response
        self.llm_response = llm_response

    def is_approved(self) -> bool:
        """Check if validation passed."""
        return self.decision == "approve"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "feedback": self.feedback,
            "suggested_changes": self.suggested_changes,
            "requires_human_review": self.requires_human_review,
        }


class ValidatorAgent:
    """Agent that validates campaign analysis recommendations.

    Uses LLM with tool access to review analyzer output.
    Can request additional information via tools.
    """

    def __init__(
        self,
        provider: AnthropicStyleProvider,
        tool_registry: ToolRegistry | None = None,
        system_prompt: str | None = None,
        max_tool_iterations: int = 3,
    ):
        """Initialize validator with LLM provider.

        Args:
            provider: Anthropic-style LLM provider
            tool_registry: Optional tools for information gathering
            system_prompt: Custom system prompt
            max_tool_iterations: Max tool calls per validation
        """
        self.provider = provider
        self.tool_registry = tool_registry or ToolRegistry()
        self.system_prompt = system_prompt or DEFAULT_VALIDATOR_SYSTEM_PROMPT
        self.max_tool_iterations = max_tool_iterations

    def validate(
        self,
        campaign_id: str,
        analysis_result: dict[str, Any],
        original_metrics: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate an analysis result.

        Args:
            campaign_id: Campaign being analyzed
            analysis_result: Analyzer's recommendation and reasoning
            original_metrics: Original campaign metrics

        Returns:
            ValidationResult with decision and feedback
        """
        # Build messages
        messages = self._build_messages(campaign_id, analysis_result, original_metrics)

        # Get available tools
        tools = self.tool_registry.get_schemas() if len(self.tool_registry) > 0 else None

        # Initial validation call
        response = self.provider.generate(
            messages=messages,
            tools=tools,
            max_tokens=4096,
            temperature=0.2,  # Lower temp for consistent validation
        )

        # Handle tool calls if needed
        if response.has_tool_calls() and self.tool_registry:
            response = self._handle_tool_loop(messages, response, tools)

        # Parse final response
        parsed = self._parse_validation_response(response.content)

        return ValidationResult(
            decision=parsed.get("decision", "reject"),
            confidence=parsed.get("confidence", 0.0),
            feedback=parsed.get("feedback", "No feedback provided"),
            suggested_changes=parsed.get("suggested_changes", []),
            requires_human_review=parsed.get("requires_human_review", True),
            raw_response=parsed,
            llm_response=response,
        )

    def _build_messages(
        self,
        campaign_id: str,
        analysis_result: dict[str, Any],
        original_metrics: dict[str, Any] | None = None,
    ) -> list[Message]:
        """Build validation prompt messages."""
        user_prompt = f"""Validate this campaign analysis:

Campaign ID: {campaign_id}

ANALYSIS RESULT:
- Recommended Action: {analysis_result.get('recommended_action', 'unknown')}
- Reasoning: {analysis_result.get('reasoning', 'N/A')}
- Confidence: {analysis_result.get('confidence', {}).get('overall_score', 0)}
- Key Factors: {', '.join(analysis_result.get('key_factors', []))}
"""

        if original_metrics:
            user_prompt += f"""

ORIGINAL METRICS:
{self._format_metrics(original_metrics)}
"""

        user_prompt += """

Provide your validation as JSON. Use tools if you need additional information."""

        return [
            Message.system(self.system_prompt),
            Message.user(user_prompt),
        ]

    def _format_metrics(self, metrics: dict[str, Any]) -> str:
        """Format metrics for prompt."""
        lines = []
        for key, value in metrics.items():
            if isinstance(value, float):
                lines.append(f"- {key}: {value:.4f}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _handle_tool_loop(
        self,
        messages: list[Message],
        initial_response: LLMResponse,
        tools: list[Tool] | None,
    ) -> LLMResponse:
        """Handle tool calls and re-validation.

        Args:
            messages: Conversation history
            initial_response: First LLM response with tool calls
            tools: Available tools

        Returns:
            Final LLM response after tool execution
        """
        current_response = initial_response
        iteration = 0

        while current_response.has_tool_calls() and iteration < self.max_tool_iterations:
            iteration += 1

            # Execute tools
            tool_results = []
            for tool_call in current_response.get_tool_calls():
                result = self.tool_registry.execute_tool_call(tool_call)
                tool_results.append(result)

            # Add assistant message with tool calls
            messages.append(Message.assistant(current_response.content))

            # Add tool results as user message
            messages.append(Message.user(tool_results))

            # Re-call LLM with tool results
            current_response = self.provider.generate(
                messages=messages,
                tools=tools,
                max_tokens=4096,
                temperature=0.2,
            )

        return current_response

    def _parse_validation_response(self, content: list[ContentBlock]) -> dict[str, Any]:
        """Parse validation result from content blocks."""
        import json
        import re

        # Extract text content
        text_parts = []
        for block in content:
            if isinstance(block, TextContent):
                text_parts.append(block.text)

        full_text = "\n".join(text_parts)

        # Clean markdown fences
        cleaned = full_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
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

        # Try JSON parse
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "decision" in data:
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: regex extraction
        try:
            match = re.search(r'\{[^{}]*"decision"[^{}]*\}', full_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if "decision" in data:
                    return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Complete fallback
        return {
            "decision": "reject",
            "confidence": 0.0,
            "feedback": "Unable to parse validation response",
            "suggested_changes": ["Retry validation"],
            "requires_human_review": True,
        }
