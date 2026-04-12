"""
OAuth configuration for Claude Code CLI
"""

import os

CLAUDE_AI_INFERENCE_SCOPE = "user:inference"
CLAUDE_AI_PROFILE_SCOPE = "user:profile"
CONSOLE_SCOPE = "org:create_api_key"
OAUTH_BETA_HEADER = "oauth-2025-04-20"

CONSOLE_OAUTH_SCOPES = [CONSOLE_SCOPE, CLAUDE_AI_PROFILE_SCOPE]

CLAUDE_AI_OAUTH_SCOPES = [
    CLAUDE_AI_PROFILE_SCOPE,
    CLAUDE_AI_INFERENCE_SCOPE,
    "user:sessions:claude_code",
    "user:mcp_servers",
    "user:file_upload",
]

ALL_OAUTH_SCOPES = list(set(CONSOLE_OAUTH_SCOPES + CLAUDE_AI_OAUTH_SCOPES))

MCP_CLIENT_METADATA_URL = "https://claude.ai/oauth/claude-code-client-metadata"

PROD_OAUTH_CONFIG = {
    "BASE_API_URL": "https://api.anthropic.com",
    "CONSOLE_AUTHORIZE_URL": "https://platform.claude.com/oauth/authorize",
    "CLAUDE_AI_AUTHORIZE_URL": "https://claude.com/cai/oauth/authorize",
    "CLAUDE_AI_ORIGIN": "https://claude.ai",
    "TOKEN_URL": "https://platform.claude.com/v1/oauth/token",
    "API_KEY_URL": "https://api.anthropic.com/api/oauth/claude_cli/create_api_key",
    "ROLES_URL": "https://api.anthropic.com/api/oauth/claude_cli/roles",
    "CONSOLE_SUCCESS_URL": "https://platform.claude.com/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
    "CLAUDEAI_SUCCESS_URL": "https://platform.claude.com/oauth/code/success?app=claude-code",
    "MANUAL_REDIRECT_URL": "https://platform.claude.com/oauth/code/callback",
    "CLIENT_ID": "9d1c250a-e61b-44d9-88ed-5944d1962f5e",
    "OAUTH_FILE_SUFFIX": "",
    "MCP_PROXY_URL": "https://mcp-proxy.anthropic.com",
    "MCP_PROXY_PATH": "/v1/mcp/{server_id}",
}

STAGING_OAUTH_CONFIG = {
    "BASE_API_URL": "https://api-staging.anthropic.com",
    "CONSOLE_AUTHORIZE_URL": "https://platform.staging.ant.dev/oauth/authorize",
    "CLAUDE_AI_AUTHORIZE_URL": "https://claude-ai.staging.ant.dev/oauth/authorize",
    "CLAUDE_AI_ORIGIN": "https://claude-ai.staging.ant.dev",
    "TOKEN_URL": "https://platform.staging.ant.dev/v1/oauth/token",
    "API_KEY_URL": "https://api-staging.anthropic.com/api/oauth/claude_cli/create_api_key",
    "ROLES_URL": "https://api-staging.anthropic.com/api/oauth/claude_cli/roles",
    "CONSOLE_SUCCESS_URL": "https://platform.staging.ant.dev/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
    "CLAUDEAI_SUCCESS_URL": "https://platform.staging.ant.dev/oauth/code/success?app=claude-code",
    "MANUAL_REDIRECT_URL": "https://platform.staging.ant.dev/oauth/code/callback",
    "CLIENT_ID": "22422756-60c9-4084-8eb7-27705fd5cf9a",
    "OAUTH_FILE_SUFFIX": "-staging-oauth",
    "MCP_PROXY_URL": "https://mcp-proxy-staging.anthropic.com",
    "MCP_PROXY_PATH": "/v1/mcp/{server_id}",
}

ALLOWED_OAUTH_BASE_URLS = [
    "https://beacon.claude-ai.staging.ant.dev",
    "https://claude.fedstart.com",
    "https://claude-staging.fedstart.com",
]


