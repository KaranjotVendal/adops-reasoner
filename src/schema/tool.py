"""Tool types for agent tool use.

Following pi-mono patterns for extensible tool system.
"""

from typing import Any
from pydantic import BaseModel, Field

from .content import ContentBlock


class ToolInput(BaseModel):
    """Input schema for a tool (JSON Schema subset)."""

    type: str = Field(default="object", description="JSON type (always 'object' for tools)")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Property definitions",
    )
    required: list[str] = Field(
        default_factory=list,
        description="Required property names",
    )
    description: str | None = Field(None, description="Tool description")


class Tool(BaseModel):
    """Tool definition for LLM tool calling.

    Follows Anthropic/Claude Code tool format.
    """

    name: str = Field(..., description="Tool name (snake_case recommended)")
    description: str = Field(..., description="What the tool does")
    input_schema: ToolInput = Field(
        default_factory=ToolInput,
        description="JSON Schema for tool arguments",
    )

    def to_anthropic_schema(self) -> dict:
        """Convert to Anthropic API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.input_schema.properties,
                "required": self.input_schema.required,
            },
        }


class ToolResult(BaseModel):
    """Result of tool execution.

    Following pi-mono: tool results are content blocks that can include
    text, images, or error information.
    """

    success: bool = Field(..., description="Whether execution succeeded")
    content: list[ContentBlock] = Field(
        default_factory=list,
        description="Result content blocks (text, images, etc.)",
    )
    error_message: str | None = Field(
        None,
        description="Error message if success=False",
    )
    latency_ms: float = Field(default=0.0, description="Execution time")

    @classmethod
    def ok(cls, text: str, **kwargs) -> "ToolResult":
        """Create a successful tool result with text content."""
        from .content import TextContent

        return cls(
            success=True,
            content=[TextContent(text=text)],
            **kwargs,
        )

    @classmethod
    def fail(cls, message: str, **kwargs) -> "ToolResult":
        """Create a failed tool result."""
        return cls(
            success=False,
            error_message=message,
            **kwargs,
        )
