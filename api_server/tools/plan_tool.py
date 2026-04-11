"""Plan Mode Tools — switch sessions between execution and planning mode.

When plan mode is active:
- Only read-only tools are available (file_read, glob, grep, web_fetch, web_search)
- System prompt gets a PLAN MODE prefix instructing the AI to explore and plan only
"""
from typing import List, Set

from .types import ToolDef, ToolResult, ToolContext


# ─── Per-Session Plan Mode State ─────────────────────────────

_plan_mode_sessions: Set[str] = set()


def is_plan_mode(session_id: str) -> bool:
    """Check if a session is currently in plan mode."""
    return session_id in _plan_mode_sessions


def enter_plan_mode(session_id: str) -> None:
    """Enter plan mode for a session."""
    _plan_mode_sessions.add(session_id)


def exit_plan_mode(session_id: str) -> None:
    """Exit plan mode for a session."""
    _plan_mode_sessions.discard(session_id)


# ─── Plan Mode System Prompt Prefix ──────────────────────────

def get_plan_mode_system_prompt_prefix() -> str:
    """Get the system prompt prefix for plan mode."""
    return """## PLAN MODE ACTIVE

You are currently in PLAN MODE. In this mode:

1. **DO NOT** modify any files, run destructive commands, or make changes to the codebase.
2. **ONLY** use read-only tools: file_read, glob, grep, web_fetch, web_search.
3. **Focus on**: exploring the codebase, understanding architecture, gathering information, and formulating a plan.
4. **Output**: a clear, step-by-step plan of what changes need to be made, why, and in what order.
5. **Ask questions** if anything is unclear before the user exits plan mode and you begin execution.

Think carefully. Explore thoroughly. Plan before you act.

---

"""


# ─── Read-only tool whitelist ───────────────────────────────

READ_ONLY_TOOLS = frozenset([
    'file_read',
    'glob',
    'grep',
    'web_fetch',
    'web_search',
    'enter_plan_mode',
    'exit_plan_mode',
    'todo_write',
])


def is_tool_allowed_in_plan_mode(tool_name: str) -> bool:
    """Check if a tool is allowed in plan mode."""
    return tool_name in READ_ONLY_TOOLS


def get_readonly_tools() -> List[ToolDef]:
    """Get list of read-only tool definitions.
    
    Returns tools that are available in plan mode.
    """
    from . import executor
    
    all_tools = executor.get_all_tools()
    return [t for t in all_tools if t.name in READ_ONLY_TOOLS]


# ─── Enter Plan Mode Tool ────────────────────────────────────

ENTER_PLAN_MODE_SCHEMA = {
    "type": "object",
    "required": ["sessionId"],
    "properties": {
        "sessionId": {
            "type": "string",
            "description": "Session ID to switch to plan mode",
        },
    },
}


async def _execute_enter_plan_mode(args: dict, context: ToolContext) -> ToolResult:
    """Execute the enter_plan_mode tool."""
    try:
        session_id = args.get("sessionId")
        if not session_id:
            return ToolResult(tool_call_id="", output="sessionId is required.", is_error=True)

        if is_plan_mode(session_id):
            return ToolResult(tool_call_id="", output="Already in plan mode.", is_error=False)

        enter_plan_mode(session_id)
        return ToolResult(
            tool_call_id="",
            output="Entered plan mode. Only read-only tools are now available. Focus on exploring and planning.",
            is_error=False,
        )
    except Exception as err:
        return ToolResult(tool_call_id="", output=f"Error: {str(err)}", is_error=True)


enter_plan_mode_tool = ToolDef(
    name="enter_plan_mode",
    description="Switch the current session to plan mode. In plan mode, only read-only tools are available and the AI focuses on exploration and planning rather than making changes.",
    input_schema=ENTER_PLAN_MODE_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_execute_enter_plan_mode,
)


# ─── Exit Plan Mode Tool ─────────────────────────────────────

EXIT_PLAN_MODE_SCHEMA = {
    "type": "object",
    "required": ["sessionId"],
    "properties": {
        "sessionId": {
            "type": "string",
            "description": "Session ID to exit plan mode",
        },
    },
}


async def _execute_exit_plan_mode(args: dict, context: ToolContext) -> ToolResult:
    """Execute the exit_plan_mode tool."""
    try:
        session_id = args.get("sessionId")
        if not session_id:
            return ToolResult(tool_call_id="", output="sessionId is required.", is_error=True)

        if not is_plan_mode(session_id):
            return ToolResult(tool_call_id="", output="Not currently in plan mode.", is_error=False)

        exit_plan_mode(session_id)
        return ToolResult(
            tool_call_id="",
            output="Exited plan mode. All tools are now available. Ready to execute.",
            is_error=False,
        )
    except Exception as err:
        return ToolResult(tool_call_id="", output=f"Error: {str(err)}", is_error=True)


exit_plan_mode_tool = ToolDef(
    name="exit_plan_mode",
    description="Exit plan mode and return to normal execution mode where all tools are available.",
    input_schema=EXIT_PLAN_MODE_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_execute_exit_plan_mode,
)
