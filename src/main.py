#!/usr/bin/env python3
"""
Claude Code CLI - Main entry point
Python version of the TypeScript Claude Code CLI
"""

import sys
import asyncio
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from claude_code.cli.commands import (
    handle_version,
    handle_help,
    handle_init,
    handle_config,
)
from claude_code.cli.repl import REPLScreen
from claude_code.config.settings import Settings
from claude_code.state.app_state import AppState, AppStateManager
from claude_code.utils.logging import setup_logging
from claude_code.tools import (
    ToolRegistry,
    BashTool,
    FileReadTool,
    FileWriteTool,
    FileEditTool,
)


class ClaudeCodeCLI:
    """Main CLI application class"""

    def __init__(self):
        self.console = Console()
        self.settings = Settings()

        # Initialize app state
        self.app_state = AppStateManager.get_instance(self.settings)

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(BashTool())
        self.tool_registry.register(FileReadTool())
        self.tool_registry.register(FileWriteTool())
        self.tool_registry.register(FileEditTool())

        # Initialize permission manager
        from claude_code.types import PermissionManager, PermissionContext

        self.permission_manager = PermissionManager()

        # Initialize tool execution framework
        from claude_code.tools.execution import ToolExecutionFramework

        self.tool_executor = ToolExecutionFramework(
            self.tool_registry,
            self.permission_manager
        )

    async def main(self, args: list[str]) -> int:
        """
        Main entry point for CLI

        Equivalent to TypeScript cli.tsx main() function
        """
        # Fast-path for --version/-v: zero module loading needed
        if len(args) == 1 and (args[0] in ['--version', '-v', '-V']):
            return await handle_version()

        # Fast-path for --help/-h
        if len(args) == 1 and (args[0] in ['--help', '-h']):
            return await handle_help()

        # Setup logging
        setup_logging(self.settings.log_level)

        # Handle specific commands
        if len(args) > 0:
            command = args[0]

            # Handle init command
            if command == 'init':
                return await handle_init(args[1:])

            # Handle config command
            if command == 'config':
                return await handle_config(args[1:])

            # Handle other specific commands...
            # (Will be expanded as we implement more features)

        # Default: Start the REPL (Read-Eval-Print Loop)
        # This is equivalent to main TypeScript CLI behavior
        try:
            repl = REPLScreen(
                settings=self.settings,
                app_state=self.app_state,
                console=self.console
            )
            return await repl.run()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return 130
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return 1


async def main() -> int:
    """
    Main entry point - called from poetry script

    Equivalent to TypeScript main() function in cli.tsx
    """
    cli = ClaudeCodeCLI()
    args = sys.argv[1:]  # Skip the script name

    try:
        return await cli.main(args)
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        console.print_exception(e)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)