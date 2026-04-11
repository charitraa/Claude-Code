"""
Configuration system for Claude Code CLI
Converted from TypeScript config system
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from ..types import PermissionLevel, ToolCategory


class ThemeSettings(BaseModel):
    """Theme configuration"""
    mode: str = "dark"
    colors_enabled: bool = True
    syntax_highlighting: bool = True


class AISettings(BaseModel):
    """AI/Model configuration"""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ToolSettings(BaseModel):
    """Tool configuration"""
    default_permission_level: PermissionLevel = PermissionLevel.ASK
    enabled_tools: List[str] = Field(default_factory=list)
    disabled_tools: List[str] = Field(default_factory=list)
    tool_presets: List[str] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    """MCP server configuration"""
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: dict = Field(default_factory=dict)


class MCPSettings(BaseModel):
    """MCP configuration"""
    enabled: bool = True
    servers: dict = Field(default_factory=dict)


class GitSettings(BaseModel):
    """Git configuration"""
    auto_commit: bool = False
    commit_message_template: str = "claude: {description}"
    include_diff_in_messages: bool = True


class LoggingSettings(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    file_path: Optional[str] = None
    console_output: bool = True


class PerformanceSettings(BaseModel):
    """Performance configuration"""
    startup_profiling: bool = False
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300


class SecuritySettings(BaseModel):
    """Security configuration"""
    allow_network_access: bool = True
    allow_system_commands: bool = True
    sandbox_mode: bool = False


class Settings(BaseModel):
    """
    Main settings class for Claude Code CLI

    Equivalent to TypeScript GlobalConfig and ProjectConfig combined
    """

    # Core settings
    version: str = "1.0.0"
    debug_mode: bool = False
    simple_mode: bool = False

    # Feature flags
    feature_background_tasks: bool = True
    feature_agent_swarms: bool = False
    feature_mcp: bool = True
    feature_worktree: bool = True

    # Component settings
    theme: ThemeSettings = Field(default_factory=ThemeSettings)
    ai: AISettings = Field(default_factory=AISettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    git: GitSettings = Field(default_factory=GitSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # Directory settings
    claude_dir: Path = Field(
        default_factory=lambda: Path.home() / ".claude"
    )
    project_dir: Optional[Path] = None
    cache_dir: Optional[Path] = None

    # Session settings
    session_persistence: bool = True
    session_dir: Optional[Path] = None

    @property
    def log_level(self) -> str:
        """Get log level for logging setup"""
        return self.logging.level

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_directories()

    def _setup_directories(self) -> None:
        """Setup and create necessary directories"""
        # Create main Claude directory
        self.claude_dir.mkdir(parents=True, exist_ok=True)

        # Setup cache directory
        if not self.cache_dir:
            self.cache_dir = self.claude_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Setup session directory
        if not self.session_dir:
            self.session_dir = self.claude_dir / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_project_config(self, project_path: Path) -> "Settings":
        """
        Get project-specific settings

        Args:
            project_path: Path to the project directory

        Returns:
            Settings with project-specific overrides
        """
        config_file = project_path / ".claude" / "config.json"
        if not config_file.exists():
            return self

        # Load project config and merge with global settings
        # (Implementation would read JSON file and override values)
        return self

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if a tool is enabled

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is enabled, False otherwise
        """
        if tool_name in self.tools.disabled_tools:
            return False

        if self.tools.enabled_tools and tool_name not in self.tools.enabled_tools:
            return False

        return True

    def get_api_key(self) -> Optional[str]:
        """
        Get Anthropic API key from various sources

        Returns:
            API key if found, None otherwise
        """
        # Check explicit setting first
        if self.ai.api_key:
            return self.ai.api_key

        # Check environment variable
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            return env_key

        # Check from keyring (would need keyring library)
        # This is a placeholder for keyring integration
        return None

    def to_dict(self) -> dict:
        """
        Convert settings to dictionary for serialization

        Returns:
            Dictionary representation of settings
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """
        Create settings from dictionary

        Args:
            data: Dictionary of settings

        Returns:
            Settings instance
        """
        return cls(**data)