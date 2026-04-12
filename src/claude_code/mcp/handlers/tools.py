"""
MCP Tool Handlers
Handles tool invocation and result streaming
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from ...types import ToolContext, ToolResult, ToolPermissionLevel
from ...tools import ToolExecutionFramework, ToolRegistry
from ...permissions import PermissionManager

logger = logging.getLogger(__name__)


class MCPToolHandler:
    """
    Handler for MCP tool operations

    Manages tool invocation, permission checking, and result streaming
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutionFramework,
        permission_manager: PermissionManager
    ):
        """
        Initialize tool handler

        Args:
            tool_registry: Tool registry
            tool_executor: Tool execution framework
            permission_manager: Permission manager for permission checking
        """
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.permission_manager = permission_manager

        # Tool invocation state
        self._active_invocations: Dict[str, Dict[str, Any]] = {}

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> Dict[str, Any]:
        """
        Invoke a tool with permission checking

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments
            context: Tool execution context

        Returns:
            Tool invocation result in MCP format
        """
        try:
            # Check if tool exists
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                return self._format_error(
                    f"Tool not found: {tool_name}",
                    is_error=True
                )

            # Check permissions
            permission = await self._check_tool_permission(tool_name, arguments, context)
            if permission.level == ToolPermissionLevel.DENY:
                return self._format_error(
                    f"Tool execution denied: {permission.reason or 'Permission denied'}",
                    is_error=True
                )

            # Create context if not provided
            if not context:
                context = self._create_default_context()

            # Execute tool
            invocation_id = f"{tool_name}_{asyncio.get_event_loop().time()}"
            self._active_invocations[invocation_id] = {
                "tool_name": tool_name,
                "start_time": asyncio.get_event_loop().time(),
                "status": "executing"
            }

            try:
                result = await self.tool_executor.execute_tool(
                    tool_name=tool_name,
                    input_data=arguments,
                    context=context
                )

                # Update invocation state
                self._active_invocations[invocation_id]["status"] = "completed"
                self._active_invocations[invocation_id]["end_time"] = asyncio.get_event_loop().time()

                # Format result
                if result.success:
                    return self._format_success(result)
                else:
                    return self._format_error(
                        result.error or "Tool execution failed",
                        is_error=False
                    )

            finally:
                # Clean up invocation state
                if invocation_id in self._active_invocations:
                    del self._active_invocations[invocation_id]

        except Exception as e:
            logger.error(f"Error invoking tool {tool_name}: {e}", exc_info=True)
            return self._format_error(str(e), is_error=True)

    async def invoke_tool_stream(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext] = None
    ):
        """
        Invoke a tool with streaming result

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments
            context: Tool execution context

        Yields:
            Streaming result chunks
        """
        try:
            # Check if tool exists
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                yield {
                    "type": "error",
                    "error": f"Tool not found: {tool_name}"
                }
                return

            # Check permissions
            permission = await self._check_tool_permission(tool_name, arguments, context)
            if permission.level == ToolPermissionLevel.DENY:
                yield {
                    "type": "error",
                    "error": f"Tool execution denied: {permission.reason or 'Permission denied'}"
                }
                return

            # Create context if not provided
            if not context:
                context = self._create_default_context()

            # Start stream
            yield {
                "type": "start",
                "tool_name": tool_name
            }

            # Execute tool (would need streaming support in tool executor)
            # For now, use non-streaming execution
            result = await self.tool_executor.execute_tool(
                tool_name=tool_name,
                input_data=arguments,
                context=context
            )

            # Yield result
            if result.success:
                yield {
                    "type": "data",
                    "content": result.result.model_dump() if result.result else None
                }
            else:
                yield {
                    "type": "error",
                    "error": result.error or "Tool execution failed"
                }

            # End stream
            yield {
                "type": "end",
                "tool_name": tool_name
            }

        except Exception as e:
            logger.error(f"Error in streaming tool invocation: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }

    async def _check_tool_permission(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext]
    ) -> Any:
        """
        Check if tool execution is permitted

        Args:
            tool_name: Name of tool
            arguments: Tool arguments
            context: Execution context

        Returns:
            Permission decision
        """
        # This would integrate with the permission manager
        # For now, allow all executions
        return type('Permission', (), {
            'level': ToolPermissionLevel.ALLOW,
            'reason': None
        })()

    def _create_default_context(self) -> ToolContext:
        """
        Create default tool execution context

        Returns:
            Default ToolContext
        """
        import os
        from pathlib import Path

        return ToolContext(
            cwd=str(Path.cwd()),
            user_id=None,
            session_id=None,
            permissions=[],
            environment=dict(os.environ)
        )

    def _format_success(self, result: ToolResult) -> Dict[str, Any]:
        """
        Format successful tool result for MCP

        Args:
            result: Tool execution result

        Returns:
            MCP-formatted result
        """
        content = []

        if result.result:
            # Add result content
            if hasattr(result.result, 'content'):
                content.append({
                    "type": "text",
                    "text": str(result.result.content)
                })
            elif hasattr(result.result, 'model_dump'):
                content.append({
                    "type": "text",
                    "text": str(result.result.model_dump())
                })
            else:
                content.append({
                    "type": "text",
                    "text": str(result.result)
                })

        return {
            "content": content,
            "isError": False
        }

    def _format_error(self, error_message: str, is_error: bool = True) -> Dict[str, Any]:
        """
        Format error result for MCP

        Args:
            error_message: Error message
            is_error: Whether this is an error (vs warning)

        Returns:
            MCP-formatted error result
        """
        return {
            "content": [
                {
                    "type": "text",
                    "text": error_message
                }
            ],
            "isError": is_error
        }

    def get_active_invocations(self) -> List[Dict[str, Any]]:
        """
        Get list of active tool invocations

        Returns:
            List of active invocations
        """
        return [
            {
                "invocation_id": invocation_id,
                **invocation_data
            }
            for invocation_id, invocation_data in self._active_invocations.items()
        ]

    def cancel_invocation(self, invocation_id: str) -> bool:
        """
        Cancel an active tool invocation

        Args:
            invocation_id: ID of invocation to cancel

        Returns:
            True if cancelled, False if not found
        """
        if invocation_id in self._active_invocations:
            self._active_invocations[invocation_id]["status"] = "cancelled"
            # Note: Actual cancellation would need to be implemented in tool executor
            return True
        return False


