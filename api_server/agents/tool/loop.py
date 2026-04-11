import asyncio
from typing import Any, AsyncIterator

from ..tools.types import ToolContext
from .types import AgentResult, AgentSpawnParams


async def run_agent_loop(
    agent_id: str,
    params: AgentSpawnParams,
    tool_context: ToolContext,
) -> AgentResult:
    messages: list[dict] = []
    output_parts: list[str] = []
    turns = 0
    max_turns = params.max_turns or 100

    while turns < max_turns:
        turns += 1

        if params.cwd:
            tool_context.cwd = params.cwd

    return AgentResult(
        success=True,
        agent_id=agent_id,
        output="".join(output_parts),
        messages=messages,
    )
