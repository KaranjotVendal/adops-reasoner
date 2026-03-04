"""Content block types for unified LLM response handling.

Following pi-mono patterns for Anthropic-style API compatibility.
Supports: text, thinking, tool_use, redacted_thinking, tool_result
"""

from typing import Literal
from pydantic import BaseModel, Field

ContentBlockType = Literal["text", "thinking", "tool_use", "redacted_thinking", "tool_result"]


class TextContent(BaseModel):
    """Plain text content block."""

    type: Literal["text"] = "text"
    text: str = Field(..., description="The text content")


class ThinkingContent(BaseModel):
    """Model's chain-of-thought / reasoning content.

    Captures the model's internal reasoning process. For multi-turn
    continuity, the thinking_signature may be preserved.
    """

    type: Literal["thinking"] = "thinking"
    thinking: str = Field(..., description="The reasoning text")
    thinking_signature: str | None = Field(
        None,
        description="Signature for multi-turn continuity (Anthropic-specific)",
    )


class RedactedThinkingContent(BaseModel):
    """Redacted thinking block (safety filtered).

    When thinking is redacted by safety filters, an opaque payload
    is provided for API continuity in multi-turn conversations.
    """

    type: Literal["redacted_thinking"] = "redacted_thinking"
    data: str = Field(..., description="Opaque redacted payload")


class ToolUseBlock(BaseModel):
    """Tool call request from the model."""

    id: str = Field(..., description="Unique tool call ID")
    name: str = Field(..., description="Tool name to invoke")
    input: dict = Field(default_factory=dict, description="Tool arguments")


class ToolUseContent(BaseModel):
    """Tool use content block (model requesting tool execution)."""

    type: Literal["tool_use"] = "tool_use"
    tool_use: ToolUseBlock = Field(..., description="Tool call details")


class ToolResultContent(BaseModel):
    """Tool execution result sent back to model.

    Following pi-mono pattern: tool results are content blocks
    that can include text and/or images.
    """

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = Field(..., description="ID of the tool call being responded to")
    tool_name: str = Field(..., description="Name of the tool that was executed")
    # Note: content is list of simple blocks (text/image), not recursive tool_result
    content: list["SimpleContentBlock"] = Field(
        default_factory=list,
        description="Result content (text, images, etc.)",
    )
    is_error: bool = Field(default=False, description="Whether the tool execution failed")


class ImageContent(BaseModel):
    """Image content block (for vision capabilities)."""

    type: Literal["image"] = "image"
    data: str = Field(..., description="Base64-encoded image data")
    mime_type: str = Field(..., description="Image MIME type (e.g., image/jpeg)")


# Simple content blocks (for tool results - no nesting)
SimpleContentBlock = TextContent | ImageContent

# Union type for all content blocks
ContentBlock = (
    TextContent
    | ThinkingContent
    | RedactedThinkingContent
    | ToolUseContent
    | ToolResultContent
    | ImageContent
)
