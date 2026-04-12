"""
System constants
"""

import os

DEFAULT_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."
AGENT_SDK_CLAUDE_CODE_PRESET_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK."
AGENT_SDK_PREFIX = "You are a Claude agent, built on Anthropic's Claude Agent SDK."

CLI_SYSPROMPT_PREFIXES = {DEFAULT_PREFIX, AGENT_SDK_CLAUDE_CODE_PRESET_PREFIX, AGENT_SDK_PREFIX}

MACRO_VERSION = os.environ.get("CLAUDE_CODE_VERSION", "0.0.0")


def get_cli_sysprompt_prefix(is_non_interactive: bool = False, has_append_system_prompt: bool = False) -> str:
    """Get the CLI system prompt prefix based on options."""
    if is_non_interactive:
        if has_append_system_prompt:
            return AGENT_SDK_CLAUDE_CODE_PRESET_PREFIX
        return AGENT_SDK_PREFIX
    return DEFAULT_PREFIX


def is_attribution_header_enabled() -> bool:
    """Check if attribution header is enabled."""
    env_val = os.environ.get("CLAUDE_CODE_ATTRIBUTION_HEADER")
    if env_val is None or env_val.lower() in ("false", "0", ""):
        return False
    return True


def get_attribution_header(fingerprint: str) -> str:
    """Get attribution header for API requests."""
    if not is_attribution_header_enabled():
        return ""
    
    version = f"{MACRO_VERSION}.{fingerprint}"
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "unknown")
    
    cch = " cch=00000;" if os.environ.get("NATIVE_CLIENT_ATTESTATION") else ""
    workload = os.environ.get("CC_WORKLOAD", "")
    workload_pair = f" cc_workload={workload};" if workload else ""
    
    return f"x-anthropic-billing-header: cc_version={version}; cc_entrypoint={entrypoint};{cch}{workload_pair}"
