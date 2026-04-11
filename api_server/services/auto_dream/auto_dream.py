"""
Main Auto Dream service with gate logic for memory consolidation.

Gate order (cheapest first):
1. Time: hours since lastConsolidatedAt >= minHours
2. Sessions: transcript count with mtime > lastConsolidatedAt >= minSessions
3. Lock: no other process mid-consolidation
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..services.memory import _get_memory_dir
from .config import get_config, is_auto_dream_enabled
from .constants import SESSION_SCAN_INTERVAL_MS
from .consolidation_lock import (
    list_sessions_touched_since_async,
    read_last_consolidated_at_async,
    record_consolidation_async,
    rollback_consolidation_lock_async,
    try_acquire_consolidation_lock_async,
)
from .consolidation_prompt import build_consolidation_prompt
from .dream_task import (
    add_dream_turn,
    complete_dream_task,
    fail_dream_task,
    register_dream_task,
)
from .fork_agent import run_forked_agent
from .types import AutoDreamConfig, CacheSafeParams, DreamTurn, REPLHookContext

logger = logging.getLogger(__name__)


class AutoDreamService:
    """
    Main service for auto dream memory consolidation.
    
    Manages the gate logic, lock acquisition, and forked agent execution
    for background memory consolidation.
    """
    
    _runner: Optional[Callable] = None
    _last_session_scan_at: float = 0
    
    def __init__(self):
        self._runner = None
        self._last_session_scan_at = 0
    
    def init_auto_dream(self, runner: Optional[Callable] = None) -> None:
        """
        Initialize the auto dream runner function.
        
        Args:
            runner: Optional runner function to use for execution.
        """
        self._runner = runner
    
    async def execute_auto_dream(
        self,
        context: REPLHookContext,
        append_system_message: Optional[Callable] = None,
    ) -> None:
        """
        Entry point - checks gates and fires dream if ready.
        
        Args:
            context: REPL hook context with messages and tool_use_context.
            append_system_message: Optional callback to append system messages.
        """
        if not is_auto_dream_enabled():
            logger.debug("Auto dream is not enabled")
            return
        
        await self._run_auto_dream(context, append_system_message)
    
    async def _run_auto_dream(
        self,
        context: REPLHookContext,
        append_system_message: Optional[Callable],
    ) -> None:
        """
        Main logic: time gate -> scan throttle -> session gate -> lock -> fork.
        
        Args:
            context: REPL hook context.
            append_system_message: Optional callback for system messages.
        """
        config = get_config()
        
        last_consolidated_at = await read_last_consolidated_at_async()
        
        if not self._check_time_gate(last_consolidated_at, config.min_hours):
            logger.debug("Time gate not satisfied")
            return
        
        if not self._check_scan_throttle():
            logger.debug("Scan throttle active")
            return
        
        touched_sessions = await list_sessions_touched_since_async(last_consolidated_at)
        session_count = len(touched_sessions)
        
        if session_count < config.min_sessions:
            logger.debug(f"Session gate not satisfied: {session_count} < {config.min_sessions}")
            return
        
        prior_mtime = await try_acquire_consolidation_lock_async()
        if prior_mtime is not None:
            logger.debug("Lock held by another process")
            return
        
        task_id = await register_dream_task(session_count, prior_mtime or 0)
        
        try:
            await self._execute_dream_consolidation(
                task_id=task_id,
                context=context,
                session_count=session_count,
                prior_mtime=prior_mtime or 0,
                config=config,
                append_system_message=append_system_message,
            )
        except Exception as e:
            logger.error(f"Dream consolidation failed: {e}")
            await fail_dream_task(task_id)
            await rollback_consolidation_lock_async(prior_mtime or 0)
    
    async def _execute_dream_consolidation(
        self,
        task_id: str,
        context: REPLHookContext,
        session_count: int,
        prior_mtime: float,
        config: AutoDreamConfig,
        append_system_message: Optional[Callable],
    ) -> None:
        """
        Execute the actual dream consolidation.
        
        Args:
            task_id: The dream task ID.
            context: REPL hook context.
            session_count: Number of sessions to consolidate.
            prior_mtime: Prior consolidation timestamp.
            config: Auto dream configuration.
            append_system_message: Optional callback.
        """
        memory_dir = str(_get_memory_dir())
        transcript_dir = str(Path.home() / ".claude" / "sessions")
        
        prompt = build_consolidation_prompt(
            memory_root=memory_dir,
            transcript_dir=transcript_dir,
        )
        
        messages = [
            {"role": "user", "content": prompt},
        ]
        
        cache_safe_params = CacheSafeParams(
            system_prompt="You are a memory consolidation agent.",
            tools=[],
            model="claude-3-5-haiku-20241022",
            thinking_config={},
            messages_prefix=[],
        )
        
        can_use_tool = self._create_can_use_tool(memory_dir)
        
        abort_controller = asyncio.Event()
        
        async def on_message(msg: Dict[str, Any]) -> None:
            content = msg.get("content", [])
            text = ""
            tool_count = 0
            
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_count += 1
            
            turn = DreamTurn(text=text, tool_use_count=tool_count)
            touched = self._extract_touched_paths(content)
            await add_dream_turn(task_id, turn, touched)
        
        result = await run_forked_agent(
            prompt_messages=messages,
            cache_safe_params=cache_safe_params,
            can_use_tool=can_use_tool,
            query_source="auto_dream",
            fork_label="haiku",
            skip_transcript=True,
            max_turns=50,
            abort_controller=abort_controller,
            on_message=on_message,
        )
        
        if result.success:
            await complete_dream_task(task_id)
            await record_consolidation_async()
        else:
            await fail_dream_task(task_id)
            await rollback_consolidation_lock_async(prior_mtime)
    
    def _check_time_gate(self, last_consolidated_at: float, min_hours: float) -> bool:
        """Check if the time gate is satisfied."""
        if last_consolidated_at <= 0:
            return True
        
        hours_since = (time.time() * 1000 - last_consolidated_at) / (1000 * 60 * 60)
        return hours_since >= min_hours
    
    def _check_scan_throttle(self) -> bool:
        """Check if we're within the scan throttle window."""
        now_ms = time.time() * 1000
        if now_ms - self._last_session_scan_at < SESSION_SCAN_INTERVAL_MS:
            return False
        self._last_session_scan_at = now_ms
        return True
    
    def _create_can_use_tool(self, memory_dir: str) -> Callable:
        """Create a can_use_tool function for the dream."""
        from .extract_memories import create_auto_mem_can_use_tool
        return create_auto_mem_can_use_tool(memory_dir)
    
    def _extract_touched_paths(self, content: List[Any]) -> List[str]:
        """Extract file paths from tool use content blocks."""
        paths = []
        if not isinstance(content, list):
            return paths
        
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            
            tool_name = block.get("name", "")
            if tool_name in ("FileEdit", "FileWrite"):
                inp = block.get("input", {})
                if isinstance(inp, dict):
                    path = inp.get("file_path")
                    if path:
                        paths.append(path)
        
        return paths


_auto_dream_service: Optional[AutoDreamService] = None


def get_auto_dream_service() -> AutoDreamService:
    """Get the global auto dream service instance."""
    global _auto_dream_service
    if _auto_dream_service is None:
        _auto_dream_service = AutoDreamService()
    return _auto_dream_service


async def trigger_manual_dream(
    context: REPLHookContext,
) -> str:
    """
    Trigger a manual dream consolidation via /dream command.
    
    Args:
        context: REPL hook context.
    
    Returns:
        Task ID of the dream task.
    """
    last_consolidated_at = await read_last_consolidated_at_async()
    touched_sessions = await list_sessions_touched_since_async(last_consolidated_at)
    
    task_id = await register_dream_task(len(touched_sessions), last_consolidated_at)
    
    await record_consolidation_async()
    
    await complete_dream_task(task_id)
    
    return task_id
