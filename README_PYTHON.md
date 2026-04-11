# Claude Code CLI - Python Version

**Python conversion of the TypeScript Claude Code CLI - AI-powered command-line interface**

## 🚀 Installation

### Prerequisites
- Python 3.11 or higher
- pip or virtual environment support

### Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Or install with poetry (if available)
poetry install
```

### Quick Start

```bash
# Start the interactive REPL
python src/main.py

# Show version
python src/main.py --version

# Show help
python src/main.py --help

# Initialize in current directory
python src/main.py init

# Configure settings
python src/main.py config
```

## 📁 Project Structure

```
claude-code/
├── src/
│   ├── claude_code/          # Main package
│   │   ├── types/            # Type system (messages, tools, permissions)
│   │   ├── config/           # Configuration management
│   │   ├── state/            # State management (app state, conversations)
│   │   ├── tools/            # Tool implementations
│   │   ├── cli/              # CLI commands and REPL
│   │   ├── services/         # External services (API, MCP)
│   │   └── utils/            # Utilities (logging, helpers)
│   └── main.py              # Entry point
├── tests/                    # Test suites
├── pyproject.toml            # Project configuration
└── README_PYTHON.md          # This file
```

## 🛠️ Available Tools

### Core Tools (Implemented)
- **Bash**: Execute shell commands
- **FileRead**: Read file contents
- **FileWrite**: Write content to files
- **FileEdit**: Edit file contents with search/replace
- **Grep**: Search text in files using regular expressions
- **Glob**: Find files matching patterns

### Tool Categories
- **FILE_OPERATIONS**: File read/write/edit operations
- **SHELL**: Shell command execution
- **SEARCH**: File searching and pattern matching
- **SYSTEM**: System-level operations

### Permission System
- **ALLOW**: Automatically allow tool execution
- **ASK**: Ask user for confirmation
- **DENY**: Automatically deny tool execution

## 🎨 Features

### Terminal UI
- **Textual-based**: Modern terminal interface using Textual framework
- **Rich formatting**: Beautiful output with colors and styling
- **Interactive prompts**: User-friendly permission requests
- **Message display**: Clear conversation history
- **Tool results**: Formatted tool execution output

### State Management
- **Pub/Sub pattern**: Event-driven state updates
- **Conversation tracking**: Complete message history
- **Tool execution**: Permission-aware tool calling
- **API integration**: Streaming responses from Claude

### Configuration
- **Pydantic-based**: Type-safe configuration
- **Environment variables**: Support for CLAUDE_CODE_* prefix
- **File-based**: JSON configuration files
- **Feature flags**: Conditional feature enabling

## 🔧 Configuration

### Environment Variables
```bash
# API Configuration
CLAUDE_CODE_ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_CODE_BASE_URL=https://api.anthropic.com

# Feature Flags
CLAUDE_CODE_SIMPLE=false
CLAUDE_CODE_DEBUG=false

# Logging
CLAUDE_CODE_LOG_LEVEL=INFO
```

### Configuration Files
- **Global**: `~/.claude/config.json`
- **Project**: `.claude/config.json` (in project directory)

## 🤖️ API Integration

### Claude API
- **Streaming support**: Real-time response streaming
- **Tool calling**: Automatic tool execution based on model responses
- **Model selection**: Support for multiple Claude models
- **Error handling**: Comprehensive error management

### Tool Execution Framework
- **Permission checking**: Multi-level permission system
- **Async execution**: Non-blocking tool operations
- **Error handling**: Graceful failure handling
- **User interaction**: Interactive permission requests

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_types.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run async tests
pytest -k asyncio
```

### Test Structure
- **Unit tests**: Individual component testing
- **Integration tests**: API and tool integration testing
- **E2E tests**: End-to-end workflow testing

## 📊 Architecture

### Key Components

1. **Type System**: Pydantic models for type safety
2. **State Management**: Pub/sub pattern for reactive updates
3. **Tool System**: Extensible tool framework with permissions
4. **API Client**: Async Anthropic API integration
5. **Terminal UI**: Textual-based interactive interface
6. **Configuration**: Flexible, environment-aware settings

### Design Principles
- **Async-first**: All I/O operations are asynchronous
- **Type-safe**: Pydantic validation throughout
- **Extensible**: Plugin-based tool system
- **User-friendly**: Rich terminal UI with clear feedback
- **Maintainable**: Clean code structure and documentation

## 🔮 Roadmap

### Short-term (Weeks 5-12)
- [ ] Implement remaining 40+ tools
- [ ] Complete permission system UI
- [ ] Add MCP integration
- [ ] Implement multi-agent system

### Medium-term (Weeks 13-18)
- [ ] Build skills framework
- [ ] Add LSP integration
- [ ] Implement git operations
- [ ] Create configuration UI

### Long-term (Weeks 19-24)
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Complete documentation
- [ ] Deployment automation

## 🐛 Troubleshooting

### Common Issues

**Import Error**: `ModuleNotFoundError`
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

**Permission Denied**: Tool execution blocked
- Check configuration settings
- Verify API key is set correctly

**API Errors**: Connection or rate limiting
- Verify internet connection
- Check API key validity
- Review rate limits

## 📞 Support

- **Documentation**: See inline docstrings and type hints
- **Examples**: Check tests for usage patterns
- **Issues**: Report bugs in GitHub issues

## 📄 License

Proprietary - Copyright © 2026 Anthropic

## 🙏 Acknowledgments

This project converts the TypeScript Claude Code CLI to Python, maintaining full feature parity while leveraging Python's strengths for CLI applications.

Original TypeScript version: https://github.com/anthropics/claude-code

---

**Note**: This is a work-in-progress Python conversion. Some features may not yet be fully implemented.