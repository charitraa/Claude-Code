"""
MCP Server implementation
Provides Model Context Protocol server functionality
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .types import (
    MCPCapabilities,
    MCPTool,
    MCPResource,
    MCPPrompt,
    MCPError,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    ServerInfo,
    InitializeRequest,
    MCPErrorCode,
)
from ..config import Settings
from ..tools import ToolRegistry

logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP Server implementation

    Handles JSON-RPC communication and provides tools, resources, and prompts
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        Initialize MCP server

        Args:
            settings: Application settings
            tool_registry: Tool registry for exposing tools
        """
        self.settings = settings or Settings()
        self.tool_registry = tool_registry or ToolRegistry()

        # Server state
        self.running = False
        self.initialized = False
        self.client_info: Optional[Dict[str, str]] = None

        # Capability providers
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}

        # Request handlers
        self._request_handlers: Dict[str, Callable] = {}
        self._notification_handlers: Dict[str, Callable] = {}

        # Setup default handlers
        self._setup_handlers()

        # Initialize capabilities
        self._initialize_capabilities()

    def _setup_handlers(self) -> None:
        """Setup default request and notification handlers"""
        self._request_handlers.update({
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "shutdown": self._handle_shutdown,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        })

        self._notification_handlers.update({
            "notifications/initialized": self._handle_notification_initialized,
            "notifications/cancelled": self._handle_notification_cancelled,
            "notifications/progress": self._handle_notification_progress,
        })

    def _initialize_capabilities(self) -> None:
        """Initialize server capabilities"""
        self.capabilities = MCPCapabilities(
            tools={
                "listChanged": True,  # Support for dynamic tool lists
            },
            resources={
                "subscribe": True,  # Support for resource subscriptions
                "listChanged": True,
            },
            prompts={
                "listChanged": True,
            },
            logging={},
        )

    async def start(self) -> None:
        """Start the MCP server"""
        if self.running:
            logger.warning("MCP server is already running")
            return

        logger.info("Starting MCP server")
        self.running = True

        # Load tools from registry
        await self._load_tools()

        # Load resources
        await self._load_resources()

        # Load prompts
        await self._load_prompts()

        logger.info("MCP server started successfully")

    async def stop(self) -> None:
        """Stop the MCP server"""
        if not self.running:
            return

        logger.info("Stopping MCP server")
        self.running = False
        self.initialized = False

        # Clear client info
        self.client_info = None

        logger.info("MCP server stopped")

    async def restart(self) -> None:
        """Restart the MCP server"""
        await self.stop()
        await asyncio.sleep(0.1)  # Brief delay
        await self.start()

    async def handle_request(self, request_data: str) -> str:
        """
        Handle an incoming JSON-RPC request

        Args:
            request_data: JSON-RPC request as string

        Returns:
            JSON-RPC response as string
        """
        try:
            # Parse request
            request = JSONRPCRequest.model_validate_json(request_data)
            logger.debug(f"Received request: {request.method}")

            # Check if server is running
            if request.method != "initialize" and not self.running:
                error = MCPError(
                    code=MCPErrorCode.SERVER_ERROR_START,
                    message="Server not running"
                )
                response = JSONRPCResponse(
                    jsonrpc="2.0",
                    error=error,
                    id=request.id
                )
                return response.model_dump_json()

            # Handle request
            handler = self._request_handlers.get(request.method)
            if not handler:
                error = MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method not found: {request.method}"
                )
                response = JSONRPCResponse(
                    jsonrpc="2.0",
                    error=error,
                    id=request.id
                )
                return response.model_dump_json()

            # Call handler
            result = await handler(request.params or {})

            # Create response
            response = JSONRPCResponse(
                jsonrpc="2.0",
                result=result,
                id=request.id
            )
            return response.model_dump_json()

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            error = MCPError.from_exception(e)
            response = JSONRPCResponse(
                jsonrpc="2.0",
                error=error,
                id=None
            )
            return response.model_dump_json()

    async def handle_notification(self, notification_data: str) -> None:
        """
        Handle an incoming JSON-RPC notification

        Args:
            notification_data: JSON-RPC notification as string
        """
        try:
            # Parse notification
            notification = JSONRPCNotification.model_validate_json(notification_data)
            logger.debug(f"Received notification: {notification.method}")

            # Handle notification
            handler = self._notification_handlers.get(notification.method)
            if handler:
                await handler(notification.params or {})
            else:
                logger.debug(f"No handler for notification: {notification.method}")

        except Exception as e:
            logger.error(f"Error handling notification: {e}", exc_info=True)

    # Request handlers

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        logger.info("Handling initialize request")

        # Store client info
        if "clientInfo" in params:
            self.client_info = params["clientInfo"]
            logger.info(f"Client: {self.client_info.get('name')} {self.client_info.get('version')}")

        # Create server info
        server_info = ServerInfo(
            name="claude-code-mcp",
            version="1.0.0",
            protocolVersion="2024-11-05",
            capabilities=self.capabilities,
            serverInfo={
                "description": "Claude Code MCP Server",
                "homepage": "https://github.com/anthropics/claude-code",
            }
        )

        return server_info.model_dump()

    async def _handle_initialized(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialized notification"""
        logger.info("Client initialized")
        self.initialized = True
        return {}

    async def _handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown request"""
        logger.info("Shutting down")
        await self.stop()
        return {}

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [tool.model_dump() for tool in self._tools.values()]
        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        # This would integrate with the tool execution framework
        # For now, return a placeholder response
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Tool execution not yet implemented for: {tool_name}"
                }
            ],
            "isError": False
        }

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = [resource.model_dump() for resource in self._resources.values()]
        return {"resources": resources}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        if not uri:
            raise ValueError("Resource URI is required")

        # This would integrate with resource providers
        # For now, return a placeholder response
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": "Resource reading not yet implemented"
                }
            ]
        }

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = [prompt.model_dump() for prompt in self._prompts.values()]
        return {"prompts": prompts}

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Prompt name is required")

        prompt = self._prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        # This would integrate with prompt templates
        # For now, return a placeholder response
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Prompt template not yet implemented: {name}"
                    }
                }
            ]
        }

    # Notification handlers

    async def _handle_notification_initialized(self, params: Dict[str, Any]) -> None:
        """Handle notifications/initialized"""
        logger.debug("Received initialized notification")

    async def _handle_notification_cancelled(self, params: Dict[str, Any]) -> None:
        """Handle notifications/cancelled"""
        logger.debug("Received cancelled notification")

    async def _handle_notification_progress(self, params: Dict[str, Any]) -> None:
        """Handle notifications/progress"""
        logger.debug(f"Received progress notification: {params}")

    # Tool, resource, and prompt loading

    async def _load_tools(self) -> None:
        """Load tools from the tool registry"""
        logger.info("Loading tools from registry")

        available_tools = self.tool_registry.get_available_tools()

        for tool in available_tools:
            definition = tool.get_definition()

            mcp_tool = MCPTool(
                name=definition.name,
                description=definition.description,
                inputSchema=definition.input_schema,
                metadata={
                    "category": definition.category.value if definition.category else None,
                    "permission_level": definition.permission_level.value if definition.permission_level else None,
                }
            )

            self._tools[definition.name] = mcp_tool
            logger.debug(f"Loaded tool: {definition.name}")

        logger.info(f"Loaded {len(self._tools)} tools")

    async def _load_resources(self) -> None:
        """Load resources"""
        logger.info("Loading resources")

        # This would integrate with resource providers
        # For now, add a placeholder resource
        self._resources["current-directory"] = MCPResource(
            uri="file://.",
            name="Current Directory",
            description="The current working directory",
            mimeType="text/directory"
        )

        logger.info(f"Loaded {len(self._resources)} resources")

    async def _load_prompts(self) -> None:
        """Load prompts"""
        logger.info("Loading prompts")

        # This would integrate with prompt templates
        # For now, add a placeholder prompt
        self._prompts["code-review"] = MCPPrompt(
            name="code-review",
            description="Review code for issues and improvements",
            arguments=[
                {
                    "name": "code",
                    "description": "Code to review",
                    "required": True
                }
            ]
        )

        logger.info(f"Loaded {len(self._prompts)} prompts")

    # Public API for dynamic registration

    def register_tool(self, tool: MCPTool) -> None:
        """
        Register a tool dynamically

        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool

        Args:
            name: Name of tool to unregister
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")

    def register_resource(self, resource: MCPResource) -> None:
        """
        Register a resource dynamically

        Args:
            resource: Resource to register
        """
        self._resources[resource.uri] = resource
        logger.info(f"Registered resource: {resource.uri}")

    def unregister_resource(self, uri: str) -> None:
        """
        Unregister a resource

        Args:
            uri: URI of resource to unregister
        """
        if uri in self._resources:
            del self._resources[uri]
            logger.info(f"Unregistered resource: {uri}")

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """
        Register a prompt dynamically

        Args:
            prompt: Prompt to register
        """
        self._prompts[prompt.name] = prompt
        logger.info(f"Registered prompt: {prompt.name}")

    def unregister_prompt(self, name: str) -> None:
        """
        Unregister a prompt

        Args:
            name: Name of prompt to unregister
        """
        if name in self._prompts:
            del self._prompts[name]
            logger.info(f"Unregistered prompt: {name}")

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information

        Returns:
            Server information dictionary
        """
        return {
            "name": "claude-code-mcp",
            "version": "1.0.0",
            "running": self.running,
            "initialized": self.initialized,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
        }
