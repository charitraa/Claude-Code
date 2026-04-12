"""
MCP (Model Context Protocol) type definitions
Defines data structures for MCP communication
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MCPErrorCode(str, Enum):
    """MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099


class MCPCapabilities(BaseModel):
    """MCP server capabilities"""
    tools: Dict[str, Any] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=dict)
    prompts: Dict[str, Any] = Field(default_factory=dict)
    logging: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class MCPToolInputSchema(BaseModel):
    """Tool input schema"""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = True


class MCPTool(BaseModel):
    """MCP tool definition"""
    name: str
    description: str
    inputSchema: MCPToolInputSchema
    metadata: Optional[Dict[str, Any]] = None


class MCPResourceContents(BaseModel):
    """Resource contents"""
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded


class MCPResource(BaseModel):
    """MCP resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPPromptArgument(BaseModel):
    """Prompt argument definition"""
    name: str
    description: Optional[str] = None
    required: bool = False


class MCPPrompt(BaseModel):
    """MCP prompt definition"""
    name: str
    description: Optional[str] = None
    arguments: List[MCPPromptArgument] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class MCPMessage(BaseModel):
    """MCP message"""
    role: str
    content: Dict[str, Any]


class MCPError(BaseModel):
    """MCP error response"""
    code: int
    message: str
    data: Optional[Any] = None

    @classmethod
    def from_exception(cls, exception: Exception) -> "MCPError":
        """Create error from exception"""
        return cls(
            code=MCPErrorCode.INTERNAL_ERROR,
            message=str(exception),
            data={"type": type(exception).__name__}
        )


class JSONRPCRequest(BaseModel):
    """JSON-RPC request"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC response"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    id: Optional[Union[str, int]] = None


class JSONRPCNotification(BaseModel):
    """JSON-RPC notification (no response expected)"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class ServerInfo(BaseModel):
    """Server information"""
    name: str
    version: str
    protocolVersion: str = "2024-11-05"
    capabilities: MCPCapabilities
    serverInfo: Optional[Dict[str, Any]] = None


class InitializeRequest(BaseModel):
    """Initialize request"""
    protocolVersion: str
    capabilities: MCPCapabilities
    clientInfo: Dict[str, str]
    implementation: Optional[Dict[str, Any]] = None
