"""
Auth command implementation
Manage authentication with Anthropic API
"""

from pathlib import Path
import json
import os
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


class AuthCommand(BaseCommand):
    """
    Manage authentication with Anthropic API
    """

    def _get_metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="auth",
            description="Manage authentication with Anthropic API",
            category="auth",
            examples=[
                "claude auth login sk-ant-api03-...",
                "claude auth logout",
                "claude auth status",
                "claude auth whoami"
            ],
            see_also=["config", "init"]
        )

    def _get_arguments(self) -> List[CommandArgument]:
        return [
            CommandArgument(
                name="action",
                description="Action to perform (login, logout, status, whoami)",
                required=False,
                choices=["login", "logout", "status", "whoami"],
                default="status"
            ),
            CommandArgument(
                name="api_key",
                description="API key for login action",
                required=False
            )
        ]

    def _get_options(self) -> List[CommandOption]:
        return [
            CommandOption(
                name="env",
                description="Use environment variable for API key",
                is_flag=True,
                default=False
            ),
            CommandOption(
                name="check",
                short_name="c",
                description="Verify API key is valid",
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
        use_env = options.get("env", False)
        check_key = options.get("check", False)

        # Parse arguments
        action = args[0] if len(args) > 0 else "status"
        api_key = args[1] if len(args) > 1 else None

        # Execute action
        if action == "login":
            return await self._login(api_key, use_env, check_key)
        elif action == "logout":
            return await self._logout()
        elif action == "status":
            return await self._status(check_key)
        elif action == "whoami":
            return await self._whoami()
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Unknown action: {action}. Available actions: login, logout, status, whoami",
                exit_code=1
            )

    def _get_config_file(self) -> Path:
        """Get the config file path"""
        return Path.home() / ".claude" / "config.json"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        config_file = self._get_config_file()
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        config_file = self._get_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_api_key(self, use_env: bool = False) -> Optional[str]:
        """Get API key from config or environment"""
        if use_env:
            return os.environ.get("ANTHROPIC_API_KEY")

        # Check config first
        config = self._load_config()
        if "api_key" in config:
            return config["api_key"]

        # Fallback to environment
        return os.environ.get("ANTHROPIC_API_KEY")

    async def _login(self, api_key: Optional[str], use_env: bool, check_key: bool) -> CommandResult:
        """Login with API key"""
        if use_env:
            # Use environment variable
            env_key = os.environ.get("ANTHROPIC_API_KEY")
            if not env_key:
                return CommandResult(
                    status=CommandStatus.ERROR,
                    message="ANTHROPIC_API_KEY environment variable not set",
                    exit_code=1
                )
            api_key = env_key

        if not api_key:
            return CommandResult(
                status=CommandStatus.ERROR,
                message="API key required. Use: claude auth login YOUR_API_KEY",
                exit_code=1
            )

        # Validate API key format
        if not api_key.startswith("sk-ant-"):
            self.console.print("[yellow]Warning: API key doesn't start with 'sk-ant-'[/yellow]")
            confirm = input("Continue anyway? (yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                return CommandResult(
                    status=CommandStatus.CANCELLED,
                    message="Login cancelled"
                )

        # Check if API key is valid
        if check_key:
            self.console.print("[yellow]Verifying API key...[/yellow]")
            is_valid = await self._verify_api_key(api_key)
            if not is_valid:
                return CommandResult(
                    status=CommandStatus.ERROR,
                    message="Invalid API key. Please check your key and try again.",
                    exit_code=1
                )
            self.console.print("[green]✓[/green] API key is valid")

        # Save API key to config
        config = self._load_config()
        config["api_key"] = api_key
        self._save_config(config)

        # Display success message
        self.console.print(Panel.fit(
            f"[bold green]✓ Authentication Successful[/bold green]\n\n"
            f"API Key: {api_key[:10]}...{api_key[-4:]}\n"
            f"Storage: {self._get_config_file()}",
            border_style="green"
        ))

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Authentication successful",
            data={"api_key_prefix": api_key[:10]}
        )

    async def _logout(self) -> CommandResult:
        """Logout and remove API key"""
        config = self._load_config()

        if "api_key" not in config:
            return CommandResult(
                status=CommandStatus.SKIPPED,
                message="No API key found in configuration"
            )

        # Remove API key from config
        del config["api_key"]
        self._save_config(config)

        self.console.print("[green]✓[/green] Logged out successfully")
        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Logged out successfully"
        )

    async def _status(self, check_key: bool) -> CommandResult:
        """Show authentication status"""
        api_key = self._get_api_key()

        if not api_key:
            self.console.print(Panel.fit(
                "[bold red]✗ Not Authenticated[/bold red]\n\n"
                "No API key found.\n"
                "Set your API key with: claude auth login YOUR_KEY",
                border_style="red"
            ))
            return CommandResult(
                status=CommandStatus.FAILURE,
                message="Not authenticated"
            )

        # Get additional info
        config = self._load_config()

        # Verify API key if requested
        key_valid = None
        if check_key:
            self.console.print("[yellow]Verifying API key...[/yellow]")
            key_valid = await self._verify_api_key(api_key)

        # Create status table
        table = Table(title="Authentication Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", "[green]✓ Authenticated[/green]" if key_valid is None or key_valid else "[red]✓ Key Invalid[/red]")
        table.add_row("API Key", f"{api_key[:10]}...{api_key[-4:]}")
        table.add_row("Source", "Environment Variable" if os.environ.get("ANTHROPIC_API_KEY") == api_key else "Configuration File")
        table.add_row("Model", config.get("model", "claude-sonnet-4-20250514"))

        if check_key:
            table.add_row("Key Valid", "Yes" if key_valid else "No")

        self.console.print(table)

        return CommandResult(
            status=CommandStatus.SUCCESS if key_valid is None or key_valid else CommandStatus.FAILURE,
            message="Authenticated" if key_valid is None or key_valid else "Invalid API key",
            data={
                "authenticated": key_valid if key_valid is not None else True,
                "api_key_prefix": api_key[:10]
            }
        )

    async def _whoami(self) -> CommandResult:
        """Show current authentication information"""
        api_key = self._get_api_key()

        if not api_key:
            return CommandResult(
                status=CommandStatus.FAILURE,
                message="Not authenticated"
            )

        self.console.print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
        self.console.print(f"Prefix: {api_key[:20]}")

        return CommandResult(
            status=CommandStatus.SUCCESS,
            data={"api_key_prefix": api_key[:20]}
        )

    async def _verify_api_key(self, api_key: str) -> bool:
        """
        Verify if API key is valid

        Args:
            api_key: API key to verify

        Returns:
            True if valid, False otherwise
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            # Try to make a simple API call
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )

            return True

        except anthropic.AuthenticationError:
            return False
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not verify API key: {e}[/yellow]")
            return True  # Assume valid if we can't verify

    async def validate(
        self,
        args: List[str],
        options: Dict[str, Any]
    ) -> List[str]:
        """Validate command arguments"""
        errors = []

        if len(args) > 0:
            action = args[0]
            if action not in ["login", "logout", "status", "whoami"]:
                errors.append(f"Invalid action: {action}")

            if action == "login" and len(args) < 2 and not options.get("env", False):
                errors.append("'login' action requires an API key argument")

        return errors
