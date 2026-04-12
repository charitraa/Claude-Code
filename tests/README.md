# Test Suite for Claude Code CLI

This directory contains the test suite for the Python implementation of Claude Code CLI.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_cli/               # CLI-related tests
│   └── test_commands.py    # Command handler tests
├── test_commands/          # Command system tests
│   ├── test_base.py        # Command base class tests
│   └── test_registry.py    # Command registry tests
├── test_tools/             # Tool system tests
│   └── test_base.py        # Tool base class tests
├── test_mcp/               # MCP server tests (to be added)
└── test_integration/       # Integration tests
    └── test_basic_workflow.py  # End-to-end workflow tests
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test categories:
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run specific test files:
```bash
# Test command registry
pytest tests/test_commands/test_registry.py

# Test CLI commands
pytest tests/test_cli/test_commands.py
```

### Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

### Run in verbose mode:
```bash
pytest -v
```

### Run a specific test:
```bash
pytest tests/test_commands/test_registry.py::TestCommandRegistry::test_register_command
```

## Test Fixtures

The following fixtures are available in `conftest.py`:

### Directory & File Fixtures:
- `temp_dir` - Temporary directory for tests
- `temp_config_dir` - Temporary config directory
- `mock_config_file` - Mock configuration file

### Mock Fixtures:
- `mock_settings` - Mock Settings instance
- `mock_app_state` - Mock AppState instance
- `mock_tool_registry` - Mock ToolRegistry instance
- `mock_api_client` - Mock Claude API client
- `mock_console` - Mock Rich console for output capture
- `mock_command_registry` - Mock CommandRegistry instance
- `mock_mcp_server` - Mock MCP server

### Utility Fixtures:
- `test_utils` - Test utility functions for creating files, directories, etc.

## Test Markers

Tests are marked with the following markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (slower, test component interaction)
- `@pytest.mark.slow` - Slow tests (long-running or resource-intensive)
- `@pytest.mark.requires_api` - Tests that require API access

## Writing Tests

### Example Unit Test:

```python
import pytest
from claude_code.commands import CommandRegistry, BaseCommand

@pytest.mark.unit
class TestMyFeature:
    def test_basic_functionality(self, mock_console):
        # Arrange
        registry = CommandRegistry(console=mock_console)

        # Act
        result = registry.execute("test", [], {})

        # Assert
        assert result.is_success()
```

### Example Async Test:

```python
@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncFeature:
    async def test_async_operation(self, mock_app_state):
        # Arrange
        # Setup code

        # Act
        await mock_app_state.update_status(AppState.AppStateStatus.READY)

        # Assert
        assert mock_app_state.status == AppState.AppStateStatus.READY
```

### Example Integration Test:

```python
@pytest.mark.integration
@pytest.mark.slow
class TestWorkflow:
    async def test_complete_workflow(self, temp_workspace, mock_console):
        # Test full workflow from start to finish
        pass
```

## Test Coverage

To generate coverage report:

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
start htmlcov/index.html  # On Windows
```

## Continuous Integration

Tests are configured to run in CI with the following command:

```bash
pytest -m "not slow" --cov=src --cov-report=xml
```

This excludes slow tests and generates coverage in XML format for CI tools.

## Troubleshooting

### Import Errors:
If you get import errors, ensure you're running tests from the project root:
```bash
cd /path/to/claude-code
pytest
```

### Async Tests Not Running:
Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

### Tests Failing Due to Missing Fixtures:
Make sure you're using the fixtures provided in conftest.py. Check the test file imports.

## Contributing

When adding new features, please:

1. Write unit tests for new components
2. Add integration tests for workflows
3. Ensure all tests pass before submitting
4. Maintain test coverage above 80%

## Test Best Practices

1. **Arrange-Act-Assert Pattern**: Structure tests clearly
2. **Descriptive Names**: Use clear test names that describe what's being tested
3. **One Assert Per Test**: Keep tests focused
4. **Use Fixtures**: Reuse fixtures for common setup
5. **Mock External Dependencies**: Don't make real API calls in tests
6. **Test Edge Cases**: Include error conditions and edge cases
7. **Keep Tests Independent**: Tests should not depend on each other
8. **Use Appropriate Markers**: Mark tests correctly for selective running
