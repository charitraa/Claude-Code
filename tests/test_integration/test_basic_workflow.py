"""
Integration tests for basic workflow
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from claude_code.config import Settings
from claude_code.state import AppState, AppStateManager
from claude_code.commands import CommandRegistry
from claude_code.commands.builtin import InitCommand, ConfigCommand


@pytest.mark.integration
@pytest.mark.slow
class TestBasicWorkflow:
    """Integration tests for basic CLI workflow"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            yield workspace

    @pytest.fixture
    def initialized_workspace(self, temp_workspace):
        """Create an initialized workspace"""
        import os
        os.chdir(temp_workspace)

        # Create settings
        settings = Settings()
        settings.claude_dir = temp_workspace / ".claude"

        # Initialize workspace
        claude_dir = temp_workspace / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        config_file = claude_dir / "config.json"
        config = {
            "version": "1.0.0",
            "model": "claude-sonnet-4-20250514",
            "theme": "dark",
            "api_key": "test-api-key"
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return temp_workspace

    @pytest.mark.asyncio
    async def test_full_init_workflow(self, temp_workspace, mock_console):
        """Test complete initialization workflow"""
        import os
        os.chdir(temp_workspace)

        # Create command registry
        registry = CommandRegistry(console=mock_console)
        registry.register(InitCommand)

        # Execute init command
        result = await registry.execute("init", [], {})

        assert result.is_success()
        assert (temp_workspace / ".claude").exists()
        assert (temp_workspace / ".claude" / "config.json").exists()
        assert (temp_workspace / ".claude" / "sessions").exists()
        assert (temp_workspace / ".claude" / "cache").exists()

    @pytest.mark.asyncio
    async def test_config_workflow(self, initialized_workspace, mock_console):
        """Test configuration management workflow"""
        import os
        os.chdir(initialized_workspace)

        # Create command registry
        registry = CommandRegistry(console=mock_console)
        registry.register(ConfigCommand)

        # Test setting a config value
        result = await registry.execute("config", ["set", "model", "claude-opus-4-20250514"], {})
        assert result.is_success()

        # Test getting a config value
        result = await registry.execute("config", ["get", "model"], {})
        assert result.is_success()

        # Verify the value was set
        config_file = initialized_workspace / ".claude" / "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert config["model"] == "claude-opus-4-20250514"

    @pytest.mark.asyncio
    async def test_app_state_lifecycle(self, temp_workspace):
        """Test app state lifecycle"""
        import os
        os.chdir(temp_workspace)

        # Create settings
        settings = Settings()
        settings.claude_dir = temp_workspace / ".claude"

        # Create app state
        app_state = AppState(settings=settings)

        # Test initial state
        assert app_state.status == AppState.AppStateStatus.INITIALIZING

        # Update status
        await app_state.update_status(AppState.AppStateStatus.READY)
        assert app_state.status == AppState.AppStateStatus.READY

        # Add a message
        from claude_code.types import UserMessage, TextContent
        message = UserMessage(content=[TextContent(text="Hello")])
        await app_state.add_message(message)

        messages = app_state.get_messages()
        assert len(messages) == 1
        assert messages[0].role == "user"

        # Clear messages
        await app_state.clear_messages()
        assert len(app_state.get_messages()) == 0

    @pytest.mark.asyncio
    async def test_command_history_workflow(self, initialized_workspace, mock_console):
        """Test command history tracking"""
        import os
        os.chdir(initialized_workspace)

        # Create command registry
        registry = CommandRegistry(console=mock_console)
        registry.register(ConfigCommand)

        # Execute multiple commands
        await registry.execute("config", ["list"], {})
        await registry.execute("config", ["get", "model"], {})
        await registry.execute("config", ["get", "theme"], {})

        # Check history
        history = registry.get_history()
        assert len(history) >= 3

        # Verify history entries
        config_commands = [h for h in history if h["name"] == "config"]
        assert len(config_commands) >= 3

    @pytest.mark.asyncio
    async def test_command_dependency_workflow(self, initialized_workspace, mock_console):
        """Test command with dependencies"""
        import os
        os.chdir(initialized_workspace)

        # Create command registry
        registry = CommandRegistry(console=mock_console)
        registry.register(ConfigCommand)

        # Set up a command with dependencies
        registry.set_command_dependencies("config", ["init"])

        # Execute command with dependencies
        # Note: This is a simplified test - actual dependency resolution
        # would need the init command to be registered and executed first

        # For now, just verify the dependency was set
        dependencies = registry.get_command_dependencies("config")
        assert "init" in dependencies

    @pytest.mark.asyncio
    async def test_settings_persistence(self, temp_workspace):
        """Test settings persistence"""
        import os
        os.chdir(temp_workspace)

        # Create settings with custom values
        settings = Settings(
            ai={
                "model": "claude-opus-4-20250514",
                "max_tokens": 2000,
                "temperature": 0.8
            },
            theme={
                "mode": "light"
            }
        )

        # Convert to dict and back
        settings_dict = settings.to_dict()
        restored_settings = Settings.from_dict(settings_dict)

        assert restored_settings.ai.model == "claude-opus-4-20250514"
        assert restored_settings.ai.max_tokens == 2000
        assert restored_settings.ai.temperature == 0.8
        assert restored_settings.theme.mode == "light"

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, initialized_workspace, mock_console):
        """Test error handling in command execution"""
        import os
        os.chdir(initialized_workspace)

        # Create command registry
        registry = CommandRegistry(console=mock_console)
        registry.register(ConfigCommand)

        # Execute command that should fail (invalid action)
        result = await registry.execute("config", ["invalid_action"], {})

        assert not result.is_success()
        assert "invalid" in result.message.lower() or "unknown" in result.message.lower()

    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self, temp_workspace):
        """Test concurrent state updates"""
        import os
        os.chdir(temp_workspace)

        settings = Settings()
        settings.claude_dir = temp_workspace / ".claude"
        app_state = AppState(settings=settings)

        # Add multiple messages concurrently
        from claude_code.types import UserMessage, TextContent

        async def add_message(index):
            message = UserMessage(content=[TextContent(text=f"Message {index}")])
            await app_state.add_message(message)

        # Run concurrent additions
        await asyncio.gather(*[add_message(i) for i in range(10)])

        # Verify all messages were added
        messages = app_state.get_messages()
        assert len(messages) == 10


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_complete_user_session(self, temp_workspace, mock_console):
        """Test a complete user session workflow"""
        import os
        os.chdir(temp_workspace)

        # 1. Initialize workspace
        registry = CommandRegistry(console=mock_console)
        registry.register(InitCommand)
        result = await registry.execute("init", [], {})
        assert result.is_success()

        # 2. Configure settings
        registry.register(ConfigCommand)
        result = await registry.execute("config", ["set", "model", "claude-opus-4-20250514"], {})
        assert result.is_success()

        # 3. Verify configuration
        result = await registry.execute("config", ["get", "model"], {})
        assert result.is_success()

        # 4. Check command history
        history = registry.get_history()
        assert len(history) >= 3

        # 5. Verify workspace structure
        assert (temp_workspace / ".claude").exists()
        assert (temp_workspace / ".claude" / "config.json").exists()

    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_api_integration_workflow(self, initialized_workspace, mock_console):
        """Test API integration workflow (requires API key)"""
        import os
        os.chdir(initialized_workspace)

        # This test would require a valid API key
        # It's marked with @pytest.mark.requires_api to skip unless
        # explicitly run with API credentials

        # For now, this is a placeholder
        pytest.skip("Requires valid API key")
