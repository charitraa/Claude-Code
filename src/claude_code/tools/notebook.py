"""
Notebook/Jupyter integration tools for Claude Code CLI
Allows execution and manipulation of Jupyter notebooks
"""

import json
import asyncio
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


class NotebookExecuteInput(BaseModel):
    """Input schema for NotebookExecute tool"""

    notebook_path: str = Field(..., description="Path to Jupyter notebook (.ipynb) file")
    cell_id: Optional[str] = Field(default=None, description="Cell ID to execute (omit for all cells)")


class NotebookEditInput(BaseModel):
    """Input schema for NotebookEdit tool"""

    notebook_path: str = Field(..., description="Path to Jupyter notebook (.ipynb) file")
    cell_id: str = Field(..., description="Cell ID to edit")
    new_source: str = Field(..., description="New cell source code")
    cell_type: Optional[str] = Field(default=None, description="Cell type (code, markdown) (default: keep existing)")


class NotebookReadInput(BaseModel):
    """Input schema for NotebookRead tool"""

    notebook_path: str = Field(..., description="Path to Jupyter notebook (.ipynb) file")
    pages: Optional[str] = Field(default=None, description="Page range for PDF files (not applicable for notebooks)")


class NotebookExecuteTool(Tool):
    """
    Notebook execute tool for running Jupyter notebook cells

    Allows execution of Jupyter notebook cells using a Python kernel
    """

    # Tool metadata
    name: str = "NotebookExecute"
    description: str = "Execute code in a Jupyter notebook"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: NotebookExecuteInput,
        context: ToolContext
    ) -> ToolResult:
        """Execute notebook cells"""
        import time
        start_time = time.time()

        try:
            notebook_path = Path(input_data.notebook_path)
            if not notebook_path.is_absolute():
                notebook_path = Path(context.cwd) / input_data.notebook_path

            if not notebook_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Notebook not found: {notebook_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            if not notebook_path.suffix == '.ipynb':
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Not a Jupyter notebook: {notebook_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read notebook
            with open(notebook_path, 'r') as f:
                notebook_data = json.load(f)

            # For now, we'll simulate execution
            # In production, this would connect to a running Jupyter kernel
            if input_data.cell_id:
                # Execute specific cell
                cell = self._find_cell(notebook_data, input_data.cell_id)
                if not cell:
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        content="",
                        error=f"Cell not found: {input_data.cell_id}",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )

                execution_result = await self._execute_cell(cell, notebook_path.parent)
            else:
                # Execute all cells
                execution_results = []
                for cell in notebook_data.get('cells', []):
                    if cell.get('cell_type') == 'code':
                        result = await self._execute_cell(cell, notebook_path.parent)
                        execution_results.append(result)

                execution_result = '\n'.join(execution_results)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=execution_result,
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "notebook_path": str(notebook_path),
                    "cell_id": input_data.cell_id,
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

    def _find_cell(self, notebook_data: Dict, cell_id: str) -> Optional[Dict]:
        """Find cell by ID in notebook"""
        for cell in notebook_data.get('cells', []):
            if cell.get('id') == cell_id:
                return cell
        return None

    async def _execute_cell(self, cell: Dict, working_dir: Path) -> str:
        """Execute a single cell (simplified implementation)"""
        code = cell.get('source', '')
        if not code:
            return "Empty cell, nothing to execute"

        # This is a simplified implementation
        # In production, use proper Jupyter kernel integration
        try:
            # Try to execute as Python code
            process = await asyncio.create_subprocess_exec(
                ["python3", "-c", code],
                cwd=str(working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return f"Execution failed: {stderr.decode()}"
            else:
                return stdout.decode() or "Execution completed with no output"

        except Exception as e:
            return f"Execution error: {str(e)}"

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "notebook_path": {
                        "type": "string",
                        "description": "Path to Jupyter notebook (.ipynb) file",
                    },
                    "cell_id": {
                        "type": "string",
                        "description": "Cell ID to execute (omit for all cells)",
                    },
                },
                "required": ["notebook_path"],
            },
        )


