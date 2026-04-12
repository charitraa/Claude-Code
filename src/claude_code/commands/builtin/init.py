"""
Init command implementation
Initialize Claude Code in current directory
"""

from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from rich.console import Console

from ..base import (
    BaseCommand,
    CommandResult,
    CommandStatus,
    CommandMetadata,
    CommandOption,
)


class InitCommand(BaseCommand):
    """
    Initialize Claude Code in the current directory
    """

    def _get_metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="init",
            description="Initialize Claude Code in the current directory",
            category="setup",
            examples=[
                "claude init",
                "claude init --force",
                "claude init --template=web-app"
            ],
            see_also=["config", "auth"]
        )

    def _get_options(self) -> List[CommandOption]:
        return [
            CommandOption(
                name="force",
                short_name="f",
                description="Force reinitialization even if already initialized",
                is_flag=True,
                default=False
            ),
            CommandOption(
                name="template",
                short_name="t",
                description="Initialize from a template",
                default=None
            ),
            CommandOption(
                name="no-git",
                description="Skip Git initialization",
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
        force = options.get("force", False)
        template = options.get("template")
        no_git = options.get("no_git", False)

        cwd = Path.cwd()
        claude_dir = cwd / ".claude"

        # Check if already initialized
        if claude_dir.exists() and not force:
            return CommandResult(
                status=CommandStatus.SKIPPED,
                message="Claude Code is already initialized in this directory. Use --force to reinitialize.",
                data={"claude_dir": str(claude_dir)}
            )

        # Create .claude directory
        try:
            claude_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Failed to create .claude directory: {str(e)}",
                error=e
            )

        # Create default configuration
        config_file = claude_dir / "config.json"
        default_config = {
            "version": "1.0.0",
            "model": "claude-sonnet-4-20250514",
            "theme": "dark",
            "enabled_tools": [],
            "disabled_tools": [],
            "git": {
                "auto_commit": False,
                "include_diff_in_messages": True
            }
        }

        # Apply template if specified
        if template:
            template_config = self._apply_template(template)
            if template_config:
                default_config.update(template_config)

        try:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Failed to create configuration file: {str(e)}",
                error=e
            )

        # Initialize Git if not skipped
        git_initialized = False
        if not no_git:
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "init"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    git_initialized = True
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass  # Git not available or failed

        # Create .gitignore if not exists
        gitignore_file = cwd / ".gitignore"
        if not gitignore_file.exists():
            gitignore_content = """# Claude Code
.claude/
.claude-code/
*.claude-code

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
"""
            try:
                with open(gitignore_file, 'w') as f:
                    f.write(gitignore_content)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not create .gitignore: {e}[/yellow]")

        # Create directory structure
        (claude_dir / "sessions").mkdir(exist_ok=True)
        (claude_dir / "cache").mkdir(exist_ok=True)
        (claude_dir / "templates").mkdir(exist_ok=True)

        # Success message
        self.console.print(f"\n[bold green]✓[/bold green] Initialized Claude Code in {cwd}")
        self.console.print(f"[green]✓[/green] Created configuration: {config_file}")
        if git_initialized:
            self.console.print("[green]✓[/green] Initialized Git repository")
        self.console.print("\n[yellow]Next steps:[/yellow]")
        self.console.print("1. Review the generated configuration")
        self.console.print("2. Set your API key: claude auth login YOUR_API_KEY")
        self.console.print("3. Start with: claude")
        self.console.print("4. Or run: claude --help")

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Claude Code initialized successfully",
            data={
                "claude_dir": str(claude_dir),
                "config_file": str(config_file),
                "git_initialized": git_initialized,
                "template": template
            }
        )

    def _apply_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Apply a template configuration

        Args:
            template_name: Name of template to apply

        Returns:
            Template configuration or None
        """
        templates = {
            "web-app": {
                "enabled_tools": ["bash", "file", "search", "git"],
                "model": "claude-sonnet-4-20250514",
                "theme": "dark"
            },
            "data-science": {
                "enabled_tools": ["bash", "file", "search", "notebook", "web"],
                "model": "claude-sonnet-4-20250514",
                "theme": "dark"
            },
            "minimal": {
                "enabled_tools": ["bash", "file"],
                "model": "claude-haiku-4-20250514",
                "theme": "light"
            }
        }

        return templates.get(template_name)
