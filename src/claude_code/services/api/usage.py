"""
Usage tracking for Claude Code CLI
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Usage:
    """Usage statistics for an API request"""
    
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class SessionUsage:
    """Usage statistics for a session"""
    
    messages: list[Usage] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_usage(self, usage: Usage) -> None:
        self.messages.append(usage)
    
    @property
    def total_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.messages)
    
    @property
    def total_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.messages)
    
    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.messages)
    
    def to_dict(self) -> dict:
        return {
            "messages": [u.to_dict() for u in self.messages],
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
        }
