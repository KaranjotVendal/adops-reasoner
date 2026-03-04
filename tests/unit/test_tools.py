"""Tests for tool system."""

import tempfile
from pathlib import Path

import pytest

from src.tools import ReadFileTool, ToolRegistry, WriteFileTool


class TestReadFileTool:
    """Test read file tool."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def tool(self, temp_dir):
        """Create read file tool."""
        return ReadFileTool(allowed_dirs=[temp_dir])

    def test_read_existing_file(self, tool, temp_dir):
        """Test reading an existing file."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")

        result = tool.execute(path=str(test_file))

        assert result.success is True
        assert len(result.content) == 1
        assert result.content[0].text == "Hello, World!"

    def test_read_nonexistent_file(self, tool, temp_dir):
        """Test reading non-existent file."""
        result = tool.execute(path=f"{temp_dir}/nonexistent_file.txt")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_read_outside_allowed(self, tool):
        """Test reading file outside allowed directories."""
        result = tool.execute(path="/etc/passwd")

        assert result.success is False
        assert "access denied" in result.error_message.lower()

    def test_read_directory(self, tool, temp_dir):
        """Test reading a directory (should fail)."""
        result = tool.execute(path=temp_dir)

        assert result.success is False
        assert "not a file" in result.error_message.lower()

    def test_missing_path_argument(self, tool):
        """Test missing path argument."""
        result = tool.execute()

        assert result.success is False
        assert "missing" in result.error_message.lower()

    def test_tool_schema(self, tool):
        """Test tool schema generation."""
        schema = tool.to_schema()

        assert schema.name == "read_file"
        assert "read" in schema.description.lower()
        assert "path" in schema.input_schema.properties


class TestWriteFileTool:
    """Test write file tool."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def tool(self, temp_dir):
        """Create write file tool."""
        return WriteFileTool(allowed_dirs=[temp_dir])

    def test_write_new_file(self, tool, temp_dir):
        """Test writing a new file."""
        file_path = Path(temp_dir) / "output.txt"

        result = tool.execute(path=str(file_path), content="Test content")

        assert result.success is True
        assert file_path.exists()
        assert file_path.read_text() == "Test content"

    def test_overwrite_existing_file(self, tool, temp_dir):
        """Test overwriting an existing file."""
        file_path = Path(temp_dir) / "existing.txt"
        file_path.write_text("Original content")

        result = tool.execute(path=str(file_path), content="New content")

        assert result.success is True
        assert file_path.read_text() == "New content"

    def test_create_subdirectories(self, tool, temp_dir):
        """Test creating nested directories."""
        file_path = Path(temp_dir) / "nested" / "dir" / "file.txt"

        result = tool.execute(path=str(file_path), content="Nested content")

        assert result.success is True
        assert file_path.exists()

    def test_write_outside_allowed(self, tool):
        """Test writing outside allowed directories."""
        result = tool.execute(path="/etc/malicious.txt", content="bad")

        assert result.success is False
        assert "access denied" in result.error_message.lower()

    def test_missing_arguments(self, tool):
        """Test missing arguments."""
        result = tool.execute()
        assert result.success is False
        assert "missing" in result.error_message.lower()

        result = tool.execute(path="test.txt")
        assert result.success is False
        assert "missing" in result.error_message.lower()


class TestToolRegistry:
    """Test tool registry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = ReadFileTool()

        registry.register(tool)

        assert len(registry) == 1
        assert "read_file" in registry

    def test_register_multiple(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()

        registry.register_all([ReadFileTool(), WriteFileTool()])

        assert len(registry) == 2
        assert registry.list_tools() == ["read_file", "write_file"]

    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()
        tool = ReadFileTool()
        registry.register(tool)

        retrieved = registry.get("read_file")

        assert retrieved is not None
        assert retrieved.name == "read_file"

    def test_get_nonexistent_tool(self):
        """Test getting non-existent tool."""
        registry = ToolRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_execute_tool(self):
        """Test executing a tool through registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ToolRegistry()
            registry.register(ReadFileTool(allowed_dirs=[tmpdir]))

            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Registry test")

            result = registry.execute("read_file", path=str(test_file))

            assert result.success is True
            assert result.content[0].text == "Registry test"

    def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool."""
        registry = ToolRegistry()

        result = registry.execute("nonexistent", arg="value")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_get_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        registry.register_all([ReadFileTool(), WriteFileTool()])

        schemas = registry.get_schemas()

        assert len(schemas) == 2
        names = [s.name for s in schemas]
        assert "read_file" in names
        assert "write_file" in names
