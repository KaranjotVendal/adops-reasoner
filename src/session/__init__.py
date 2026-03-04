"""Session management for persistent conversation state.

pi-mono style: file-based storage with unlimited lifetime.
"""

from .manager import SessionManager
from .models import Session

__all__ = ["SessionManager", "Session"]
