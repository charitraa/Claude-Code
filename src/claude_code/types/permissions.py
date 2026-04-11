"""
Permission types and enums for Claude Code CLI
Converted from TypeScript permission types
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PermissionLevel(str, Enum):
    """Permission levels"""
    ALLOW = "allow"        # Automatically allow
    ASK = "ask"          # Ask user for confirmation
    DENY = "deny"        # Automatically deny


class PermissionType(str, Enum):
    """Types of permissions"""
    TOOL = "tool"                  # Tool execution permissions
    FILE_READ = "file_read"        # File read permissions
    FILE_WRITE = "file_write"      # File write permissions
    NETWORK = "network"            # Network access permissions
    SYSTEM = "system"              # System command permissions
    GIT = "git"                   # Git operation permissions


class PermissionRule(BaseModel):
    """A single permission rule"""
    name: str = Field(..., description="Rule name or pattern")
    type: PermissionType
    level: PermissionLevel
    description: str = ""
    applies_to: List[str] = Field(default_factory=list, description="Specific tools/operations this applies to")


class PermissionDecision(BaseModel):
    """A permission decision made during runtime"""
    rule_name: str
    tool_name: str
    operation: str
    level: PermissionLevel
    user_allowed: Optional[bool] = None
    timestamp: float


class PermissionContext(BaseModel):
    """Context for permission evaluation"""
    current_directory: str = Field(..., description="Current working directory")
    command_context: str = Field(default="", description="Context of the current command")
    user_trust_level: str = Field(default="default", description="User trust level")
    session_mode: str = Field(default="interactive", description="Current session mode")
    environment: Dict[str, str] = Field(default_factory=dict)


class PermissionManager:
    """Manages permission rules and decisions"""

    def __init__(self):
        self._rules: List[PermissionRule] = []
        self._decisions: List[PermissionDecision] = []
        self._deny_rules: Dict[str, PermissionRule] = {}

    def add_rule(self, rule: PermissionRule) -> None:
        """
        Add a permission rule

        Args:
            rule: Permission rule to add
        """
        self._rules.append(rule)

        # Track deny rules for quick lookup
        if rule.level == PermissionLevel.DENY:
            self._deny_rules[rule.name] = rule

    def get_rule_for_tool(self, tool_name: str, context: PermissionContext) -> Optional[PermissionRule]:
        """
        Get the permission rule that applies to a tool

        Args:
            tool_name: Name of the tool
            context: Permission context

        Returns:
            Matching permission rule, or None if no rule applies
        """
        # Check for exact tool match first
        for rule in self._rules:
            if tool_name in rule.applies_to:
                return rule

        # Check for pattern matches
        for rule in self._rules:
            if rule.name.startswith("mcp__") and tool_name.startswith(rule.name):
                return rule

        return None

    def is_denied(self, tool_name: str) -> bool:
        """
        Check if a tool is blanket-denied

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is denied, False otherwise
        """
        return tool_name in self._deny_rules

    def check_permission(
        self,
        tool_name: str,
        operation: str,
        context: PermissionContext
    ) -> PermissionLevel:
        """
        Check what permission level is required for a tool operation

        Args:
            tool_name: Name of the tool
            operation: Specific operation being performed
            context: Permission context

        Returns:
            Permission level required (ALLOW, ASK, or DENY)
        """
        # Check if tool is blanket-denied
        if self.is_denied(tool_name):
            return PermissionLevel.DENY

        # Check for specific rule
        rule = self.get_rule_for_tool(tool_name, context)
        if rule:
            return rule.level

        # Default to ASK if no rule applies
        return PermissionLevel.ASK

    def record_decision(self, decision: PermissionDecision) -> None:
        """
        Record a permission decision

        Args:
            decision: Permission decision that was made
        """
        self._decisions.append(decision)

    def get_decisions_for_tool(self, tool_name: str) -> List[PermissionDecision]:
        """
        Get all permission decisions for a specific tool

        Args:
            tool_name: Name of the tool

        Returns:
            List of permission decisions for the tool
        """
        return [d for d in self._decisions if d.tool_name == tool_name]