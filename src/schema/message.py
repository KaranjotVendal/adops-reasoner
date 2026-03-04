"""Message types for conversation history."""

from typing import Literal
from pydantic import BaseModel, Field

from .content import ContentBlock

MessageRole = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    """Single message in conversation history.

    Supports both simple text messages (for API requests)
    and rich content blocks (for internal representation).
    """

    role: MessageRole = Field(..., description="Message role")
    content: str | list[ContentBlock] = Field(
        ...,
        description="Message content (string for API, blocks for internal)",
    )
    timestamp: int | None = Field(
        None,
        description="Unix timestamp in milliseconds (for session tracking)",
    )

    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: list[ContentBlock]) -> "Message":
        """Create an assistant message with content blocks."""
        return cls(role="assistant", content=content)

    @classmethod
    def tool_result(
        cls,
        tool_use_id: str,
        tool_name: str,
        result_blocks: list[ContentBlock],
        is_error: bool = False,
    ) -> "Message":
        """Create a tool result message.

        Following pi-mono pattern: tool results are sent as user messages
        with tool_result content blocks.
        """
        from .content import ToolResultContent

        return cls(
            role="user",
            content=[
                ToolResultContent(
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    content=result_blocks,
                    is_error=is_error,
                )
            ],
        )

    def to_text(self) -> str:
        """Convert message to plain text (for simple display)."""
        if isinstance(self.content, str):
            return self.content
        # For content blocks, extract text
        texts = []
        for block in self.content:
            if block.type == "text":
                texts.append(block.text)
            elif block.type == "thinking":
                texts.append(f"[Thinking: {block.thinking[:100]}...]")
            elif block.type == "tool_use":
                texts.append(f"[Tool call: {block.tool_use.name}]")
            elif block.type == "tool_result":
                texts.append(f"[Tool result from {block.tool_name}]")
        return "\n".join(texts)
