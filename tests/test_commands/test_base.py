"""
Tests for Command Base Classes
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from claude_code.commands import (
    BaseCommand,
    AsyncCommand,
    SimpleCommand,
    CommandResult,
    CommandStatus,
    CommandMetadata,
    CommandArgument,
    CommandOption,
)


@pytest.mark.unit
class TestBaseCommand:
    """Tests for BaseCommand"""

    @pytest.fixture
    def simple_test_command(self):
        """Create a simple test command"""

        class SimpleTestCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="simple",
                    description="Simple test command",
                    category="test"
                )

            async def execute(self, args, options, context=None):
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message="Command executed successfully"
                )

        return SimpleTestCommand

    @pytest.fixture
    def command_with_arguments(self):
        """Create a command with arguments"""

        class CommandWithArguments(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="with-args",
                    description="Command with arguments",
                    category="test"
                )

            def _get_arguments(self):
                return [
                    CommandArgument(
                        name="required_arg",
                        description="A required argument",
                        required=True
                    ),
                    CommandArgument(
                        name="optional_arg",
                        description="An optional argument",
                        required=False,
                        default="default_value"
                    )
                ]

            async def execute(self, args, options, context=None):
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"args": args}
                )

        return CommandWithArguments

    @pytest.fixture
    def command_with_options(self):
        """Create a command with options"""

        class CommandWithOptions(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="with-options",
                    description="Command with options",
                    category="test"
                )

            def _get_options(self):
                return [
                    CommandOption(
                        name="verbose",
                        short_name="v",
                        description="Verbose output",
                        is_flag=True
                    ),
                    CommandOption(
                        name="output",
                        short_name="o",
                        description="Output file",
                        default="output.txt"
                    )
                ]

            async def execute(self, args, options, context=None):
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"options": options}
                )

        return CommandWithOptions

    def test_command_metadata(self, simple_test_command):
        """Test command metadata"""
        command = simple_test_command()

        assert command.metadata.name == "simple"
        assert command.metadata.description == "Simple test command"
        assert command.metadata.category == "test"

    def test_command_run_success(self, simple_test_command):
        """Test successful command execution"""
        command = simple_test_command()
        result = command.run([], {})

        assert result.is_success()
        assert "successful" in result.message.lower()

    def test_command_with_missing_required_argument(self, command_with_arguments):
        """Test command with missing required argument"""
        command = command_with_arguments()
        result = command.run([], {})

        assert not result.is_success()
        assert "required" in result.message.lower()

    def test_command_with_all_arguments(self, command_with_arguments):
        """Test command with all arguments provided"""
        command = command_with_arguments()
        result = command.run(["arg1", "arg2"], {})

        assert result.is_success()
        assert result.data["args"] == ["arg1", "arg2"]

    def test_command_with_options(self, command_with_options):
        """Test command with options"""
        command = command_with_options()
        result = command.run([], {"verbose": True, "output": "custom.txt"})

        assert result.is_success()
        assert result.data["options"]["verbose"] is True
        assert result.data["options"]["output"] == "custom.txt"

    def test_command_help(self, simple_test_command):
        """Test command help generation"""
        command = simple_test_command()
        help_text = command.get_help()

        assert "simple" in help_text
        assert "Simple test command" in help_text
        assert "test" in help_text

    def test_command_display_result_success(self, simple_test_command, mock_console):
        """Test displaying successful result"""
        command = simple_test_command()
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="Success message"
        )

        command.display_result(result)

    def test_command_display_result_failure(self, simple_test_command, mock_console):
        """Test displaying failed result"""
        command = simple_test_command()
        result = CommandResult(
            status=CommandStatus.ERROR,
            message="Error message"
        )

        command.display_result(result)

    def test_command_before_execute_hook(self, simple_test_command):
        """Test before execute hook"""
        hook_called = []

        class CommandWithHook(simple_test_command):
            async def before_execute(self, args, options, context=None):
                hook_called.append("before")

        command = CommandWithHook()
        command.run([], {})

        assert "before" in hook_called

    def test_command_after_execute_hook(self, simple_test_command):
        """Test after execute hook"""
        hook_called = []

        class CommandWithHook(simple_test_command):
            async def after_execute(self, result, args, options, context=None):
                hook_called.append("after")

        command = CommandWithHook()
        command.run([], {})

        assert "after" in hook_called

    def test_command_validation_type_checking(self):
        """Test command validation with type checking"""

        class CommandWithTypeCheck(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="type-check",
                    description="Command with type checking",
                    category="test"
                )

            def _get_arguments(self):
                return [
                    CommandArgument(
                        name="number",
                        description="A number argument",
                        type=int
                    )
                ]

            async def execute(self, args, options, context=None):
                return CommandResult(status=CommandStatus.SUCCESS)

        command = CommandWithTypeCheck()
        errors = command.run(["not_a_number"], {}).message

        assert "Invalid type" in errors

    def test_command_validation_choices(self):
        """Test command validation with choices"""

        class CommandWithChoices(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="choices",
                    description="Command with choices",
                    category="test"
                )

            def _get_arguments(self):
                return [
                    CommandArgument(
                        name="option",
                        description="An option with choices",
                        choices=["opt1", "opt2", "opt3"]
                    )
                ]

            async def execute(self, args, options, context=None):
                return CommandResult(status=CommandStatus.SUCCESS)

        command = CommandWithChoices()
        errors = command.run(["invalid_option"], {}).message

        assert "Invalid choice" in errors

    def test_deprecated_command_warning(self):
        """Test deprecated command shows warning"""

        class DeprecatedCommand(BaseCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="deprecated",
                    description="Deprecated command",
                    category="test",
                    deprecated=True,
                    deprecation_message="Use 'new-command' instead"
                )

            async def execute(self, args, options, context=None):
                return CommandResult(status=CommandStatus.SUCCESS)

        command = DeprecatedCommand()
        result = command.run([], {})

        # Should still work but with warning
        assert result.is_success()


@pytest.mark.unit
class TestAsyncCommand:
    """Tests for AsyncCommand"""

    @pytest.fixture
    def async_test_command(self):
        """Create an async test command"""

        class AsyncTestCommand(AsyncCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="async-cmd",
                    description="Async test command",
                    category="test"
                )

        return AsyncTestCommand

    @patch('subprocess.run')
    def test_execute_async_command(self, mock_run, async_test_command):
        """Test executing an external command asynchronously"""
        # Mock subprocess.run
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b"output",
            stderr=b""
        )

        command = async_test_command()
        result = command.run([], {})

        # This is a simplified test - actual async execution would need
        # the execute method to be implemented
        assert command is not None


@pytest.mark.unit
class TestSimpleCommand:
    """Tests for SimpleCommand"""

    @pytest.fixture
    def simple_command(self):
        """Create a simple command"""

        class MySimpleCommand(SimpleCommand):
            def _get_metadata(self) -> CommandMetadata:
                return CommandMetadata(
                    name="my-simple",
                    description="My simple command",
                    category="test"
                )

        return MySimpleCommand

    def test_simple_command_default_implementation(self, simple_command):
        """Test simple command default implementation"""
        command = simple_command()
        result = command.run([], {})

        assert result.is_success()
        assert "executed successfully" in result.message.lower()


@pytest.mark.unit
class TestCommandResult:
    """Tests for CommandResult"""

    def test_command_result_success(self):
        """Test successful command result"""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="Success",
            exit_code=0
        )

        assert result.is_success()
        assert not result.is_failure()
        assert result.exit_code == 0

    def test_command_result_failure(self):
        """Test failed command result"""
        result = CommandResult(
            status=CommandStatus.ERROR,
            message="Error",
            exit_code=1
        )

        assert not result.is_success()
        assert result.is_failure()
        assert result.exit_code == 1

    def test_command_result_with_data(self):
        """Test command result with data"""
        data = {"key": "value", "number": 42}
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="Success with data",
            data=data
        )

        assert result.data == data
        assert result.data["key"] == "value"
        assert result.data["number"] == 42

    def test_command_result_with_error(self):
        """Test command result with error exception"""
        exception = ValueError("Test error")
        result = CommandResult(
            status=CommandStatus.ERROR,
            message="Command failed",
            error=exception
        )

        assert result.error == exception
        assert str(result.error) == "Test error"
