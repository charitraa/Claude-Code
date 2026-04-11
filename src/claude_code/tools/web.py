"""
Web integration tools for Claude Code CLI
Allows web search and web content retrieval
"""

import httpx
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from .base import Tool
from ..types import (
    ToolContext,
    ToolResult,
    ToolCategory,
    PermissionLevel,
)


class WebSearchInput(BaseModel):
    """Input schema for WebSearch tool"""

    query: str = Field(..., description="Search query")
    allowed_domains: Optional[List[str]] = Field(default=None, description="Allow only these domains")
    blocked_domains: Optional[List[str]] = Field(default=None, description="Block these domains")


class WebReaderInput(BaseModel):
    """Input schema for WebReader tool"""

    url: str = Field(..., description="URL to fetch and read")
    timeout: int = Field(default=20, description="Request timeout in seconds (default: 20)")
    no_cache: bool = Field(default=False, description="Disable cache (default: false)")
    return_format: str = Field(default="markdown", description="Response format (markdown or text, default: markdown)")
    retain_images: bool = Field(default=True, description="Retain images (default: true)")
    no_gfm: bool = Field(default=False, description="Disable GitHub Flavored Markdown (default: false)")
    keep_img_data_url: bool = Field(default=False, description="Keep image data URLs (default: false)")
    with_images_summary: bool = Field(default=False, description="Include images summary (default: false)")
    with_links_summary: bool = Field(default=False, description="Include links summary (default: false)")


class WebSearchTool(Tool):
    """
    Web search tool for searching the internet

    Allows searching the web and retrieving up-to-date information
    """

    # Tool metadata
    name: str = "WebSearch"
    description: str = "Search the web and retrieve results"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        self.search_api_url = "https://api.duckduckgo.com/"  # Using DuckDuckGo as example

    async def execute(
        self,
        input_data: WebSearchInput,
        context: ToolContext
    ) -> ToolResult:
        """Perform web search"""
        import time
        start_time = time.time()

        try:
            # This is a simplified implementation
            # In production, use a proper web search API
            params = {
                "q": input_data.query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.search_api_url, params=params)
                response.raise_for_status()

                search_data = response.json()

            # Parse search results
            results = []

            # Abstract text result
            if 'AbstractText' in search_data and search_data['AbstractText']:
                results.append({
                    "title": search_data.get('Heading', ''),
                    "url": search_data.get('AbstractURL', ''),
                    "snippet": search_data['AbstractText'],
                })

            # Related topics
            if 'RelatedTopics' in search_data:
                for topic in search_data['RelatedTopics'][:10]:
                    if isinstance(topic, dict):
                        results.append({
                            "title": topic.get('Text', '').split(' - ')[0],
                            "url": topic.get('FirstURL', ''),
                            "snippet": topic.get('Text', ''),
                        })

            # Format output
            if not results:
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=f"No results found for: {input_data.query}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            output_lines = [f"Search results for: {input_data.query}", ""]

            for i, result in enumerate(results[:10], 1):
                output_lines.append(f"{i}. [{result['title']}]({result['url']})")
                output_lines.append(f"   {result['snippet']}")
                output_lines.append("")

            # Add sources section
            output_lines.append("Sources:")
            for i, result in enumerate(results[:10], 1):
                output_lines.append(f"- [{result['title']}]({result['url']})")

            return ToolResult(
                tool_name=self.name,
                success=True,
                content='\n'.join(output_lines),
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "query": input_data.query,
                    "result_count": len(results),
                    "results": results[:10],
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
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "allowed_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Allow only these domains",
                    },
                    "blocked_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Block these domains",
                    },
                },
                "required": ["query"],
            },
        )


class WebReaderTool(Tool):
    """
    Web reader tool for fetching and converting web content

    Fetches web content and converts it to markdown or plain text
    """

    # Tool metadata
    name: str = "WebReader"
    description: str = "Fetch and convert URL content to readable format"
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"

    # Permission settings
    permission_level: PermissionLevel = PermissionLevel.ASK
    is_enabled: bool = True

    # Async execution support
    requires_async: bool = True

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    async def execute(
        self,
        input_data: WebReaderInput,
        context: ToolContext
    ) -> ToolResult:
        """Fetch and read web content"""
        import time
        start_time = time.time()

        try:
            # Check cache if enabled
            if not input_data.no_cache and input_data.url in self.cache:
                cached_result = self.cache[input_data.url]
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    content=cached_result['content'],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    metadata={"cached": True},
                )

            # Fetch web content
            async with httpx.AsyncClient(timeout=input_data.timeout) as client:
                response = await client.get(input_data.url, follow_redirects=True)
                response.raise_for_status()

            html_content = response.text

            # Convert HTML to markdown (simplified implementation)
            markdown_content = self._html_to_markdown(html_content, input_data)

            # Cache result
            if not input_data.no_cache:
                self.cache[input_data.url] = {
                    'content': markdown_content,
                    'timestamp': time.time(),
                }

            # Add metadata
            metadata = {
                "url": input_data.url,
                "status_code": response.status_code,
                "content_length": len(markdown_content),
                "return_format": input_data.return_format,
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                content=markdown_content[:10000],  # Limit output size
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata=metadata,
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                content="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _html_to_markdown(self, html_content: str, input_data: WebReaderInput) -> str:
        """Convert HTML to markdown (simplified)"""
        # This is a simplified implementation
        # In production, use a proper HTML-to-markdown library
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text

        except ImportError:
            # Fallback if BeautifulSoup is not available
            import re
            text = re.sub('<[^<]+?>', '', html_content)
            return text

    def get_definition(self):
        """Get tool definition for API"""
        from ..types import ToolDefinition

        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch and read",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds (default: 20)",
                        "default": 20,
                    },
                    "no_cache": {
                        "type": "boolean",
                        "description": "Disable cache (default: false)",
                        "default": False,
                    },
                    "return_format": {
                        "type": "string",
                        "description": "Response format (markdown or text, default: markdown)",
                        "default": "markdown",
                    },
                    "retain_images": {
                        "type": "boolean",
                        "description": "Retain images (default: true)",
                        "default": True,
                    },
                    "no_gfm": {
                        "type": "boolean",
                        "description": "Disable GitHub Flavored Markdown (default: false)",
                        "default": False,
                    },
                    "keep_img_data_url": {
                        "type": "boolean",
                        "description": "Keep image data URLs (default: false)",
                        "default": False,
                    },
                    "with_images_summary": {
                        "type": "boolean",
                        "description": "Include images summary (default: false)",
                        "default": False,
                    },
                    "with_links_summary": {
                        "type": "boolean",
                        "description": "Include links summary (default: false)",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        )
