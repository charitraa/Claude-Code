"""
Task management tools for Claude Code CLI
Converted from TypeScript task management system
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class TaskCreateInput(BaseModel):
    """Input schema for TaskCreate tool"""

    subject: str = Field(..., description="Brief title of the task")
    description: str = Field(..., description="Detailed description of what needs to be done")
    active_form: Optional[str] = Field(default=None, description="Present continuous form for the task")


class TaskGetInput(BaseModel):
    """Input schema for TaskGet tool"""

    task_id: str = Field(..., description="Unique identifier of the task to retrieve")


class TaskUpdateInput(BaseModel):
    """Input schema for TaskUpdate tool"""

    task_id: str = Field(..., description="Unique identifier of the task to update")
    subject: Optional[str] = Field(default=None, description="New subject for the task")
    description: Optional[str] = Field(default=None, description="New description for the task")
    active_form: Optional[str] = Field(default=None, description="New present continuous form for the task")
    status: Optional[str] = Field(default=None, description="New status for the task (pending, in_progress, completed)")
    add_blocks: Optional[List[str]] = Field(default=None, description="List of task IDs this task blocks")
    add_blocked_by: Optional[List[str]] = Field(default=None, description="List of task IDs that block this task")


class TaskListInput(BaseModel):
    """Input schema for TaskList tool"""

    show_all: bool = Field(default=False, description="Show all tasks including completed")
    show_pending_only: bool = Field(default=False, description="Show only pending tasks")


class TaskCreateTool(Tool):
    """
    Task creation tool

    Replaces TypeScript TaskCreateTool
    """

    # Tool metadata
    name: str = "TaskCreate"
    description: str = "Create a new task for tracking work"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: TaskCreateInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Create a new task

        Args:
            input_data: Validated task creation input
            context: Execution context

        Returns:
            ToolResult with task creation status
        """
        import time
        start_time = time.time()

        try:
            # Generate unique task ID
            task_id = str(uuid.uuid4())

            # Create task object
            task = {
                "id": task_id,
                "subject": input_data.subject,
                "description": input_data.description,
                "active_form": input_data.active_form,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "blocks": [],
                "blocked_by": [],
                "owner": None,
            }

            # Save task to file
            task_file = self._get_task_file(task_id)
            task_file.parent.mkdir(parents=True, exist_ok=True)

            with open(task_file, 'w') as f:
                json.dump(task, f, indent=2)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Created task '{input_data.subject}' with ID: {task_id}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "task_id": task_id,
                    "task": task,
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
                    "subject": {
                        "type": "string",
                        "description": "Brief title of the task",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what needs to be done",
                    },
                    "active_form": {
                        "type": "string",
                        "description": "Present continuous form for the task (optional)",
                    },
                },
                "required": ["subject", "description"],
            },
        )


class TaskGetTool(Tool):
    """
    Task retrieval tool

    Replaces TypeScript TaskGetTool
    """

    # Tool metadata
    name: str = "TaskGet"
    description: str = "Retrieve a specific task by ID"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: TaskGetInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Retrieve a task by ID

        Args:
            input_data: Validated task retrieval input
            context: Execution context

        Returns:
            ToolResult with task details
        """
        import time
        start_time = time.time()

        try:
            # Get task file
            task_file = self._get_task_file(input_data.task_id)

            if not task_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Task '{input_data.task_id}' not found",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read task
            with open(task_file, 'r') as f:
                task = json.load(f)

            # Format task for display
            task_display = self._format_task_display(task)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=task_display,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "task": task,
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
                    "task_id": {
                        "type": "string",
                        "description": "Unique identifier of the task to retrieve",
                    },
                },
                "required": ["task_id"],
            },
        )


class TaskUpdateTool(Tool):
    """
    Task update tool

    Replaces TypeScript TaskUpdateTool
    """

    # Tool metadata
    name: str = "TaskUpdate"
    description: str = "Update an existing task"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: TaskUpdateInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Update an existing task

        Args:
            input_data: Validated task update input
            context: Execution context

        Returns:
            ToolResult with update status
        """
        import time
        start_time = time.time()

        try:
            # Get existing task
            task_file = self._get_task_file(input_data.task_id)

            if not task_file.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Task '{input_data.task_id}' not found",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read existing task
            with open(task_file, 'r') as f:
                task = json.load(f)

            # Update task fields
            if input_data.subject is not None:
                task["subject"] = input_data.subject
            if input_data.description is not None:
                task["description"] = input_data.description
            if input_data.active_form is not None:
                task["active_form"] = input_data.active_form
            if input_data.status is not None:
                task["status"] = input_data.status
                if input_data.status == "in_progress":
                    task["owner"] = "claude"  # Assign to current agent

            # Handle task dependencies
            if input_data.add_blocks:
                task["blocks"] = input_data.add_blocks
            if input_data.add_blocked_by:
                task["blocked_by"] = input_data.add_blocked_by

            # Update timestamp
            task["updated_at"] = datetime.now().isoformat()

            # Save updated task
            with open(task_file, 'w') as f:
                json.dump(task, f, indent=2)

            changes = []
            if input_data.subject is not None:
                changes.append(f"subject → {input_data.subject}")
            if input_data.status is not None:
                changes.append(f"status → {input_data.status}")

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Updated task '{input_data.task_id}': {', '.join(changes)}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "task_id": input_data.task_id,
                    "updated_task": task,
                    "changes": changes,
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
                    "task_id": {
                        "type": "string",
                        "description": "Unique identifier of the task to update",
                    },
                    "subject": {
                        "type": "string",
                        "description": "New subject for the task (optional)",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the task (optional)",
                    },
                    "active_form": {
                        "type": "string",
                        "description": "New present continuous form for the task (optional)",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status for the task (optional)",
                    },
                    "add_blocks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task IDs this task blocks (optional)",
                    },
                    "add_blocked_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task IDs that block this task (optional)",
                    },
                },
                "required": ["task_id"],
            },
        )


