"""Anthropic-style provider base class.

Unified interface for all LLM providers using Anthropic Messages API format.
Supports: Kimi, MiniMax (anthropic endpoint), and future providers.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..schema import CostBreakdown, LLMResponse, Message, TokenUsage, Tool


class AnthropicStyleProvider(ABC):
    """Abstract base for Anthropic-style LLM providers.

    All providers using Anthropic Messages API format inherit from this:
    - Kimi (api.kimi.com/coding/v1/messages)
    - MiniMax (api.minimax.io/anthropic/v1/messages)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ):
        """Initialize provider.

        Args:
            api_key: API key for authentication
            base_url: Base URL (e.g., https://api.kimi.com/coding)
            model: Model ID (e.g., 'k2p5', 'MiniMax-M2.5')
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name for logging/metadata (e.g., 'kimi', 'minimax')."""
        pass

    @property
    @abstractmethod
    def api_version(self) -> str:
        """Anthropic API version header value."""
        pass

    def _get_headers(self) -> dict[str, str]:
        """Get request headers following Anthropic pattern.

        Kimi and MiniMax both accept Bearer auth with Anthropic headers.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": self.api_version,
        }

    def _get_endpoint(self) -> str:
        """Get the messages endpoint URL."""
        return f"{self.base_url}/v1/messages"

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert internal Message objects to Anthropic API format.

        Handles system messages (extracted separately), user messages,
        and assistant messages with content blocks.
        """
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                # System messages handled separately via system parameter
                continue

            if msg.role == "user":
                api_messages.append(self._convert_user_message(msg))

            elif msg.role == "assistant":
                api_messages.append(self._convert_assistant_message(msg))

        return api_messages

    def _convert_user_message(self, msg: Message) -> dict[str, Any]:
        """Convert user message to Anthropic format."""
        if isinstance(msg.content, str):
            return {"role": "user", "content": msg.content}

        # Content blocks - convert to Anthropic format
        content_blocks = []
        for block in msg.content:
            if block.type == "text":
                content_blocks.append({"type": "text", "text": block.text})
            elif block.type == "image":
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": block.mime_type,
                        "data": block.data,
                    },
                })
            elif block.type == "tool_result":
                # Tool result as content block
                tool_result_content = []
                for result_block in block.content:
                    if result_block.type == "text":
                        tool_result_content.append({
                            "type": "text",
                            "text": result_block.text,
                        })
                    elif result_block.type == "image":
                        tool_result_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": result_block.mime_type,
                                "data": result_block.data,
                            },
                        })

                content_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "content": tool_result_content,
                    "is_error": block.is_error,
                })

        return {"role": "user", "content": content_blocks}

    def _convert_assistant_message(self, msg: Message) -> dict[str, Any]:
        """Convert assistant message to Anthropic format."""
        if isinstance(msg.content, str):
            return {"role": "assistant", "content": msg.content}

        # Content blocks
        content_blocks = []
        for block in msg.content:
            if block.type == "text":
                content_blocks.append({"type": "text", "text": block.text})
            elif block.type == "thinking":
                thinking_block = {
                    "type": "thinking",
                    "thinking": block.thinking,
                }
                if block.thinking_signature:
                    thinking_block["signature"] = block.thinking_signature
                content_blocks.append(thinking_block)
            elif block.type == "redacted_thinking":
                content_blocks.append({
                    "type": "redacted_thinking",
                    "data": block.data,
                })
            elif block.type == "tool_use":
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.tool_use.id,
                    "name": block.tool_use.name,
                    "input": block.tool_use.input,
                })

        return {"role": "assistant", "content": content_blocks}

    def _convert_tools(self, tools: list[Tool]) -> list[dict[str, Any]]:
        """Convert tools to Anthropic format."""
        return [tool.to_anthropic_schema() for tool in tools]

    def _extract_system_message(self, messages: list[Message]) -> str | None:
        """Extract system message from conversation."""
        for msg in messages:
            if msg.role == "system":
                if isinstance(msg.content, str):
                    return msg.content
                # Content blocks - extract text
                texts = []
                for block in msg.content:
                    if block.type == "text":
                        texts.append(block.text)
                return "\n".join(texts) if texts else None
        return None

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse Anthropic API response to unified LLMResponse.

        Args:
            data: Raw JSON response from Anthropic-style API

        Returns:
            Normalized LLMResponse
        """
        from ..schema import (
            ContentBlock,
            RedactedThinkingContent,
            StopReason,
            TextContent,
            ThinkingContent,
            TokenUsage,
            ToolUseBlock,
            ToolUseContent,
        )

        # Extract content blocks
        content: list[ContentBlock] = []
        for block in data.get("content", []):
            block_type = block.get("type")

            if block_type == "text":
                content.append(TextContent(text=block.get("text", "")))

            elif block_type == "thinking":
                content.append(
                    ThinkingContent(
                        thinking=block.get("thinking", ""),
                        thinking_signature=block.get("signature"),
                    )
                )

            elif block_type == "redacted_thinking":
                content.append(
                    RedactedThinkingContent(data=block.get("data", ""))
                )

            elif block_type == "tool_use":
                content.append(
                    ToolUseContent(
                        tool_use=ToolUseBlock(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            input=block.get("input", {}),
                        )
                    )
                )

        # Extract usage
        usage_data = data.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
            cache_write_tokens=usage_data.get("cache_creation_input_tokens", 0),
        )
        usage.total_tokens = (
            usage.input_tokens + usage.output_tokens +
            usage.cache_read_tokens + usage.cache_write_tokens
        )

        # Map stop reason
        stop_reason_map: dict[str, StopReason] = {
            "end_turn": "stop",
            "max_tokens": "length",
            "tool_use": "tool_use",
            "stop_sequence": "stop",
        }
        stop_reason = stop_reason_map.get(
            data.get("stop_reason", ""), "stop"
        )

        # Calculate cost (to be implemented by subclasses)
        cost = self._calculate_cost(usage)

        return LLMResponse(
            content=content,
            usage=usage,
            cost=cost,
            latency_ms=0,  # Set by caller
            model=self.model,
            provider=self.provider_name,
            stop_reason=stop_reason,
        )

    @abstractmethod
    def _calculate_cost(self, usage: TokenUsage) -> CostBreakdown:
        """Calculate cost for this provider's pricing.

        Args:
            usage: Token usage statistics

        Returns:
            Cost breakdown in USD
        """
        pass

    def generate(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thinking: bool = False,
    ) -> LLMResponse:
        """Generate response from LLM.

        Synchronous wrapper for the async implementation.

        Args:
            messages: Conversation messages
            tools: Available tools for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            thinking: Whether to enable thinking/reasoning

        Returns:
            Normalized LLM response
        """
        import time

        start_time = time.time()

        # Build request payload
        api_messages = self._convert_messages(messages)
        system_message = self._extract_system_message(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": api_messages,
            "temperature": temperature,
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            payload["tools"] = self._convert_tools(tools)

        if thinking:
            payload["thinking"] = {"type": "enabled"}

        # Make request
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._get_endpoint(),
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Parse response
        llm_response = self._parse_response(data)
        llm_response.latency_ms = (time.time() - start_time) * 1000

        return llm_response

    async def generate_async(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        thinking: bool = False,
    ) -> LLMResponse:
        """Async version of generate."""
        import time

        start_time = time.time()

        api_messages = self._convert_messages(messages)
        system_message = self._extract_system_message(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": api_messages,
            "temperature": temperature,
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            payload["tools"] = self._convert_tools(tools)

        if thinking:
            payload["thinking"] = {"type": "enabled"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self._get_endpoint(),
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        llm_response = self._parse_response(data)
        llm_response.latency_ms = (time.time() - start_time) * 1000

        return llm_response

    def health_check(self) -> bool:
        """Check if provider is available and authenticated."""
        try:
            # Simple test request
            test_messages = [Message.user("Hi")]
            self.generate(test_messages, max_tokens=5, temperature=0.1)
            return True
        except Exception:
            return False
