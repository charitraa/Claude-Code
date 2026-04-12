"""
Main entry point for Claude Code CLI
Replaces TypeScript entrypoints/cli.tsx
"""

import sys
import asyncio
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import Settings
from .state import AppState, AppStateManager
from .cli import REPLScreen
from .cli.commands import (
    handle_version,
    handle_help,
    handle_init,
    handle_config,
    handle_auth,
    handle_agents,
    handle_mcp,
    handle_plugins,
    handle_bridge,
)
from .commands import CommandRegistry
from .commands.builtin import get_builtin_commands

# Create Typer app
app = typer.Typer(
    name="claude",
    help="Claude Code CLI - AI-powered command-line interface",
    add_completion=False,
)

# Rich console for output
console = Console()


# Global state
_settings: Optional[Settings] = None
_app_state: Optional[AppState] = None
_command_registry: Optional[CommandRegistry] = None


def get_settings() -> Settings:
    """
    Get or create global settings instance

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_app_state() -> AppState:
    """
    Get or create global app state instance

    Returns:
        AppState instance
    """
    global _app_state
    if _app_state is None:
        _app_state = AppStateManager.get_instance(get_settings())
    return _app_state


def get_command_registry() -> CommandRegistry:
    """
    Get or create global command registry instance

    Returns:
        CommandRegistry instance
    """
    global _command_registry
    if _command_registry is None:
        _command_registry = CommandRegistry(console=console)

        # Register built-in commands
        for command_class in get_builtin_commands():
            _command_registry.register(command_class)

        # Load commands from directory
        from pathlib import Path
        builtin_dir = Path(__file__).parent / "commands" / "builtin"
        _command_registry.load_commands_from_directory(builtin_dir)

    return _command_registry


async def initialize_application() -> None:
    """
    Initialize the application

    Sets up configuration, state, and event loops
    """
    settings = get_settings()
    app_state = get_app_state()

    # Start event processing loop
    asyncio.create_task(app_state.start_event_loop())

    # Update status to ready
    await app_state.update_status(AppState.AppStateStatus.READY)


async def shutdown_application() -> None:
    """
    Shutdown the application gracefully

    Saves state and cleans up resources
    """
    app_state = get_app_state()

    # Update status to shutting down
    await app_state.update_status(AppState.AppStateStatus.SHUTTING_DOWN)

    # Save session if persistence is enabled
    if get_settings().session_persistence:
        # Save session logic would go here
        pass

    # Reset global state
    AppStateManager.reset()


@app.command()
def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reinitialization even if already initialized"
    )
) -> None:
    """
    Initialize Claude Code in the current directory

    Creates .claude directory with default configuration
    """
    asyncio.run(_handle_init(force))


async def _handle_init(force: bool) -> None:
    """Handle init command asynchronously"""
    from .cli.commands import handle_init
    args = ["--force"] if force else []
    exit_code = await handle_init(args)
    sys.exit(exit_code)


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Configuration key"),
    value: Optional[str] = typer.Argument(None, help="Configuration value"),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all configuration values"
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset configuration to defaults"
    )
) -> None:
    """
    Configure Claude Code settings

    Get, set, or list configuration values
    """
    asyncio.run(_handle_config(key, value, list_all, reset))


async def _handle_config(
    key: Optional[str],
    value: Optional[str],
    list_all: bool,
    reset: bool
) -> None:
    """Handle config command asynchronously"""
    from .cli.commands import handle_config

    args = []
    if reset:
        args = ["reset"]
    elif list_all:
        args = ["list"]
    elif key and value:
        args = ["set", key, value]
    elif key:
        args = ["get", key]

    exit_code = await handle_config(args)
    sys.exit(exit_code)


@app.command()
def auth(
    login: Optional[str] = typer.Option(None, "--login", help="Login with API key"),
    logout: bool = typer.Option(False, "--logout", help="Logout"),
    status: bool = typer.Option(False, "--status", help="Show authentication status")
) -> None:
    """
    Manage authentication

    Login, logout, or check authentication status
    """
    asyncio.run(_handle_auth(login, logout, status))


async def _handle_auth(login: Optional[str], logout: bool, status: bool) -> None:
    """Handle auth command asynchronously"""
    args = []
    if login:
        args = ["login", login]
    elif logout:
        args = ["logout"]
    elif status:
        args = ["status"]

    exit_code = await handle_auth(args)
    sys.exit(exit_code)


@app.command()
def agents(
    list_agents: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List available agents"
    ),
    run: Optional[str] = typer.Option(
        None,
        "--run",
        "-r",
        help="Run a specific agent"
    )
) -> None:
    """
    Manage AI agents

    List or run specialized AI agents
    """
    asyncio.run(_handle_agents(list_agents, run))


async def _handle_agents(list_agents: bool, run: Optional[str]) -> None:
    """Handle agents command asynchronously"""
    args = []
    if list_agents:
        args = ["list"]
    elif run:
        args = ["run", run]

    exit_code = await handle_agents(args)
    sys.exit(exit_code)


@app.command()
def mcp(
    start: bool = typer.Option(False, "--start", help="Start MCP server"),
    stop: bool = typer.Option(False, "--stop", help="Stop MCP server"),
    status: bool = typer.Option(False, "--status", help="Show MCP server status"),
    list_servers: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List configured MCP servers"
    )
) -> None:
    """
    Manage MCP (Model Context Protocol) server

    Start, stop, or check status of MCP server
    """
    asyncio.run(_handle_mcp(start, stop, status, list_servers))


async def _handle_mcp(start: bool, stop: bool, status: bool, list_servers: bool) -> None:
    """Handle mcp command asynchronously"""
    args = []
    if start:
        args = ["start"]
    elif stop:
        args = ["stop"]
    elif status:
        args = ["status"]
    elif list_servers:
        args = ["list"]

    exit_code = await handle_mcp(args)
    sys.exit(exit_code)


@app.command()
def plugins(
    list_plugins: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List installed plugins"
    ),
    install: Optional[str] = typer.Option(
        None,
        "--install",
        "-i",
        help="Install a plugin"
    ),
    remove: Optional[str] = typer.Option(
        None,
        "--remove",
        "-r",
        help="Remove a plugin"
    )
) -> None:
    """
    Manage plugins

    Install, remove, or list plugins
    """
    asyncio.run(_handle_plugins(list_plugins, install, remove))


async def _handle_plugins(list_plugins: bool, install: Optional[str], remove: Optional[str]) -> None:
    """Handle plugins command asynchronously"""
    args = []
    if list_plugins:
        args = ["list"]
    elif install:
        args = ["install", install]
    elif remove:
        args = ["remove", remove]

    exit_code = await handle_plugins(args)
    sys.exit(exit_code)


@app.command()
def bridge(
    start: bool = typer.Option(False, "--start", help="Start bridge server"),
    stop: bool = typer.Option(False, "--stop", help="Stop bridge server"),
    status: bool = typer.Option(False, "--status", help="Show bridge status")
) -> None:
    """
    Manage bridge for remote sessions

    Start, stop, or check bridge server status
    """
    asyncio.run(_handle_bridge(start, stop, status))


async def _handle_bridge(start: bool, stop: bool, status: bool) -> None:
    """Handle bridge command asynchronously"""
    args = []
    if start:
        args = ["start"]
    elif stop:
        args = ["stop"]
    elif status:
        args = ["status"]

    exit_code = await handle_bridge(args)
    sys.exit(exit_code)


@app.command()
def run(
    command: str = typer.Argument(..., help="Command to run"),
    args: List[str] = typer.Argument(None, help="Command arguments")
) -> None:
    """
    Run a command through the command registry

    Execute any registered command with arguments
    """
    asyncio.run(_handle_run(command, args or []))


async def _handle_run(command: str, cmd_args: List[str]) -> None:
    """Handle run command asynchronously"""
    registry = get_command_registry()

    # Check if command exists
    command_class = registry.get_command(command)
    if not command_class:
        console.print(f"[red]Command not found: {command}[/red]")
        console.print("Run 'claude commands' to see available commands")
        sys.exit(1)

    # Execute command
    result = await registry.execute(command, cmd_args, {})

    # Display result
    if result.is_success():
        if result.message:
            console.print(f"[green]{result.message}[/green]")
        sys.exit(result.exit_code)
    else:
        if result.message:
            console.print(f"[red]{result.message}[/red]")
        sys.exit(result.exit_code)


@app.command()
def commands(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search commands")
) -> None:
    """
    List available commands

    Show all registered commands or filter by category/search
    """
    registry = get_command_registry()

    if search:
        matches = registry.search_commands(search)
        if matches:
            console.print(f"[bold]Commands matching '{search}':[/bold]")
            for cmd in matches:
                console.print(f"  • {cmd}")
        else:
            console.print(f"[yellow]No commands found matching '{search}'[/yellow]")
    else:
        registry.display_commands(category)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of entries to show"),
    command_filter: Optional[str] = typer.Option(None, "--command", "-c", help="Filter by command")
) -> None:
    """
    Show command execution history

    Display recent command executions
    """
    registry = get_command_registry()
    history_entries = registry.get_history(limit, command_filter)

    if not history_entries:
        console.print("[yellow]No command history found[/yellow]")
        return

    table = Table(title=f"Command History (Last {len(history_entries)})")
    table.add_column("Time", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Duration", style="white")

    from datetime import datetime
    for entry in history_entries:
        timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
        cmd_str = f"{entry['name']} {' '.join(entry['args'])}"
        status = entry["status"]
        duration = f"{entry['execution_time_ms']:.0f}ms" if entry.get("execution_time_ms") else "N/A"

        table.add_row(timestamp, cmd_str, status, duration)

    console.print(table)


@app.command()
def chat(
    simple: bool = typer.Option(
        False,
        "--simple",
        help="Run in simple mode (basic tools only)"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Specify AI model to use"
    )
) -> None:
    """
    Start interactive chat session with Claude

    Opens the REPL interface for conversing with Claude
    """
    asyncio.run(_handle_chat(simple, debug, model))


async def _handle_chat(simple: bool, debug: bool, model: Optional[str]) -> None:
    """Handle chat command asynchronously"""
    # Get or create settings
    settings = get_settings()

    # Apply command-line overrides
    if simple:
        settings.simple_mode = True
    if debug:
        settings.debug_mode = True
    if model:
        settings.ai.model = model

    # Check for API key
    api_key = settings.get_api_key()
    if not api_key:
        console.print(Panel.fit(
            "[bold red]No API Key Found[/bold red]\n\n"
            "Please set your Anthropic API key:\n"
            "  1. Export ANTHROPIC_API_KEY environment variable\n"
            "  2. Or run: claude config set api-key YOUR_KEY",
            border_style="red"
        ))
        sys.exit(1)

    # Initialize application
    await initialize_application()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
        asyncio.create_task(shutdown_application())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run REPL
    try:
        app_state = get_app_state()
        repl = REPLScreen(settings=settings, app_state=app_state, console=console)
        await repl.run_async()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if settings.debug_mode:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
    finally:
        await shutdown_application()


@app.command()
def version() -> None:
    """
    Show version information
    """
    console.print(f"Claude Code CLI v{__version__}")
    console.print("Python implementation of Claude Code")


@app.callback()
def main(
    version_flag: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit"
    ),
    simple: bool = typer.Option(
        False,
        "--simple",
        help="Run in simple mode"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode"
    )
) -> None:
    """
    Claude Code CLI - AI-powered command-line interface

    Run without arguments to start interactive chat session
    """
    if version_flag:
        version()
        raise typer.Exit()

    # Apply global flags
    if simple or debug:
        settings = get_settings()
        if simple:
            settings.simple_mode = True
        if debug:
            settings.debug_mode = True


def cli() -> None:
    """
    Main CLI entry point

    This function is called when the CLI is invoked
    """
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        if get_settings().debug_mode:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    cli()