class TaskListTool(Tool):
    """
    Task listing tool

    Replaces TypeScript TaskListTool
    """

    # Tool metadata
    name: str = "TaskList"
    description: str = "List all tasks with optional filtering"
    category: ToolCategory = ToolCategory.TASK
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: TaskListInput,
        context: ToolContext
    ) -> ToolResult:
        """
        List tasks with optional filtering

        Args:
            input_data: Validated task listing input
            context: Execution context

        Returns:
            ToolResult with task list
        """
        import time
        start_time = time.time()

        try:
            # Get task directory
            task_dir = Path.home() / ".claude" / "tasks"
            task_dir.mkdir(parents=True, exist_ok=True)

            # Get all task files
            tasks = []
            for task_file in task_dir.glob("*.json"):
                try:
                    with open(task_file, 'r') as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception:
                    continue

            # Apply filters
            filtered_tasks = tasks
            if not input_data.show_all:
                filtered_tasks = [t for t in tasks if t.get("status") != "completed"]
            if input_data.show_pending_only:
                filtered_tasks = [t for t in filtered_tasks if t.get("status") == "pending"]

            # Format results
            result_content = self._format_task_list(filtered_tasks)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=result_content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "total_tasks": len(tasks),
                    "filtered_tasks": len(filtered_tasks),
                    "tasks": filtered_tasks,
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
                    "show_all": {
                        "type": "boolean",
                        "description": "Show all tasks including completed (default: false)",
                        "default": False,
                    },
                    "show_pending_only": {
                        "type": "boolean",
                        "description": "Show only pending tasks (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
        )

    def _get_task_file(self, task_id: str) -> Path:
        """Get file path for a task ID"""
        return Path.home() / ".claude" / "tasks" / f"{task_id}.json"

    def _format_task_display(self, task: Dict) -> str:
        """Format a single task for display"""
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
        }.get(task.get("status", "pending"), "❓")

        lines = [
            f"{status_emoji} {task.get('id', 'unknown')}",
            f"Subject: {task.get('subject', 'No subject')}",
            f"Status: {task.get('status', 'unknown')}",
            f"Created: {task.get('created_at', 'unknown')}",
            f"Updated: {task.get('updated_at', 'unknown')}",
        ]

        if task.get('description'):
            lines.append(f"Description: {task.get('description')}")

        if task.get('blocked_by'):
            lines.append(f"Blocked by: {', '.join(task['blocked_by'])}")

        return '\n'.join(lines)

    def _format_task_list(self, tasks: List[Dict]) -> str:
        """Format task list for display"""
        if not tasks:
            return "No tasks found"

        # Group by status
        pending = [t for t in tasks if t.get("status") == "pending"]
        in_progress = [t for t in tasks if t.get("status") == "in_progress"]
        completed = [t for t in tasks if t.get("status") == "completed"]

        lines = []
        lines.append(f"Total tasks: {len(tasks)}")
        lines.append(f"Pending: {len(pending)} | In Progress: {len(in_progress)} | Completed: {len(completed)}")
        lines.append("")

        # Show pending tasks first
        if pending:
            lines.append("⏳ Pending:")
            for task in pending[:10]:  # Limit display
                lines.append(f"  • {task.get('subject', 'No subject')} ({task.get('id', 'unknown')})")

        # Show in-progress tasks
        if in_progress:
            lines.append("🔄 In Progress:")
            for task in in_progress[:10]:
                lines.append(f"  • {task.get('subject', 'No subject')} ({task.get('id', 'unknown')})")

        # Show completed tasks if requested
        if completed:
            lines.append("✅ Completed:")
            for task in completed[:5]:  # Limit display
                lines.append(f"  • {task.get('subject', 'No subject')} ({task.get('id', 'unknown')})")

        return '\n'.join(lines)