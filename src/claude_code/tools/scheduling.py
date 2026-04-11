"""
Scheduling tools for Claude Code CLI
Allows task scheduling and reminder management
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class CronCreateInput(BaseModel):
    """Input schema for CronCreate tool"""

    cron: str = Field(..., description="Cron expression (minute hour day-of-month month day-of-week)")
    prompt: str = Field(..., description="Prompt to execute when cron triggers")
    recurring: bool = Field(default=True, description="Recurring job (default: true)")
    durable: bool = Field(default=False, description="Persist to disk (default: false)")


class CronDeleteInput(BaseModel):
    """Input schema for CronDelete tool"""

    id: str = Field(..., description="Job ID to delete")


class CronListInput(BaseModel):
    """Input schema for CronList tool"""

    all: bool = Field(default=False, description="Show all jobs including completed (default: false)")


class CronTool:
    """
    Base scheduling tool with common functionality
    """

    def __init__(self):
        # Scheduler storage
        self.session_jobs: Dict[str, Dict[str, Any]] = {}
        self.durable_file = Path.home() / ".claude" / "scheduled_tasks.json"

    def _load_durable_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Load durable jobs from disk"""
        if self.durable_file.exists():
            try:
                with open(self.durable_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_durable_jobs(self, jobs: Dict[str, Dict[str, Any]]) -> None:
        """Save durable jobs to disk"""
        self.durable_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.durable_file, 'w') as f:
            json.dump(jobs, f, indent=2)

    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        import uuid
        return str(uuid.uuid4())


class CronCreateTool(Tool, CronTool):
    """
    Cron create tool for scheduling tasks

    Allows scheduling recurring or one-time tasks using cron expressions
    """

    # Tool metadata
    name: str = "CronCreate"
    description: str = "Schedule a task with cron expression"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: CronCreateInput,
        context: ToolContext
    ) -> ToolResult:
        """Create scheduled task"""
        import time
        start_time = time.time()

        try:
            # Validate cron expression
            self._validate_cron_expression(input_data.cron)

            # Generate job ID
            job_id = self._generate_job_id()

            # Create job configuration
            job = {
                "id": job_id,
                "cron": input_data.cron,
                "prompt": input_data.prompt,
                "recurring": input_data.recurring,
                "durable": input_data.durable,
                "created_at": datetime.now().isoformat(),
                "next_run": self._calculate_next_run(input_data.cron),
            }

            # Store job
            if input_data.durable:
                durable_jobs = self._load_durable_jobs()
                durable_jobs[job_id] = job
                self._save_durable_jobs(durable_jobs)
            else:
                self.session_jobs[job_id] = job

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Scheduled task with ID: {job_id}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "job_id": job_id,
                    "cron": input_data.cron,
                    "recurring": input_data.recurring,
                    "durable": input_data.durable,
                    "next_run": job["next_run"],
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

    def _validate_cron_expression(self, cron_expr: str) -> None:
        """Validate cron expression format"""
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: '{cron_expr}'. Expected 5 parts (M H DoM Mon DoW)")

    def _calculate_next_run(self, cron_expr: str) -> str:
        """Calculate next run time (simplified)"""
        # This is a simplified implementation
        # In production, use a proper cron library
        from datetime import datetime, timedelta
        return (datetime.now() + timedelta(minutes=1)).isoformat()

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "cron": {
                        "type": "string",
                        "description": "Cron expression (minute hour day-of-month month day-of-week)",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt to execute when cron triggers",
                    },
                    "recurring": {
                        "type": "boolean",
                        "description": "Recurring job (default: true)",
                        "default": True,
                    },
                    "durable": {
                        "type": "boolean",
                        "description": "Persist to disk (default: false)",
                        "default": False,
                    },
                },
                "required": ["cron", "prompt"],
            },
        )


class CronDeleteTool(Tool, CronTool):
    """
    Cron delete tool for removing scheduled tasks
    """

    # Tool metadata
    name: str = "CronDelete"
    description: str = "Delete a scheduled task"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: CronDeleteInput,
        context: ToolContext
    ) -> ToolResult:
        """Delete scheduled task"""
        import time
        start_time = time.time()

        try:
            # Try session jobs first
            if input_data.id in self.session_jobs:
                del self.session_jobs[input_data.id]
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=f"Deleted task {input_data.id} from session storage",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Try durable jobs
            durable_jobs = self._load_durable_jobs()
            if input_data.id in durable_jobs:
                del durable_jobs[input_data.id]
                self._save_durable_jobs(durable_jobs)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=f"Deleted task {input_data.id} from durable storage",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=f"Task not found: {input_data.id}",
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
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Job ID to delete",
                    },
                },
                "required": ["id"],
            },
        )


class CronListTool(Tool, CronTool):
    """
    Cron list tool for showing scheduled tasks
    """

    # Tool metadata
    name: str = "CronList"
    description: str = "List all scheduled tasks"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: CronListInput,
        context: ToolContext
    ) -> ToolResult:
        """List scheduled tasks"""
        import time
        start_time = time.time()

        try:
            # Get all jobs
            all_jobs = {}
            all_jobs.update(self.session_jobs)
            all_jobs.update(self._load_durable_jobs())

            # Format output
            if not all_jobs:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content="No scheduled tasks",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            output_lines = ["Scheduled Tasks:"]
            for job_id, job in all_jobs.items():
                storage_type = "durable" if job.get("durable") else "session"
                recurring = "recurring" if job.get("recurring") else "one-time"
                output_lines.append(f"\n  Job ID: {job_id}")
                output_lines.append(f"    Storage: {storage_type}")
                output_lines.append(f"    Type: {recurring}")
                output_lines.append(f"    Cron: {job['cron']}")
                output_lines.append(f"    Prompt: {job['prompt']}")
                output_lines.append(f"    Next run: {job.get('next_run', 'unknown')}")

            return ToolResult(
                tool_name=self.name,
                success=True,
                content='\n'.join(output_lines),
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "job_count": len(all_jobs),
                    "jobs": list(all_jobs.keys()),
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
                    "all": {
                        "type": "boolean",
                        "description": "Show all jobs including completed (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
        )
