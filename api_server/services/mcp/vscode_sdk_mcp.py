"""
VSCode SDK MCP server integration.

Provides notifications for VSCode MCP server communication.
"""

import os
from typing import Any, Dict, List, Optional


class VSCodeMCPClient:
    """VSCode MCP client reference for notifications."""

    def __init__(self, client: Any, name: str, capabilities: Dict[str, Any]):
        self.client = client
        self.name = name
        self.capabilities = capabilities

    async def notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a notification to the VSCode MCP server."""
        pass


_vscode_mcp_client: Optional[VSCodeMCPClient] = None


def notify_vscode_file_updated(
    file_path: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> None:
    """
    Sends a file_updated notification to the VSCode MCP server.

    Args:
        file_path: Path to the file that was updated
        old_content: Previous content (None for new files)
        new_content: New content (None for deleted files)
    """
    global _vscode_mcp_client

    if os.environ.get("USER_TYPE") != "ant" or not _vscode_mcp_client:
        return

    try:
        client = _vscode_mcp_client.client
        if hasattr(client, "notification"):
            import asyncio
            asyncio.create_task(
                client.notification(
                    "file_updated",
                    {"filePath": file_path, "oldContent": old_content, "newContent": new_content}
                )
            )
    except Exception:
        pass


def setup_vscode_sdk_mcp(sdk_clients: List[Any]) -> None:
    """
    Sets up the special internal VSCode MCP for bidirectional communication.

    Args:
        sdk_clients: List of MCP server connections
    """
    global _vscode_mcp_client

    for client in sdk_clients:
        if getattr(client, "name", None) == "claude-vscode" and client.type == "connected":
            _vscode_mcp_client = VSCodeMCPClient(
                client.client,
                client.name,
                client.capabilities or {},
            )

            if hasattr(client.client, "set_notification_handler"):
                client.client.set_notification_handler(
                    {"method": "log_event", "params": {"eventName": str, "eventData": dict}},
                    lambda notification: None,
                )

            break
