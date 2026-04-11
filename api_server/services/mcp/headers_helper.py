"""
HTTP headers helper for MCP server configurations.

Provides utilities to get dynamic headers from a headersHelper script
and combine them with static headers.
"""

import os
import subprocess
from typing import Any, Dict, Optional

try:
    import json
except ImportError:
    json = None


async def exec_file_no_throw_with_cwd(
    command: str,
    args: list,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_ms: int = 10000,
    shell: bool = True,
) -> Dict[str, Any]:
    """
    Execute a file and return the result.

    Args:
        command: The command to execute
        args: Arguments to pass
        cwd: Working directory
        env: Environment variables
        timeout_ms: Timeout in milliseconds
        shell: Whether to use shell

    Returns:
        Dict with code, stdout, stderr
    """
    full_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=full_env,
            timeout=timeout_ms / 1000,
            shell=shell,
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"code": -1, "stdout": "", "stderr": "Timeout"}
    except Exception as e:
        return {"code": -1, "stdout": "", "stderr": str(e)}


async def get_mcp_headers_from_helper(
    server_name: str,
    config: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Get dynamic headers for an MCP server using the headersHelper script.

    Args:
        server_name: The name of the MCP server
        config: The MCP server configuration with headersHelper and url

    Returns:
        Headers dict or None if not configured or failed
    """
    headers_helper = config.get("headers_helper")
    if not headers_helper:
        return None

    result = await exec_file_no_throw_with_cwd(
        headers_helper,
        [],
        env={
            **os.environ,
            "CLAUDE_CODE_MCP_SERVER_NAME": server_name,
            "CLAUDE_CODE_MCP_SERVER_URL": config.get("url", ""),
        },
        timeout=10000,
        shell=True,
    )

    if result["code"] != 0 or not result["stdout"]:
        return None

    try:
        headers = json.loads(result["stdout"].strip()) if json else {}
    except json.JSONDecodeError:
        return None

    if not isinstance(headers, dict) or headers is None:
        return None

    for key, value in headers.items():
        if not isinstance(value, str):
            return None

    return headers


async def get_mcp_server_headers(
    server_name: str,
    config: Dict[str, Any],
) -> Dict[str, str]:
    """
    Get combined headers for an MCP server (static + dynamic).

    Args:
        server_name: The name of the MCP server
        config: The MCP server configuration

    Returns:
        Combined headers object (dynamic overrides static)
    """
    static_headers = config.get("headers") or {}
    dynamic_headers = (await get_mcp_headers_from_helper(server_name, config)) or {}
    return {**static_headers, **dynamic_headers}
