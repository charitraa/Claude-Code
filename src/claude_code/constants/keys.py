"""
GrowthBook client key
"""

import os

def get_growthbook_client_key() -> str:
    """Get GrowthBook client key based on environment."""
    user_type = os.environ.get("USER_TYPE", "")
    
    if user_type == "ant":
        if os.environ.get("ENABLE_GROWTHBOOK_DEV"):
            return "sdk-yZQvlplybuXjYh6L"
        return "sdk-xRVcrliHIlrg4og4"
    return "sdk-zAZezfDKGoZuXXKe"
