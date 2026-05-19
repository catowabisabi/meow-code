import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class AgentStatus(Enum):
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNRESPONSIVE = "unresponsive"
    STOPPED = "stopped"

@dataclass
class AgentHeartbeat:
    agent_id: str
    status: AgentStatus
    last_heartbeat: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    total_restarts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class HeartbeatMonitor:
    def __init__(self):
        self._heartbeats: Dict[str, AgentHeartbeat] = {}
        self._handlers: Dict[str, Callable] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._healthy_threshold: float = 30.0
        self._unhealthy_threshold: float = 60.0
        self._check_interval: float = 10.0
        self._max_restarts: int = 3
        self._restart_cooldown: float = 60.0
        self._last_restart_time: Dict[str, float] = {}

    def register_agent(
        self,
        agent_id: str,
        on_unhealthy: Optional[Callable] = None,
        on_restart: Optional[Callable] = None,
    ):
        heartbeat = AgentHeartbeat(
            agent_id=agent_id,
            status=AgentStatus.STARTING,
        )

        self._heartbeats[agent_id] = heartbeat
        self._handlers[agent_id] = {
            "on_unhealthy": on_unhealthy,
            "on_restart": on_restart,
        }

    async def start_monitoring(self, agent_id: str):
        if agent_id in self._monitoring_tasks:
            return

        task = asyncio.create_task(self._monitor_loop(agent_id))
        self._monitoring_tasks[agent_id] = task

    async def stop_monitoring(self, agent_id: str):
        if agent_id in self._monitoring_tasks:
            self._monitoring_tasks[agent_id].cancel()
            del self._monitoring_tasks[agent_id]

    async def record_heartbeat(
        self,
        agent_id: str,
        status: AgentStatus = AgentStatus.HEALTHY,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if agent_id not in self._heartbeats:
            self.register_agent(agent_id)

        heartbeat = self._heartbeats[agent_id]
        heartbeat.last_heartbeat = time.time()
        heartbeat.status = status
        heartbeat.consecutive_failures = 0

        if metadata:
            heartbeat.metadata.update(metadata)

    async def _monitor_loop(self, agent_id: str):
        while True:
            try:
                await asyncio.sleep(self._check_interval)
                await self._check_agent_health(agent_id)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _check_agent_health(self, agent_id: str):
        if agent_id not in self._heartbeats:
            return

        heartbeat = self._heartbeats[agent_id]
        time_since_heartbeat = time.time() - heartbeat.last_heartbeat

        if time_since_heartbeat > self._unhealthy_threshold:
            if heartbeat.status != AgentStatus.UNRESPONSIVE:
                heartbeat.status = AgentStatus.UNRESPONSIVE
                await self._handle_unresponsive_agent(agent_id)

        elif time_since_heartbeat > self._healthy_threshold:
            if heartbeat.status != AgentStatus.UNHEALTHY:
                heartbeat.status = AgentStatus.UNHEALTHY
                await self._handle_unhealthy_agent(agent_id)

    async def _handle_unhealthy_agent(self, agent_id: str):
        heartbeat = self._heartbeats[agent_id]
        heartbeat.consecutive_failures += 1

        handlers = self._handlers.get(agent_id, {})
        on_unhealthy = handlers.get("on_unhealthy")

        if on_unhealthy:
            try:
                if asyncio.iscoroutinefunction(on_unhealthy):
                    await on_unhealthy(agent_id, heartbeat.consecutive_failures)
                else:
                    on_unhealthy(agent_id, heartbeat.consecutive_failures)
            except Exception:
                pass

    async def _handle_unresponsive_agent(self, agent_id: str):
        heartbeat = self._heartbeats[agent_id]

        if heartbeat.total_restarts >= self._max_restarts:
            return

        last_restart = self._last_restart_time.get(agent_id, 0)
        if time.time() - last_restart < self._restart_cooldown:
            return

        handlers = self._handlers.get(agent_id, {})
        on_restart = handlers.get("on_restart")

        if on_restart:
            try:
                heartbeat.status = AgentStatus.STARTING

                if asyncio.iscoroutinefunction(on_restart):
                    await on_restart(agent_id)
                else:
                    on_restart(agent_id)

                heartbeat.total_restarts += 1
                self._last_restart_time[agent_id] = time.time()
                heartbeat.consecutive_failures = 0

            except Exception:
                heartbeat.status = AgentStatus.UNHEALTHY

    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        heartbeat = self._heartbeats.get(agent_id)
        if not heartbeat:
            return None

        time_since_heartbeat = time.time() - heartbeat.last_heartbeat

        return {
            "agent_id": agent_id,
            "status": heartbeat.status.value,
            "last_heartbeat": heartbeat.last_heartbeat,
            "time_since_heartbeat": time_since_heartbeat,
            "consecutive_failures": heartbeat.consecutive_failures,
            "total_restarts": heartbeat.total_restarts,
            "is_healthy": time_since_heartbeat < self._healthy_threshold,
            "metadata": heartbeat.metadata,
        }

    async def get_all_agents_status(self) -> List[Dict[str, Any]]:
        return [
            await self.get_agent_status(agent_id)
            for agent_id in self._heartbeats.keys()
        ]

    async def force_restart(self, agent_id: str) -> bool:
        heartbeat = self._heartbeats.get(agent_id)
        if not heartbeat:
            return False

        heartbeat.status = AgentStatus.STARTING
        heartbeat.total_restarts += 1
        heartbeat.consecutive_failures = 0

        handlers = self._handlers.get(agent_id, {})
        on_restart = handlers.get("on_restart")

        if on_restart:
            try:
                if asyncio.iscoroutinefunction(on_restart):
                    await on_restart(agent_id)
                else:
                    on_restart(agent_id)
                return True
            except Exception:
                return False

        return False

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._heartbeats)
        healthy = sum(
            1 for h in self._heartbeats.values()
            if h.status == AgentStatus.HEALTHY
        )
        unhealthy = sum(
            1 for h in self._heartbeats.values()
            if h.status == AgentStatus.UNHEALTHY
        )
        unresponsive = sum(
            1 for h in self._heartbeats.values()
            if h.status == AgentStatus.UNRESPONSIVE
        )

        return {
            "total_agents": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "unresponsive": unresponsive,
            "health_rate": healthy / total if total > 0 else 0.0,
            "monitoring_tasks": len(self._monitoring_tasks),
        }

_heartbeat_monitor: Optional[HeartbeatMonitor] = None

def get_heartbeat_monitor() -> HeartbeatMonitor:
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor()
    return _heartbeat_monitor