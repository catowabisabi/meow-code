import asyncio
import secrets
from typing import Any

from .registry import register_agent, set_agent_status
from .types import AgentResult, AgentSpawnParams


def create_agent_id() -> str:
    alphabet = "012345abcdefghijklmnopqrstuvwxyz"
    suffix = "".join(alphabet[secrets.randbelow(len(alphabet))] for _ in range(8))
    return f"a{suffix}"


async def spawn_agent(params: AgentSpawnParams, tool_context: Any) -> AgentResult:
    agent_id = create_agent_id()

    metadata = {
        "agent_id": agent_id,
        "name": params.name,
        "agent_type": params.agent_type,
        "model": params.model,
        "prompt": params.prompt,
        "cwd": params.cwd,
        "worktree_path": params.worktree_path,
        "description": params.description,
        "status": "pending",
        "output": "",
    }
    register_agent(agent_id, metadata)

    task = asyncio.create_task(_run_agent_async(agent_id, params, tool_context))

    from .registry import _agent_tasks
    _agent_tasks[agent_id] = task

    return AgentResult(success=True, agent_id=agent_id)


async def _run_agent_async(agent_id: str, params: AgentSpawnParams, tool_context: Any) -> None:
    from .loop import run_agent_loop
    from .registry import set_agent_output, set_agent_status, unregister_agent

    set_agent_status(agent_id, "running")
    try:
        result = await run_agent_loop(agent_id, params, tool_context)
        set_agent_output(agent_id, result.output)
        set_agent_status(agent_id, "completed" if result.success else "failed")
    except Exception as e:
        set_agent_status(agent_id, "failed")
        set_agent_output(agent_id, f"Error: {str(e)}")
    finally:
        unregister_agent(agent_id)
