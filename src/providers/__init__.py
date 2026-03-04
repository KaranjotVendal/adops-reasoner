"""LLM providers package.

Unified Anthropic-style providers for multi-model support.
"""

import os
from typing import Literal

from .base import AnthropicStyleProvider
from .kimi import KimiProvider
from .minimax_anthropic import MiniMaxAnthropicProvider

ProviderName = Literal["kimi", "minimax"]

# Model routing registry
MODEL_REGISTRY: dict[str, tuple[ProviderName, type[AnthropicStyleProvider]]] = {
    # Kimi models
    "k2p5": ("kimi", KimiProvider),
    "kimi-k2-thinking": ("kimi", KimiProvider),
    # MiniMax models
    "MiniMax-M2.5": ("minimax", MiniMaxAnthropicProvider),
    "MiniMax-M2.5-highspeed": ("minimax", MiniMaxAnthropicProvider),
}


def get_provider(model: str, api_key: str | None = None) -> AnthropicStyleProvider:
    """Factory function to create appropriate provider for a model.

    Args:
        model: Model ID (e.g., 'k2p5', 'MiniMax-M2.5')
        api_key: Optional API key (uses env var if not provided)

    Returns:
        Configured provider instance

    Raises:
        ValueError: If model ID is unknown
    """
    if model not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"Unknown model: {model}. Available: {available}")

    provider_name, provider_class = MODEL_REGISTRY[model]

    # Get API key from environment if not provided
    if api_key is None:
        env_vars = {
            "kimi": "KIMI_API_KEY",
            "minimax": "MINIMAX_API_KEY",
        }
        api_key = os.environ.get(env_vars[provider_name])

    return provider_class(api_key=api_key, model=model)


def get_default_analyzer_model() -> str:
    """Get default analyzer model from environment or fallback."""
    return os.environ.get("ANALYZER_MODEL", "k2p5")


def get_default_validator_model() -> str:
    """Get default validator model from environment or fallback."""
    return os.environ.get("VALIDATOR_MODEL", "MiniMax-M2.5")


__all__ = [
    "AnthropicStyleProvider",
    "KimiProvider",
    "MiniMaxAnthropicProvider",
    "get_provider",
    "get_default_analyzer_model",
    "get_default_validator_model",
    "MODEL_REGISTRY",
]
