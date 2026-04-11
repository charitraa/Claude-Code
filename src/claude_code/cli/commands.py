"""
CLI command handlers
Replaces TypeScript command system
"""

from typing import List
from rich.console import Console
from rich.panel import Panel


console = Console()


async def handle_version() -> int:
    """
    Handle --version/-v flag

    Returns:
        Exit code (0 for success)
    """
    from .. import __version__
    console.print(f"{__version__} (Claude Code)")
    return 0


async def handle_help() -> int:
    """
    Handle --help/-h flag

    Returns:
        Exit code (0 for success)
    """
    help_text = """
Claude Code CLI - AI-powered command-line interface

USAGE:
    claude [OPTIONS] [COMMAND] [ARGS]

COMMANDS:
    init              Initialize Claude Code in current directory
    config            Configure Claude Code settings
    (no command)      Start interactive REPL

OPTIONS:
    -v, --version     Show version and exit
    -h, --help        Show this help message
    --simple           Run in simple mode (basic tools only)
    --debug            Enable debug mode

EXAMPLES:
    claude                     # Start interactive session
    claude init                # Initialize in current directory
    claude config               # View/set configuration
    claude --version           # Show version

For more information, visit: https://github.com/anthropics/claude-code
"""
    console.print(help_text)
    return 0


async def handle_init(args: List[str]) -> int:
    """
    Handle init command

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    console.print(Panel.fit(
        "[bold]Claude Code Initialization[/bold]",
        border_style="cyan"
    ))

    # Check if .claude directory exists
    from pathlib import Path
    cwd = Path.cwd()
    claude_dir = cwd / ".claude"

    if claude_dir.exists():
        console.print("[yellow]Claude Code is already initialized in this directory.[/yellow]")
        console.print(f"Configuration directory: {claude_dir}")
        return 0

    # Create .claude directory
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create default config
    config_file = claude_dir / "config.json"
    default_config = {
        "model": "claude-sonnet-4-20250514",
        "theme": "dark",
        "enabled_tools": [],
    }

    import json
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)

    console.print(f"[green]✓[/green] Initialized Claude Code in {cwd}")
    console.print(f"[green]✓[/green] Created configuration: {config_file}")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Review the generated configuration")
    console.print("2. Start with: claude")
    console.print("3. Or add API key: claude config set api-key YOUR_KEY")

    return 0


async def handle_config(args: List[str]) -> int:
    """
    Handle config command

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from pathlib import Path
    claude_dir = Path.home() / ".claude"
    config_file = claude_dir / "config.json"

    if not args:
        # Show current config
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            console.print(Panel.fit(
                json.dumps(config, indent=2),
                title="[bold]Current Configuration[/bold]",
                border_style="cyan"
            ))
        else:
            console.print("[yellow]No configuration found. Run 'claude init' first.[/yellow]")
        return 0

    # Handle config subcommands
    if args[0] == 'set':
        if len(args) < 3:
            console.print("[red]Usage: claude config set <key> <value>[/red]")
            return 1

        key = args[1]
        value = args[2]

        # Load existing config
        import json
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}

        # Update config
        config[key] = value

        # Save config
        claude_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        console.print(f"[green]✓[/green] Set {key} = {value}")
        return 0

    else:
        console.print(f"[red]Unknown config command: {args[0]}[/red]")
        console.print("Available commands: set")
        return 1