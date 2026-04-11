"""
Unit tests for configuration system
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import tempfile
import json

from claude_code.config.settings import (
    Settings,
    ThemeSettings,
    AISettings,
    ToolSettings,
)


class TestThemeSettings:
    """Test ThemeSettings model"""

    def test_theme_settings_defaults(self):
        """Test default theme settings"""
        settings = ThemeSettings()
        assert settings.mode == "dark"
        assert settings.colors_enabled is True
        assert settings.syntax_highlighting is True

    def test_theme_settings_customization(self):
        """Test custom theme settings"""
        settings = ThemeSettings(
            mode="light",
            colors_enabled=False
        )
        assert settings.mode == "light"
        assert settings.colors_enabled is False


class TestAISettings:
    """Test AISettings model"""

    def test_ai_settings_defaults(self):
        """Test default AI settings"""
        settings = AISettings()
        assert settings.model == "claude-sonnet-4-20250514"
        assert settings.max_tokens == 4096
        assert settings.temperature == 0.7

    def test_ai_settings_customization(self):
        """Test custom AI settings"""
        settings = AISettings(
            model="claude-3-opus-20240229",
            max_tokens=8192,
            temperature=0.5
        )
        assert settings.model == "claude-3-opus-20240229"
        assert settings.max_tokens == 8192
        assert settings.temperature == 0.5


class TestSettings:
    """Test Settings model"""

    def test_settings_defaults(self):
        """Test default settings"""
        settings = Settings()
        assert settings.version == "1.0.0"
        assert settings.debug_mode is False
        assert settings.simple_mode is False

    def test_settings_tool_enablement(self):
        """Test tool enablement methods"""
        settings = Settings(
            tools=ToolSettings(
                disabled_tools=["dangerous_tool"],
                enabled_tools=["safe_tool"]
            )
        )

        # Test disabled tools
        assert settings.is_tool_enabled("dangerous_tool") is False
        assert settings.is_tool_enabled("safe_tool") is True
        assert settings.is_tool_enabled("unknown_tool") is True  # Not in either list

    def test_settings_api_key_sources(self):
        """Test API key retrieval from different sources"""
        import os

        # Test with environment variable
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "test_key_from_env"

        settings = Settings()
        api_key = settings.get_api_key()
        assert api_key == "test_key_from_env"

        # Clean up
        if original_key is None:
            del os.environ["ANTHROPIC_API_KEY"]
        else:
            os.environ["ANTHROPIC_API_KEY"] = original_key

    def test_settings_directory_creation(self):
        """Test automatic directory creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(claude_dir=Path(tmpdir))
            assert settings.claude_dir.exists()
            assert settings.cache_dir.exists()
            assert settings.session_dir.exists()

    def test_settings_serialization(self):
        """Test settings serialization"""
        settings = Settings(
            ai=AISettings(model="claude-3-opus-20240229")
        )

        settings_dict = settings.to_dict()
        assert isinstance(settings_dict, dict)
        assert settings_dict["ai"]["model"] == "claude-3-opus-20240229"

    def test_settings_from_dict(self):
        """Test settings creation from dictionary"""
        settings_dict = {
            "version": "2.0.0",
            "debug_mode": True,
            "simple_mode": True,
            "ai": {
                "model": "claude-3-haiku-20240307"
            }
        }

        settings = Settings.from_dict(settings_dict)
        assert settings.version == "2.0.0"
        assert settings.debug_mode is True
        assert settings.simple_mode is True
        assert settings.ai.model == "claude-3-haiku-20240307"

    def test_project_config(self):
        """Test project-specific configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project directory
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # Create project config
            claude_dir = project_dir / ".claude"
            claude_dir.mkdir()
            config_file = claude_dir / "config.json"

            project_config = {
                "model": "custom-model",
                "theme": "light"
            }

            with open(config_file, 'w') as f:
                json.dump(project_config, f)

            # Test settings with project config
            global_settings = Settings()
            project_settings = global_settings.get_project_config(project_dir)

            # Project config should override defaults
            assert project_settings.ai.model == "custom-model"