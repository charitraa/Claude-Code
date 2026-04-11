"""
Search tools for Claude Code CLI
Converted from TypeScript Grep and Glob tools
"""

import asyncio
import re
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class GrepInput(BaseModel):
    """Input schema for Grep tool"""

    pattern: str = Field(..., description="Regular expression pattern to search for")
    path: str = Field(default=".", description="Path to search in (default: current directory)")
    file_pattern: Optional[str] = Field(default=None, description="File pattern to match (e.g., '*.py')")
    case_sensitive: bool = Field(default=False, description="Case-sensitive search")
    include_line_numbers: bool = Field(default=True, description="Include line numbers in results")
    max_results: Optional[int] = Field(default=100, description="Maximum number of results")
    context_lines: int = Field(default=2, description="Number of context lines before/after matches")


class GlobInput(BaseModel):
    """Input schema for Glob tool"""

    pattern: str = Field(..., description="File pattern to match (e.g., '*.py', 'src/**/*.ts')")
    path: str = Field(default=".", description="Path to search in (default: current directory)")
    include_hidden: bool = Field(default=False, description="Include hidden files/directories")
    max_results: Optional[int] = Field(default=100, description="Maximum number of results")


class GrepTool(Tool):
    """
    Grep tool for searching text in files

    Replaces TypeScript GrepTool
    """

    # Tool metadata
    name: str = "Grep"
    description: str = "Search for text patterns in files using regular expressions"
    category: ToolCategory = ToolCategory.SEARCH
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GrepInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Search for text patterns in files

        Args:
            input_data: Validated grep input
            context: Execution context

        Returns:
            ToolResult with search results
        """
        import time
        start_time = time.time()

        try:
            search_path = Path(input_data.path)
            if not search_path.is_absolute():
                search_path = Path(context.cwd) / input_data.path

            if not search_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {search_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Compile regex pattern
            try:
                flags = 0 if input_data.case_sensitive else re.IGNORECASE
                regex = re.compile(input_data.pattern, flags)
            except re.error as e:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Invalid regex pattern: {str(e)}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            results = []
            total_matches = 0

            # Search files
            for file_path in search_path.rglob('*'):
                if file_path.is_file():
                    # Apply file pattern if specified
                    if input_data.file_pattern:
                        if not file_path.match(input_data.file_pattern):
                            continue

                    # Skip hidden files if not requested
                    if not input_data.include_hidden:
                        if any(part.startswith('.') for part in file_path.parts):
                            continue

                    # Search in file
                    file_matches = await self._search_file(
                        file_path,
                        regex,
                        input_data.context_lines,
                        input_data.include_line_numbers
                    )

                    if file_matches:
                        total_matches += len(file_matches)
                        results.extend(file_matches)

                        # Check max results limit
                        if input_data.max_results and total_matches >= input_data.max_results:
                            break

            # Format results
            if results:
                result_content = self._format_grep_results(results)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=result_content,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "pattern": input_data.pattern,
                        "matches": total_matches,
                        "search_path": str(search_path),
                    },
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content="No matches found",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "pattern": input_data.pattern,
                        "matches": 0,
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

    async def _search_file(
        self,
        file_path: Path,
        regex: re.Pattern,
        context_lines: int,
        include_line_numbers: bool
    ) -> List[dict]:
        """
        Search for pattern in a single file

        Args:
            file_path: Path to file
            regex: Compiled regex pattern
            context_lines: Number of context lines
            include_line_numbers: Whether to include line numbers

        Returns:
            List of match dictionaries
        """
        matches = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for match in regex.finditer(line):
                        # Get context lines
                        start_context = max(0, line_num - context_lines - 1)
                        end_context = min(len(lines), line_num + context_lines)
                        context = ''.join(lines[start_context:end_context])

                        matches.append({
                            'file': str(file_path),
                            'line_number': line_num if include_line_numbers else None,
                            'match': match.group(0),
                            'context': context.strip(),
                        })

        except UnicodeDecodeError:
            # Skip binary files
            pass
        except Exception:
            # Skip files that can't be read
            pass

        return matches

    def _format_grep_results(self, matches: List[dict]) -> str:
        """
        Format grep results for display

        Args:
            matches: List of match dictionaries

        Returns:
            Formatted results string
        """
        if not matches:
            return "No matches found"

        formatted = []
        for match in matches:
            if match['line_number']:
                formatted.append(f"{match['file']}:{match['line_number']}: {match['match']}")
            else:
                formatted.append(f"{match['file']}: {match['match']}")

        return '\n'.join(formatted[:50])  # Limit to 50 results for display

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to search in (default: current directory)",
                        "default": ".",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to match (e.g., '*.py')",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case-sensitive search",
                        "default": False,
                    },
                    "include_line_numbers": {
                        "type": "boolean",
                        "description": "Include line numbers in results",
                        "default": True,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 100,
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines before/after matches",
                        "default": 2,
                    },
                },
                "required": ["pattern"],
            },
        )


class GlobTool(Tool):
    """
    Glob tool for file pattern matching

    Replaces TypeScript GlobTool
    """

    # Tool metadata
    name: str = "Glob"
    description: str = "Find files matching a pattern"
    category: ToolCategory = ToolCategory.SEARCH
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: GlobInput,
        context: ToolContext
    ) -> ToolResult:
        """
        Find files matching pattern

        Args:
            input_data: Validated glob input
            context: Execution context

        Returns:
            ToolResult with matching files
        """
        import time
        start_time = time.time()

        try:
            search_path = Path(input_data.path)
            if not search_path.is_absolute():
                search_path = Path(context.cwd) / input_data.path

            if not search_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Path not found: {search_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Convert glob pattern to Python glob
            # Handle both simple patterns and recursive patterns
            if '**' in input_data.pattern:
                # Recursive glob
                pattern = input_data.pattern.replace('**/', '**/*')
                matches = list(search_path.rglob(pattern))
            else:
                # Simple glob
                matches = list(search_path.glob(input_data.pattern))

            # Filter hidden files if not requested
            if not input_data.include_hidden:
                matches = [
                    m for m in matches
                    if not any(part.startswith('.') for part in m.parts)
                ]

            # Limit results
            if input_data.max_results and len(matches) > input_data.max_results:
                matches = matches[:input_data.max_results]

            # Format results
            if matches:
                result_content = self._format_glob_results(matches, search_path)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=result_content,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "pattern": input_data.pattern,
                        "matches": len(matches),
                        "search_path": str(search_path),
                    },
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content="No files found matching pattern",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={
                        "pattern": input_data.pattern,
                        "matches": 0,
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

    def _format_glob_results(self, matches: List[Path], base_path: Path) -> str:
        """
        Format glob results for display

        Args:
            matches: List of matching paths
            base_path: Base search path

        Returns:
            Formatted results string
        """
        if not matches:
            return "No files found"

        # Make relative paths for display
        relative_paths = []
        for match in matches:
            try:
                rel_path = match.relative_to(base_path)
                relative_paths.append(str(rel_path))
            except ValueError:
                relative_paths.append(str(match))

        return '\n'.join(relative_paths[:50])  # Limit to 50 results for display

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (e.g., '*.py', 'src/**/*.ts')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to search in (default: current directory)",
                        "default": ".",
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files/directories",
                        "default": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 100,
                    },
                },
                "required": ["pattern"],
            },
        )