"""
Background shell task executor - integrates shell with task registry.
"""

import asyncio
import logging
import os
import signal
import time
from typing import Optional, Callable

from .shell import ShellInput, ToolResult
from ..agents.task import (
    TaskType,
    TaskStatus,
    TaskStateBase,
    generate_task_id,
    register_task,
    get_registry,
)

logger = logging.getLogger(__name__)


class BackgroundShellExecutor:
    """
    Executes shell commands in background with task registry integration.
    """
    
    def __init__(self):
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._abort_signals: dict[str, asyncio.Event] = {}
    
    async def execute_background(
        self,
        input_data: ShellInput,
        cwd: Optional[str] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> tuple[str, ToolResult]:
        """
        Execute a shell command in background.
        
        Args:
            input_data: ShellInput with command, timeout, shell, cwd
            cwd: Working directory
            on_progress: Optional callback for streaming output
        
        Returns:
            Tuple of (task_id, initial_result) where initial_result
            contains task_id for status tracking
        """
        task_id = generate_task_id(TaskType.LOCAL_BASH)
        registry = get_registry()
        
        task = TaskStateBase(
            id=task_id,
            type=TaskType.LOCAL_BASH,
            status=TaskStatus.RUNNING,
            description=input_data.command[:100],
            output_file=str(registry.get_output_path(task_id)),
        )
        register_task(task)
        
        abort_signal = asyncio.Event()
        self._abort_signals[task_id] = abort_signal
        
        proc = await self._start_process(input_data, cwd)
        self._processes[task_id] = proc
        
        asyncio.create_task(
            self._run_and_monitor(task_id, proc, input_data, abort_signal, on_progress)
        )
        
        initial_result = ToolResult(
            output=f"Background task started: {task_id}\nCommand: {input_data.command}",
            is_error=False,
            metadata={
                "backgroundTaskId": task_id,
                "taskStatus": "running",
            }
        )
        
        return task_id, initial_result
    
    async def _start_process(
        self,
        input_data: ShellInput,
        cwd: Optional[str] = None,
    ) -> asyncio.subprocess.Process:
        """Start the subprocess."""
        from .shell import get_shell_config
        
        cmd, args = get_shell_config(input_data.shell)
        work_dir = input_data.cwd or cwd or os.getcwd()
        
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            input_data.command,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        
        return proc
    
    async def _run_and_monitor(
        self,
        task_id: str,
        proc: asyncio.subprocess.Process,
        input_data: ShellInput,
        abort_signal: asyncio.Event,
        on_progress: Optional[Callable[[dict], None]],
    ):
        """Monitor and record command output."""
        registry = get_registry()
        timeout_seconds = input_data.timeout / 1000.0
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
            
            returncode = proc.returncode or 0
            
            output = stdout_text
            if stderr_text:
                output += f"\n[stderr]\n{stderr_text}"
            
            status = TaskStatus.COMPLETED if returncode == 0 else TaskStatus.FAILED
            
        except asyncio.TimeoutError:
            proc.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            
            output = "[Process terminated: timeout]"
            returncode = -1
            status = TaskStatus.KILLED
        
        except Exception as e:
            output = f"[Process failed: {e}]"
            returncode = -1
            status = TaskStatus.FAILED
        
        registry.append_output(task_id, output)
        
        registry.update(task_id, lambda t: TaskStateBase(
            id=t.id,
            type=t.type,
            status=status,
            description=t.description,
            output_file=t.output_file,
            output_offset=t.output_offset,
            start_time=t.start_time,
            end_time=time.time(),
            total_paused_ms=t.total_paused_ms,
            notified=t.notified,
            tool_use_id=t.tool_use_id,
        ))
        
        if task_id in self._processes:
            del self._processes[task_id]
        if task_id in self._abort_signals:
            del self._abort_signals[task_id]
    
    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get status of a background task."""
        registry = get_registry()
        task = registry.get(task_id)
        
        if not task:
            return None
        
        return {
            "taskId": task.id,
            "status": task.status.value,
            "description": task.description,
            "running": task.status == TaskStatus.RUNNING,
        }
    
    async def get_task_output(self, task_id: str, offset: int = 0) -> Optional[tuple[str, int]]:
        """Get output delta for a task."""
        registry = get_registry()
        return await registry.get_output_delta(task_id, offset)
    
    async def kill_task(self, task_id: str) -> bool:
        """Kill a running background task."""
        if task_id not in self._processes:
            return False
        
        proc = self._processes[task_id]
        abort_signal = self._abort_signals.get(task_id)
        
        if abort_signal:
            abort_signal.set()
        
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        
        registry = get_registry()
        registry.update(task_id, lambda t: TaskStateBase(
            id=t.id,
            type=t.type,
            status=TaskStatus.KILLED,
            description=t.description,
            output_file=t.output_file,
            output_offset=t.output_offset,
            start_time=t.start_time,
            end_time=time.time(),
            total_paused_ms=t.total_paused_ms,
            notified=t.notified,
            tool_use_id=t.tool_use_id,
        ))
        
        return True
    
    async def list_tasks(self) -> list[dict]:
        """List all background tasks."""
        registry = get_registry()
        return [
            {
                "taskId": t.id,
                "status": t.status.value,
                "description": t.description,
                "running": t.status == TaskStatus.RUNNING,
            }
            for t in registry.get_all().values()
        ]


_executor: Optional[BackgroundShellExecutor] = None


def get_background_executor() -> BackgroundShellExecutor:
    global _executor
    if _executor is None:
        _executor = BackgroundShellExecutor()
    return _executor
