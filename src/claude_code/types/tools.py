"""
Tool types and schemas for Claude Code CLI
Converted from TypeScript tool types
"""

from typing import List, Optional, Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field
from enum import Enum


class PermissionLevel(str, Enum):
    """Permission levels for tools"""
    ALLOW = "allow"        # Automatically allowed
    ASK = "ask"          # Ask user for permission
    DENY = "deny"        # Automatically denied


class ToolCategory(str, Enum):
    """Tool categories"""
    FILE_OPERATIONS = "file_operations"
    SHELL = "shell"
    GIT = "git"
    SEARCH = "search"
    API = "api"
    AGENT = "agent"
    LSP = "lsp"
    MCP = "mcp"
    TASK = "task"
    CONFIG = "config"
    SYSTEM = "system"


class ToolInputSchema(BaseModel):
    """Base class for tool input schemas"""
    pass


class ToolOutputSchema(BaseModel):
    """Base class for tool output schemas"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolPermission(BaseModel):
    """Tool permission configuration"""
    name: str
    level: PermissionLevel
    description: str


class ToolDefinition(BaseModel):
    """Tool definition for API"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolContext(BaseModel):
    """Context for tool execution"""
    cwd: str = Field(..., description="Current working directory")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions: List[ToolPermission] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of tool execution"""
    tool_name: str
    success: bool
    content: str
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Tool(BaseModel):
    """Base tool interface"""

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

    async def execute(self, input_data: ToolInputSchema, context: ToolContext) -> ToolResult:
        """
        Execute the tool with given input and context

        Args:
            input_data: Validated input parameters
            context: Execution context (cwd, permissions, etc.)

        Returns:
            ToolResult with execution outcome
        """
        raise NotImplementedError(f"Tool {self.name} does not implement execute()")

    def get_definition(self) -> ToolDefinition:
        """
        Get tool definition for API registration

        Returns:
            ToolDefinition with name, description, and input schema
        """
        raise NotImplementedError(f"Tool {self.name} does not implement get_definition()")

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
        self._categories: Dict[ToolCategory, List[Tool]] = {}

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

    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name

        Args:
            name: Tool name to look up

        Returns:
            Tool if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """
        Get all registered tools

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """
        Get tools filtered by category

        Args:
            category: Tool category to filter by

        Returns:
            List of tools in the category
        """
        return self._categories.get(category, [])

    def get_available_tools(self) -> List[Tool]:
        """
        Get all available (enabled) tools

        Returns:
            List of tools that are currently available
        """
        return [tool for tool in self._tools.values() if tool.is_available()]

    def get_definitions(self) -> List[ToolDefinition]:
        """
        Get all tool definitions for API

        Returns:
            List of tool definitions
        """
        return [tool.get_definition() for tool in self._tools.values()]