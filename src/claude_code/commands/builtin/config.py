"""
Config command implementation
Manage Claude Code configuration
"""

from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..base import (
    BaseCommand,
    CommandResult,
    CommandStatus,
    CommandMetadata,
    CommandArgument,
    CommandOption,
)


class ConfigCommand(BaseCommand):
    """
    Manage Claude Code configuration
    """

    def _get_metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="config",
            description="Manage Claude Code configuration",
            category="config",
            examples=[
                "claude config",
                "claude config get model",
                "claude config set model claude-opus-4-20250514",
                "claude config list",
                "claude config reset"
            ],
            see_also=["init", "auth"]
        )

    def _get_arguments(self) -> List[CommandArgument]:
        return [
            CommandArgument(
                name="action",
                description="Action to perform (get, set, list, reset, edit)",
                required=False,
                choices=["get", "set", "list", "reset", "edit"],
                default="list"
            ),
            CommandArgument(
                name="key",
                description="Configuration key",
                required=False
            ),
            CommandArgument(
                name="value",
                description="Configuration value",
                required=False,
                multiple=True
            )
        ]

    def _get_options(self) -> List[CommandOption]:
        return [
            CommandOption(
                name="global",
                short_name="g",
                description="Use global configuration instead of project",
                is_flag=True,
                default=False
            ),
            CommandOption(
                name="json",
                short_name="j",
                description="Output in JSON format",
                is_flag=True,
                default=False
            )
        ]

    async def execute(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        global_config = options.get("global", False)
        json_output = options.get("json", False)

        # Parse arguments
        action = args[0] if len(args) > 0 else "list"
        key = args[1] if len(args) > 1 else None
        value = " ".join(args[2:]) if len(args) > 2 else None

        # Get config file path
        config_file = self._get_config_file(global_config)

        # Load or create config
        config = self._load_config(config_file)

        # Execute action
        if action == "get":
            return await self._get_config(config, key, json_output)
        elif action == "set":
            return await self._set_config(config, key, value, config_file, json_output)
        elif action == "list":
            return await self._list_config(config, json_output)
        elif action == "reset":
            return await self._reset_config(config_file, json_output)
        elif action == "edit":
            return await self._edit_config(config_file)
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Unknown action: {action}. Available actions: get, set, list, reset, edit",
                exit_code=1
            )

    def _get_config_file(self, global_config: bool) -> Path:
        """Get the config file path"""
        if global_config:
            return Path.home() / ".claude" / "config.json"
        else:
            cwd = Path.cwd()
            project_config = cwd / ".claude" / "config.json"
            if project_config.exists():
                return project_config
            else:
                return Path.home() / ".claude" / "config.json"

    def _load_config(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
        return {}

    def _save_config(self, config: Dict[str, Any], config_file: Path) -> None:
        """Save configuration to file"""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    async def _get_config(
        self,
        config: Dict[str, Any],
        key: Optional[str],
        json_output: bool
    ) -> CommandResult:
        """Get a configuration value"""
        if not key:
            return CommandResult(
                status=CommandStatus.ERROR,
                message="Please specify a key to get",
                exit_code=1
            )

        value = self._get_nested_value(config, key)
        if value is None:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Key not found: {key}",
                exit_code=1
            )

        if json_output:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"key": key, "value": value}
            )
        else:
            self.console.print(f"{key}: {value}")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"key": key, "value": value}
            )

    async def _set_config(
        self,
        config: Dict[str, Any],
        key: Optional[str],
        value: Optional[str],
        config_file: Path,
        json_output: bool
    ) -> CommandResult:
        """Set a configuration value"""
        if not key or value is None:
            return CommandResult(
                status=CommandStatus.ERROR,
                message="Please specify both key and value",
                exit_code=1
            )

        # Parse value (try JSON, fallback to string)
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value

        # Set value
        self._set_nested_value(config, key, parsed_value)

        # Save config
        self._save_config(config, config_file)

        if json_output:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"key": key, "value": parsed_value}
            )
        else:
            self.console.print(f"Set {key} = {parsed_value}")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"key": key, "value": parsed_value}
            )

    async def _list_config(self, config: Dict[str, Any], json_output: bool) -> CommandResult:
        """List all configuration values"""
        if json_output:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=config
            )
        else:
            if not config:
                self.console.print("[yellow]No configuration found. Run 'claude init' first.[/yellow]")
                return CommandResult(
                    status=CommandStatus.SKIPPED,
                    message="No configuration found"
                )

            self.console.print(Panel.fit(
                json.dumps(config, indent=2),
                title="[bold]Current Configuration[/bold]",
                border_style="cyan"
            ))

            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=config
            )

    async def _reset_config(self, config_file: Path, json_output: bool) -> CommandResult:
        """Reset configuration to defaults"""
        # Get confirmation
        self.console.print("[yellow]This will reset all configuration to defaults.[/yellow]")
        confirm = input("Are you sure? (yes/no): ")

        if confirm.lower() not in ["yes", "y"]:
            return CommandResult(
                status=CommandStatus.CANCELLED,
                message="Reset cancelled"
            )

        # Create default config
        default_config = {
            "version": "1.0.0",
            "model": "claude-sonnet-4-20250514",
            "theme": "dark",
            "enabled_tools": [],
            "disabled_tools": []
        }

        self._save_config(default_config, config_file)

        if json_output:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=default_config
            )
        else:
            self.console.print("[green]Configuration reset to defaults[/green]")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=default_config
            )

    async def _edit_config(self, config_file: Path) -> CommandResult:
        """Edit configuration in default editor"""
        import subprocess
        import os

        # Ensure config exists
        if not config_file.exists():
            self._save_config({}, config_file)

        # Get editor
        editor = os.environ.get("EDITOR", "vim")

        try:
            subprocess.run([editor, str(config_file)])
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Configuration edited with {editor}"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Failed to open editor: {str(e)}",
                error=e
            )

    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get a nested value from config using dot notation"""
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value

    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set a nested value in config using dot notation"""
        keys = key.split(".")
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    async def validate(
        self,
        args: List[str],
        options: Dict[str, Any]
    ) -> List[str]:
        """Validate command arguments"""
        errors = []

        if len(args) > 0:
            action = args[0]
            if action not in ["get", "set", "list", "reset", "edit"]:
                errors.append(f"Invalid action: {action}")

            if action in ["get", "set"] and len(args) < 2:
                errors.append(f"'{action}' action requires a key argument")

            if action == "set" and len(args) < 3:
                errors.append("'set' action requires a value argument")

        return errors
