from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import asyncio

from api_server.services.tools.execution import AbortController


MAX_SPECULATION_TURNS = 20
MAX_SPECULATION_MESSAGES = 100

WRITE_TOOLS = frozenset(["Edit", "Write", "NotebookEdit"])
SAFE_READ_ONLY_TOOLS = frozenset([
    "Read", "Glob", "Grep", "ToolSearch", "LSP", "TaskGet", "TaskList",
])


@dataclass
class SpeculationEngine:
    _active_state: Optional[Dict[str, Any]] = None
    _messages_ref: List[Dict[str, Any]] = field(default_factory=list)
    _written_paths_ref: List[str] = field(default_factory=list)
    _abort_controller: Optional[AbortController] = None
    _pipelined_suggestion: Optional[str] = None

    @classmethod
    def get_active_state(cls) -> Optional[Dict[str, Any]]:
        return cls._active_state

    @classmethod
    async def speculate(
        cls,
        suggestion_text: str,
        context: Dict[str, Any],
        set_app_state: Callable[[Callable], None],
        is_pipelined: bool = False,
    ) -> bool:
        if cls._active_state is not None:
            cls.abort_speculation(set_app_state)

        suggestion_length = len(suggestion_text)
        start_time = datetime.utcnow().timestamp()
        state_id = str(hash(suggestion_text))[:8]

        cls._active_state = {
            "id": state_id,
            "status": "active",
            "startTime": start_time,
            "suggestionLength": suggestion_length,
            "toolUseCount": 0,
            "boundary": None,
            "isPipelined": is_pipelined,
        }
        cls._messages_ref = []
        cls._written_paths_ref = []

        set_app_state(lambda prev: {
            **prev,
            "speculation": cls._active_state,
        })

        return True

    @classmethod
    async def accept_speculation(
        cls,
        set_app_state: Callable[[Callable], None],
        clean_message_count: int,
    ) -> Optional[Dict[str, Any]]:
        if cls._active_state is None or cls._active_state.get("status") != "active":
            return None

        state = cls._active_state
        state["status"] = "complete"

        boundary = state.get("boundary")
        start_time = state.get("startTime", 0)
        time_saved_ms = 0
        if boundary and boundary.get("completedAt"):
            time_saved_ms = min(boundary.get("completedAt"), start_time) - start_time

        set_app_state(lambda prev: {
            **prev,
            "speculation": {"status": "idle"},
            "speculationSessionTimeSavedMs": prev.get("speculationSessionTimeSavedMs", 0) + time_saved_ms,
        })

        cls._active_state = None

        return {
            "messages": cls._messages_ref,
            "boundary": boundary,
            "timeSavedMs": time_saved_ms,
        }

    @classmethod
    def abort_speculation(cls, set_app_state: Callable[[Callable], None]) -> None:
        if cls._active_state is None:
            return

        state = cls._active_state
        state["status"] = "idle"

        if cls._abort_controller:
            cls._abort_controller.abort()

        set_app_state(lambda prev: {
            **prev,
            "speculation": {"status": "idle"},
        })

        cls._active_state = None
        cls._messages_ref = []
        cls._written_paths_ref = []

    @classmethod
    def evaluate_speculation(
        cls,
        messages: List[Dict[str, Any]],
        boundary: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        tool_count = 0
        for msg in messages:
            if msg.get("type") == "user" and "content" in msg:
                content = msg["content"]
                if isinstance(content, list):
                    tool_count += sum(
                        1 for b in content
                        if isinstance(b, dict) and b.get("type") == "tool_result" and not b.get("is_error")
                    )

        return {
            "toolCount": tool_count,
            "messageCount": len(messages),
            "completed": boundary is not None and boundary.get("type") == "complete",
            "boundaryType": boundary.get("type") if boundary else None,
        }

    @classmethod
    def update_boundary(
        cls,
        boundary_type: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        if cls._active_state is None:
            return

        boundary_detail = detail if detail else {}
        cls._active_state["boundary"] = {
            "type": boundary_type,
            "completedAt": datetime.utcnow().timestamp(),
            **boundary_detail,
        }

    @classmethod
    def is_speculation_enabled(cls) -> bool:
        return True