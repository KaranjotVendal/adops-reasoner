"""Session manager with file-based persistence.

pi-mono style: unlimited lifetime, automatic compaction, full traceability.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.schema import Message, TextContent
from src.session.models import Session, SessionSummary


class SessionManager:
    """Manages persistent conversation sessions.

    Features:
    - File-based storage (JSON)
    - Unlimited session lifetime
    - Automatic context compaction
    - Full message history
    """

    def __init__(self, storage_path: str | None = None, context_budget: int = 16000):
        """Initialize session manager.

        Args:
            storage_path: Directory for session files (default: ./data/sessions)
            context_budget: Token budget before compaction
        """
        self.storage_path = Path(storage_path or os.environ.get(
            "SESSION_STORAGE_PATH", "./data/sessions"
        ))
        self.context_budget = context_budget
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory if needed."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        """Get path to session file."""
        return self.storage_path / f"{session_id}.json"

    def create(
        self,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            system_prompt: Optional system message to initialize session
            metadata: Optional custom metadata

        Returns:
            New session instance
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        messages: list[Message] = []

        if system_prompt:
            messages.append(Message.system(system_prompt))

        session = Session(
            id=session_id,
            messages=messages,
            context_budget=self.context_budget,
            metadata=metadata or {},
        )

        self._save(session)
        return session

    def get(self, session_id: str) -> Session | None:
        """Load session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session or None if not found
        """
        file_path = self._session_file(session_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)
            return self._deserialize(data)
        except (json.JSONDecodeError, KeyError) as e:
            # Log error but don't crash
            print(f"Error loading session {session_id}: {e}")
            return None

    def add_message(self, session_id: str, message: Message) -> Session | None:
        """Add message to session and save.

        Args:
            session_id: Session identifier
            message: Message to add

        Returns:
            Updated session or None if not found
        """
        session = self.get(session_id)
        if not session:
            return None

        # Add timestamp to message
        message.timestamp = int(datetime.utcnow().timestamp() * 1000)

        session.add_message(message)

        # Check for compaction
        if session.needs_compaction():
            session = self._compact(session)

        self._save(session)
        return session

    def get_history(self, session_id: str) -> list[Message] | None:
        """Get full conversation history.

        Args:
            session_id: Session identifier

        Returns:
            List of messages or None if session not found
        """
        session = self.get(session_id)
        return session.messages if session else None

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions (metadata only, no full messages).

        Returns:
            List of session summaries
        """
        sessions = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                sessions.append({
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                    "metadata": data.get("metadata", {}),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self._session_file(session_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def _save(self, session: Session) -> None:
        """Save session to disk."""
        file_path = self._session_file(session.id)
        with open(file_path, "w") as f:
            json.dump(session.model_dump(), f, indent=2, default=str)

    def _deserialize(self, data: dict[str, Any]) -> Session:
        """Deserialize session from JSON."""
        # Parse messages
        messages = []
        for msg_data in data.get("messages", []):
            msg = Message.model_validate(msg_data)
            messages.append(msg)

        # Parse datetimes
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return Session(
            id=data.get("id", ""),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            messages=messages,
            context_budget=data.get("context_budget", self.context_budget),
            total_tokens_used=data.get("total_tokens_used", 0),
            metadata=data.get("metadata", {}),
        )

    def _compact(self, session: Session) -> Session:
        """Compact session when context budget exceeded.

        Strategy:
        1. Keep system message and most recent N messages
        2. Summarize middle messages into a single summary message
        3. Replace old messages with summary

        Args:
            session: Session to compact

        Returns:
            Compacted session
        """
        if len(session.messages) <= 3:
            # Too few messages to compact
            return session

        # Find system message (if any)
        system_msgs = [m for m in session.messages if m.role == "system"]
        other_msgs = [m for m in session.messages if m.role != "system"]

        # Keep last 4 messages, summarize the rest
        keep_count = 4
        if len(other_msgs) <= keep_count:
            return session

        to_summarize = other_msgs[:-keep_count]
        to_keep = other_msgs[-keep_count:]

        # Create simple summary (in production, use LLM to summarize)
        summary_text = self._create_summary(to_summarize)

        # Build new message list
        new_messages: list[Message] = []
        new_messages.extend(system_msgs)
        new_messages.append(Message.user(f"[Earlier conversation summary]: {summary_text}"))
        new_messages.extend(to_keep)

        session.messages = new_messages

        # Track compaction in metadata
        if "compactions" not in session.metadata:
            session.metadata["compactions"] = []
        session.metadata["compactions"].append({
            "at": datetime.utcnow().isoformat(),
            "messages_summarized": len(to_summarize),
            "summary_length": len(summary_text),
        })

        return session

    def _create_summary(self, messages: list[Message]) -> str:
        """Create summary of old messages.

        Simple implementation - in production use LLM.
        """
        # Extract text content
        texts = []
        for msg in messages:
            if isinstance(msg.content, str):
                texts.append(f"{msg.role}: {msg.content[:100]}...")
            else:
                for block in msg.content:
                    if hasattr(block, "text") and block.text:
                        texts.append(f"{msg.role}: {block.text[:100]}...")

        # Simple concatenation with truncation
        full_summary = " | ".join(texts)
        if len(full_summary) > 1000:
            full_summary = full_summary[:997] + "..."

        return full_summary
