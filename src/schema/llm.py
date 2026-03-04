"""LLM response types for unified provider interface."""

from typing import Literal
from pydantic import BaseModel, Field

from .content import ContentBlock

StopReason = Literal["stop", "length", "tool_use", "error", "aborted"]


class TokenUsage(BaseModel):
    """Token usage statistics from LLM API response."""

    input_tokens: int = Field(default=0, description="Input/prompt tokens")
    output_tokens: int = Field(default=0, description="Output/completion tokens")
    thinking_tokens: int = Field(
        default=0, description="Reasoning/thinking tokens (if tracked separately)"
    )
    cache_read_tokens: int = Field(
        default=0, description="Cached prompt tokens (if supported)"
    )
    cache_write_tokens: int = Field(
        default=0, description="Cache creation tokens (if supported)"
    )
    total_tokens: int = Field(default=0, description="Total tokens used")


class CostBreakdown(BaseModel):
    """Cost breakdown in USD."""

    input_cost: float = Field(default=0.0, description="Input token cost")
    output_cost: float = Field(default=0.0, description="Output token cost")
    cache_read_cost: float = Field(default=0.0, description="Cache read cost (if applicable)")
    cache_write_cost: float = Field(default=0.0, description="Cache write cost (if applicable)")
    total_cost: float = Field(default=0.0, description="Total estimated cost")


class LLMResponse(BaseModel):
    """Unified LLM response regardless of provider.

    Normalizes Anthropic-style, OpenAI-style, and other provider responses
    into a consistent schema.
    """

    content: list[ContentBlock] = Field(
        default_factory=list,
        description="Ordered content blocks (text, thinking, tool_use, etc.)",
    )
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage stats")
    cost: CostBreakdown = Field(default_factory=CostBreakdown, description="Estimated cost")
    latency_ms: float = Field(default=0.0, description="Request latency in milliseconds")
    model: str = Field(..., description="Model ID that generated the response")
    provider: str = Field(..., description="Provider name (kimi, minimax, etc.)")
    stop_reason: StopReason = Field(default="stop", description="Why generation stopped")
    error_message: str | None = Field(None, description="Error message if stop_reason='error'")

    def get_text(self) -> str:
        """Extract all text content blocks as single string."""
        texts = []
        for block in self.content:
            if block.type == "text":
                texts.append(block.text)
        return "\n".join(texts)

    def get_thinking(self) -> str:
        """Extract all thinking content as single string."""
        thoughts = []
        for block in self.content:
            if block.type == "thinking":
                thoughts.append(block.thinking)
        return "\n".join(thoughts)

    def get_tool_calls(self) -> list:
        """Extract all tool use blocks."""
        tools = []
        for block in self.content:
            if block.type == "tool_use":
                tools.append(block.tool_use)
        return tools

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return any(block.type == "tool_use" for block in self.content)
