"""Tool registry for managing available tools."""

from typing import Any

from src.schema import Tool as ToolSchema, ToolResult
from src.tools.base import Tool


class ToolRegistry:
    """Registry for managing available tools.

    Provides tool lookup, schema generation, and execution.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        """Register a tool.

        Args:
            tool: Tool instance to register

        Returns:
            Self for chaining
        """
        self._tools[tool.name] = tool
        return self

    def register_all(self, tools: list[Tool]) -> "ToolRegistry":
        """Register multiple tools.

        Args:
            tools: List of tools to register

        Returns:
            Self for chaining
        """
        for tool in tools:
            self.register(tool)
        return self

    def get(self, name: str) -> Tool | None:
        """Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool or None if not found
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if tool exists.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self._tools

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_schemas(self) -> list[ToolSchema]:
        """Get all tool schemas for LLM.

        Returns:
            List of tool schemas
        """
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        tool = self.get(name)
        if not tool:
            return ToolResult.fail(f"Tool '{name}' not found")
        return tool.execute(**kwargs)

    def execute_tool_call(self, tool_use: Any) -> Any:
        """Execute from a ToolUseBlock.

        Args:
            tool_use: ToolUseBlock from LLM response

        Returns:
            ToolResult or error dict
        """
        from src.schema import ToolResultContent, TextContent

        name = tool_use.name if hasattr(tool_use, "name") else tool_use.get("name")
        tool_id = tool_use.id if hasattr(tool_use, "id") else tool_use.get("id")
        input_args = tool_use.input if hasattr(tool_use, "input") else tool_use.get("input", {})

        result = self.execute(name, **input_args)

        # Convert to ContentBlock format
        return ToolResultContent(
            tool_use_id=tool_id,
            tool_name=name,
            content=result.content,
            is_error=not result.success,
        )

    def __len__(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool exists: 'tool_name' in registry."""
        return self.has(name)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.list_tools()})"
