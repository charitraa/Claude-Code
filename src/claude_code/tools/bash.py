"""
Bash tool implementation
Converted from TypeScript BashTool
"""

import asyncio
import subprocess
from typing import Optional
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolInputSchema,
    ToolCategory,
    PermissionLevel,
)


class BashInput(ToolInputSchema):
    """Input schema for Bash tool"""

    command: str = Field(..., description="Shell command to execute")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")
    cwd: Optional[str] = Field(default=None, description="Working directory for command")


class BashTool(Tool):
    """
    Bash tool for executing shell commands

    Replaces TypeScript BashTool
    """

    # Tool metadata
    name: str = "Bash"
    description: str = "Execute shell commands in the terminal"
    category: ToolCategory = ToolCategory.SHELL
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: BashInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Execute bash command

        Args:
            input_data: Validated bash input
            context: Execution context

        Returns:
            ToolResult with execution outcome
        """
        import time

        start_time = time.time()

        try:
            # Use provided cwd or context cwd
            working_dir = input_data.cwd or context.cwd

            # Execute command
            process = await asyncio.create_subprocess_shell(
                input_data.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=input_data.timeout
                )
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()

                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Command timed out after {input_data.timeout}s",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""

            # Combine stdout and stderr
            output = stdout_text
            if stderr_text:
                output += f"\n[STDERR]\n{stderr_text}"

            return ToolResult(
                tool_name=self.name,
                success=process.returncode == 0,
                content=output,
                error=stderr_text if stderr_text else None,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "return_code": process.returncode,
                    "working_directory": working_dir,
                },
            )

        except FileNotFoundError:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error="Working directory not found",
                execution_time_ms=int((time.time() - start_time) * 1000),
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
        """
        Get tool definition for API

        Returns:
            Tool definition with schema
        """
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30,
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for command (default: current directory)",
                    },
                },
                "required": ["command"],
            },
        )