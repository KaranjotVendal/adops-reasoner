"""MiniMax provider implementation (Anthropic-style API).

Uses MiniMax's Anthropic-compatible endpoint:
https://api.minimax.io/anthropic/v1/messages

Note: This is different from the OpenAI-compatible endpoint at /v1.
Both work, but this enables unified handling with Kimi.
"""

import os
from typing import override

from .base import AnthropicStyleProvider
from ..schema import CostBreakdown, TokenUsage


class MiniMaxAnthropicProvider(AnthropicStyleProvider):
    """MiniMax LLM provider using Anthropic Messages API.

    Supports models:
    - MiniMax-M2.5
    - MiniMax-M2.5-highspeed

    Requires MINIMAX_API_KEY environment variable.
    """

    AVAILABLE_MODELS = ["MiniMax-M2.5", "MiniMax-M2.5-highspeed"]
    DEFAULT_MODEL = "MiniMax-M2.5"

    # Pricing per million tokens (USD)
    PRICING = {
        "MiniMax-M2.5": {
            "input": 0.30,
            "output": 1.20,
            "cache_read": 0.03,
            "cache_write": 0.375,
        },
        "MiniMax-M2.5-highspeed": {
            "input": 0.60,
            "output": 2.40,
            "cache_read": 0.06,
            "cache_write": 0.375,
        },
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ):
        """Initialize MiniMax provider (Anthropic-style).

        Args:
            api_key: MiniMax API key (defaults to MINIMAX_API_KEY env var)
            model: Model ID
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key not provided and MINIMAX_API_KEY not set
        """
        key = api_key or os.environ.get("MINIMAX_API_KEY")
        if not key:
            raise ValueError(
                "MiniMax API key required. Set MINIMAX_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if model not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown MiniMax model: {model}. "
                f"Available: {', '.join(self.AVAILABLE_MODELS)}"
            )

        super().__init__(
            api_key=key,
            base_url="https://api.minimax.io/anthropic",
            model=model,
            timeout=timeout,
        )

    @property
    @override
    def provider_name(self) -> str:
        return "minimax"

    @property
    @override
    def api_version(self) -> str:
        return "2023-06-01"

    @override
    def _calculate_cost(self, usage: TokenUsage) -> CostBreakdown:
        """Calculate cost for MiniMax API."""
        pricing = self.PRICING.get(self.model, self.PRICING[self.DEFAULT_MODEL])

        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost = (usage.cache_read_tokens / 1_000_000) * pricing["cache_read"]
        cache_write_cost = (usage.cache_write_tokens / 1_000_000) * pricing["cache_write"]

        return CostBreakdown(
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            cache_read_cost=round(cache_read_cost, 6),
            cache_write_cost=round(cache_write_cost, 6),
            total_cost=round(input_cost + output_cost + cache_read_cost + cache_write_cost, 6),
        )

    def __repr__(self) -> str:
        return f"MiniMaxAnthropicProvider(model={self.model}, base_url={self.base_url})"
