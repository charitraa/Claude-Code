"""
File operation tools for Claude Code CLI
Converted from TypeScript file tools
"""

import asyncio
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class FileReadInput(BaseModel):
    """Input schema for FileRead tool"""

    path: str = Field(..., description="Path to the file to read")
    start_line: Optional[int] = Field(default=None, description="Starting line number")
    end_line: Optional[int] = Field(default=None, description="Ending line number")
    encoding: Optional[str] = Field(default="utf-8", description="File encoding")


class FileWriteInput(BaseModel):
    """Input schema for FileWrite tool"""

    path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    create_directories: bool = Field(default=False, description="Create parent directories if they don't exist")
    encoding: Optional[str] = Field(default="utf-8", description="File encoding")


class FileEditInput(BaseModel):
    """Input schema for FileEdit tool"""

    path: str = Field(..., description="Path to the file to edit")
    old_text: str = Field(..., description="Text to replace")
    new_text: str = Field(..., description="New text to replace with")
    all_occurrences: bool = Field(default=False, description="Replace all occurrences")
    encoding: Optional[str] = Field(default="utf-8", description="File encoding")


class FileReadTool(Tool):
    """
    File read tool for reading file contents

    Replaces TypeScript FileReadTool
    """

    # Tool metadata
    name: str = "FileRead"
    description: str = "Read the contents of a file"
    category: ToolCategory = ToolCategory.FILE_OPERATIONS
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: FileReadInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Read file contents

        Args:
            input_data: Validated file read input
            context: Execution context

        Returns:
            ToolResult with file contents
        """
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)

            if not file_path.is_absolute():
                # Make relative to current directory
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read file with specified encoding
            with open(file_path, 'r', encoding=input_data.encoding) as f:
                content = f.read()

            # Handle line range if specified
            if input_data.start_line is not None or input_data.end_line is not None:
                lines = content.split('\n')
                start = input_data.start_line or 0
                end = input_data.end_line or len(lines)
                content = '\n'.join(lines[start:end])

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "file_path": str(file_path),
                    "encoding": input_data.encoding,
                    "file_size": len(content),
                },
            )

        except UnicodeDecodeError as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=f"Encoding error: {str(e)}",
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
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (optional)",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (optional)",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
        )


class FileWriteTool(Tool):
    """
    File write tool for writing file contents

    Replaces TypeScript FileWriteTool
    """

    # Tool metadata
    name: str = "FileWrite"
    description: str = "Write content to a file"
    category: ToolCategory = ToolCategory.FILE_OPERATIONS
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: FileWriteInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Write content to file

        Args:
            input_data: Validated file write input
            context: Execution context

        Returns:
            ToolResult with write status
        """
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)

            if not file_path.is_absolute():
                # Make relative to current directory
                file_path = Path(context.cwd) / input_data.path

            # Create parent directories if requested
            if input_data.create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(file_path, 'w', encoding=input_data.encoding) as f:
                f.write(input_data.content)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Successfully wrote {len(input_data.content)} bytes to {file_path}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "file_path": str(file_path),
                    "bytes_written": len(input_data.content),
                    "encoding": input_data.encoding,
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
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "create_directories": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist (default: false)",
                        "default": False,
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8",
                    },
                },
                "required": ["path", "content"],
            },
        )


class FileEditTool(Tool):
    """
    File edit tool for editing file contents

    Replaces TypeScript FileEditTool
    """

    # Tool metadata
    name: str = "FileEdit"
    description: str = "Edit file contents by replacing text"
    category: ToolCategory = ToolCategory.FILE_OPERATIONS
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: FileEditInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Edit file contents

        Args:
            input_data: Validated file edit input
            context: Execution context

        Returns:
            ToolResult with edit status
        """
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)

            if not file_path.is_absolute():
                # Make relative to current directory
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read file
            with open(file_path, 'r', encoding=input_data.encoding) as f:
                content = f.read()

            # Replace text
            if input_data.all_occurrences:
                content = content.replace(input_data.old_text, input_data.new_text)
                replacements = content.count(input_data.new_text)
            else:
                count = content.count(input_data.old_text)
                if count > 1:
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        content="",
                        error=f"Found {count} occurrences of '{input_data.old_text}'. Use all_occurrences=True to replace all.",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )
                content = content.replace(input_data.old_text, input_data.new_text, 1)
                replacements = 1

            # Write back
            with open(file_path, 'w', encoding=input_data.encoding) as f:
                f.write(content)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Replaced {replacements} occurrence(s) in {file_path}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "file_path": str(file_path),
                    "replacements": replacements,
                    "old_text": input_data.old_text,
                    "new_text": input_data.new_text,
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
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Text to replace",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "New text to replace with",
                    },
                    "all_occurrences": {
                        "type": "boolean",
                        "description": "Replace all occurrences (default: false)",
                        "default": False,
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        )