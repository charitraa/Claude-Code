"""
Git operations tools for Claude Code CLI
Converted from TypeScript git tools
"""

import asyncio
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class GitStatusInput(BaseModel):
    """Input schema for GitStatus tool"""

    path: Optional[str] = Field(default=None, description="Path to git repository (default: current directory)")
    show_untracked: bool = Field(default=False, description="Show untracked files")


class GitDiffInput(BaseModel):
    """Input schema for GitDiff tool"""

    path: Optional[str] = Field(default=None, description="Path to git repository (default: current directory)")
    files: Optional[List[str]] = Field(default=None, description="Specific files to diff (default: all)")
    staged: bool = Field(default=False, description="Show staged changes instead of working directory")


class GitCommitInput(BaseModel):
    """Input schema for GitCommit tool"""

    path: Optional[str] = Field(default=None, description="Path to git repository (default: current directory)")
    message: str = Field(..., description="Commit message")
    files: Optional[List[str]] = Field(default=None, description="Specific files to commit (default: all staged)")
    amend: bool = Field(default=False, description="Amend previous commit")


class GitLogInput(BaseModel):
    """Input schema for GitLog tool"""

    path: Optional[str] = Field(default=None, description="Path to git repository (default: current directory)")
    max_count: int = Field(default=10, description="Maximum number of commits to show")
    format: str = Field(default="oneline", description="Log format (oneline, medium, full)")


class GitStatusTool(Tool):
    """
    Git status tool for checking repository state

    Replaces TypeScript git status operations
    """

    # Tool metadata
    name: str = "GitStatus"
    description: str = "Get git repository status"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GitStatusInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Get git repository status

        Args:
            input_data: Validated git status input
            context: Execution context

        Returns:
            ToolResult with git status
        """
        import time
        start_time = time.time()

        try:
            repo_path = Path(input_data.path) if input_data.path else Path(context.cwd)

            if not repo_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Check if this is a git repository
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Not a git repository: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Get git status
            process = await asyncio.create_subprocess_exec(
                ["git", "status", "--porcelain"],
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Git status failed: {stderr.decode()}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            status_output = stdout.decode()

            # Parse git status output
            staged_files = []
            modified_files = []
            untracked_files = []

            for line in status_output.split('\n'):
                if not line:
                    continue

                # Parse porcelain status format
                status_code = line[0]
                file_path = line[3:]

                if status_code == 'M':
                    modified_files.append(file_path)
                elif status_code == 'A':
                    staged_files.append(file_path)
                elif status_code == '??':
                    untracked_files.append(file_path)

            # Format status output
            status_lines = []
            if staged_files:
                status_lines.append(f"Staged changes: {len(staged_files)} files")
            if modified_files:
                status_lines.append(f"Modified files: {len(modified_files)} files")
            if input_data.show_untracked and untracked_files:
                status_lines.append(f"Untracked files: {len(untracked_files)} files")

            return ToolResult(
                tool_name=self.name,
                success=True,
                content='\n'.join(status_lines) if status_lines else "Clean working directory",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "staged_files": staged_files,
                    "modified_files": modified_files,
                    "untracked_files": untracked_files if input_data.show_untracked else [],
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

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to git repository (default: current directory)",
                    },
                    "show_untracked": {
                        "type": "boolean",
                        "description": "Show untracked files (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
        )


class GitDiffTool(Tool):
    """
    Git diff tool for showing changes

    Replaces TypeScript git diff operations
    """

    # Tool metadata
    name: str = "GitDiff"
    description: str = "Show git repository changes"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GitDiffInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Show git repository changes

        Args:
            input_data: Validated git diff input
            context: Execution context

        Returns:
            ToolResult with diff output
        """
        import time
        start_time = time.time()

        try:
            repo_path = Path(input_data.path) if input_data.path else Path(context.cwd)

            if not repo_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Check if this is a git repository
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Not a git repository: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Build git diff command
            git_args = ["diff"]
            if input_data.staged:
                git_args.append("--staged")
            if input_data.files:
                git_args.extend(input_data.files)

            # Execute git diff
            process = await asyncio.create_subprocess_exec(
                ["git"] + git_args,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Git diff failed: {stderr.decode()}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            diff_output = stdout.decode()

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=diff_output,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "diff_type": "staged" if input_data.staged else "working",
                    "files": input_data.files,
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

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to git repository (default: current directory)",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to diff (default: all)",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes instead of working directory (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
        )


class GitCommitTool(Tool):
    """
    Git commit tool for creating commits

    Replaces TypeScript git commit operations
    """

    # Tool metadata
    name: str = "GitCommit"
    description: str = "Create git commit"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GitCommitInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Create git commit

        Args:
            input_data: Validated git commit input
            context: Execution context

        Returns:
            ToolResult with commit result
        """
        import time
        start_time = time.time()

        try:
            repo_path = Path(input_data.path) if input_data.path else Path(context.cwd)

            if not repo_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Check if this is a git repository
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Not a git repository: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Build git commit command
            git_args = ["commit", "-m", input_data.message]

            if input_data.amend:
                git_args.append("--amend")

            # Add specific files if provided
            if input_data.files:
                # First add the files
                add_process = await asyncio.create_subprocess_exec(
                    ["git", "add"] + input_data.files,
                    cwd=str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await add_process.communicate()

            # Execute git commit
            process = await asyncio.create_subprocess_exec(
                ["git"] + git_args,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                # Nothing to commit is not an error
                if b"nothing to commit" in stderr:
                    return ToolResult(
                        tool_name=self.name,
                        success=True,
                        content="No changes to commit",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )

                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Git commit failed: {stderr.decode()}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            commit_output = stdout.decode()

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=commit_output or "Commit created successfully",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "amend": input_data.amend,
                    "files": input_data.files,
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

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to git repository (default: current directory)",
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to commit (default: all staged)",
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "Amend previous commit (default: false)",
                        "default": False,
                    },
                },
                "required": ["message"],
            },
        )


class GitLogTool(Tool):
    """
    Git log tool for viewing commit history

    Replaces TypeScript git log operations
    """

    # Tool metadata
    name: str = "GitLog"
    description: str = "View git commit history"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GitLogInput,
        context: ToolContext
    ) -> ToolResult:
        """
        View git commit history

        Args:
            input_data: Validated git log input
            context: Execution context

        Returns:
            ToolResult with commit log
        """
        import time
        start_time = time.time()

        try:
            repo_path = Path(input_data.path) if input_data.path else Path(context.cwd)

            if not repo_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Check if this is a git repository
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Not a git repository: {repo_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Build git log command
            git_args = ["log"]

            if input_data.format == "oneline":
                git_args.append("--oneline")
            elif input_data.format == "medium":
                git_args.extend(["--format=medium"])
            elif input_data.format == "full":
                git_args.extend(["--format=fuller"])

            git_args.extend(["-n", str(input_data.max_count)])

            # Execute git log
            process = await asyncio.create_subprocess_exec(
                ["git"] + git_args,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Git log failed: {stderr.decode()}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            log_output = stdout.decode()

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=log_output,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "format": input_data.format,
                    "max_count": input_data.max_count,
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

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to git repository (default: current directory)",
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits to show (default: 10)",
                        "default": 10,
                    },
                    "format": {
                        "type": "string",
                        "description": "Log format (oneline, medium, full) (default: oneline)",
                        "default": "oneline",
                    },
                },
                "required": [],
            },
        )