"""MiniMax provider implementation."""

import os

import httpx

from .base import LLMResponse, ProviderInterface


class MiniMaxProvider(ProviderInterface):
    """MiniMax LLM provider (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/v1",
        model: str = "MiniMax-M2.5",
        timeout: float = 60.0,
    ):
        """Initialize MiniMax provider.

        Args:
            api_key: MiniMax API key (defaults to MINIMAX_API_KEY env var)
            base_url: API base URL
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chatCompletion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to MiniMax."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if response_format:
            payload["response_format"] = response_format

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Following Mini-Agent pattern: message.content can be None when tool_calls present
        message = data["choices"][0]["message"]
        content = message.get("content")
        # Store full response for advanced parsing (tool_calls, usage, etc.)
        return LLMResponse(content=content, raw_response=data)

    def health_check(self) -> bool:
        """Check if MiniMax API is accessible."""
        try:
            self.chatCompletion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                temperature=0.1,
            )
            return True
        except Exception:
            return False
