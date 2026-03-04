"""Write file tool for agent file system access."""

from pathlib import Path
from typing import Any

from src.schema import ToolInput, ToolResult
from src.tools.base import Tool


class WriteFileTool(Tool):
    """Tool to write file contents.

    Allows agents to create or overwrite files within allowed directories.
    """

    def __init__(self, allowed_dirs: list[str] | None = None, max_size: int = 1024 * 1024):
        """Initialize write file tool.

        Args:
            allowed_dirs: List of allowed directory paths (default: [./data, ./output])
            max_size: Maximum file size to write (bytes)
        """
        self.allowed_dirs = allowed_dirs or ["./data", "./output", "./docs"]
        self.max_size = max_size

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."

    @property
    def input_schema(self) -> ToolInput:
        return ToolInput(
            type="object",
            properties={
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to allowed directories)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            required=["path", "content"],
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """Write file with given content.

        Args:
            path: File path to write
            content: Content to write

        Returns:
            ToolResult with success status or error
        """
        file_path = kwargs.get("path")
        content = kwargs.get("content")

        if not file_path:
            return ToolResult.fail("Missing required argument: path")
        if content is None:
            return ToolResult.fail("Missing required argument: content")

        # Check content size
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > self.max_size:
            return ToolResult.fail(
                f"Content too large: {len(content_bytes)} bytes (max {self.max_size})"
            )

        # Resolve path
        path = Path(file_path)

        # Check if within allowed directories
        try:
            # If path is relative, resolve it
            if not path.is_absolute():
                # Try to find which allowed dir to use
                for allowed_dir in self.allowed_dirs:
                    candidate = Path(allowed_dir) / path
                    if str(candidate.resolve()).startswith(str(Path(allowed_dir).resolve())):
                        path = candidate
                        break
                else:
                    # Default to first allowed dir
                    path = Path(self.allowed_dirs[0]) / path

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

        # Ensure parent directory exists
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return ToolResult.fail(f"Cannot create directory: {e}")

        # Write file
        try:
            path.write_text(content, encoding="utf-8")
            return ToolResult.ok(f"Successfully wrote {len(content)} characters to {file_path}")
        except Exception as e:
            return ToolResult.fail(f"Write error: {e}")
