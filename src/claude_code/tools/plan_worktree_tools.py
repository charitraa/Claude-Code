"""
Plan mode and worktree tools for Claude Code CLI
"""

from typing import Optional
from pydantic import BaseModel, Field

from .base import Tool
from ..types import ToolContext, ToolResult, ToolInputSchema, ToolCategory, PermissionLevel


class EnterPlanModeInput(ToolInputSchema):
    """Input schema for EnterPlanMode tool"""
    
    plan: str = Field(..., description="Plan description")


class EnterPlanModeTool(Tool):
    """EnterPlanMode tool"""
    
    name: str = "EnterPlanMode"
    description: str = "Enter plan mode to draft a plan"
    category: ToolCategory = ToolCategory.SYSTEM
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True
    
    async def execute(self, input_data: EnterPlanModeInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="EnterPlanMode not yet implemented"
        )


class ExitPlanModeInput(ToolInputSchema):
    """Input schema for ExitPlanMode tool"""
    
    approval: bool = Field(..., description="Whether the plan is approved")


class ExitPlanModeTool(Tool):
    """ExitPlanMode tool"""
    
    name: str = "ExitPlanMode"
    description: str = "Exit plan mode and execute or cancel"
    category: ToolCategory = ToolCategory.SYSTEM
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True
    
    async def execute(self, input_data: ExitPlanModeInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="ExitPlanMode not yet implemented"
        )


class EnterWorktreeInput(ToolInputSchema):
    """Input schema for EnterWorktree tool"""
    
    path: str = Field(..., description="Path to the worktree")
    branch: Optional[str] = Field(default=None, description="Branch name")


class EnterWorktreeTool(Tool):
    """EnterWorktree tool"""
    
    name: str = "EnterWorktree"
    description: str = "Enter a git worktree"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True
    
    async def execute(self, input_data: EnterWorktreeInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="EnterWorktree not yet implemented"
        )


class ExitWorktreeInput(ToolInputSchema):
    """Input schema for ExitWorktree tool"""
    
    path: Optional[str] = Field(default=None, description="Path to the worktree")


class ExitWorktreeTool(Tool):
    """ExitWorktree tool"""
    
    name: str = "ExitWorktree"
    description: str = "Exit a git worktree"
    category: ToolCategory = ToolCategory.GIT
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True
    
    async def execute(self, input_data: ExitWorktreeInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="ExitWorktree not yet implemented"
        )


class TaskStopInput(ToolInputSchema):
    """Input schema for TaskStop tool"""
    
    task_id: str = Field(..., description="Task ID to stop")


class TaskStopTool(Tool):
    """TaskStop tool"""
    
    name: str = "TaskStop"
    description: str = "Stop a running task"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True
    
    async def execute(self, input_data: TaskStopInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="TaskStop not yet implemented"
        )


class TaskOutputInput(ToolInputSchema):
    """Input schema for TaskOutput tool"""
    
    task_id: str = Field(..., description="Task ID to get output from")


class TaskOutputTool(Tool):
    """TaskOutput tool"""
    
    name: str = "TaskOutput"
    description: str = "Get output from a task"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"
    permission_level: PermissionLevel = PermissionLevel.ALLOW
    is_enabled: bool = True
    
    async def execute(self, input_data: TaskOutputInput, context: ToolContext) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            output="",
            error="TaskOutput not yet implemented"
        )
