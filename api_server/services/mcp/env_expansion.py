"""
Environment variable expansion utilities for MCP server configurations.
"""

import os
import re
from typing import List


def expand_env_vars_in_string(value: str) -> tuple[str, List[str]]:
    """
    Expand environment variables in a string value.
    Handles ${VAR} and ${VAR:-default} syntax.

    Args:
        value: The string value containing environment variable references

    Returns:
        A tuple of (expanded string, list of missing variable names)
    """
    missing_vars: List[str] = []

    def replace_match(match: re.Match) -> str:
        nonlocal missing_vars
        var_content = match.group(1)
        # Split on :- to support default values (limit to 2 parts to preserve :- in defaults)
        parts = var_content.split(":-", 1)
        var_name = parts[0]
        default_value = parts[1] if len(parts) > 1 else None

        env_value = os.environ.get(var_name)

        if env_value is not None:
            return env_value
        if default_value is not None:
            return default_value

        # Track missing variable for error reporting
        missing_vars.append(var_name)
        # Return original if not found (allows debugging but will be reported as error)
        return match.group(0)

    expanded = re.sub(r"\$\{([^}]+)\}", replace_match, value)

    return expanded, missing_vars
