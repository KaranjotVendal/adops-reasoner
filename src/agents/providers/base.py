"""Provider interface for LLM abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Structured response from LLM provider."""

    content: str
    raw_response: dict


class ProviderInterface(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def chatCompletion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional JSON schema for structured output

        Returns:
            LLMResponse with content and raw response
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available and authenticated."""
        pass
