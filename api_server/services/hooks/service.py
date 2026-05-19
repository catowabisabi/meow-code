import asyncio
import json
import time
import uuid
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

@dataclass
class HookContext:
    trigger_type: str
    hook_type: str
    payload: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None

HookHandler = Callable[[HookContext], Awaitable[Dict[str, Any]]]

class HookService:
    def __init__(self):
        self._handlers: Dict[str, HookHandler] = {}
        self._active_hooks: Dict[str, Dict[str, Any]] = {}

    def register_handler(self, hook_type: str, handler: HookHandler):
        self._handlers[hook_type] = handler

    async def execute_pre_hook(
        self,
        hook_id: str,
        trigger_type: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if trigger_type != "pre":
            return None
        return await self._execute_hook(hook_id, "pre", payload, user_id)

    async def execute_post_hook(
        self,
        hook_id: str,
        trigger_type: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if trigger_type != "post":
            return None
        return await self._execute_hook(hook_id, "post", payload, user_id)

    async def _execute_hook(
        self,
        hook_id: str,
        hook_type: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if hook_id not in self._handlers:
            return None

        context = HookContext(
            trigger_type=hook_type,
            hook_type=hook_type,
            payload=payload,
            user_id=user_id,
        )

        start_time = time.time()
        execution_id = str(uuid.uuid4())

        self._active_hooks[execution_id] = {
            "hook_id": hook_id,
            "status": "running",
            "started_at": start_time,
        }

        try:
            result = await self._handlers[hook_id](context)
            duration_ms = int((time.time() - start_time) * 1000)

            self._active_hooks[execution_id].update({
                "status": "completed",
                "duration_ms": duration_ms,
                "result": result,
            })

            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self._active_hooks[execution_id].update({
                "status": "failed",
                "duration_ms": duration_ms,
                "error": str(e),
            })

            raise

    def get_active_hooks(self) -> Dict[str, Dict[str, Any]]:
        return self._active_hooks.copy()

    def clear_completed_hooks(self, older_than_seconds: int = 3600):
        current_time = time.time()
        completed_keys = [
            k for k, v in self._active_hooks.items()
            if v.get("status") in ("completed", "failed")
            and (current_time - v.get("started_at", 0)) > older_than_seconds
        ]
        for key in completed_keys:
            del self._active_hooks[key]

_hook_service: Optional[HookService] = None

def get_hook_service() -> HookService:
    global _hook_service
    if _hook_service is None:
        _hook_service = HookService()
    return _hook_service