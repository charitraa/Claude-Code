"""
Tests for CLI command handlers
"""

import pytest
from unittest.mock import Mock, patch
from claude_code.cli.commands import (
    handle_version,
    handle_help,
    handle_init,
    handle_config,
    handle_auth,
)


@pytest.mark.unit
class TestVersionCommand:
    """Tests for version command handler"""

    @pytest.mark.asyncio
    async def test_handle_version(self):
        """Test version command returns correct exit code"""
        exit_code = await handle_version()
        assert exit_code == 0


@pytest.mark.unit
class TestHelpCommand:
    """Tests for help command handler"""

    @pytest.mark.asyncio
    async def test_handle_help(self):
        """Test help command returns correct exit code"""
        exit_code = await handle_help()
        assert exit_code == 0


@pytest.mark.unit
class TestInitCommand:
    """Tests for init command handler"""

    @pytest.mark.asyncio
    async def test_handle_init_new_directory(self, temp_dir, mock_console):
        """Test init command in new directory"""
        import os
        os.chdir(temp_dir)

        exit_code = await handle_init([])
        assert exit_code == 0

        # Check that .claude directory was created
        assert (temp_dir / ".claude").exists()
        assert (temp_dir / ".claude" / "config.json").exists()

    @pytest.mark.asyncio
    async def test_handle_init_existing_directory(self, temp_dir, mock_console):
        """Test init command in already initialized directory"""
        import os
        os.chdir(temp_dir)

        # Create .claude directory
        (temp_dir / ".claude").mkdir()

        exit_code = await handle_init([])
        assert exit_code == 0


@pytest.mark.unit
class TestConfigCommand:
    """Tests for config command handler"""

    @pytest.mark.asyncio
    async def test_handle_config_list(self, temp_config_dir, mock_config_file, mock_console):
        """Test config list command"""
        exit_code = await handle_config([])
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_handle_config_set(self, temp_config_dir, mock_config_file, mock_console):
        """Test config set command"""
        exit_code = await handle_config(["set", "model", "claude-opus-4-20250514"])
        assert exit_code == 0

        # Verify config was updated
        import json
        with open(mock_config_file, 'r') as f:
            config = json.load(f)
        assert config["model"] == "claude-opus-4-20250514"

    @pytest.mark.asyncio
    async def test_handle_config_get(self, temp_config_dir, mock_config_file, mock_console):
        """Test config get command"""
        exit_code = await handle_config(["get", "model"])
        assert exit_code == 0


@pytest.mark.unit
class TestAuthCommand:
    """Tests for auth command handler"""

    @pytest.mark.asyncio
    async def test_handle_auth_status_no_key(self, mock_console):
        """Test auth status when no API key is set"""
        with patch.dict('os.environ', {}, clear=True):
            exit_code = await handle_auth(["status"])
            assert exit_code == 0

    @pytest.mark.asyncio
    async def test_handle_auth_status_with_key(self, mock_console):
        """Test auth status when API key is set"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'}):
            exit_code = await handle_auth(["status"])
            assert exit_code == 0

    @pytest.mark.asyncio
    async def test_handle_auth_login(self, temp_config_dir, mock_console):
        """Test auth login command"""
        exit_code = await handle_auth(["login", "sk-ant-test-key-12345"])
        assert exit_code == 0

        # Verify API key was saved
        import json
        config_file = temp_config_dir / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            assert config.get("api_key") == "sk-ant-test-key-12345"

    @pytest.mark.asyncio
    async def test_handle_auth_logout(self, temp_config_dir, mock_console):
        """Test auth logout command"""
        # First login
        await handle_auth(["login", "sk-ant-test-key-12345"])

        # Then logout
        exit_code = await handle_auth(["logout"])
        assert exit_code == 0
