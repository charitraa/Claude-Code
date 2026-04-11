"""
Tool execution framework for Claude Code CLI
Converted from TypeScript tool execution system
"""

import asyncio
from typing import Dict, Optional, List, Callable, Awaitable, Any
from pydantic import BaseModel, Field

from .base import Tool, ToolRegistry
from ..types import (
    ToolContext,
    ToolResult,
    PermissionLevel,
    PermissionManager,
    PermissionDecision,
    PermissionContext,
)


class ToolExecutionResult(BaseModel):
    """Result of tool execution workflow"""
    tool_name: str
    success: bool
    result: Optional[ToolResult] = None
    error: Optional[str] = None
    user_approved: bool = True
    execution_time_ms: int = 0


class ToolExecutionFramework:
    """
    Framework for executing tools with permission handling

    Replaces TypeScript tool execution system
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager
    ):
        """
        Initialize tool execution framework

        Args:
            tool_registry: Registry of available tools
            permission_manager: Permission manager for checking permissions
        """
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self._active_executions: Dict[str, asyncio.Task] = {}

    async def execute_tool(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolContext,
        auto_approve: bool = False
    ) -> ToolExecutionResult:
        """
        Execute a tool with permission checking

        Args:
            tool_name: Name of the tool to execute
            input_data: Input data for the tool
            context: Execution context
            auto_approve: Whether to skip permission approval

        Returns:
            ToolExecutionResult with execution outcome
        """
        import time

        start_time = time.time()

        # Get tool from registry
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found"
            )

        # Check tool availability
        if not tool.is_available():
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is not available"
            )

        # Check permissions
        permission_level = self.permission_manager.check_permission(
            tool_name,
            f"execute_{tool_name}",
            context
        )

        # Handle permission levels
        if permission_level == PermissionLevel.DENY:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                user_approved=False,
                error=f"Tool '{tool_name}' is denied by policy"
            )

        user_approved = True
        if permission_level == PermissionLevel.ASK and not auto_approve:
            # Ask user for approval (this would integrate with UI)
            user_approved = await self._ask_permission(tool_name, context)
            if not user_approved:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=False,
                    user_approved=False,
                    error=f"Tool '{tool_name}' execution denied by user"
                )

        # Record permission decision
        decision = PermissionDecision(
            rule_name=f"tool_{tool_name}",
            tool_name=tool_name,
            operation=f"execute_{tool_name}",
            level=permission_level,
            user_approved=user_approved,
            timestamp=time.time()
        )
        self.permission_manager.record_decision(decision)

        try:
            # Create tool input model
            tool_input = tool.input_schema(**input_data)

            # Execute tool
            result = await tool.execute(tool_input, context)

            execution_time_ms = int((time.time() - start_time) * 1000)

            if result.success:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    user_approved=user_approved,
                    result=result,
                    execution_time_ms=execution_time_ms
                )
            else:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=False,
                    user_approved=user_approved,
                    result=result,
                    error=result.error,
                    execution_time_ms=execution_time_ms
                )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                user_approved=user_approved,
                error=f"Tool execution error: {str(e)}",
                execution_time_ms=execution_time_ms
            )

    async def _ask_permission(self, tool_name: str, context: ToolContext) -> bool:
        """
        Ask user for tool execution permission

        Args:
            tool_name: Name of the tool
            context: Execution context

        Returns:
            True if user approves, False otherwise
        """
        # This would integrate with the UI to prompt the user
        # For now, we'll implement a simple console prompt
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()

        # Get tool for description
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            description = tool.description
        else:
            description = f"Execute {tool_name}"

        console.print(f"\n[yellow]Tool Permission Request[/yellow]")
        console.print(f"Tool: [cyan]{tool_name}[/cyan]")
        console.print(f"Description: {description}")
        console.print(f"Directory: [cyan]{context.current_directory}[/cyan]")

        response = Prompt.ask(
            "[yellow]Allow this tool execution?[/yellow]",
            choices=["yes", "no", "always"],
            default="yes"
        )

        if response == "always":
            # Add allow rule for this tool
            from ..types import PermissionRule, PermissionType
            rule = PermissionRule(
                name=f"tool_{tool_name}",
                type=PermissionType.TOOL,
                level=PermissionLevel.ALLOW,
                description=f"User approved {tool_name} always",
                applies_to=[tool_name]
            )
            self.permission_manager.add_rule(rule)
            return True

        return response == "yes"

    async def execute_multiple_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: ToolContext,
        parallel: bool = False
    ) -> List[ToolExecutionResult]:
        """
        Execute multiple tools

        Args:
            tool_calls: List of tool call specifications
            context: Execution context
            parallel: Whether to execute tools in parallel

        Returns:
            List of tool execution results
        """
        if parallel:
            # Execute all tools concurrently
            tasks = [
                self.execute_tool(
                    call.get("tool_name"),
                    call.get("input_data", {}),
                    context,
                    call.get("auto_approve", False)
                )
                for call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        else:
            # Execute tools sequentially
            results = []
            for call in tool_calls:
                result = await self.execute_tool(
                    call.get("tool_name"),
                    call.get("input_data", {}),
                    context,
                    call.get("auto_approve", False)
                )
                results.append(result)

                # Stop if previous tool failed
                if not result.success:
                    break

            return results

    async def cancel_execution(self, tool_name: str) -> bool:
        """
        Cancel an active tool execution

        Args:
            tool_name: Name of the tool to cancel

        Returns:
            True if cancelled, False otherwise
        """
        if tool_name in self._active_executions:
            task = self._active_executions[tool_name]
            task.cancel()
            del self._active_executions[tool_name]
            return True

        return False

    def get_active_executions(self) -> List[str]:
        """
        Get list of currently executing tools

        Returns:
            List of tool names currently being executed
        """
        return list(self._active_executions.keys())