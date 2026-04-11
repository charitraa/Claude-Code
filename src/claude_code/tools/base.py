"""
Base tool implementation
Converted from TypeScript tool base classes
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field

from ..types import (
    ToolDefinition,
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class ToolInputSchema(BaseModel):
    """Base class for tool input schemas"""
    pass


class Tool(ABC):
    """
    Base tool interface

    Replaces TypeScript Tool base class
    """

    # Tool metadata
    name: str = Field(..., description="Unique name for the tool")
    description: str = Field(..., description="Human-readable description")
    category: ToolCategory = Field(..., description="Tool category")
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def execute(
        self,
        input_data: ToolInputSchema,
        context: ToolContext
    ) -> ToolResult:
        """
        Execute the tool with given input and context

        Args:
            input_data: Validated input parameters
            context: Execution context (cwd, permissions, etc.)

        Returns:
            ToolResult with execution outcome
        """
        pass

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """
        Get tool definition for API registration

        Returns:
            ToolDefinition with name, description, and input schema
        """
        pass

    def is_available(self) -> bool:
        """
        Check if tool is available in current environment

        Returns:
            True if tool can be used, False otherwise
        """
        return self.is_enabled


class ToolRegistry:
    """Registry for managing available tools"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, list] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool

        # Update category index
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool)

    def get_tool(self, name: str):
        """
        Get a tool by name

        Args:
            name: Tool name to look up

        Returns:
            Tool if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_tools(self) -> list:
        """
        Get all registered tools

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> list:
        """
        Get tools filtered by category

        Args:
            category: Tool category to filter by

        Returns:
            List of tools in the category
        """
        return self._categories.get(category, [])

    def get_available_tools(self) -> list:
        """
        Get all available (enabled) tools

        Returns:
            List of tools that are currently available
        """
        return [tool for tool in self._tools.values() if tool.is_available()]

    def get_definitions(self) -> list:
        """
        Get all tool definitions for API

        Returns:
            List of tool definitions
        """
        return [tool.get_definition() for tool in self._tools.values()]