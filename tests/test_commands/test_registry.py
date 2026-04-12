"""
Tests for Command Registry
"""

import pytest
from unittest.mock import Mock, AsyncMock

from claude_code.commands import (
    CommandRegistry,
    BaseCommand,
    CommandResult,
    CommandStatus,
    CommandMetadata,
)


@pytest.mark.unit
class TestCommandRegistry:
    """Tests for CommandRegistry"""

    @pytest.fixture
    def sample_command(self):
        """Create a sample command for testing"""

        class SampleCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="sample",
                    description="Sample command for testing",
                    category="test",
                    examples=["claude sample arg1"],
                    see_also=["help"]
                )

            async def execute(self, args, options, context=None):
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message="Sample executed",
                    data={"args": args, "options": options}
                )

        return SampleCommand

    @pytest.fixture
    def failing_command(self):
        """Create a command that fails for testing"""

        class FailingCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="failing",
                    description="Command that always fails",
                    category="test"
                )

            async def execute(self, args, options, context=None):
                raise ValueError("Test error")

        return FailingCommand

    def test_register_command(self, mock_command_registry, sample_command):
        """Test registering a command"""
        mock_command_registry.register(sample_command)
        assert "sample" in mock_command_registry.list_commands()

    def test_unregister_command(self, mock_command_registry, sample_command):
        """Test unregistering a command"""
        mock_command_registry.register(sample_command)
        assert mock_command_registry.unregister("sample") is True
        assert "sample" not in mock_command_registry.list_commands()

    def test_unregister_nonexistent_command(self, mock_command_registry):
        """Test unregistering a non-existent command"""
        assert mock_command_registry.unregister("nonexistent") is False

    def test_get_command(self, mock_command_registry, sample_command):
        """Test getting a registered command"""
        mock_command_registry.register(sample_command)
        command_class = mock_command_registry.get_command("sample")
        assert command_class == sample_command

    def test_get_command_with_alias(self, mock_command_registry, sample_command):
        """Test getting a command by alias"""
        # Create command with alias
        class AliasedCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="aliased",
                    description="Command with alias",
                    category="test",
                    aliases=["alias1", "alias2"]
                )

            async def execute(self, args, options, context=None):
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message="Aliased command executed"
                )

        mock_command_registry.register(AliasedCommand)

        # Should be accessible by any alias
        assert mock_command_registry.get_command("aliased") is not None
        assert mock_command_registry.get_command("alias1") is not None
        assert mock_command_registry.get_command("alias2") is not None

    def test_list_commands(self, mock_command_registry, sample_command):
        """Test listing all commands"""
        mock_command_registry.register(sample_command)
        commands = mock_command_registry.list_commands()
        assert "test" in commands
        assert "sample" in commands

    def test_list_commands_by_category(self, mock_command_registry, sample_command):
        """Test listing commands by category"""
        mock_command_registry.register(sample_command)
        test_commands = mock_command_registry.list_commands(category="test")
        assert "sample" in test_commands

    def test_get_command_info(self, mock_command_registry, sample_command):
        """Test getting command information"""
        mock_command_registry.register(sample_command)
        info = mock_command_registry.get_command_info("sample")

        assert info is not None
        assert info["name"] == "sample"
        assert info["description"] == "Sample command for testing"
        assert info["category"] == "test"
        assert "claude sample arg1" in info["examples"]
        assert "help" in info["see_also"]

    @pytest.mark.asyncio
    async def test_execute_command(self, mock_command_registry, sample_command):
        """Test executing a command"""
        mock_command_registry.register(sample_command)
        result = await mock_command_registry.execute("sample", ["arg1"], {"opt1": "val1"})

        assert result.is_success()
        assert result.message == "Sample executed"
        assert result.data["args"] == ["arg1"]
        assert result.data["options"] == {"opt1": "val1"}

    @pytest.mark.asyncio
    async def test_execute_failing_command(self, mock_command_registry, failing_command):
        """Test executing a command that fails"""
        mock_command_registry.register(failing_command)
        result = await mock_command_registry.execute("failing", [], {})

        assert not result.is_success()
        assert result.status == CommandStatus.ERROR
        assert "Test error" in result.message

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(self, mock_command_registry):
        """Test executing a non-existent command"""
        result = await mock_command_registry.execute("nonexistent", [], {})

        assert not result.is_success()
        assert result.status == CommandStatus.ERROR
        assert "not found" in result.message.lower()

    def test_command_history(self, mock_command_registry, sample_command):
        """Test command execution history"""
        mock_command_registry.register(sample_command)

        # Execute a command (sync for testing)
        import asyncio
        asyncio.run(mock_command_registry.execute("sample", [], {}))

        # Check history
        history = mock_command_registry.get_history()
        assert len(history) > 0
        assert history[-1]["name"] == "sample"

    def test_command_history_with_limit(self, mock_command_registry, sample_command):
        """Test command history with limit"""
        mock_command_registry.register(sample_command)

        # Execute multiple commands
        import asyncio
        for i in range(5):
            asyncio.run(mock_command_registry.execute("sample", [f"arg{i}"], {}))

        # Get limited history
        history = mock_command_registry.get_history(limit=3)
        assert len(history) == 3

    def test_command_history_filter(self, mock_command_registry, sample_command):
        """Test filtering command history by command name"""
        mock_command_registry.register(sample_command)

        # Execute commands
        import asyncio
        asyncio.run(mock_command_registry.execute("sample", [], {}))
        asyncio.run(mock_command_registry.execute("test", [], {}))

        # Filter history
        history = mock_command_registry.get_history(command_filter="sample")
        assert all(h["name"] == "sample" for h in history)

    def test_clear_history(self, mock_command_registry, sample_command):
        """Test clearing command history"""
        mock_command_registry.register(sample_command)

        # Execute a command
        import asyncio
        asyncio.run(mock_command_registry.execute("sample", [], {}))

        # Clear history
        mock_command_registry.clear_history()
        assert len(mock_command_registry.get_history()) == 0

    def test_search_commands(self, mock_command_registry, sample_command):
        """Test searching for commands"""
        mock_command_registry.register(sample_command)

        # Search by name
        results = mock_command_registry.search_commands("sample")
        assert "sample" in results

        # Search by description
        results = mock_command_registry.search_commands("testing")
        assert "sample" in results

    def test_before_execute_hook(self, mock_command_registry, sample_command):
        """Test before execute hook"""
        hook_called = []

        async def before_hook(name, args, options, context):
            hook_called.append(("before", name))

        mock_command_registry.add_before_execute_hook(before_hook)
        mock_command_registry.register(sample_command)

        # Execute command
        import asyncio
        asyncio.run(mock_command_registry.execute("sample", [], {}))

        assert len(hook_called) == 1
        assert hook_called[0] == ("before", "sample")

    def test_after_execute_hook(self, mock_command_registry, sample_command):
        """Test after execute hook"""
        hook_called = []

        async def after_hook(name, result, args, options, context):
            hook_called.append(("after", name, result.status))

        mock_command_registry.add_after_execute_hook(after_hook)
        mock_command_registry.register(sample_command)

        # Execute command
        import asyncio
        asyncio.run(mock_command_registry.execute("sample", [], {}))

        assert len(hook_called) == 1
        assert hook_called[0][0] == "after"
        assert hook_called[0][1] == "sample"
        assert hook_called[0][2] == CommandStatus.SUCCESS

    def test_get_stats(self, mock_command_registry, sample_command):
        """Test getting registry statistics"""
        mock_command_registry.register(sample_command)

        stats = mock_command_registry.get_stats()

        assert "total_commands" in stats
        assert stats["total_commands"] >= 2  # sample + test
        assert "categories" in stats
        assert "history_entries" in stats
