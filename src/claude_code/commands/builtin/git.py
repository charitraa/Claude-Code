"""
Git command implementation
Git operations and integration
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

from ..base import (
    BaseCommand,
    AsyncCommand,
    CommandResult,
    CommandStatus,
    CommandMetadata,
    CommandArgument,
    CommandOption,
)


class GitCommand(AsyncCommand):
    """
    Git operations and integration
    """

    def _get_metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="git",
            description="Perform Git operations",
            category="git",
            examples=[
                "claude git status",
                "claude git diff",
                "claude git commit 'feat: add new feature'",
                "claude git log",
                "claude git branch"
            ],
            see_also=["config", "init"]
        )

    def _get_arguments(self) -> List[CommandArgument]:
        return [
            CommandArgument(
                name="action",
                description="Git action to perform",
                required=False,
                choices=["status", "diff", "commit", "log", "branch", "add", "push", "pull", "checkout"],
                default="status"
            ),
            CommandArgument(
                name="args",
                description="Additional arguments for git command",
                required=False,
                multiple=True
            )
        ]

    def _get_options(self) -> List[CommandOption]:
        return [
            CommandOption(
                name="color",
                short_name="c",
                description="Enable colored output",
                is_flag=True,
                default=True
            ),
            CommandOption(
                name="staged",
                short_name="s",
                description="Show only staged changes",
                is_flag=True,
                default=False
            ),
            CommandOption(
                name="limit",
                short_name="n",
                description="Limit number of log entries",
                type=int,
                default=10
            )
        ]

    async def execute(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        # Parse arguments
        action = args[0] if len(args) > 0 else "status"
        git_args = args[1:] if len(args) > 1 else []

        # Check if we're in a git repository
        if not self._is_git_repo():
            return CommandResult(
                status=CommandStatus.ERROR,
                message="Not a Git repository. Initialize with: git init",
                exit_code=1
            )

        # Execute action
        if action == "status":
            return await self._git_status(options)
        elif action == "diff":
            return await self._git_diff(git_args, options)
        elif action == "commit":
            return await self._git_commit(git_args, options)
        elif action == "log":
            return await self._git_log(git_args, options)
        elif action == "branch":
            return await self._git_branch(git_args, options)
        elif action == "add":
            return await self._git_add(git_args)
        elif action == "push":
            return await self._git_push(git_args)
        elif action == "pull":
            return await self._git_pull(git_args)
        elif action == "checkout":
            return await self._git_checkout(git_args)
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Unknown action: {action}",
                exit_code=1
            )

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        cwd = Path.cwd()
        return (cwd / ".git").exists()

    async def _git_status(self, options: Dict[str, Any]) -> CommandResult:
        """Show git status"""
        result = await self.execute_async(
            "git", "status", "--short",
            cwd=str(Path.cwd()),
            timeout=10
        )

        if result.is_success():
            output = result.data.get("stdout", "").strip()
            if not output:
                self.console.print("[green]Working directory clean[/green]")
            else:
                table = Table(title="Git Status")
                table.add_column("Status", style="yellow")
                table.add_column("File", style="white")

                for line in output.split('\n'):
                    if line:
                        status = line[:2]
                        file_path = line[3:]
                        table.add_row(status, file_path)

                self.console.print(table)

            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Git status retrieved",
                data={"status": output}
            )
        else:
            return result

    async def _git_diff(self, git_args: List[str], options: Dict[str, Any]) -> CommandResult:
        """Show git diff"""
        color = options.get("color", True)
        staged = options.get("staged", False)

        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if not color:
            cmd.append("--no-color")
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=30)

        if result.is_success():
            output = result.data.get("stdout", "")

            if not output.strip():
                self.console.print("[yellow]No changes to display[/yellow]")
            else:
                # Display with syntax highlighting if possible
                try:
                    syntax = Syntax(output, "diff", theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                except Exception:
                    self.console.print(output)

            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Git diff retrieved",
                data={"diff": output}
            )
        else:
            return result

    async def _git_commit(self, git_args: List[str], options: Dict[str, Any]) -> CommandResult:
        """Commit changes"""
        if not git_args:
            return CommandResult(
                status=CommandStatus.ERROR,
                message="Commit message required",
                exit_code=1
            )

        commit_message = " ".join(git_args)

        # Stage all changes first
        add_result = await self.execute_async("git", "add", ".", cwd=str(Path.cwd()), timeout=30)
        if not add_result.is_success():
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Failed to stage changes: {add_result.message}",
                exit_code=1
            )

        # Commit
        result = await self.execute_async(
            "git", "commit", "-m", commit_message,
            cwd=str(Path.cwd()),
            timeout=30
        )

        if result.is_success():
            output = result.data.get("stdout", "")
            self.console.print(f"[green]✓[/green] Committed: {commit_message}")
            if output:
                self.console.print(output)

            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Changes committed",
                data={"message": commit_message}
            )
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Commit failed: {result.message}",
                exit_code=1
            )

    async def _git_log(self, git_args: List[str], options: Dict[str, Any]) -> CommandResult:
        """Show git log"""
        limit = options.get("limit", 10)

        cmd = ["git", "log", "--oneline", f"-{limit}"]
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=10)

        if result.is_success():
            output = result.data.get("stdout", "").strip()

            if not output:
                self.console.print("[yellow]No commits found[/yellow]")
            else:
                table = Table(title=f"Recent Commits (Last {limit})")
                table.add_column("Commit", style="cyan")
                table.add_column("Message", style="white")

                for line in output.split('\n'):
                    if line:
                        parts = line.split(" ", 1)
                        commit_hash = parts[0]
                        commit_msg = parts[1] if len(parts) > 1 else ""
                        table.add_row(commit_hash, commit_msg)

                self.console.print(table)

            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Git log retrieved",
                data={"log": output}
            )
        else:
            return result

    async def _git_branch(self, git_args: List[str], options: Dict[str, Any]) -> CommandResult:
        """Show git branches"""
        result = await self.execute_async(
            "git", "branch", "-a",
            cwd=str(Path.cwd()),
            timeout=10
        )

        if result.is_success():
            output = result.data.get("stdout", "").strip()

            if not output:
                self.console.print("[yellow]No branches found[/yellow]")
            else:
                table = Table(title="Git Branches")
                table.add_column("Branch", style="white")

                current_branch = None
                try:
                    current_result = await self.execute_async(
                        "git", "branch", "--show-current",
                        cwd=str(Path.cwd()),
                        timeout=5
                    )
                    if current_result.is_success():
                        current_branch = current_result.data.get("stdout", "").strip()
                except Exception:
                    pass

                for line in output.split('\n'):
                    if line:
                        branch_name = line.strip().lstrip('* ').strip()
                        if branch_name == current_branch:
                            table.add_row(f"* {branch_name}", style="green")
                        else:
                            table.add_row(branch_name)

                self.console.print(table)

            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Git branches retrieved",
                data={"branches": output}
            )
        else:
            return result

    async def _git_add(self, git_args: List[str]) -> CommandResult:
        """Stage files"""
        if not git_args:
            git_args = ["."]

        cmd = ["git", "add"]
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=30)

        if result.is_success():
            self.console.print(f"[green]✓[/green] Staged: {' '.join(git_args)}")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Files staged",
                data={"files": git_args}
            )
        else:
            return result

    async def _git_push(self, git_args: List[str]) -> CommandResult:
        """Push changes to remote"""
        cmd = ["git", "push"]
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=60)

        if result.is_success():
            output = result.data.get("stdout", "")
            self.console.print("[green]✓[/green] Changes pushed")
            if output:
                self.console.print(output)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Changes pushed",
                data={"output": output}
            )
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Push failed: {result.message}",
                exit_code=1
            )

    async def _git_pull(self, git_args: List[str]) -> CommandResult:
        """Pull changes from remote"""
        cmd = ["git", "pull"]
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=60)

        if result.is_success():
            output = result.data.get("stdout", "")
            self.console.print("[green]✓[/green] Changes pulled")
            if output:
                self.console.print(output)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Changes pulled",
                data={"output": output}
            )
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Pull failed: {result.message}",
                exit_code=1
            )

    async def _git_checkout(self, git_args: List[str]) -> CommandResult:
        """Checkout branch or commit"""
        if not git_args:
            return CommandResult(
                status=CommandStatus.ERROR,
                message="Branch or commit required",
                exit_code=1
            )

        cmd = ["git", "checkout"]
        cmd.extend(git_args)

        result = await self.execute_async(*cmd, cwd=str(Path.cwd()), timeout=30)

        if result.is_success():
            output = result.data.get("stdout", "")
            self.console.print(f"[green]✓[/green] Checked out: {' '.join(git_args)}")
            if output:
                self.console.print(output)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Checked out: {' '.join(git_args)}",
                data={"ref": ' '.join(git_args)}
            )
        else:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Checkout failed: {result.message}",
                exit_code=1
            )

    async def validate(
        self,
        args: List[str],
        options: Dict[str, Any]
    ) -> List[str]:
        """Validate command arguments"""
        errors = []

        if len(args) > 0:
            action = args[0]
            if action not in ["status", "diff", "commit", "log", "branch", "add", "push", "pull", "checkout"]:
                errors.append(f"Invalid action: {action}")

            if action == "commit" and len(args) < 2:
                errors.append("'commit' action requires a commit message")

        return errors
