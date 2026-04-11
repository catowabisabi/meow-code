import asyncio
from typing import Optional

from .built_in import BuiltInAgent
from .built_in.explore import get_explore_agent
from .built_in.plan import get_plan_agent
from .built_in.verification import get_verification_agent
from .built_in.claude_code_guide import get_claude_code_guide_agent
from .built_in.statusline_setup import get_statusline_setup_agent
from .built_in.general_purpose import get_general_purpose_agent


_agents: dict[str, dict] = {}
_agent_tasks: dict[str, asyncio.Task] = {}
_built_in_agents: dict[str, BuiltInAgent] = {}


def _register_built_in_agents() -> None:
    global _built_in_agents
    
    _built_in_agents = {
        "explore": get_explore_agent(),
        "plan": get_plan_agent(),
        "verification": get_verification_agent(),
        "claude-code-guide": get_claude_code_guide_agent(),
        "statusline-setup": get_statusline_setup_agent(),
        "general-purpose": get_general_purpose_agent(),
    }
    
    for agent_type, agent in _built_in_agents.items():
        _agents[agent_type] = agent.to_definition()


_register_built_in_agents()


def get_built_in_agent(agent_type: str) -> Optional[BuiltInAgent]:
    return _built_in_agents.get(agent_type)


def create_agent(agent_type: str, **kwargs) -> Optional[dict]:
    agent = _built_in_agents.get(agent_type)
    if not agent:
        return None
    
    definition = agent.to_definition()
    definition.update(kwargs)
    return definition


def register_agent(agent_id: str, metadata: dict) -> None:
    _agents[agent_id] = metadata


def unregister_agent(agent_id: str) -> None:
    _agents.pop(agent_id, None)
    _agent_tasks.pop(agent_id, None)


def get_agent(agent_id: str) -> dict | None:
    return _agents.get(agent_id)


def list_agents() -> list[dict]:
    return list(_agents.values())


def list_built_in_agents() -> list[dict]:
    return [agent.to_definition() for agent in _built_in_agents.values()]


def set_agent_status(agent_id: str, status: str) -> None:
    if agent_id in _agents:
        _agents[agent_id]["status"] = status


def set_agent_output(agent_id: str, output: str) -> None:
    if agent_id in _agents:
        _agents[agent_id]["output"] = output
