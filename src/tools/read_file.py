"""Read file tool for agent file system access."""

from pathlib import Path
from typing import Any

from src.schema import TextContent, ToolInput, ToolResult
from src.tools.base import Tool


class ReadFileTool(Tool):
    """Tool to read file contents.

    Allows agents to read files within allowed directories.
    """

    def __init__(self, allowed_dirs: list[str] | None = None, max_size: int = 1024 * 1024):
        """Initialize read file tool.

        Args:
            allowed_dirs: List of allowed directory paths (default: [./data, ./docs])
            max_size: Maximum file size to read (bytes)
        """
        self.allowed_dirs = allowed_dirs or ["./data", "./docs"]
        self.max_size = max_size

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns the file content as text."

    @property
    def input_schema(self) -> ToolInput:
        return ToolInput(
            type="object",
            properties={
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to allowed directories)",
                },
            },
            required=["path"],
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """Read file and return contents.

        Args:
            path: File path to read

        Returns:
            ToolResult with file content or error
        """
        file_path = kwargs.get("path")
        if not file_path:
            return ToolResult.fail("Missing required argument: path")

        # Resolve path
        path = Path(file_path)

        # Check if absolute path is within allowed directories
        try:
            resolved = path.resolve()
            allowed = any(
                str(resolved).startswith(str(Path(d).resolve()))
                for d in self.allowed_dirs
            )
            if not allowed:
                return ToolResult.fail(
                    f"Access denied: {file_path} is not in allowed directories"
                )
        except (OSError, ValueError) as e:
            return ToolResult.fail(f"Invalid path: {e}")

        # Check if file exists
        if not path.exists():
            return ToolResult.fail(f"File not found: {file_path}")

        if not path.is_file():
            return ToolResult.fail(f"Not a file: {file_path}")

        # Check size
        try:
            size = path.stat().st_size
            if size > self.max_size:
                return ToolResult.fail(
                    f"File too large: {size} bytes (max {self.max_size})"
                )
        except OSError as e:
            return ToolResult.fail(f"Cannot access file: {e}")

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
            return ToolResult.ok(content)
        except UnicodeDecodeError:
            # Try binary and return hex representation for binary files
            try:
                content = path.read_bytes()
                return ToolResult.fail(f"Binary file ({len(content)} bytes)")
            except Exception as e:
                return ToolResult.fail(f"Cannot read file: {e}")
        except Exception as e:
            return ToolResult.fail(f"Read error: {e}")
