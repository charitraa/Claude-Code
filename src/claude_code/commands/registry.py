"""
Command Registry
Manages command registration, discovery, and execution
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type, Callable, Any
from collections import defaultdict
from pathlib import Path

from .base import (
    BaseCommand,
    CommandResult,
    CommandMetadata,
    CommandStatus,
)
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Registry for managing commands

    Provides command registration, discovery, and execution functionality
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize command registry

        Args:
            console: Console for output
        """
        self.console = console or Console()
        self._commands: Dict[str, Type[BaseCommand]] = {}
        self._aliases: Dict[str, str] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

        # Execution hooks
        self._before_execute_hooks: List[Callable] = []
        self._after_execute_hooks: List[Callable] = []

        # History
        self._history: List[Dict[str, Any]] = []

        # Command dependencies and aliases for orchestration
        self._dependencies: Dict[str, List[str]] = {}
        self._command_chains: List[List[Dict[str, Any]]] = []

    def register(self, command_class: Type[BaseCommand]) -> None:
        """
        Register a command class

        Args:
            command_class: Command class to register
        """
        # Create instance to get metadata
        instance = command_class(console=self.console)
        metadata = instance.metadata

        # Register main command name
        self._commands[metadata.name] = command_class

        # Register aliases
        for alias in metadata.aliases:
            self._aliases[alias] = metadata.name

        # Add to category
        self._categories[metadata.category].append(metadata.name)

        logger.info(f"Registered command: {metadata.name} (category: {metadata.category})")

    def register_function(self, name: str, func: Callable, metadata: CommandMetadata) -> None:
        """
        Register a function as a command

        Args:
            name: Command name
            func: Function to execute
            metadata: Command metadata
        """
        # Create a command class from the function
        class FunctionCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return metadata

            async def execute(
                self,
                args: List[str],
                options: Dict[str, Any],
                context: Optional[Dict[str, Any]] = None
            ) -> CommandResult:
                try:
                    result = func(args, options, context)
                    if asyncio.iscoroutine(result):
                        result = await result

                    if isinstance(result, CommandResult):
                        return result
                    else:
                        return CommandResult(
                            status=CommandStatus.SUCCESS,
                            message=str(result)
                        )
                except Exception as e:
                    return CommandResult(
                        status=CommandStatus.ERROR,
                        message=str(e),
                        error=e
                    )

        self.register(FunctionCommand)

    def unregister(self, name: str) -> bool:
        """
        Unregister a command

        Args:
            name: Command name or alias

        Returns:
            True if unregistered, False if not found
        """
        # Resolve alias
        if name in self._aliases:
            actual_name = self._aliases[name]
            del self._aliases[name]
            name = actual_name

        if name in self._commands:
            command_class = self._commands[name]
            instance = command_class(console=self.console)
            metadata = instance.metadata

            # Remove from commands
            del self._commands[name]

            # Remove from category
            if metadata.category in self._categories:
                self._categories[metadata.category].remove(name)

            # Remove aliases
            aliases_to_remove = [
                alias for alias, target in self._aliases.items()
                if target == name
            ]
            for alias in aliases_to_remove:
                del self._aliases[alias]

            logger.info(f"Unregistered command: {name}")
            return True

        return False

    def get_command(self, name: str) -> Optional[Type[BaseCommand]]:
        """
        Get a command class by name or alias

        Args:
            name: Command name or alias

        Returns:
            Command class or None if not found
        """
        # Resolve alias
        actual_name = self._aliases.get(name, name)
        return self._commands.get(actual_name)

    def list_commands(self, category: Optional[str] = None) -> List[str]:
        """
        List registered commands

        Args:
            category: Optional category filter

        Returns:
            List of command names
        """
        if category:
            return self._categories.get(category, []).copy()
        return list(self._commands.keys())

    def list_categories(self) -> List[str]:
        """
        List command categories

        Returns:
            List of category names
        """
        return list(self._categories.keys())

    def get_command_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a command

        Args:
            name: Command name or alias

        Returns:
            Command information or None if not found
        """
        command_class = self.get_command(name)
        if not command_class:
            return None

        instance = command_class(console=self.console)
        metadata = instance.metadata

        return {
            "name": metadata.name,
            "description": metadata.description,
            "category": metadata.category,
            "aliases": metadata.aliases,
            "examples": metadata.examples,
            "see_also": metadata.see_also,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                    "default": arg.default,
                    "type": arg.type.__name__
                }
                for arg in instance.arguments
            ],
            "options": [
                {
                    "name": opt.name,
                    "short_name": opt.short_name,
                    "description": opt.description,
                    "is_flag": opt.is_flag,
                    "default": opt.default
                }
                for opt in instance.options
            ]
        }

    async def execute(
        self,
        name: str,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute a command

        Args:
            name: Command name or alias
            args: Command arguments
            options: Command options
            context: Optional execution context

        Returns:
            CommandResult
        """
        # Get command
        command_class = self.get_command(name)
        if not command_class:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Command not found: {name}",
                exit_code=1
            )

        # Create command instance
        command = command_class(console=self.console)

        # Run before hooks
        for hook in self._before_execute_hooks:
            try:
                result = hook(name, args, options, context)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in before_execute hook: {e}")

        # Execute command
        result = await command.run(args, options, context)

        # Run after hooks
        for hook in self._after_execute_hooks:
            try:
                hook_result = hook(name, result, args, options, context)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except Exception as e:
                logger.error(f"Error in after_execute hook: {e}")

        # Add to history
        self._add_to_history(name, args, options, result)

        return result

    def _add_to_history(
        self,
        name: str,
        args: List[str],
        options: Dict[str, Any],
        result: CommandResult
    ) -> None:
        """
        Add command to execution history

        Args:
            name: Command name
            args: Command arguments
            options: Command options
            result: Command result
        """
        import time

        entry = {
            "name": name,
            "args": args,
            "options": options,
            "status": result.status,
            "exit_code": result.exit_code,
            "timestamp": time.time(),
            "execution_time_ms": result.execution_time_ms
        }

        self._history.append(entry)

        # Keep only last 1000 entries
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    def get_history(
        self,
        limit: Optional[int] = None,
        command_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get command execution history

        Args:
            limit: Maximum number of entries to return
            command_filter: Filter by command name

        Returns:
            List of history entries
        """
        history = self._history.copy()

        if command_filter:
            history = [h for h in history if h["name"] == command_filter]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear command history"""
        self._history.clear()

    def add_before_execute_hook(self, hook: Callable) -> None:
        """
        Add a hook to run before command execution

        Args:
            hook: Hook function
        """
        self._before_execute_hooks.append(hook)

    def add_after_execute_hook(self, hook: Callable) -> None:
        """
        Add a hook to run after command execution

        Args:
            hook: Hook function
        """
        self._after_execute_hooks.append(hook)

    def display_commands(self, category: Optional[str] = None) -> None:
        """
        Display registered commands in a table

        Args:
            category: Optional category filter
        """
        commands = self.list_commands(category)

        if not commands:
            self.console.print("[yellow]No commands found[/yellow]")
            return

        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Category", style="yellow")

        for cmd_name in sorted(commands):
            command_class = self._commands.get(cmd_name)
            if command_class:
                instance = command_class(console=self.console)
                metadata = instance.metadata

                table.add_row(
                    cmd_name,
                    metadata.description,
                    metadata.category
                )

        self.console.print(table)

    def search_commands(self, query: str) -> List[str]:
        """
        Search for commands by name or description

        Args:
            query: Search query

        Returns:
            List of matching command names
        """
        query_lower = query.lower()
        matches = []

        for name, command_class in self._commands.items():
            instance = command_class(console=self.console)
            metadata = instance.metadata

            # Search in name, description, and aliases
            if (query_lower in name.lower() or
                query_lower in metadata.description.lower() or
                any(query_lower in alias.lower() for alias in metadata.aliases)):
                matches.append(name)

        return matches

    def load_commands_from_directory(self, directory: Path) -> None:
        """
        Load commands from a directory

        Args:
            directory: Directory containing command modules
        """
        if not directory.exists():
            logger.warning(f"Command directory does not exist: {directory}")
            return

        import importlib.util
        import sys

        for module_file in directory.glob("*.py"):
            if module_file.name.startswith("_"):
                continue

            try:
                module_name = f"claude_code.commands.builtin.{module_file.stem}"

                # Load module
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Find and register command classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseCommand) and
                            attr != BaseCommand and
                            not attr.__name__.startswith("_")):
                            self.register(attr)

                    logger.info(f"Loaded commands from {module_file}")

            except Exception as e:
                logger.error(f"Error loading commands from {module_file}: {e}")

    def set_command_dependencies(self, command_name: str, dependencies: List[str]) -> None:
        """
        Set command dependencies

        Args:
            command_name: Name of command
            dependencies: List of command names that must be executed first
        """
        self._dependencies[command_name] = dependencies
        logger.info(f"Set dependencies for {command_name}: {dependencies}")

    def get_command_dependencies(self, command_name: str) -> List[str]:
        """
        Get command dependencies

        Args:
            command_name: Name of command

        Returns:
            List of dependency command names
        """
        return self._dependencies.get(command_name, [])

    async def execute_with_dependencies(
        self,
        name: str,
        args: List[str],
        options: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute a command with its dependencies

        Args:
            name: Command name or alias
            args: Command arguments
            options: Command options
            context: Optional execution context

        Returns:
            CommandResult
        """
        dependencies = self.get_command_dependencies(name)

        # Execute dependencies first
        for dep_name in dependencies:
            self.console.print(f"[cyan]Running dependency: {dep_name}[/cyan]")
            dep_result = await self.execute(dep_name, [], {}, context)
            if not dep_result.is_success():
                return CommandResult(
                    status=CommandStatus.ERROR,
                    message=f"Dependency {dep_name} failed: {dep_result.message}",
                    exit_code=dep_result.exit_code
                )

        # Execute main command
        return await self.execute(name, args, options, context)

    async def execute_chain(self, commands: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> List[CommandResult]:
        """
        Execute a chain of commands

        Args:
            commands: List of command specifications
                Each spec: {"name": str, "args": List[str], "options": Dict[str, Any]}
            context: Optional execution context

        Returns:
            List of CommandResult for each command
        """
        results = []

        for i, cmd_spec in enumerate(commands):
            cmd_name = cmd_spec.get("name")
            cmd_args = cmd_spec.get("args", [])
            cmd_options = cmd_spec.get("options", {})

            self.console.print(f"[cyan]Executing command {i+1}/{len(commands)}: {cmd_name}[/cyan]")

            result = await self.execute(cmd_name, cmd_args, cmd_options, context)
            results.append(result)

            # Stop chain if command failed
            if not result.is_success() and not cmd_spec.get("continue_on_failure", False):
                self.console.print(f"[red]Command chain stopped at {cmd_name}[/red]")
                break

        return results

    def create_command_alias(self, alias: str, command_chain: List[Dict[str, Any]]) -> None:
        """
        Create a command alias that executes a chain of commands

        Args:
            alias: Alias name
            command_chain: List of command specifications
        """
        self._command_chains.append({
            "alias": alias,
            "commands": command_chain
        })
        self._aliases[alias] = f"_chain_{len(self._command_chains) - 1}"
        logger.info(f"Created command alias: {alias}")

    async def execute_alias(self, alias: str, context: Optional[Dict[str, Any]] = None) -> CommandResult:
        """
        Execute a command alias

        Args:
            alias: Alias name
            context: Optional execution context

        Returns:
            CommandResult
        """
        # Find the chain
        chain_spec = None
        for spec in self._command_chains:
            if spec["alias"] == alias:
                chain_spec = spec
                break

        if not chain_spec:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Alias not found: {alias}",
                exit_code=1
            )

        # Execute the chain
        results = await self.execute_chain(chain_spec["commands"], context)

        # Return summary
        successful = sum(1 for r in results if r.is_success())
        total = len(results)

        return CommandResult(
            status=CommandStatus.SUCCESS if successful == total else CommandStatus.FAILURE,
            message=f"Alias {alias} completed: {successful}/{total} commands successful",
            data={
                "alias": alias,
                "successful": successful,
                "total": total,
                "results": [r.model_dump() for r in results]
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_commands": len(self._commands),
            "total_aliases": len(self._aliases),
            "categories": {
                category: len(commands)
                for category, commands in self._categories.items()
            },
            "history_entries": len(self._history),
            "before_hooks": len(self._before_execute_hooks),
            "after_hooks": len(self._after_execute_hooks),
        }