class NotebookEditTool(Tool):
    """
    Notebook edit tool for modifying Jupyter notebook cells
    """

    # Tool metadata
    name: str = "NotebookEdit"
    description: str = "Edit a cell in a Jupyter notebook"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: NotebookEditInput,
        context: ToolContext
    ) -> ToolResult:
        """Edit notebook cell"""
        import time
        start_time = time.time()

        try:
            notebook_path = Path(input_data.notebook_path)
            if not notebook_path.is_absolute():
                notebook_path = Path(context.cwd) / input_data.notebook_path

            if not notebook_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Notebook not found: {notebook_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read notebook
            with open(notebook_path, 'r') as f:
                notebook_data = json.load(f)

            # Find and edit cell
            cell = self._find_cell(notebook_data, input_data.cell_id)
            if not cell:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Cell not found: {input_data.cell_id}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Update cell content
            cell['source'] = input_data.new_source

            # Update cell type if specified
            if input_data.cell_type:
                cell['cell_type'] = input_data.cell_type

            # Save notebook
            with open(notebook_path, 'w') as f:
                json.dump(notebook_data, f, indent=2)

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=f"Updated cell {input_data.cell_id} in {notebook_path}",
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "notebook_path": str(notebook_path),
                    "cell_id": input_data.cell_id,
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

    def _find_cell(self, notebook_data: Dict, cell_id: str) -> Optional[Dict]:
        """Find cell by ID in notebook"""
        for cell in notebook_data.get('cells', []):
            if cell.get('id') == cell_id:
                return cell
        return None

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "notebook_path": {
                        "type": "string",
                        "description": "Path to Jupyter notebook (.ipynb) file",
                    },
                    "cell_id": {
                        "type": "string",
                        "description": "Cell ID to edit",
                    },
                    "new_source": {
                        "type": "string",
                        "description": "New cell source code",
                    },
                    "cell_type": {
                        "type": "string",
                        "description": "Cell type (code, markdown) (default: keep existing)",
                    },
                },
                "required": ["notebook_path", "cell_id", "new_source"],
            },
        )


class NotebookReadTool(Tool):
    """
    Notebook read tool for reading Jupyter notebook contents

    Reads entire Jupyter notebooks including cell outputs
    """

    # Tool metadata
    name: str = "NotebookRead"
    description: str = "Read contents of a Jupyter notebook"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    async def execute(
        self,
        input_data: NotebookReadInput,
        context: ToolContext
    ) -> ToolResult:
        """Read notebook contents"""
        import time
        start_time = time.time()

        try:
            notebook_path = Path(input_data.notebook_path)
            if not notebook_path.is_absolute():
                notebook_path = Path(context.cwd) / input_data.notebook_path

            if not notebook_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    content="",
                    error=f"Notebook not found: {notebook_path}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Read notebook
            with open(notebook_path, 'r') as f:
                notebook_data = json.load(f)

            # Format notebook content for display
            output_lines = [f"Notebook: {notebook_path.name}"]
            output_lines.append(f"Cells: {len(notebook_data.get('cells', []))}")
            output_lines.append("")

            for i, cell in enumerate(notebook_data.get('cells', []), 1):
                cell_type = cell.get('cell_type', 'unknown')
                cell_source = ''.join(cell.get('source', []))

                output_lines.append(f"Cell {i} ({cell_type}):")
                output_lines.append("```")
                output_lines.append(cell_source)
                output_lines.append("```")

                # Show outputs if present
                if 'outputs' in cell:
                    outputs = cell['outputs']
                    if outputs:
                        output_lines.append("Outputs:")
                        for j, output in enumerate(outputs, 1):
                            if 'output_type' in output:
                                output_type = output['output_type']
                                output_lines.append(f"  {j}. [{output_type}]")

                                if 'text' in output:
                                    text_data = ''.join(output['text'])
                                    output_lines.append(f"     {text_data[:200]}")
                                elif 'data' in output:
                                    output_lines.append(f"     [Output data present]")

            return ToolResult(
                tool_name=self.name,
                success=True,
                content='\n'.join(output_lines),
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "notebook_path": str(notebook_path),
                    "cell_count": len(notebook_data.get('cells', [])),
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
                    "notebook_path": {
                        "type": "string",
                        "description": "Path to Jupyter notebook (.ipynb) file",
                    },
                    "pages": {
                        "type": "string",
                        "description": "Page range for PDF files (not applicable for notebooks)",
                    },
                },
                "required": ["notebook_path"],
            },
        )