def _get_oauth_config_type() -> str:
    user_type = os.environ.get("USER_TYPE", "")
    if user_type == "ant":
        if os.environ.get("USE_LOCAL_OAUTH"):
            return "local"
        if os.environ.get("USE_STAGING_OAUTH"):
            return "staging"
    return "prod"


def file_suffix_for_oauth_config() -> str:
    custom_url = os.environ.get("CLAUDE_CODE_CUSTOM_OAUTH_URL")
    if custom_url:
        return "-custom-oauth"
    
    config_type = _get_oauth_config_type()
    if config_type == "local":
        return "-local-oauth"
    if config_type == "staging":
        return "-staging-oauth"
    return ""


def _get_local_oauth_config() -> dict:
    api = os.environ.get("CLAUDE_LOCAL_OAUTH_API_BASE", "http://localhost:8000").rstrip("/")
    apps = os.environ.get("CLAUDE_LOCAL_OAUTH_APPS_BASE", "http://localhost:4000").rstrip("/")
    console_base = os.environ.get("CLAUDE_LOCAL_OAUTH_CONSOLE_BASE", "http://localhost:3000").rstrip("/")
    
    return {
        "BASE_API_URL": api,
        "CONSOLE_AUTHORIZE_URL": f"{console_base}/oauth/authorize",
        "CLAUDE_AI_AUTHORIZE_URL": f"{apps}/oauth/authorize",
        "CLAUDE_AI_ORIGIN": apps,
        "TOKEN_URL": f"{api}/v1/oauth/token",
        "API_KEY_URL": f"{api}/api/oauth/claude_cli/create_api_key",
        "ROLES_URL": f"{api}/api/oauth/claude_cli/roles",
        "CONSOLE_SUCCESS_URL": f"{console_base}/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
        "CLAUDEAI_SUCCESS_URL": f"{console_base}/oauth/code/success?app=claude-code",
        "MANUAL_REDIRECT_URL": f"{console_base}/oauth/code/callback",
        "CLIENT_ID": "22422756-60c9-4084-8eb7-27705fd5cf9a",
        "OAUTH_FILE_SUFFIX": "-local-oauth",
        "MCP_PROXY_URL": "http://localhost:8205",
        "MCP_PROXY_PATH": "/v1/toolbox/shttp/mcp/{server_id}",
    }


def get_oauth_config() -> dict:
    config_type = _get_oauth_config_type()
    
    if config_type == "local":
        config = _get_local_oauth_config()
    elif config_type == "staging":
        user_type = os.environ.get("USER_TYPE", "")
        if user_type == "ant":
            config = STAGING_OAUTH_CONFIG
        else:
            config = PROD_OAUTH_CONFIG
    else:
        config = PROD_OAUTH_CONFIG.copy()
    
    oauth_base_url = os.environ.get("CLAUDE_CODE_CUSTOM_OAUTH_URL")
    if oauth_base_url:
        base = oauth_base_url.rstrip("/")
        if base not in ALLOWED_OAUTH_BASE_URLS:
            raise ValueError("CLAUDE_CODE_CUSTOM_OAUTH_URL is not an approved endpoint.")
        
        config = {
            **config,
            "BASE_API_URL": base,
            "CONSOLE_AUTHORIZE_URL": f"{base}/oauth/authorize",
            "CLAUDE_AI_AUTHORIZE_URL": f"{base}/oauth/authorize",
            "CLAUDE_AI_ORIGIN": base,
            "TOKEN_URL": f"{base}/v1/oauth/token",
            "API_KEY_URL": f"{base}/api/oauth/claude_cli/create_api_key",
            "ROLES_URL": f"{base}/api/oauth/claude_cli/roles",
            "CONSOLE_SUCCESS_URL": f"{base}/oauth/code/success?app=claude-code",
            "CLAUDEAI_SUCCESS_URL": f"{base}/oauth/code/success?app=claude-code",
            "MANUAL_REDIRECT_URL": f"{base}/oauth/code/callback",
            "OAUTH_FILE_SUFFIX": "-custom-oauth",
        }
    
    client_id_override = os.environ.get("CLAUDE_CODE_OAUTH_CLIENT_ID")
    if client_id_override:
        config["CLIENT_ID"] = client_id_override
    
    return config