class MCPToolDiscovery:
    """
    Handler for tool discovery and schema export
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize tool discovery

        Args:
            tool_registry: Tool registry
        """
        self.tool_registry = tool_registry

    def discover_tools(self, filter_category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover available tools

        Args:
            filter_category: Optional category filter

        Returns:
            List of tool definitions
        """
        tools = self.tool_registry.get_available_tools()

        if filter_category:
            tools = [t for t in tools if t.get_definition().category == filter_category]

        return [
            self._export_tool_schema(tool)
            for tool in tools
        ]

    def export_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Export schema for a specific tool

        Args:
            tool_name: Name of tool

        Returns:
            Tool schema or None if not found
        """
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return None

        return self._export_tool_schema(tool)

    def _export_tool_schema(self, tool) -> Dict[str, Any]:
        """
        Export tool schema

        Args:
            tool: Tool instance

        Returns:
            Tool schema dictionary
        """
        definition = tool.get_definition()

        return {
            "name": definition.name,
            "description": definition.description,
            "inputSchema": definition.input_schema.model_dump() if hasattr(definition.input_schema, 'model_dump') else definition.input_schema,
            "metadata": {
                "category": definition.category.value if definition.category else None,
                "permission_level": definition.permission_level.value if definition.permission_level else None,
            }
        }

    def get_tool_categories(self) -> List[str]:
        """
        Get list of available tool categories

        Returns:
            List of category names
        """
        tools = self.tool_registry.get_available_tools()
        categories = set()

        for tool in tools:
            definition = tool.get_definition()
            if definition.category:
                categories.add(definition.category.value)

        return sorted(list(categories))
