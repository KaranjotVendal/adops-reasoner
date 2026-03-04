"""Tests for session management."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.schema import Message
from src.session import SessionManager


class TestSessionManager:
    """Test session manager functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_storage):
        """Create session manager with temp storage."""
        return SessionManager(storage_path=temp_storage, context_budget=1000)

    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create(system_prompt="You are a test assistant")

        assert session.id.startswith("sess_")
        assert len(session.messages) == 1
        assert session.messages[0].role == "system"
        assert session.context_budget == 1000

    def test_get_session(self, manager):
        """Test retrieving a session."""
        created = manager.create(system_prompt="Test")
        retrieved = manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert len(retrieved.messages) == 1

    def test_get_nonexistent_session(self, manager):
        """Test retrieving non-existent session."""
        result = manager.get("sess_nonexistent")
        assert result is None

    def test_add_message(self, manager):
        """Test adding messages to session."""
        session = manager.create(system_prompt="Test system prompt")

        updated = manager.add_message(session.id, Message.user("Hello"))

        assert updated is not None
        assert len(updated.messages) == 2  # system + user
        assert updated.messages[1].role == "user"
        assert updated.messages[1].content == "Hello"

    def test_add_message_to_nonexistent(self, manager):
        """Test adding message to non-existent session."""
        result = manager.add_message("sess_nonexistent", Message.user("Hello"))
        assert result is None

    def test_list_sessions(self, manager):
        """Test listing sessions."""
        # Create some sessions
        s1 = manager.create(metadata={"name": "session1"})
        s2 = manager.create(metadata={"name": "session2"})

        sessions = manager.list_sessions()

        assert len(sessions) == 2
        ids = [s["id"] for s in sessions]
        assert s1.id in ids
        assert s2.id in ids

    def test_delete_session(self, manager):
        """Test deleting a session."""
        session = manager.create()

        result = manager.delete(session.id)

        assert result is True
        assert manager.get(session.id) is None

    def test_delete_nonexistent(self, manager):
        """Test deleting non-existent session."""
        result = manager.delete("sess_nonexistent")
        assert result is False

    def test_persistence(self, manager, temp_storage):
        """Test that sessions persist to disk."""
        session = manager.create(system_prompt="Persistent session")
        manager.add_message(session.id, Message.user("Test message"))

        # Create new manager pointing to same storage
        new_manager = SessionManager(storage_path=temp_storage)
        retrieved = new_manager.get(session.id)

        assert retrieved is not None
        assert retrieved.id == session.id
        assert len(retrieved.messages) == 2

    def test_estimate_tokens(self, manager):
        """Test token estimation."""
        session = manager.create(system_prompt="Short prompt")

        # Add some messages
        session.add_message(Message.user("Hello world"))
        session.add_message(Message.assistant([{"type": "text", "text": "Hi there"}]))

        tokens = session.estimate_tokens()
        # Should be roughly (5+11+5+8)/4 = 7 tokens
        assert tokens > 0
        assert tokens < 50  # Very rough upper bound
