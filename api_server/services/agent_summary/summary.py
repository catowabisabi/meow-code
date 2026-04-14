from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@dataclass
class AgentSummary:
    agent_id: str
    summary: str
    timestamp: float
    is_final: bool = False


@dataclass
class AgentSummaryConfig:
    interval_seconds: float = 30.0
    max_summary_length: int = 200
    summary_delay_ms: float = 100.0


class AgentSummaryService:
    _tasks: Dict[str, asyncio.Task] = {}
    _previous_summaries: Dict[str, str] = {}
    _messages: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, config: Optional[AgentSummaryConfig] = None):
        self._config = config or AgentSummaryConfig()
        self._summaries: Dict[str, AgentSummary] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    @property
    def config(self) -> AgentSummaryConfig:
        return self._config
    
    @classmethod
    def get_messages(cls, agent_id: str) -> List[Dict[str, Any]]:
        return cls._messages.get(agent_id, [])
    
    @classmethod
    def add_message(cls, agent_id: str, message: Dict[str, Any]) -> None:
        if agent_id not in cls._messages:
            cls._messages[agent_id] = []
        cls._messages[agent_id].append(message)
    
    @classmethod
    def clear_messages(cls, agent_id: str) -> None:
        cls._messages.pop(agent_id, None)
    
    @classmethod
    def stop(cls, agent_id: str) -> None:
        task = cls._tasks.pop(agent_id, None)
        if task:
            task.cancel()
    
    def get_summary(self, agent_id: str) -> Optional[AgentSummary]:
        return self._summaries.get(agent_id)
    
    def get_all_summaries(self) -> Dict[str, AgentSummary]:
        return dict(self._summaries)
    
    def clear_summaries(self) -> None:
        self._summaries.clear()
    
    def update_summary(
        self,
        agent_id: str,
        summary: str,
        is_final: bool = False,
    ) -> None:
        self._summaries[agent_id] = AgentSummary(
            agent_id=agent_id,
            summary=summary,
            timestamp=datetime.utcnow().timestamp(),
            is_final=is_final,
        )
        self._previous_summaries[agent_id] = summary
    
    async def _summarize_loop(
        self,
        get_agents_fn,
        generate_summary_fn,
    ) -> None:
        while self._running:
            try:
                agents = get_agents_fn()
                for agent in agents:
                    if agent.get("status") == "active":
                        summary_text = await generate_summary_fn(agent)
                        if summary_text:
                            self.update_summary(
                                agent["id"],
                                summary_text[:self._config.max_summary_length],
                            )
            except Exception:
                pass
            
            await asyncio.sleep(self._config.interval_seconds)
    
    async def start(
        self,
        get_agents_fn,
        generate_summary_fn,
    ) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._summarize_loop(get_agents_fn, generate_summary_fn)
        )
    
    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    @property
    def is_running(self) -> bool:
        return self._running


_default_service: Optional[AgentSummaryService] = None


def get_agent_summary_service() -> AgentSummaryService:
    global _default_service
    if _default_service is None:
        _default_service = AgentSummaryService()
    return _default_service


async def generate_agent_summary(
    agent_id: str,
    agent_state: Dict[str, Any],
) -> str:
    status = agent_state.get("status", "unknown")
    agent_type = agent_state.get("type", "general-purpose")
    
    summary_parts = [
        f"Agent {agent_id}",
        f"type: {agent_type}",
        f"status: {status}",
    ]
    
    if agent_state.get("current_task"):
        summary_parts.append(f"task: {agent_state['current_task'][:50]}")
    
    if agent_state.get("last_activity"):
        summary_parts.append(f"activity: {agent_state['last_activity']}")
    
    return " | ".join(summary_parts)
