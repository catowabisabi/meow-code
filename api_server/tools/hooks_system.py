"""Hook system - bridging gap with TypeScript hooks/"""
import asyncio
import logging
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import hashlib


logger = logging.getLogger(__name__)


class HookEvent(Enum):
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    PRE_MESSAGE = "pre_message"
    POST_MESSAGE = "post_message"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PERMISSION_REQUEST = "permission_request"
    ERROR = "error"


@dataclass
class HookContext:
    session_id: str
    user_id: Optional[str] = None
    cwd: str = "."
    env: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    allowed: bool
    modified_input: Optional[Any] = None
    error: Optional[str] = None


class Hook:
    def __init__(
        self,
        name: str,
        event: HookEvent,
        matcher: Optional[Callable] = None,
        command: Optional[str] = None,
        prompt: Optional[str] = None
    ):
        self.name = name
        self.event = event
        self.matcher = matcher
        self.command = command
        self.prompt = prompt
        self.enabled = True
    
    def matches(self, context: HookContext, input_data: Any) -> bool:
        if not self.enabled:
            return False
        
        if self.matcher:
            return self.matcher(context, input_data)
        
        return True
    
    async def execute(self, context: HookContext, input_data: Any) -> HookResult:
        if self.command:
            return await self._execute_command(context, input_data)
        elif self.prompt:
            return await self._execute_prompt(context, input_data)
        else:
            return HookResult(allowed=True)


class HookManager:
    def __init__(self):
        self._hooks: Dict[HookEvent, List[Hook]] = {
            event: [] for event in HookEvent
        }
        self._global_hooks: List[Hook] = []
    
    def register_hook(self, hook: Hook) -> None:
        if hook.event:
            self._hooks[hook.event].append(hook)
        else:
            self._global_hooks.append(hook)
    
    def unregister_hook(self, name: str) -> bool:
        for event_hooks in self._hooks.values():
            for i, hook in enumerate(event_hooks):
                if hook.name == name:
                    event_hooks.pop(i)
                    return True
        
        for i, hook in enumerate(self._global_hooks):
            if hook.name == name:
                self._global_hooks.pop(i)
                return True
        
        return False
    
    def get_hooks(self, event: HookEvent) -> List[Hook]:
        return list(self._hooks.get(event, []))
    
    async def execute_hooks(
        self,
        event: HookEvent,
        context: HookContext,
        input_data: Any
    ) -> HookResult:
        hooks = self._hooks.get(event, []) + self._global_hooks
        
        for hook in hooks:
            if not hook.matches(context, input_data):
                continue
            
            try:
                result = await hook.execute(context, input_data)
                if not result.allowed:
                    return result
                if result.modified_input:
                    input_data = result.modified_input
            except Exception as e:
                logger.error(f"Hook {hook.name} failed: {e}")
                return HookResult(allowed=False, error=str(e))
        
        return HookResult(allowed=True, modified_input=input_data)


class InboxPoller:
    """
    Teammate mailbox polling system.
    
    TypeScript equivalent: useInboxPoller.ts
    Python gap: No inbox polling API.
    """
    
    def __init__(
        self,
        poll_interval: int = 30,
        max_messages: int = 100
    ):
        self.poll_interval = poll_interval
        self.max_messages = max_messages
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._message_handlers: List[Callable] = []
        self._inbox: List[Dict[str, Any]] = []
    
    def on_message(self, handler: Callable) -> None:
        self._message_handlers.append(handler)
    
    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
    
    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
    
    async def _poll_loop(self) -> None:
        while self._running:
            try:
                messages = await self._fetch_messages()
                
                for message in messages:
                    self._inbox.append(message)
                    
                    for handler in self._message_handlers:
                        await handler(message)
                
                if len(self._inbox) > self.max_messages:
                    self._inbox = self._inbox[-self.max_messages:]
            
            except Exception as e:
                logger.error(f"Inbox poll failed: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _fetch_messages(self) -> List[Dict[str, Any]]:
        return []
    
    def get_messages(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        if unread_only:
            return [m for m in self._inbox if not m.get("read", False)]
        return list(self._inbox)
    
    def mark_read(self, message_id: str) -> None:
        for message in self._inbox:
            if message.get("id") == message_id:
                message["read"] = True


_hook_manager: Optional[HookManager] = None
_inbox_poller: Optional[InboxPoller] = None


def get_hook_manager() -> HookManager:
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def get_inbox_poller() -> InboxPoller:
    global _inbox_poller
    if _inbox_poller is None:
        _inbox_poller = InboxPoller()
    return _inbox_poller
