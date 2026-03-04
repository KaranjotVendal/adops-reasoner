"""Kimi provider implementation (Anthropic-style API).

Uses Kimi's Anthropic-compatible endpoint:
https://api.kimi.com/coding/v1/messages
"""

import os
from typing import override

from .base import AnthropicStyleProvider
from ..schema import CostBreakdown, TokenUsage


class KimiProvider(AnthropicStyleProvider):
    """Kimi LLM provider using Anthropic Messages API.

    Supports models:
    - k2p5 (Kimi K2.5)
    - kimi-k2-thinking (Kimi K2 Thinking)

    Requires KIMI_API_KEY environment variable.
    """

    AVAILABLE_MODELS = ["k2p5", "kimi-k2-thinking"]
    DEFAULT_MODEL = "k2p5"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ):
        """Initialize Kimi provider.

        Args:
            api_key: Kimi API key (defaults to KIMI_API_KEY env var)
            model: Model ID (k2p5 or kimi-k2-thinking)
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key not provided and KIMI_API_KEY not set
        """
        key = api_key or os.environ.get("KIMI_API_KEY")
        if not key:
            raise ValueError(
                "Kimi API key required. Set KIMI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if model not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown Kimi model: {model}. "
                f"Available: {', '.join(self.AVAILABLE_MODELS)}"
            )

        super().__init__(
            api_key=key,
            base_url="https://api.kimi.com/coding",
            model=model,
            timeout=timeout,
        )

    @property
    @override
    def provider_name(self) -> str:
        return "kimi"

    @property
    @override
    def api_version(self) -> str:
        # Kimi uses Anthropic API version 2023-06-01
        return "2023-06-01"

    @override
    def _calculate_cost(self, usage: TokenUsage) -> CostBreakdown:
        """Calculate cost for Kimi API.

        Kimi pricing (as of testing):
        - k2p5: Currently free during beta period
        """
        # During beta, Kimi is free
        # Update this when pricing is announced
        return CostBreakdown(
            input_cost=0.0,
            output_cost=0.0,
            cache_read_cost=0.0,
            cache_write_cost=0.0,
            total_cost=0.0,
        )

    def __repr__(self) -> str:
        return f"KimiProvider(model={self.model}, base_url={self.base_url})"
