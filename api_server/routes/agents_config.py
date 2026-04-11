import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/agents-config", tags=["agents"])

AGENTS_CONFIG_PATH = Path.home() / ".claude" / "agents_config.json"

AGENT_TYPES = [
    {"name": "auto", "description": "Auto mode - automatically selects the best agent for the task", "features": ["automatic_selection", "adaptive_behavior"]},
    {"name": "agent", "description": "Agent mode for complex tasks", "features": ["complex_reasoning", "tool_use", "multi_step_planning"]},
    {"name": "compact", "description": "Compact mode for efficiency", "features": ["minimal_tokens", "fast_responses", "concise_output"]},
]


class AgentConfig(BaseModel):
    current_agent_type: str
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    model: Optional[str] = None


class AgentConfigUpdate(BaseModel):
    current_agent_type: Optional[str] = None
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    model: Optional[str] = None


class AgentConfigResponse(BaseModel):
    config: AgentConfig
    available_types: List[str]


class AgentType(BaseModel):
    name: str
    description: str
    features: List[str]


def _get_default_config() -> AgentConfig:
    return AgentConfig(
        current_agent_type="auto",
        max_iterations=None,
        temperature=None,
        model=None,
    )


def _load_config() -> AgentConfig:
    try:
        if AGENTS_CONFIG_PATH.exists():
            with open(AGENTS_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AgentConfig(**data)
    except Exception:
        pass
    return _get_default_config()


def _save_config(config: AgentConfig) -> None:
    AGENTS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENTS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)


def _init_default_config() -> None:
    if not AGENTS_CONFIG_PATH.exists():
        default_config = _get_default_config()
        _save_config(default_config)


_init_default_config()


@router.get("/config", response_model=AgentConfigResponse)
async def get_agent_config() -> AgentConfigResponse:
    config = _load_config()
    available_types = [at["name"] for at in AGENT_TYPES]
    return AgentConfigResponse(config=config, available_types=available_types)


@router.put("/config", response_model=AgentConfigResponse)
async def update_agent_config(update: AgentConfigUpdate) -> AgentConfigResponse:
    config = _load_config()

    if update.current_agent_type is not None:
        valid_types = [at["name"] for at in AGENT_TYPES]
        if update.current_agent_type not in valid_types:
            raise ValueError(f"Invalid agent type: {update.current_agent_type}")
        config.current_agent_type = update.current_agent_type
    if update.max_iterations is not None:
        config.max_iterations = update.max_iterations
    if update.temperature is not None:
        config.temperature = update.temperature
    if update.model is not None:
        config.model = update.model

    _save_config(config)
    available_types = [at["name"] for at in AGENT_TYPES]
    return AgentConfigResponse(config=config, available_types=available_types)


@router.get("/types", response_model=List[AgentType])
async def list_agent_types() -> List[AgentType]:
    return [AgentType(**at) for at in AGENT_TYPES]
