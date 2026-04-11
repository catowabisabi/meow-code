"""
Fetch and store the user's first Claude Code token date.
"""

import os
from typing import Dict, Any

import httpx


def _get_oauth_config() -> Dict[str, str]:
    return {
        "BASE_API_URL": os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai"),
    }


def _get_global_config() -> Dict[str, Any]:
    return {}


def _save_global_config(updater) -> None:
    pass


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}, "error": None}


def _log_error(err: Exception) -> None:
    print(f"[first_token_date] Error: {err}", flush=True)


def _get_claude_code_user_agent() -> str:
    return os.environ.get("CLAUDE_CODE_USER_AGENT", "Claude Code/1.0")


async def fetch_and_store_claude_code_first_token_date() -> None:
    """
    Fetch the user's first Claude Code token date and store in config.
    This is called after successful login to cache when they started using Claude Code.
    """
    try:
        config = _get_global_config()

        if config.get("claudeCodeFirstTokenDate") is not None:
            return

        auth_headers = _get_auth_headers()
        if auth_headers.get("error"):
            _log_error(Exception(f"Failed to get auth headers: {auth_headers['error']}"))
            return

        oauth_config = _get_oauth_config()
        url = f"{oauth_config['BASE_API_URL']}/api/organization/claude_code_first_token_date"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    **auth_headers.get("headers", {}),
                    "User-Agent": _get_claude_code_user_agent(),
                },
            )

        first_token_date = response.json().get("first_token_date") if response.status_code == 200 else None

        if first_token_date is not None:
            try:
                _ = os.path.getmtime(first_token_date) if first_token_date else None
            except (ValueError, OSError):
                _log_error(
                    Exception(
                        f"Received invalid first_token_date from API: {first_token_date}",
                    ),
                )
                return

        def updater(current: Dict[str, Any]) -> Dict[str, Any]:
            return {
                **current,
                "claudeCodeFirstTokenDate": first_token_date,
            }
        
        _save_global_config(updater)
    except Exception as error:
        _log_error(error)
