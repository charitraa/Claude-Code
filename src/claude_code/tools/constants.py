"""
Tool constants for Claude Code CLI
"""

# Agent tool
AGENT_TOOL_NAME = "Agent"
LEGACY_AGENT_TOOL_NAME = "Task"
VERIFICATION_AGENT_TYPE = "verification"
ONE_SHOT_BUILTIN_AGENT_TYPES = {"Explore", "Plan"}

# Skill tool
SKILL_TOOL_NAME = "Skill"

# TodoWrite tool
TODO_WRITE_TOOL_NAME = "TodoWrite"

# File tools
FILE_EDIT_TOOL_NAME = "Edit"
FILE_READ_TOOL_NAME = "Read"
FILE_WRITE_TOOL_NAME = "Write"
CLAUDE_FOLDER_PERMISSION_PATTERN = "/.claude/**"
GLOBAL_CLAUDE_FOLDER_PERMISSION_PATTERN = "~/.claude/**"
FILE_UNEXPECTEDLY_MODIFIED_ERROR = "File has been unexpectedly modified. Read it again before attempting to write it."

# Bash tool
BASH_TOOL_NAME = "Bash"

# Search tools
GREP_TOOL_NAME = "Grep"
GLOB_TOOL_NAME = "Glob"

# Web tools
WEB_SEARCH_TOOL_NAME = "WebSearch"
WEB_FETCH_TOOL_NAME = "WebFetch"

# Task tools
TASK_CREATE_TOOL_NAME = "TaskCreate"
TASK_GET_TOOL_NAME = "TaskGet"
TASK_UPDATE_TOOL_NAME = "TaskUpdate"
TASK_LIST_TOOL_NAME = "TaskList"
TASK_STOP_TOOL_NAME = "TaskStop"
TASK_OUTPUT_TOOL_NAME = "TaskOutput"

# Git tools
GIT_STATUS_TOOL_NAME = "GitStatus"
GIT_DIFF_TOOL_NAME = "GitDiff"
GIT_COMMIT_TOOL_NAME = "GitCommit"
GIT_LOG_TOOL_NAME = "GitLog"

# Config tools
CONFIG_TOOL_NAME = "Config"

# Notebook tools
NOTEBOOK_EDIT_TOOL_NAME = "NotebookEdit"

# MCP tools
LIST_MCP_RESOURCES_TOOL_NAME = "ListMcpResources"
READ_MCP_RESOURCE_TOOL_NAME = "ReadMcpResource"

# LSP tool
LSP_TOOL_NAME = "LSP"

# Schedule tools
CRON_CREATE_TOOL_NAME = "CronCreate"
CRON_DELETE_TOOL_NAME = "CronDelete"
CRON_LIST_TOOL_NAME = "CronList"

# Exit/Enter tools
EXIT_PLAN_MODE_V2_TOOL_NAME = "ExitPlanModeV2"
ENTER_PLAN_MODE_TOOL_NAME = "EnterPlanMode"
ENTER_WORKTREE_TOOL_NAME = "EnterWorktree"
EXIT_WORKTREE_TOOL_NAME = "ExitWorktree"

# Other tools
ASK_USER_QUESTION_TOOL_NAME = "AskUserQuestion"
TOOL_SEARCH_TOOL_NAME = "ToolSearch"
SYNTHETIC_OUTPUT_TOOL_NAME = "SyntheticOutput"
SEND_MESSAGE_TOOL_NAME = "SendMessage"
