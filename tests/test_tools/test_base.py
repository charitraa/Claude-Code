"""
Tests for Tool Base Classes
"""

import pytest
from unittest.mock import Mock, AsyncMock

from claude_code.tools import (
    Tool,
    ToolRegistry,
    ToolInputSchema,
    ToolDefinition,
    ToolContext,
    ToolResult,
    ToolPermission,
    ToolPermissionLevel,
    ToolCategory,
)


@pytest.mark.unit
class TestTool:
    """Tests for Tool base class"""

    @pytest.fixture
    def sample_tool(self):
        """Create a sample tool for testing"""

        class SampleTool(Tool):
            name = "sample_tool"
            description = "A sample tool for testing"

            async def execute(self, input_data):
                return {"result": "success", "data": input_data}

        return SampleTool

    def test_tool_name(self, sample_tool):
        """Test tool name"""
        assert sample_tool.name == "sample_tool"

    def test_tool_description(self, sample_tool):
        """Test tool description"""
        assert sample_tool.description == "A sample tool for testing"

    @pytest.mark.asyncio
    async def test_tool_execution(self, sample_tool):
        """Test tool execution"""
        tool = sample_tool()
        result = await tool.execute({"test": "data"})

        assert result["result"] == "success"
        assert result["data"] == {"test": "data"}


@pytest.mark.unit
class TestToolRegistry:
    """Tests for ToolRegistry"""

    @pytest.fixture
    def sample_tools(self):
        """Create sample tools for testing"""

        class Tool1(Tool):
            name = "tool1"
            description = "First tool"

            async def execute(self, input_data):
                return {"tool": "tool1", "data": input_data}

        class Tool2(Tool):
            name = "tool2"
            description = "Second tool"

            async def execute(self, input_data):
                return {"tool": "tool2", "data": input_data}

        return [Tool1, Tool2]

    def test_register_tool(self, sample_tools):
        """Test registering a tool"""
        registry = ToolRegistry()
        registry.register(sample_tools[0])

        assert "tool1" in registry.list_tools()

    def test_register_multiple_tools(self, sample_tools):
        """Test registering multiple tools"""
        registry = ToolRegistry()
        for tool_class in sample_tools:
            registry.register(tool_class)

        assert "tool1" in registry.list_tools()
        assert "tool2" in registry.list_tools()

    def test_get_tool(self, sample_tools):
        """Test getting a registered tool"""
        registry = ToolRegistry()
        registry.register(sample_tools[0])

        tool = registry.get_tool("tool1")
        assert tool is not None
        assert tool.name == "tool1"

    def test_get_nonexistent_tool(self):
        """Test getting a non-existent tool"""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent")
        assert tool is None

    def test_unregister_tool(self, sample_tools):
        """Test unregistering a tool"""
        registry = ToolRegistry()
        registry.register(sample_tools[0])

        assert registry.unregister("tool1") is True
        assert "tool1" not in registry.list_tools()

    def test_unregister_nonexistent_tool(self):
        """Test unregistering a non-existent tool"""
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_list_tools(self, sample_tools):
        """Test listing all tools"""
        registry = ToolRegistry()
        for tool_class in sample_tools:
            registry.register(tool_class)

        tools = registry.list_tools()
        assert "tool1" in tools
        assert "tool2" in tools

    @pytest.mark.asyncio
    async def test_execute_tool(self, sample_tools):
        """Test executing a tool through registry"""
        registry = ToolRegistry()
        registry.register(sample_tools[0])

        result = await registry.execute_tool("tool1", {"test": "data"})
        assert result is not None
        # The actual implementation would need to be tested based on
        # how the registry executes tools

    def test_tool_categories(self):
        """Test tool categories"""

        class CategorizedTool(Tool):
            name = "categorized"
            description = "Tool with category"
            category = ToolCategory.FILE_OPERATIONS

            async def execute(self, input_data):
                return {}

        registry = ToolRegistry()
        registry.register(CategorizedTool)

        tools = registry.get_tools_by_category(ToolCategory.FILE_OPERATIONS)
        assert "categorized" in [t.name for t in tools]


@pytest.mark.unit
class TestToolDefinition:
    """Tests for ToolDefinition"""

    def test_tool_definition_creation(self):
        """Test creating a tool definition"""
        schema = ToolInputSchema(
            type="object",
            properties={
                "arg1": {"type": "string"},
                "arg2": {"type": "integer"}
            },
            required=["arg1"]
        )

        definition = ToolDefinition(
            name="test_tool",
            description="Test tool",
            input_schema=schema,
            category=ToolCategory.BASH,
            permission_level=ToolPermissionLevel.ASK
        )

        assert definition.name == "test_tool"
        assert definition.description == "Test tool"
        assert definition.category == ToolCategory.BASH
        assert definition.permission_level == ToolPermissionLevel.ASK
        assert "arg1" in definition.input_schema.required


@pytest.mark.unit
class TestToolResult:
    """Tests for ToolResult"""

    def test_successful_result(self):
        """Test successful tool result"""
        from claude_code.tools.execution import ToolResult

        result_data = Mock()
        result = ToolResult(
            success=True,
            result=result_data,
            execution_time_ms=100.0
        )

        assert result.success is True
        assert result.result == result_data
        assert result.execution_time_ms == 100.0

    def test_failed_result(self):
        """Test failed tool result"""
        from claude_code.tools.execution import ToolResult

        result = ToolResult(
            success=False,
            error="Tool execution failed",
            execution_time_ms=50.0
        )

        assert result.success is False
        assert result.error == "Tool execution failed"


@pytest.mark.unit
class TestToolPermission:
    """Tests for ToolPermission"""

    def test_allow_permission(self):
        """Test allow permission"""
        permission = ToolPermission(
            level=ToolPermissionLevel.ALLOW,
            reason="Explicitly allowed"
        )

        assert permission.level == ToolPermissionLevel.ALLOW
        assert permission.reason == "Explicitly allowed"

    def test_deny_permission(self):
        """Test deny permission"""
        permission = ToolPermission(
            level=ToolPermissionLevel.DENY,
            reason="Security restriction"
        )

        assert permission.level == ToolPermissionLevel.DENY
        assert permission.reason == "Security restriction"


@pytest.mark.unit
class TestToolContext:
    """Tests for ToolContext"""

    def test_tool_context_creation(self):
        """Test creating a tool context"""
        context = ToolContext(
            cwd="/test/directory",
            user_id="user123",
            session_id="session456",
            permissions=["read", "write"],
            environment={"VAR1": "value1"}
        )

        assert context.cwd == "/test/directory"
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert "read" in context.permissions
        assert "write" in context.permissions
        assert context.environment["VAR1"] == "value1"
