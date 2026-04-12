"""
Command base classes
Provides abstract interfaces and base implementations for commands
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import inspect

from rich.console import Console
from rich.panel import Panel


class CommandStatus(str, Enum):
    """Command execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class CommandResult:
    """Result of command execution"""
    status: CommandStatus
    exit_code: int = 0
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    execution_time_ms: Optional[float] = None

    def is_success(self) -> bool:
        """Check if command was successful"""
        return self.status == CommandStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if command failed"""
        return self.status in [CommandStatus.FAILURE, CommandStatus.ERROR]


@dataclass
class CommandArgument:
    """Command argument definition"""
    name: str
    description: str
    required: bool = False
    default: Any = None
    type: type = str
    choices: Optional[List[str]] = None
    multiple: bool = False


@dataclass
class CommandOption:
    """Command option definition"""
    name: str
    short_name: Optional[str] = None
    description: str = ""
    required: bool = False
    default: Any = None
    type: type = str
    is_flag: bool = False
    multiple: bool = False


@dataclass
class CommandMetadata:
    """Command metadata"""
    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    author: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)


class BaseCommand(ABC):
    """
    Abstract base class for commands

    All commands should inherit from this class and implement
    the execute method
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize command

        Args:
            console: Console for output
        """
        self.console = console or Console()
        self.metadata = self._get_metadata()
        self.arguments = self._get_arguments()
        self.options = self._get_options()

    @abstractmethod
    def _get_metadata(self) -> CommandMetadata:
        """
        Get command metadata

        Returns:
            CommandMetadata instance
        """
        pass

    def _get_arguments(self) -> List[CommandArgument]:
        """
        Get command arguments

        Returns:
            List of CommandArgument instances
        """
        return []

    def _get_options(self) -> List[CommandOption]:
        """
        Get command options

        Returns:
            List of CommandOption instances
        """
        return []

    @abstractmethod
    async def execute(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute the command

        Args:
            args: Command arguments
            options: Command options
            context: Optional execution context

        Returns:
            CommandResult instance
        """
        pass

    async def validate(
        self,
        args: List[str],
        options: Dict[str, Any]
    ) -> List[str]:
        """
        Validate command arguments and options

        Args:
            args: Command arguments
            options: Command options

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required arguments
        for i, arg_def in enumerate(self.arguments):
            if arg_def.required and i >= len(args):
                errors.append(f"Missing required argument: {arg_def.name}")

        # Validate argument types
        for i, arg_value in enumerate(args):
            if i < len(self.arguments):
                arg_def = self.arguments[i]
                try:
                    if arg_def.type != str:
                        arg_def.type(arg_value)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for argument {arg_def.name}: expected {arg_def.type.__name__}")

        # Validate choices
        for i, arg_value in enumerate(args):
            if i < len(self.arguments):
                arg_def = self.arguments[i]
                if arg_def.choices and arg_value not in arg_def.choices:
                    errors.append(f"Invalid choice for {arg_def.name}: must be one of {', '.join(arg_def.choices)}")

        return errors

    async def before_execute(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Hook called before command execution

        Args:
            args: Command arguments
            options: Command options
            context: Execution context
        """
        pass

    async def after_execute(
        self,
        result: CommandResult,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Hook called after command execution

        Args:
            result: Command execution result
            args: Command arguments
            options: Command options
            context: Execution context
        """
        pass

    async def run(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Run the command with validation and hooks

        Args:
            args: Command arguments
            options: Command options
            context: Execution context

        Returns:
            CommandResult instance
        """
        import time

        start_time = time.time()

        # Check if deprecated
        if self.metadata.deprecated:
            msg = self.metadata.deprecation_message or f"Command '{self.metadata.name}' is deprecated"
            self.console.print(f"[yellow]Warning: {msg}[/yellow]")

        # Validate
        validation_errors = await self.validate(args, options)
        if validation_errors:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Validation errors: {'; '.join(validation_errors)}",
                exit_code=1
            )

        try:
            # Before execute hook
            await self.before_execute(args, options, context)

            # Execute command
            result = await self.execute(args, options, context)

            # After execute hook
            await self.after_execute(result, args, options, context)

            # Add execution time
            result.execution_time_ms = (time.time() - start_time) * 1000

            return result

        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Command error: {str(e)}",
                error=e,
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def get_help(self) -> str:
        """
        Get help text for the command

        Returns:
            Help text string
        """
        lines = [
            f"[bold]{self.metadata.name}[/bold]",
            f"  {self.metadata.description}",
            ""
        ]

        if self.metadata.aliases:
            lines.append(f"Aliases: {', '.join(self.metadata.aliases)}")
            lines.append("")

        if self.arguments:
            lines.append("[bold]Arguments:[/bold]")
            for arg in self.arguments:
                required = " (required)" if arg.required else ""
                default = f" [default: {arg.default}]" if arg.default is not None else ""
                choices = f" [choices: {', '.join(arg.choices)}]" if arg.choices else ""
                lines.append(f"  {arg.name}{required}{default}{choices}")
                lines.append(f"    {arg.description}")
            lines.append("")

        if self.options:
            lines.append("[bold]Options:[/bold]")
            for opt in self.options:
                short = f", -{opt.short_name}" if opt.short_name else ""
                flag = " (flag)" if opt.is_flag else ""
                default = f" [default: {opt.default}]" if opt.default is not None else ""
                lines.append(f"  --{opt.name}{short}{flag}{default}")
                lines.append(f"    {opt.description}")
            lines.append("")

        if self.metadata.examples:
            lines.append("[bold]Examples:[/bold]")
            for example in self.metadata.examples:
                lines.append(f"  {example}")
            lines.append("")

        if self.metadata.see_also:
            lines.append("[bold]See also:[/bold]")
            for cmd in self.metadata.see_also:
                lines.append(f"  {cmd}")

        return "\n".join(lines)

    def display_result(self, result: CommandResult) -> None:
        """
        Display command result to user

        Args:
            result: Command result to display
        """
        if result.is_success():
            if result.message:
                self.console.print(f"[green]✓[/green] {result.message}")
            if result.data:
                import json
                self.console.print(json.dumps(result.data, indent=2))
        else:
            if result.message:
                self.console.print(f"[red]✗[/red] {result.message}")
            if result.error and self.metadata.deprecated is False:
                import traceback
                self.console.print(traceback.format_exc())


class AsyncCommand(BaseCommand):
    """
    Base class for async commands

    Provides convenience methods for async operations
    """

    async def execute_async(
        self,
        *command_args: str,
        **command_options
    ) -> CommandResult:
        """
        Execute an external command asynchronously

        Args:
            *command_args: Command and arguments
            **command_options: Additional options (cwd, env, etc.)

        Returns:
            CommandResult with command output
        """
        import asyncio
        import subprocess

        try:
            process = await asyncio.create_subprocess_exec(
                *command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=command_options.get('cwd'),
                env=command_options.get('env')
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=command_options.get('timeout', 30)
            )

            if process.returncode == 0:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    exit_code=0,
                    data={
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode()
                    }
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILURE,
                    exit_code=process.returncode,
                    message=stderr.decode(),
                    data={
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode()
                    }
                )

        except asyncio.TimeoutError:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Command timed out: {' '.join(command_args)}"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Command execution error: {str(e)}",
                error=e
            )


class SimpleCommand(BaseCommand):
    """
    Simplified command base class for simple commands

    Provides a simpler interface for commands that don't need
    the full complexity of BaseCommand
    """

    async def execute(
        self,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute the command (simplified version)

        Override this method in subclasses
        """
        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Command executed successfully"
        )
