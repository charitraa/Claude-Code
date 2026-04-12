"""
Product URLs and remote session utilities
"""

PRODUCT_URL = "https://claude.com/claude-code"

CLAUDE_AI_BASE_URL = "https://claude.ai"
CLAUDE_AI_STAGING_BASE_URL = "https://claude-ai.staging.ant.dev"
CLAUDE_AI_LOCAL_BASE_URL = "http://localhost:4000"


def is_remote_session_staging(session_id: str | None = None, ingress_url: str | None = None) -> bool:
    return (session_id and "_staging_" in session_id) or (ingress_url and "staging" in ingress_url)


def is_remote_session_local(session_id: str | None = None, ingress_url: str | None = None) -> bool:
    return (session_id and "_local_" in session_id) or (ingress_url and "localhost" in ingress_url)


def get_claude_ai_base_url(session_id: str | None = None, ingress_url: str | None = None) -> str:
    if is_remote_session_local(session_id, ingress_url):
        return CLAUDE_AI_LOCAL_BASE_URL
    if is_remote_session_staging(session_id, ingress_url):
        return CLAUDE_AI_STAGING_BASE_URL
    return CLAUDE_AI_BASE_URL


def get_remote_session_url(session_id: str, ingress_url: str | None = None) -> str:
    base_url = get_claude_ai_base_url(session_id, ingress_url)
    return f"{base_url}/code/{session_id}"
