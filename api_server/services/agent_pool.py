"""
Multi-Agent / Sub-agent Pool Service.

Manages sub-agents spawned by the main agentic loop. Each sub-agent
runs its own mini agentic loop but without a WebSocket - results are
collected in memory and returned to the caller.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator

import aiosqlite

from ..models.message import Message
from ..models.content_block import ContentBlock, TextBlock, ToolUseBlock, ToolResultBlock
from ..models.tool import ToolDefinition, ToolCall as ModelToolCall, ToolResult
from ..tools.executor import execute_tool, ToolContext, get_tool_schemas_for_ai
from ..adapters.router import AdapterRouter


MAX_SUB_AGENT_ITERATIONS = 15

AGENT_DB_PATH = Path.home() / ".claude" / "agent_pool.db"

AgentType = str
AgentStatus = str

SUB_AGENT_CONTEXT: Dict[AgentType, str] = {
    "explore": "\n".join([
        "## Sub-Agent Role: Explorer",
        "You are an exploration sub-agent. Your job is to gather information using read-only tools.",
        "Do NOT modify any files or run destructive commands.",
        "Focus on reading files, searching code, and summarizing findings.",
    ]),
    "plan": "\n".join([
        "## Sub-Agent Role: Planner",
        "You are a planning sub-agent. Your job is to analyze a task and produce a step-by-step plan.",
        "You may read files and search code to inform your plan, but do NOT make changes.",
        "Output a clear, actionable plan as your final response.",
    ]),
    "general": "\n".join([
        "## Sub-Agent Role: General",
        "You are a general-purpose sub-agent. You can use all available tools to complete your task.",
        "Work autonomously and return a concise summary of what you did.",
    ]),
    "verify": "\n".join([
        "## Sub-Agent Role: Verifier",
        "You are a verification sub-agent. Your job is to verify that something is correct.",
        "Run tests, check file contents, validate outputs. Report pass/fail with details.",
        "Do NOT make changes - only observe and report.",
    ]),
}


@dataclass
class Agent:
    id: str
    parent_session_id: str
    name: str
    type: AgentType
    status: AgentStatus
    task: str
    model: str
    provider: str
    result: Optional[str] = None
    error: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tools_used: List[str] = field(default_factory=list)
    total_tokens: int = 0
    output_logs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_session_id": self.parent_session_id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "task": self.task,
            "model": self.model,
            "provider": self.provider,
            "result": self.result,
            "error": self.error,
            "messages": [m.model_dump() if hasattr(m, 'model_dump') else m for m in self.messages],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tools_used": self.tools_used,
            "total_tokens": self.total_tokens,
            "output_logs": self.output_logs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        messages = []
        for m in data.get("messages", []):
            if isinstance(m, dict):
                messages.append(Message.from_dict(m))
            else:
                messages.append(m)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif not created_at:
            created_at = datetime.now()

        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = None

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        else:
            completed_at = None

        return cls(
            id=data.get("id", ""),
            parent_session_id=data.get("parent_session_id", ""),
            name=data.get("name", ""),
            type=data.get("type", "general"),
            status=data.get("status", "pending"),
            task=data.get("task", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            result=data.get("result"),
            error=data.get("error"),
            messages=messages,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            tools_used=data.get("tools_used", []),
            total_tokens=data.get("total_tokens", 0),
            output_logs=data.get("output_logs", []),
        )


class AgentPool:
    """
    Agent pool manages sub-agents spawned by the main agent.
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._router: Optional[AdapterRouter] = None
        self._initialized = False
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        if self._initialized:
            return

        AGENT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    parent_session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    messages TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    tools_used TEXT NOT NULL DEFAULT '[]',
                    total_tokens INTEGER DEFAULT 0,
                    output_logs TEXT NOT NULL DEFAULT '[]'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    agent_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    PRIMARY KEY (agent_id, memory_key)
                )
            """)
            await db.commit()

        self._initialized = True

    def _get_router(self) -> AdapterRouter:
        if self._router is None:
            self._router = AdapterRouter()
        return self._router

    async def _save_agent(self, agent: Agent) -> None:
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO agents 
                (id, parent_session_id, name, type, status, task, model, provider, result, error, messages, created_at, started_at, completed_at, tools_used, total_tokens, output_logs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent.id,
                agent.parent_session_id,
                agent.name,
                agent.type,
                agent.status,
                agent.task,
                agent.model,
                agent.provider,
                agent.result,
                agent.error,
                json.dumps([m.model_dump() if hasattr(m, 'model_dump') else m for m in agent.messages], ensure_ascii=False),
                agent.created_at.isoformat() if agent.created_at else datetime.now().isoformat(),
                agent.started_at.isoformat() if agent.started_at else None,
                agent.completed_at.isoformat() if agent.completed_at else None,
                json.dumps(agent.tools_used, ensure_ascii=False),
                agent.total_tokens,
                json.dumps(agent.output_logs, ensure_ascii=False),
            ))
            await db.commit()

    async def _load_agent(self, agent_id: str) -> Optional[Agent]:
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            )
            row = await cursor.fetchone()
            if row:
                return Agent.from_dict(dict(row))
            return None

    async def _delete_agent(self, agent_id: str) -> None:
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            await db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            await db.execute("DELETE FROM agent_memory WHERE agent_id = ?", (agent_id,))
            await db.commit()

    async def spawn_agent(
        self,
        parent_session_id: str,
        name: str,
        agent_type: AgentType,
        task: str,
        model: str,
        provider: str,
    ) -> Agent:
        await self.initialize()

        agent = Agent(
            id=str(uuid.uuid4()),
            parent_session_id=parent_session_id,
            name=name,
            type=agent_type,
            status="pending",
            task=task,
            model=model,
            provider=provider,
            messages=[Message(role="user", content=task)],
            created_at=datetime.now(),
        )

        self._agents[agent.id] = agent
        await self._save_agent(agent)
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    async def get_agent_async(self, agent_id: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if agent is None:
            agent = await self._load_agent(agent_id)
            if agent:
                self._agents[agent.id] = agent
        return agent

    def list_agents(self, session_id: Optional[str] = None) -> List[Agent]:
        agents = list(self._agents.values())
        if session_id:
            agents = [a for a in agents if a.parent_session_id == session_id]
        return sorted(agents, key=lambda a: a.created_at, reverse=True)

    async def list_agents_async(self, session_id: Optional[str] = None) -> List[Agent]:
        await self.initialize()

        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM agents ORDER BY created_at DESC")
            rows = await cursor.fetchall()

        for row in rows:
            agent_id = row["id"]
            if agent_id not in self._agents:
                self._agents[agent_id] = Agent.from_dict(dict(row))

        return self.list_agents(session_id)

    async def remove_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
        if agent_id in self._memory_store:
            del self._memory_store[agent_id]
        await self._delete_agent(agent_id)
        return True

    def _build_sub_agent_system_prompt(self, agent_type: AgentType) -> str:
        type_context = SUB_AGENT_CONTEXT.get(agent_type, SUB_AGENT_CONTEXT["general"])
        return f"{type_context}\n\nYou are running as a sub-agent. Be concise and focused on the task. Return your final answer as plain text."

    async def run_agent(
        self,
        agent_id: str,
        abort_signal: Optional[asyncio.Event] = None,
    ) -> str:
        agent = await self.get_agent_async(agent_id)
        if not agent:
            raise ValueError(f'Agent "{agent_id}" not found')

        agent.status = "running"
        agent.started_at = datetime.now()
        await self._save_agent(agent)

        system_prompt = self._build_sub_agent_system_prompt(agent.type)

        try:
            tools = get_tool_schemas_for_ai()

            def check_abort() -> bool:
                return abort_signal is not None and abort_signal.is_set()

            ctx = ToolContext(
                cwd=str(Path.cwd()),
                abort_signal=check_abort,
            )

            iterations = 0
            messages = list(agent.messages)

            while iterations < MAX_SUB_AGENT_ITERATIONS:
                if abort_signal and abort_signal.is_set():
                    agent.status = "error"
                    agent.error = "Aborted"
                    agent.result = "Agent was aborted."
                    agent.completed_at = datetime.now()
                    await self._save_agent(agent)
                    return "Agent was aborted."

                iterations += 1

                assistant_blocks: List[ContentBlock] = []
                tool_calls: List[ModelToolCall] = []
                current_text = ""
                stop_reason = "end_turn"

                async for event in self._stream_chat(
                    messages=messages,
                    model=agent.model,
                    provider=agent.provider,
                    system_prompt=system_prompt,
                    tools=tools,
                    abort_signal=abort_signal,
                ):
                    if abort_signal and abort_signal.is_set():
                        break

                    if event.type == "stream_text_delta":
                        current_text += event.text or ""
                        agent.output_logs.append(f"[stream] {event.text}")

                    elif event.type == "stream_tool_use_start":
                        agent.output_logs.append(f"[tool_use_start] {event.tool_name}")

                    elif event.type == "stream_tool_use_delta":
                        pass

                    elif event.type == "stream_tool_use_end":
                        if current_text:
                            assistant_blocks.append(TextBlock(type="text", text=current_text))
                            current_text = ""

                        assistant_blocks.append(ToolUseBlock(
                            type="tool_use",
                            id=event.tool_id or "",
                            name=event.tool_name or "",
                            input=event.tool_input or {},
                        ))

                        tool_calls.append(ModelToolCall(
                            id=event.tool_id or "",
                            name=event.tool_name or "",
                            arguments=event.tool_input or {},
                        ))
                        
                        if event.tool_name and event.tool_name not in agent.tools_used:
                            agent.tools_used.append(event.tool_name)

                    elif event.type == "stream_end":
                        if current_text:
                            assistant_blocks.append(TextBlock(type="text", text=current_text))
                            current_text = ""
                        stop_reason = event.stop_reason or "end_turn"
                        
                        if hasattr(event, 'usage') and event.usage:
                            if hasattr(event.usage, 'input_tokens'):
                                agent.total_tokens += (event.usage.input_tokens or 0) + (event.usage.output_tokens or 0)

                    elif event.type == "stream_error":
                        raise Exception(event.error or "Stream error occurred")

                if assistant_blocks:
                    messages.append(Message(role="assistant", content=assistant_blocks))
                    agent.messages = list(messages)

                if not tool_calls or stop_reason != "tool_use":
                    final_text = ""
                    for block in assistant_blocks:
                        if hasattr(block, 'text'):
                            final_text += block.text + "\n"
                        elif hasattr(block, 'type') and block.type == "text":
                            final_text += getattr(block, 'text', '') + "\n"

                    final_text = final_text.strip()
                    agent.status = "completed"
                    agent.result = final_text
                    agent.completed_at = datetime.now()
                    await self._save_agent(agent)
                    return final_text

                tool_results: List[ToolResult] = []
                for tc in tool_calls:
                    if abort_signal and abort_signal.is_set():
                        break

                    result = await execute_tool(tc, ctx)

                    tool_results.append(ToolResult(
                        tool_call_id=tc.id,
                        output=result.output,
                        is_error=result.is_error,
                    ))
                    
                    agent.output_logs.append(f"[tool_result] {tc.name}: {result.output[:200]}")

                    messages.append(Message(role="user", content=[
                        ToolResultBlock(
                            type="tool_result",
                            tool_use_id=tc.id,
                            content=result.output,
                            is_error=result.is_error,
                        )
                    ]))

                agent.messages = list(messages)

            partial_text = ""
            for msg in agent.messages:
                if msg.role == "assistant" and isinstance(msg.content, list):
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            partial_text += block.text + "\n"
                        elif isinstance(block, dict) and block.get("type") == "text":
                            partial_text += block.get("text", "") + "\n"

            agent.status = "completed"
            agent.result = partial_text.strip() or "Sub-agent reached iteration limit without a final response."
            agent.completed_at = datetime.now()
            await self._save_agent(agent)
            return agent.result

        except Exception as err:
            err_msg = str(err)
            agent.status = "error"
            agent.error = err_msg
            agent.result = f"Error: {err_msg}"
            agent.completed_at = datetime.now()
            await self._save_agent(agent)
            return agent.result

    async def _stream_chat(
        self,
        messages: List[Message],
        model: str,
        provider: str,
        system_prompt: str,
        tools: List[Dict],
        abort_signal: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[Any]:
        from ..ws.chat import _get_adapter_router
        router = _get_adapter_router()

        tool_defs = [ToolDefinition.from_dict(t) for t in tools]

        try:
            async for event in router.route_chat(
                provider=provider,
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                tools=tool_defs,
                stream=True,
            ):
                if abort_signal and abort_signal.is_set():
                    break
                yield event
        except Exception as e:
            from ..adapters.base import ChatEvent
            yield ChatEvent.stream_error(error=str(e), index=0)

    async def store_memory(self, agent_id: str, key: str, value: Any) -> None:
        self._memory_store.setdefault(agent_id, {})[key] = value
        
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO agent_memory (agent_id, memory_key, memory_value)
                VALUES (?, ?, ?)
            """, (agent_id, key, json.dumps(value)))
            await db.commit()

    async def get_memory(self, agent_id: str, key: str) -> Optional[Any]:
        if agent_id in self._memory_store and key in self._memory_store[agent_id]:
            return self._memory_store[agent_id][key]
        
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT memory_value FROM agent_memory WHERE agent_id = ? AND memory_key = ?",
                (agent_id, key)
            )
            row = await cursor.fetchone()
            if row:
                value = json.loads(row["memory_value"])
                self._memory_store.setdefault(agent_id, {})[key] = value
                return value
        return None

    async def get_all_memory(self, agent_id: str) -> Dict[str, Any]:
        if agent_id in self._memory_store:
            return dict(self._memory_store[agent_id])
        
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT memory_key, memory_value FROM agent_memory WHERE agent_id = ?",
                (agent_id,)
            )
            rows = await cursor.fetchall()
        
        memory = {}
        for row in rows:
            memory[row["memory_key"]] = json.loads(row["memory_value"])
        
        self._memory_store[agent_id] = memory
        return memory

    async def clear_memory(self, agent_id: str) -> None:
        if agent_id in self._memory_store:
            del self._memory_store[agent_id]
        
        async with aiosqlite.connect(AGENT_DB_PATH) as db:
            await db.execute("DELETE FROM agent_memory WHERE agent_id = ?", (agent_id,))
            await db.commit()

    def get_agent_output_logs(self, agent_id: str) -> List[str]:
        agent = self.get_agent(agent_id)
        if agent:
            return agent.output_logs
        return []


agent_pool = AgentPool()