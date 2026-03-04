"""Unified schema for multi-agent campaign analysis.

This module provides provider-agnostic data types that work with
Anthropic-style APIs (Kimi, MiniMax, and future providers).
"""

from .content import (
    ContentBlock,
    ContentBlockType,
    ImageContent,
    RedactedThinkingContent,
    SimpleContentBlock,
    TextContent,
    ThinkingContent,
    ToolResultContent,
    ToolUseBlock,
    ToolUseContent,
)
from .llm import CostBreakdown, LLMResponse, StopReason, TokenUsage
from .message import Message, MessageRole
from .tool import Tool, ToolInput, ToolResult

__all__ = [
    # Content blocks
    "ContentBlock",
    "ContentBlockType",
    "TextContent",
    "ThinkingContent",
    "RedactedThinkingContent",
    "ToolUseBlock",
    "ToolUseContent",
    "ToolResultContent",
    "ImageContent",
    # LLM response
    "LLMResponse",
    "TokenUsage",
    "StopReason",
    "CostBreakdown",
    # Messages
    "Message",
    "MessageRole",
    # Tools
    "Tool",
    "ToolInput",
    "ToolResult",
]
