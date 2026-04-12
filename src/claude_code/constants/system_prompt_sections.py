"""
System prompt sections and utilities
"""

from typing import Callable, Any

SystemPromptSection = dict[str, Any]


def system_prompt_section(
    name: str,
    compute: Callable[[], str | None],
) -> SystemPromptSection:
    return {"name": name, "compute": compute, "cacheBreak": False}


def dangerous_uncached_system_prompt_section(
    name: str,
    compute: Callable[[], str | None],
    reason: str,
) -> SystemPromptSection:
    return {"name": name, "compute": compute, "cacheBreak": True}
