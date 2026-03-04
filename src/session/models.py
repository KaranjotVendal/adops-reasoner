"""Session models for persistent conversation state.

Following pi-mono patterns for session management.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from src.schema import Message


class Session(BaseModel):
    """A conversation session with persistent state.

    Sessions have unlimited lifetime and full traceability.
    Context compaction happens automatically when budget exceeded.
    """

    id: str = Field(..., description="Unique session ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[Message] = Field(default_factory=list)
    context_budget: int = Field(default=16000, description="Max tokens before compaction")
    total_tokens_used: int = Field(default=0, description="Cumulative token usage")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom session metadata")

    def add_message(self, message: Message) -> "Session":
        """Add a message and update timestamp."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return self

    def get_messages(self) -> list[Message]:
        """Get conversation history."""
        return self.messages.copy()

    def estimate_tokens(self) -> int:
        """Rough token estimate for context budget checking.

        Uses simple heuristic: ~4 chars per token.
        """
        total_chars = 0
        for msg in self.messages:
            if isinstance(msg.content, str):
                total_chars += len(msg.content)
            else:
                # Content blocks - count text blocks
                for block in msg.content:
                    if hasattr(block, "text") and block.text:
                        total_chars += len(block.text)
                    elif hasattr(block, "thinking") and block.thinking:
                        total_chars += len(block.thinking)
        return total_chars // 4

    def needs_compaction(self) -> bool:
        """Check if session exceeds context budget."""
        return self.estimate_tokens() > self.context_budget

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override to handle datetime serialization."""
        data = super().model_dump(**kwargs)
        # Convert datetime to ISO format strings
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data.get("updated_at"), datetime):
            data["updated_at"] = data["updated_at"].isoformat()
        return data


class SessionSummary(BaseModel):
    """Summary of old messages after compaction."""

    original_message_count: int
    summary: str
    preserved_message_ids: list[str] = Field(default_factory=list)
    compacted_at: datetime = Field(default_factory=datetime.utcnow)
