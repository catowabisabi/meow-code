"""
Elicitation handling for MCP servers.

Manages user elicitation requests and responses via the MCP protocol.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


class ElicitRequestParams(TypedDict, total=False):
    message: str
    requested_schema: Dict[str, Any]
    mode: str
    elicitation_id: Optional[str]
    url: Optional[str]


class ElicitationRequestEvent:
    server_name: str
    request_id: str
    params: ElicitRequestParams
    respond: Callable[[Dict[str, Any]], None]
    waiting_state: Optional[Dict[str, Any]] = None
    completed: bool = False


class ElicitationQueue:
    def __init__(self):
        self.queue: List[ElicitationRequestEvent] = []

    def add(self, event: ElicitationRequestEvent) -> None:
        self.queue.append(event)

    def find_by_elicitation_id(self, server_name: str, elicitation_id: str) -> int:
        for i, e in enumerate(self.queue):
            if (
                e.server_name == server_name
                and e.params.get("mode") == "url"
                and e.params.get("elicitation_id") == elicitation_id
            ):
                return i
        return -1

    def mark_completed(self, server_name: str, elicitation_id: str) -> bool:
        idx = self.find_by_elicitation_id(server_name, elicitation_id)
        if idx != -1:
            self.queue[idx].completed = True
            return True
        return False


_elicitation_queue: Optional[ElicitationQueue] = None


def get_elicitation_queue() -> ElicitationQueue:
    global _elicitation_queue
    if _elicitation_queue is None:
        _elicitation_queue = ElicitationQueue()
    return _elicitation_queue


async def execute_elicitation_hooks(
    server_name: str,
    params: ElicitRequestParams,
    signal: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Execute elicitation hooks for the given request.

    Returns response if hook handled it, None otherwise.
    """
    return None


async def execute_elicitation_result_hooks(
    server_name: str,
    result: Dict[str, Any],
    signal: Optional[Any] = None,
    mode: Optional[str] = None,
    elicitation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute elicitation result hooks after user responds.

    Returns potentially modified result.
    """
    return result


async def execute_notification_hooks(message: str, notification_type: str) -> None:
    """Execute notification hooks for observability."""
    pass


def register_elicitation_handler(
    client: Any,
    server_name: str,
    set_app_state: Optional[Callable[[Callable], None]] = None,
) -> None:
    """
    Register elicitation handler on MCP client.

    Args:
        client: MCP client instance
        server_name: Server name for logging
        set_app_state: State setter function
    """
    if not hasattr(client, "set_request_handler"):
        return

    async def handle_elicitation_request(request: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        params = request.get("params", {})
        mode = params.get("mode", "form")

        elicitation_id = None
        if mode == "url" and "elicitation_id" in params:
            elicitation_id = params["elicitation_id"]

        hook_response = await execute_elicitation_hooks(server_name, params, extra.get("signal"))
        if hook_response:
            return hook_response

        waiting_state = {"actionLabel": "Skip confirmation"} if elicitation_id else None

        queue = get_elicitation_queue()
        event = ElicitationRequestEvent()
        event.server_name = server_name
        event.request_id = str(extra.get("requestId", ""))
        event.params = ElicitRequestParams(
            message=params.get("message", ""),
            requested_schema=params.get("requestedSchema", {}),
            mode=mode,
            elicitation_id=elicitation_id,
            url=params.get("url"),
        )
        event.waiting_state = waiting_state

        queue.add(event)

        response = {"action": "cancel"}
        return response

    if hasattr(client, "set_request_handler"):
        try:
            client.set_request_handler(
                {"method": "elicitation", "params": {}},
                handle_elicitation_request,
            )
        except Exception:
            pass

    if hasattr(client, "set_notification_handler"):
        async def handle_elicitation_complete(notification: Dict[str, Any]) -> None:
            params = notification.get("params", {})
            elicitation_id = params.get("elicitationId")
            if elicitation_id:
                queue = get_elicitation_queue()
                queue.mark_completed(server_name, elicitation_id)
                await execute_notification_hooks(
                    f'MCP server "{server_name}" confirmed elicitation {elicitation_id} complete',
                    "elicitation_complete",
                )

        try:
            client.set_notification_handler(
                {"method": "elicitation/complete", "params": {}},
                handle_elicitation_complete,
            )
        except Exception:
            pass


async def run_elicitation_hooks(
    server_name: str,
    params: ElicitRequestParams,
    signal: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run elicitation hooks for programmatic response.

    Args:
        server_name: Name of MCP server
        params: Elicitation parameters
        signal: Abort signal

    Returns:
        ElicitResult if hook handled, None otherwise
    """
    return await execute_elicitation_hooks(server_name, params, signal)


async def run_elicitation_result_hooks(
    server_name: str,
    result: Dict[str, Any],
    signal: Optional[Any] = None,
    mode: Optional[str] = None,
    elicitation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run ElicitationResult hooks after user responds.

    Args:
        server_name: Name of MCP server
        result: User's response
        signal: Abort signal
        mode: Elicitation mode
        elicitation_id: Elicitation ID for URL mode

    Returns:
        Potentially modified ElicitResult
    """
    return await execute_elicitation_result_hooks(server_name, result, signal, mode, elicitation_id)
