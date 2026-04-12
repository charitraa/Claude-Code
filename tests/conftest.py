"""
Pytest configuration and fixtures for Claude Code CLI tests
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ===============================
# Async Configuration
# ===============================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===============================
# Temporary Directories
# ===============================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary config directory."""
    config_dir = temp_dir / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir


# ===============================
# Mock Configuration
# ===============================

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from claude_code.config import Settings

    settings = Settings(
        debug_mode=True,
        simple_mode=False,
        ai={
            "model": "claude-test-model",
            "max_tokens": 1000,
            "temperature": 0.5,
            "api_key": "test-api-key-12345",
        },
        theme={
            "mode": "dark",
            "colors_enabled": True,
        },
    )

    # Override with temp directory
    settings.claude_dir = temp_dir / ".claude" if 'temp_dir' in locals() else Path.home() / ".claude"

    return settings


@pytest.fixture
def mock_config_file(temp_config_dir):
    """Create a mock configuration file."""
    config_file = temp_config_dir / "config.json"

    default_config = {
        "version": "1.0.0",
        "model": "claude-sonnet-4-20250514",
        "theme": "dark",
        "enabled_tools": ["bash", "file", "search"],
        "disabled_tools": [],
        "api_key": "test-api-key-12345",
    }

    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)

    yield config_file


# ===============================
# Mock App State
# ===============================

@pytest.fixture
def mock_app_state(mock_settings):
    """Create a mock app state for testing."""
    from claude_code.state import AppState

    app_state = AppState(settings=mock_settings)
    app_state.status = AppState.AppStateStatus.READY

    return app_state


# ===============================
# Mock Tools
# ===============================

@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    from claude_code.tools import ToolRegistry

    registry = ToolRegistry()

    # Register a mock tool
    @registry.register
    class MockTool:
        name = "mock_tool"
        description = "A mock tool for testing"

        async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            return {"result": "mock_result", "success": True}

    return registry


@pytest.fixture
def mock_tool_executor():
    """Create a mock tool executor."""
    from claude_code.tools import ToolExecutionFramework

    executor = ToolExecutionFramework(tool_registry=Mock())

    return executor


# ===============================
# Mock API Client
# ===============================

@pytest.fixture
def mock_api_client():
    """Create a mock Claude API client."""
    client = Mock()

    # Mock async methods
    client.create_message = AsyncMock()
    client._messages_to_api_format = Mock(return_value=[])

    # Mock streaming response
    async def mock_stream():
        yield {"type": "chunk", "data": {"type": "content_block_start", "content_block": {"type": "text"}}}
        yield {"type": "chunk", "data": {"type": "content_block_delta", "delta": {"text": "Hello"}}}
        yield {"type": "chunk", "data": {"type": "content_block_stop"}}
        yield {"type": "chunk", "data": {"type": "message_stop"}}

    client.create_message.return_value = mock_stream()

    return client


# ===============================
# Mock Console
# ===============================

@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    from rich.console import Console
    from io import StringIO

    # Create console with string buffer for output capture
    console = Console(file=StringIO(), force_terminal=True)

    return console


# ===============================
# Mock Command Registry
# ===============================

@pytest.fixture
def mock_command_registry(mock_console):
    """Create a mock command registry."""
    from claude_code.commands import CommandRegistry

    registry = CommandRegistry(console=mock_console)

    # Register a test command
    from claude_code.commands.base import (
        BaseCommand,
        CommandResult,
        CommandStatus,
        CommandMetadata,
    )

    class TestCommand(BaseCommand):
        def _get_metadata(self) -> CommandMetadata:
            return CommandMetadata(
                name="test",
                description="Test command",
                category="test"
            )

        async def execute(self, args, options, context=None):
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Test command executed",
                data={"args": args, "options": options}
            )

    registry.register(TestCommand)

    return registry


# ===============================
# Mock MCP Server
# ===============================

@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server."""
    from claude_code.mcp import MCPServer

    server = MCPServer()

    # Start the server
    import asyncio
    asyncio.run(server.start())

    yield server

    # Cleanup
    asyncio.run(server.stop())


# ===============================
# Test Utilities
# ===============================

@pytest.fixture
def test_utils():
    """Provide test utility functions."""

    class TestUtils:
        @staticmethod
        def create_test_file(path: Path, content: str = "test content"):
            """Create a test file with given content."""
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        @staticmethod
        def create_test_directory(path: Path, structure: Dict[str, Any]):
            """
            Create a test directory structure.

            Args:
                path: Base directory path
                structure: Nested dict representing structure
                    {"file1.txt": "content", "dir1": {"file2.txt": "content"}}
            """
            for name, content in structure.items():
                item_path = path / name
                if isinstance(content, dict):
                    item_path.mkdir(parents=True, exist_ok=True)
                    TestUtils.create_test_directory(item_path, content)
                else:
                    item_path.write_text(content)

        @staticmethod
        async def wait_for_condition(condition, timeout=5.0, interval=0.1):
            """
            Wait for a condition to become true.

            Args:
                condition: Async function that returns bool
                timeout: Maximum wait time in seconds
                interval: Check interval in seconds
            """
            import time
            start = time.time()

            while time.time() - start < timeout:
                if await condition():
                    return True
                await asyncio.sleep(interval)

            return False

        @staticmethod
        def assert_dict_contains(subset: Dict, superset: Dict):
            """Assert that all key-value pairs in subset exist in superset."""
            for key, value in subset.items():
                assert key in superset, f"Key '{key}' not found in superset"
                assert superset[key] == value, f"Value mismatch for key '{key}'"

    return TestUtils()


# ===============================
# Pytest Hooks
# ===============================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add slow marker to integration tests
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.integration)

        # Add unit marker to unit tests
        if any(x in str(item.fspath) for x in ["test_tools", "test_cli", "test_commands"]):
            item.add_marker(pytest.mark.unit)