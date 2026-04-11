"""
FastAPI routes for agent summary management.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.agent_summary import AgentSummaryService

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentMessageRequest(BaseModel):
    role: str
    content: str | list


class AgentSummaryStartResponse(BaseModel):
    ok: bool
    agentId: str
    message: str


class AgentSummaryStopResponse(BaseModel):
    ok: bool
    agentId: str
    message: str


class AgentSummaryResponse(BaseModel):
    agentId: str
    summary: Optional[str] = None
    messageCount: int = 0


@router.post("/{agent_id}/summary/start", response_model=AgentSummaryStartResponse)
async def start_agent_summary(agent_id: str) -> AgentSummaryStartResponse:
    """
    Start periodic summarization for an agent.

    Note: WebSocket connection should be established separately via /ws/agent-summary/{agent_id}
    to receive the actual summary updates.
    """
    if agent_id in AgentSummaryService._tasks and not AgentSummaryService._tasks[agent_id].done():
        return AgentSummaryStartResponse(
            ok=True,
            agentId=agent_id,
            message="Summarization already running",
        )

    return AgentSummaryStartResponse(
        ok=True,
        agentId=agent_id,
        message="Summarization started - connect to WebSocket /ws/agent-summary/{agent_id} to receive updates",
    )


@router.delete("/{agent_id}/summary/stop", response_model=AgentSummaryStopResponse)
async def stop_agent_summary(agent_id: str) -> AgentSummaryStopResponse:
    """Stop periodic summarization for an agent."""
    if agent_id not in AgentSummaryService._tasks:
        return AgentSummaryStopResponse(
            ok=True,
            agentId=agent_id,
            message="No summarization task found",
        )

    AgentSummaryService.stop(agent_id)

    return AgentSummaryStopResponse(
        ok=True,
        agentId=agent_id,
        message="Summarization stopped",
    )


@router.get("/{agent_id}/summary", response_model=AgentSummaryResponse)
async def get_agent_summary(agent_id: str) -> AgentSummaryResponse:
    """Get current summary state for an agent."""
    messages = AgentSummaryService.get_messages(agent_id)
    previous_summary = AgentSummaryService._previous_summaries.get(agent_id)

    return AgentSummaryResponse(
        agentId=agent_id,
        summary=previous_summary,
        messageCount=len(messages),
    )


@router.post("/{agent_id}/messages", response_model=Dict[str, Any])
async def add_agent_message(agent_id: str, message: AgentMessageRequest) -> Dict[str, Any]:
    """Add a message to the agent's conversation history for summarization."""
    message_dict: Dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }
    AgentSummaryService.add_message(agent_id, message_dict)

    return {"ok": True, "agentId": agent_id, "messageCount": len(AgentSummaryService.get_messages(agent_id))}


@router.delete("/{agent_id}/messages")
async def clear_agent_messages(agent_id: str) -> Dict[str, Any]:
    """Clear all messages for an agent."""
    AgentSummaryService.clear_messages(agent_id)

    return {"ok": True, "agentId": agent_id}


class AgentInfo(BaseModel):
    id: str
    status: str
    messageCount: int


class AgentsListResponse(BaseModel):
    agents: list[AgentInfo]


@router.get("", response_model=AgentsListResponse)
async def list_agents() -> AgentsListResponse:
    return AgentsListResponse(agents=[])
