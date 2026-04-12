"""
CLI command handlers
Replaces TypeScript command system
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path


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
        console.print("Available commands: set, get, list, reset")
        return 1


async def handle_auth(args: List[str]) -> int:
    """
    Handle authentication commands

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args:
        # Show authentication status
        from ..config import Settings
        settings = Settings()
        api_key = settings.get_api_key()

        if api_key:
            console.print(Panel.fit(
                "[bold green]✓ Authenticated[/bold green]\n\n"
                f"API Key: {api_key[:10]}...{api_key[-4:]}\n"
                f"Model: {settings.ai.model}",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                "[bold red]✗ Not Authenticated[/bold red]\n\n"
                "No API key found.\n"
                "Set your API key with: claude auth login YOUR_KEY",
                border_style="red"
            ))
        return 0

    command = args[0]

    if command == 'login':
        if len(args) < 2:
            console.print("[red]Usage: claude auth login <api-key>[/red]")
            return 1

        api_key = args[1]
        # Save API key to config
        from ..config import Settings
        settings = Settings()
        claude_dir = Path.home() / ".claude"
        config_file = claude_dir / "config.json"

        import json
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}

        config['api_key'] = api_key
        claude_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        console.print("[green]✓[/green] API key saved successfully")
        console.print(f"Key: {api_key[:10]}...{api_key[-4:]}")
        return 0

    elif command == 'logout':
        # Remove API key from config
        from ..config import Settings
        claude_dir = Path.home() / ".claude"
        config_file = claude_dir / "config.json"

        import json
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            if 'api_key' in config:
                del config['api_key']
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                console.print("[green]✓[/green] Logged out successfully")
                return 0

        console.print("[yellow]No API key found[/yellow]")
        return 0

    elif command == 'status':
        # Show detailed authentication status
        from ..config import Settings
        settings = Settings()
        api_key = settings.get_api_key()

        table = Table(title="Authentication Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("API Key", "✓ Set" if api_key else "✗ Not Set")
        table.add_row("Model", settings.ai.model)
        table.add_row("Base URL", settings.ai.base_url or "Default")
        table.add_row("Max Tokens", str(settings.ai.max_tokens))

        console.print(table)
        return 0

    else:
        console.print(f"[red]Unknown auth command: {command}[/red]")
        console.print("Available commands: login, logout, status")
        return 1


async def handle_agents(args: List[str]) -> int:
    """
    Handle agent management commands

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args:
        # List available agents
        console.print(Panel.fit(
            "[bold]Available Agents[/bold]\n\n"
            "• general-purpose - General purpose agent for complex tasks\n"
            "• explore - Codebase exploration agent\n"
            "• plan - Implementation planning agent",
            border_style="cyan"
        ))
        return 0

    command = args[0]

    if command == 'list':
        console.print("[bold]Available Agents:[/bold]")
        console.print("  • general-purpose")
        console.print("  • explore")
        console.print("  • plan")
        return 0

    elif command == 'run':
        if len(args) < 2:
            console.print("[red]Usage: claude agents run <agent-name> [prompt][/red]")
            return 1

        agent_name = args[1]
        prompt = " ".join(args[2:]) if len(args) > 2 else None

        console.print(f"[yellow]Running agent: {agent_name}[/yellow]")
        if prompt:
            console.print(f"Prompt: {prompt}")

        # Placeholder for actual agent execution
        console.print("[yellow]Agent execution not yet implemented[/yellow]")
        return 0

    else:
        console.print(f"[red]Unknown agents command: {command}[/red]")
        console.print("Available commands: list, run")
        return 1


async def handle_mcp(args: List[str]) -> int:
    """
    Handle MCP (Model Context Protocol) commands

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args:
        # Show MCP status
        from ..config import Settings
        settings = Settings()

        console.print(Panel.fit(
            f"[bold]MCP Status[/bold]\n\n"
            f"Enabled: {'Yes' if settings.mcp.enabled else 'No'}\n"
            f"Servers: {len(settings.mcp.servers)} configured",
            border_style="cyan"
        ))
        return 0

    command = args[0]

    if command == 'start':
        console.print("[yellow]Starting MCP server...[/yellow]")
        console.print("[yellow]MCP server not yet implemented[/yellow]")
        return 0

    elif command == 'stop':
        console.print("[yellow]Stopping MCP server...[/yellow]")
        console.print("[yellow]MCP server not yet implemented[/yellow]")
        return 0

    elif command == 'status':
        from ..config import Settings
        settings = Settings()

        table = Table(title="MCP Server Status")
        table.add_column("Server", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Command", style="yellow")

        if settings.mcp.servers:
            for name, config in settings.mcp.servers.items():
                table.add_row(name, "Running", config.get('command', 'N/A'))
        else:
            table.add_row("None", "N/A", "No servers configured")

        console.print(table)
        return 0

    elif command == 'list':
        from ..config import Settings
        settings = Settings()

        if settings.mcp.servers:
            console.print("[bold]Configured MCP Servers:[/bold]")
            for name in settings.mcp.servers.keys():
                console.print(f"  • {name}")
        else:
            console.print("[yellow]No MCP servers configured[/yellow]")
        return 0

    else:
        console.print(f"[red]Unknown mcp command: {command}[/red]")
        console.print("Available commands: start, stop, status, list")
        return 1


async def handle_plugins(args: List[str]) -> int:
    """
    Handle plugin management commands

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args:
        # List installed plugins
        console.print(Panel.fit(
            "[bold]Plugins[/bold]\n\n"
            "No plugins installed.\n"
            "Plugin management coming soon.",
            border_style="cyan"
        ))
        return 0

    command = args[0]

    if command == 'list':
        console.print("[bold]Installed Plugins:[/bold]")
        console.print("  (No plugins installed)")
        return 0

    elif command == 'install':
        if len(args) < 2:
            console.print("[red]Usage: claude plugins install <plugin-name>[/red]")
            return 1

        plugin_name = args[1]
        console.print(f"[yellow]Installing plugin: {plugin_name}[/yellow]")
        console.print("[yellow]Plugin installation not yet implemented[/yellow]")
        return 0

    elif command == 'remove':
        if len(args) < 2:
            console.print("[red]Usage: claude plugins remove <plugin-name>[/red]")
            return 1

        plugin_name = args[1]
        console.print(f"[yellow]Removing plugin: {plugin_name}[/yellow]")
        console.print("[yellow]Plugin removal not yet implemented[/yellow]")
        return 0

    else:
        console.print(f"[red]Unknown plugins command: {command}[/red]")
        console.print("Available commands: list, install, remove")
        return 1


async def handle_bridge(args: List[str]) -> int:
    """
    Handle bridge commands for remote sessions

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args:
        # Show bridge status
        console.print(Panel.fit(
            "[bold]Bridge Status[/bold]\n\n"
            "Status: Not running\n"
            "Mode: Local",
            border_style="cyan"
        ))
        return 0

    command = args[0]

    if command == 'start':
        console.print("[yellow]Starting bridge server...[/yellow]")
        console.print("[yellow]Bridge system not yet implemented[/yellow]")
        return 0

    elif command == 'stop':
        console.print("[yellow]Stopping bridge server...[/yellow]")
        console.print("[yellow]Bridge system not yet implemented[/yellow]")
        return 0

    elif command == 'status':
        console.print("[bold]Bridge Status:[/bold]")
        console.print("  Status: Not running")
        console.print("  Mode: Local")
        console.print("  Sessions: 0")
        return 0

    else:
        console.print(f"[red]Unknown bridge command: {command}[/red]")
        console.print("Available commands: start, stop, status")
        return 1