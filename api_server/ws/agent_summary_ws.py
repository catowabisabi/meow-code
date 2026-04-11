"""
WebSocket handler for agent summary updates.

Pushes periodic 3-5 word summaries to connected clients.
"""

from fastapi import WebSocket, WebSocketDisconnect

from ..services.agent_summary import AgentSummaryService


async def agent_summary_websocket(websocket: WebSocket, agent_id: str) -> None:
    """
    WebSocket handler for agent summary updates.

    Args:
        websocket: WebSocket connection
        agent_id: Agent identifier to monitor
    """
    await websocket.accept()

    try:
        await AgentSummaryService.start(agent_id, session_id=None, websocket=websocket)
    except WebSocketDisconnect:
        AgentSummaryService.stop(agent_id)
