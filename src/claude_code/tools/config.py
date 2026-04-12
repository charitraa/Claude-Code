"""
Configuration management tools for Claude Code CLI (Fixed version)
Allows runtime settings modification
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)
from ..config.settings import Settings


class ConfigSetInput(BaseModel):
    """Input schema for ConfigSet tool"""

    key: str = Field(..., description="Configuration key to set")
    value: Any = Field(..., description="Configuration value to set")
    scope: Optional[str] = Field(default=None, description="Configuration scope (global, project)")


class ConfigGetInput(BaseModel):
    """Input schema for ConfigGet tool"""

    key: Optional[str] = Field(default=None, description="Configuration key to get (omit for all)")
    scope: Optional[str] = Field(default=None, description="Configuration scope (global, project)")


class ConfigListInput(BaseModel):
    """Input schema for ConfigList tool"""

    scope: Optional[str] = Field(default=None, description="Configuration scope to list (omit for all)")


class ConfigResetInput(BaseModel):
    """Input schema for ConfigReset tool"""

    key: Optional[str] = Field(default=None, description="Configuration key to reset (omit for all)")
    scope: Optional[str] = Field(default=None, description="Configuration scope to reset")
    defaults: bool = Field(default=False, description="Reset to defaults instead of deleting")


class ConfigSetTool(Tool):
    """
    Configuration set tool for modifying runtime settings

    Replaces TypeScript config set functionality
    """

    # Tool metadata
    name: str = "ConfigSet"
    description: str = "Set configuration value"
    category: ToolCategory = ToolCategory.CONFIG
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        # Configuration file paths
        self.global_config_path = Path.home() / ".claude" / "config.json"
        self.project_config_path = Path.cwd() / ".claude" / "config.json"

    async def execute(
        self,
        input_data: ConfigSetInput,
        context: ToolContext
    ) -> ToolResult:
        """Set configuration value"""
        import time
        start_time = time.time()

        try:
            # Determine config file
            config_file = self._get_config_file(input_data.scope)

            # Read existing config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}

            # Update configuration
            self._set_config_value(config, input_data.key, input_data.value)

            # Save configuration
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Set {input_data.key} = {input_data.value} in {input_data.scope or 'default'} scope",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "config_file": str(config_file),
                    "scope": input_data.scope or "default",
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _get_config_file(self, scope: Optional[str]) -> Path:
        """Get appropriate config file path"""
        if scope == "project":
            return self.project_config_path
        else:
            return self.global_config_path

    def _set_config_value(self, config: dict, key: str, value: Any) -> None:
        """Set a configuration value with proper nesting"""
        keys = key.split('.')
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
        current[keys[-1]] = value

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Configuration key to set",
                    },
                    "value": {
                        "type": "any",
                        "description": "Configuration value to set",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Configuration scope (global, project)",
                    },
                },
                "required": ["key", "value"],
            },
        )


class ConfigGetTool(Tool):
    """
    Configuration get tool for retrieving settings

    Replaces TypeScript config get functionality
    """

    # Tool metadata
    name: str = "ConfigGet"
    description: str = "Get configuration value"
    category: ToolCategory = ToolCategory.CONFIG
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        # Reuse config file paths from ConfigSetTool
        self.global_config_path = Path.home() / ".claude" / "config.json"
        self.project_config_path = Path.cwd() / ".claude" / "config.json"

    async def execute(
        self,
        input_data: ConfigGetInput,
        context: ToolContext
    ) -> ToolResult:
        """Get configuration value"""
        import time
        start_time = time.time()

        try:
            # Determine config file
            config_file = self._get_config_file(input_data.scope)

            # Read configuration
            if not config_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Configuration file not found: {config_file}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            with open(config_file, 'r') as f:
                config = json.load(f)

            # Get configuration value
            if input_data.key:
                keys = input_data.key.split('.')
                value = config
                for k in keys:
                    if k in value:
                        value = value[k]
                    else:
                        value = None

                result_content = f"{input_data.key} = {value}"
            else:
                # Show all configuration
                result_content = self._format_config_display(config)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=result_content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "config_file": str(config_file),
                    "scope": input_data.scope or "default",
                    "config": config,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _format_config_display(self, config: dict) -> str:
        """Format configuration for display"""
        lines = ["Current Configuration:"]

        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"  {key} = {value}")
            elif isinstance(value, dict):
                lines.append(f"  {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"    {sub_key} = {sub_value}")
            else:
                lines.append(f"  {key} = {type(value).__name__}")

        return '\n'.join(lines)

    def _get_config_file(self, scope: Optional[str]) -> Path:
        """Get appropriate config file path"""
        if scope == "project":
            return self.project_config_path
        else:
            return self.global_config_path

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Configuration key to get (omit for all)",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Configuration scope (global, project)",
                    },
                },
                "required": [],
            },
        )


class ConfigListTool(Tool):
    """
    Configuration list tool for showing all settings

    Replaces TypeScript config list functionality
    """

    # Tool metadata
    name: str = "ConfigList"
    description: str = "List all configuration values"
    category: ToolCategory = ToolCategory.CONFIG
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        # Reuse config file paths from ConfigSetTool
        self.global_config_path = Path.home() / ".claude" / "config.json"
        self.project_config_path = Path.cwd() / ".claude" / "config.json"

    async def execute(
        self,
        input_data: ConfigListInput,
        context: ToolContext
    ) -> ToolResult:
        """List configuration values"""
        import time
        start_time = time.time()

        try:
            # Determine config file
            config_file = self._get_config_file(input_data.scope)

            # Read configuration
            if not config_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Configuration file not found: {config_file}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            with open(config_file, 'r') as f:
                config = json.load(f)

            # Format configuration for display
            result_content = self._format_config_display(config)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=result_content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "config_file": str(config_file),
                    "scope": input_data.scope or "default",
                    "config": config,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _format_config_display(self, config: dict) -> str:
        """Format configuration for display"""
        lines = ["Current Configuration:"]

        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"  {key} = {value}")
            elif isinstance(value, dict):
                lines.append(f"  {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"    {sub_key} = {sub_value}")
            else:
                lines.append(f"  {key} = {type(value).__name__}")

        return '\n'.join(lines)

    def _get_config_file(self, scope: Optional[str]) -> Path:
        """Get appropriate config file path"""
        if scope == "project":
            return self.project_config_path
        else:
            return self.global_config_path

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Configuration scope to list (omit for all)",
                    },
                },
                "required": [],
            },
        )


class ConfigResetTool(Tool):
    """
    Configuration reset tool for resetting settings

    Replaces TypeScript config reset functionality
    """

    # Tool metadata
    name: str = "ConfigReset"
    description: str = "Reset configuration to defaults"
    category: ToolCategory = ToolCategory.CONFIG
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        # Default configuration
        self.default_config = {
            "version": "1.0.0",
            "debug_mode": False,
            "simple_mode": False,
            "feature_background_tasks": True,
            "feature_agent_swarms": False,
            "feature_mcp": True,
            "feature_worktree": True,
        }

    async def execute(
        self,
        input_data: ConfigResetInput,
        context: ToolContext
    ) -> ToolResult:
        """Reset configuration"""
        import time
        start_time = time.time()

        try:
            # Determine config file
            config_file = self._get_config_file(input_data.scope)

            # Get default configuration
            if input_data.defaults:
                config = self.default_config.copy()
                # Remove specified key if provided
                if input_data.key:
                    keys_to_remove = input_data.key.split('.')
                    current = config
                    for k in keys_to_remove[:-1]:
                        if k in current:
                            current = current[k]
                        if keys_to_remove[-1] in current:
                            del current[keys_to_remove[-1]]

            else:
                # Read existing config
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)

                # Save configuration
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

            keys_reset = [input_data.key] if input_data.key else ["all"]
            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Reset {keys_reset} in {input_data.scope or 'default'} scope to defaults",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "config_file": str(config_file),
                    "scope": input_data.scope or "default",
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _get_config_file(self, scope: Optional[str]) -> Path:
        """Get appropriate config file path"""
        if scope == "project":
            return self.project_config_path
        else:
            return self.global_config_path

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Configuration key to reset (omit for all)",
                    },
                    "defaults": {
                        "type": "boolean",
                        "description": "Reset to defaults instead of deleting (default: false)",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Configuration scope to reset",
                    },
                },
                "required": [],
            },
        )