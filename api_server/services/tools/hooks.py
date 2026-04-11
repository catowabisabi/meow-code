"""Tool hook system for pre/post execution hooks."""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class ToolHook:
    name: str
    hook_type: str
    callback: Callable[..., Coroutine[Any, Any, Any]]
    priority: int = 0


@dataclass 
class HookHandler:
    pre_hooks: list[ToolHook] = field(default_factory=list)
    post_hooks: list[ToolHook] = field(default_factory=list)


class ToolHooks:
    
    def __init__(self) -> None:
        self._handlers: dict[str, HookHandler] = {}
    
    def register_pre_tool_hook(
        self,
        tool_name: str,
        hook: ToolHook,
    ) -> None:
        if tool_name not in self._handlers:
            self._handlers[tool_name] = HookHandler()
        self._handlers[tool_name].pre_hooks.append(hook)
        self._handlers[tool_name].pre_hooks.sort(key=lambda h: h.priority, reverse=True)
    
    def register_post_tool_hook(
        self,
        tool_name: str,
        hook: ToolHook,
    ) -> None:
        if tool_name not in self._handlers:
            self._handlers[tool_name] = HookHandler()
        self._handlers[tool_name].post_hooks.append(hook)
        self._handlers[tool_name].post_hooks.sort(key=lambda h: h.priority, reverse=True)
    
    async def run_pre_tool_hooks(
        self,
        tool_name: str,
        tool_use_id: str,
        tool_input: dict[str, Any],
        context: Any,
    ) -> list[dict[str, Any]]:
        results = []
        handler = self._handlers.get(tool_name)
        if not handler:
            return results
        
        for hook in handler.pre_hooks:
            try:
                if asyncio.iscoroutinefunction(hook.callback):
                    result = await hook.callback(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        tool_input=tool_input,
                        context=context,
                    )
                else:
                    result = hook.callback(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        tool_input=tool_input,
                        context=context,
                    )
                    if asyncio.iscoroutine(result):
                        result = await result
                if result:
                    results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "hook_name": hook.name,
                })
        
        return results
    
    async def run_post_tool_hooks(
        self,
        tool_name: str,
        tool_use_id: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        context: Any,
    ) -> list[dict[str, Any]]:
        results = []
        handler = self._handlers.get(tool_name)
        if not handler:
            return results
        
        for hook in handler.post_hooks:
            try:
                if asyncio.iscoroutinefunction(hook.callback):
                    result = await hook.callback(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        tool_input=tool_input,
                        tool_output=tool_output,
                        context=context,
                    )
                else:
                    result = hook.callback(
                        tool_name=tool_name,
                        tool_use_id=tool_use_id,
                        tool_input=tool_input,
                        tool_output=tool_output,
                        context=context,
                    )
                    if asyncio.iscoroutine(result):
                        result = await result
                if result:
                    results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "hook_name": hook.name,
                })
        
        return results


def get_max_tool_use_concurrency() -> int:
    env_value = os.environ.get("CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY", "")
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass
    return 10
