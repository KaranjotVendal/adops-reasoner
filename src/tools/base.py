"""Base tool class for agent tool calling.

Following Anthropic tool format for LLM compatibility.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.schema import Tool as ToolSchema, ToolInput, ToolResult


class Tool(ABC):
    """Abstract base class for tools.

    Tools are callable units that agents can invoke via LLM tool calling.
    Each tool defines its name, description, input schema, and execution logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (snake_case recommended)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> ToolInput:
        """JSON Schema for tool arguments."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            **kwargs: Arguments validated against input_schema

        Returns:
            Tool execution result
        """
        pass

    def to_schema(self) -> ToolSchema:
        """Convert to ToolSchema for LLM tool calling."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )

    def __call__(self, **kwargs: Any) -> ToolResult:
        """Allow direct calling: tool(arg1="value")."""
        return self.execute(**kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
