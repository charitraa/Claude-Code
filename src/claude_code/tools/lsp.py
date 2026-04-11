"""
LSP (Language Server Protocol) integration tools for Claude Code CLI
Converted from TypeScript LSP tools
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class LSPDefinitionInput(BaseModel):
    """Input schema for LSPDefinition tool"""

    path: str = Field(..., description="Path to the file or directory")
    language: Optional[str] = Field(default=None, description="Programming language (auto-detected if not provided)")


class LSPCompletionInput(BaseModel):
    """Input schema for LSPCompletion tool"""

    path: str = Field(..., description="Path to the file")
    line: int = Field(..., description="Line number for completion")
    character: int = Field(default=0, description="Character position for completion")
    language: Optional[str] = Field(default=None, description="Programming language (auto-detected if not provided)")


class LSPReferencesInput(BaseModel):
    """Input schema for LSPReferences tool"""

    path: str = Field(..., description="Path to the file")
    line: int = Field(..., description="Line number to find references for")
    character: int = Field(default=0, description="Character position to find references for")
    language: Optional[str] = Field(default=None, description="Programming language (auto-detected if not provided)")


class LSPHoverInput(BaseModel):
    """Input schema for LSPHover tool"""

    path: str = Field(..., description="Path to the file")
    line: int = Field(..., description="Line number for hover information")
    character: int = Field(default=0, description="Character position for hover information")
    language: Optional[str] = Field(default=None, description="Programming language (auto-detected if not provided)")


class LSPDiagnosticsInput(BaseModel):
    """Input schema for LSPDiagnostics tool"""

    path: Optional[str] = Field(default=None, description="Path to file or directory (default: all)")
    language: Optional[str] = Field(default=None, description="Programming language filter")


class LSPTool:
    """
    Base LSP tool with common functionality

    Replaces TypeScript LSP tool infrastructure
    """

    def __init__(self):
        # Language detection
        self.language_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
        }

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        import os
        _, ext = os.path.splitext(file_path)
        return self.language_map.get(ext.lower(), 'unknown')

    def _get_lsp_command(self, tool_name: str) -> str:
        """Get appropriate LSP server command"""
        # This would be expanded to detect installed LSP servers
        # For now, we'll use a placeholder approach
        return f"lsp_{tool_name}"

    async def _execute_lsp_command(
        self,
        tool_name: str,
        args: List[str],
        cwd: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute LSP command and return result"""
        command = self._get_lsp_command(tool_name)

        try:
            process = await asyncio.create_subprocess_exec(
                [command] + args,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": stderr.decode(),
                    "output": stdout.decode(),
                }

            # Try to parse JSON output
            try:
                result = json.loads(stdout.decode())
                result["success"] = True
                return result
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "output": stdout.decode(),
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"LSP command timed out after {timeout}s",
                "output": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
            }


class LSPDefinitionTool(Tool):
    """
    LSP definition tool for getting symbol definitions

    Replaces TypeScript LSP definition functionality
    """

    # Tool metadata
    name: str = "LSPDefinition"
    description: str = "Get definition of a symbol using Language Server Protocol"
    category: ToolCategory = ToolCategory.LSP
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: LSPDefinitionInput,
        context: ToolContext
    ) -> ToolResult:
        """Get LSP definition"""
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)
            if not file_path.is_absolute():
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            language = input_data.language or self._detect_language(str(file_path))

            # Execute LSP definition command
            result = await self._execute_lsp_command(
                "definition",
                [str(file_path), str(input_data.path)],
                str(context.cwd),
                timeout=30
            )

            if not result["success"]:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=result.get("error", "LSP definition failed"),
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Format results
            if "result" in result:
                definition = result["result"]
                output_lines = [
                    f"File: {file_path}",
                    f"Language: {language}",
                    f"Definition: {definition}",
                ]
                output_content = '\n'.join(output_lines)

                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=output_content,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "file_path": str(file_path),
                        "language": language,
                        "definition": definition,
                    },
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=result["output"],
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
                        "description": "Path to the file or directory",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (auto-detected if not provided)",
                    },
                },
                "required": ["path"],
            },
        )


class LSPCompletionTool(Tool):
    """
    LSP completion tool for getting code completions

    Replaces TypeScript LSP completion functionality
    """

    # Tool metadata
    name: str = "LSPCompletion"
    description: str = "Get code completions using Language Server Protocol"
    category: ToolCategory = ToolCategory.LSP
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: LSPCompletionInput,
        context: ToolContext
    ) -> ToolResult:
        """Get LSP completions"""
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)
            if not file_path.is_absolute():
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            language = input_data.language or self._detect_language(str(file_path))

            # Execute LSP completion command
            result = await self._execute_lsp_command(
                "completion",
                [str(file_path), str(input_data.line), str(input_data.character)],
                str(context.cwd),
                timeout=30
            )

            if not result["success"]:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=result.get("error", "LSP completion failed"),
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Format results
            if "result" in result:
                completions = result.get("result", result.get("output", []))
                output_lines = [
                    f"File: {file_path}",
                    f"Language: {language}",
                    f"Position: Line {input_data.line}, Character {input_data.character}",
                    f"Completions: {len(completions)} available",
                ]
                if completions:
                    output_lines.append("Suggestions:")
                    for i, completion in enumerate(completions[:5]):  # Show first 5
                        output_lines.append(f"  {i+1}. {completion}")

                output_content = '\n'.join(output_lines)

                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=output_content,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "file_path": str(file_path),
                        "language": language,
                        "position": {"line": input_data.line, "character": input_data.character},
                        "completions": completions,
                    },
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=result["output"],
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
                        "description": "Path to the file",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number for completion",
                    },
                    "character": {
                        "type": "integer",
                        "description": "Character position for completion (default: 0)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (auto-detected if not provided)",
                    },
                },
                "required": ["path", "line"],
            },
        )


class LSPDiagnosticsTool(Tool):
    """
    LSP diagnostics tool for getting code issues and problems

    Replaces TypeScript LSP diagnostics functionality
    """

    # Tool metadata
    name: str = "LSPDiagnostics"
    description: str = "Get code diagnostics and issues using Language Server Protocol"
    category: ToolCategory = ToolCategory.LSP
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: LSPDiagnosticsInput,
        context: ToolContext
    ) -> ToolResult:
        """Get LSP diagnostics"""
        import time
        start_time = time.time()

        try:
            working_dir = input_data.path if input_data.path else context.cwd

            # Execute LSP diagnostics command
            result = await self._execute_lsp_command(
                "diagnostics",
                [],
                working_dir,
                timeout=30
            )

            if not result["success"]:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=result.get("error", "LSP diagnostics failed"),
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Format results
            diagnostics = result.get("result", result.get("output", []))
            output_lines = [
                f"Directory: {working_dir}",
                f"Diagnostics: {len(diagnostics)} issues found",
            ]

            if diagnostics:
                output_lines.append("Issues:")
                for i, diagnostic in enumerate(diagnostics[:10]):  # Show first 10
                    severity = diagnostic.get("severity", "unknown")
                    message = diagnostic.get("message", "No message")
                    file_path = diagnostic.get("path", "unknown")
                    output_lines.append(f"  {i+1}. [{severity}] {message}")
                    if file_path:
                        output_lines.append(f"     File: {file_path}")

            output_content = '\n'.join(output_lines)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=output_content if diagnostics else "No issues found",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "diagnostics": diagnostics,
                    "working_dir": working_dir,
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
                        "description": "Path to file or directory (default: all)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language filter",
                    },
                },
                "required": [],
            },
        )


class LSPReferencesTool(Tool):
    """
    LSP references tool for finding symbol references

    Replaces TypeScript LSP references functionality
    """

    # Tool metadata
    name: str = "LSPReferences"
    description: str = "Find all references to a symbol using Language Server Protocol"
    category: ToolCategory = ToolCategory.LSP
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: LSPReferencesInput,
        context: ToolContext
    ) -> ToolResult:
        """Get LSP references"""
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)
            if not file_path.is_absolute():
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            language = input_data.language or self._detect_language(str(file_path))

            # Execute LSP references command
            result = await self._execute_lsp_command(
                "references",
                [str(file_path), str(input_data.line), str(input_data.character)],
                str(context.cwd),
                timeout=30
            )

            if not result["success"]:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=result.get("error", "LSP references failed"),
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Format results
            references = result.get("result", result.get("output", []))
            output_lines = [
                f"File: {file_path}",
                f"Language: {language}",
                f"Position: Line {input_data.line}, Character {input_data.character}",
                f"References: {len(references)} found",
            ]

            if references:
                output_lines.append("Reference locations:")
                for i, ref in enumerate(references[:10]):  # Show first 10
                    output_lines.append(f"  {i+1}. {ref}")

            output_content = '\n'.join(output_lines)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=output_content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "file_path": str(file_path),
                    "language": language,
                    "position": {"line": input_data.line, "character": input_data.character},
                    "references": references,
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
                        "description": "Path to the file",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number to find references for",
                    },
                    "character": {
                        "type": "integer",
                        "description": "Character position to find references for (default: 0)",
                        "default": 0,
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (auto-detected if not provided)",
                    },
                },
                "required": ["path", "line"],
            },
        )


class LSPHoverTool(Tool):
    """
    LSP hover tool for getting hover information

    Replaces TypeScript LSP hover functionality
    """

    # Tool metadata
    name: str = "LSPHover"
    description: str = "Get hover information for a symbol using Language Server Protocol"
    category: ToolCategory = ToolCategory.LSP
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: LSPHoverInput,
        context: ToolContext
    ) -> ToolResult:
        """Get LSP hover information"""
        import time
        start_time = time.time()

        try:
            file_path = Path(input_data.path)
            if not file_path.is_absolute():
                file_path = Path(context.cwd) / input_data.path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            language = input_data.language or self._detect_language(str(file_path))

            # Execute LSP hover command
            result = await self._execute_lsp_command(
                "hover",
                [str(file_path), str(input_data.line), str(input_data.character)],
                str(context.cwd),
                timeout=30
            )

            if not result["success"]:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=result.get("error", "LSP hover failed"),
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Format results
            hover_info = result.get("result", result.get("output", ""))
            output_lines = [
                f"File: {file_path}",
                f"Language: {language}",
                f"Position: Line {input_data.line}, Character {input_data.character}",
                f"Hover information:",
            ]

            if hover_info:
                output_lines.append(hover_info)
            else:
                output_lines.append("No hover information available")

            output_content = '\n'.join(output_lines)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=output_content,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "file_path": str(file_path),
                    "language": language,
                    "position": {"line": input_data.line, "character": input_data.character},
                    "hover_info": hover_info,
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
                        "description": "Path to the file",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number for hover information",
                    },
                    "character": {
                        "type": "integer",
                        "description": "Character position for hover information (default: 0)",
                        "default": 0,
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (auto-detected if not provided)",
                    },
                },
                "required": ["path", "line"],
            },
        )