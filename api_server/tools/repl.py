"""
REPLTool - Interactive REPL (Read-Eval-Print Loop) execution tool.

Provides an interactive Python/JS REPL session for exploratory programming.

Based on the TypeScript REPLTool implementation in _claude_code_leaked_source_code.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .types import ToolDef, ToolContext, ToolResult


TOOL_NAME = "repl"


@dataclass
class REPLSession:
    session_id: str
    language: str
    history: list[str] = field(default_factory=list)
    variables: dict = field(default_factory=dict)
    output: list[str] = field(default_factory=list)
    status: str = "active"


_sessions: dict[str, REPLSession] = {}
_session_lock = asyncio.Lock()


async def create_session(language: str = "python") -> REPLSession:
    session_id = str(uuid.uuid4())
    session = REPLSession(session_id=session_id, language=language)
    async with _session_lock:
        _sessions[session_id] = session
    return session


async def get_session(session_id: str) -> Optional[REPLSession]:
    async with _session_lock:
        return _sessions.get(session_id)


async def execute_code(session_id: str, code: str) -> tuple[str, str]:
    session = await get_session(session_id)
    if not session:
        return "", f"Session {session_id} not found"
    
    session.history.append(code)
    
    language = session.language.lower()
    
    if language == "python":
        return await _execute_python(session, code)
    elif language in ("javascript", "js"):
        return await _execute_javascript(session, code)
    else:
        return "", f"Unsupported language: {language}"


async def _execute_python(session: REPLSession, code: str) -> tuple[str, str]:
    stdout_buffer = []
    stderr_buffer = []
    
    try:
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            result = eval(code, session.variables)
            
            if result is not None:
                stdout_buffer.append(repr(result))
            
            stdout_val = sys.stdout.getvalue()
            stderr_val = sys.stderr.getvalue()
            
            if stdout_val:
                stdout_buffer.append(stdout_val)
            if stderr_val:
                stderr_buffer.append(stderr_val)
            
            for line in stdout_val.strip().split("\n"):
                if line:
                    session.output.append(line)
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
    except SyntaxError:
        try:
            exec(code, session.variables)
            stderr_buffer.append("Code executed (no output)")
        except Exception as e:
            stderr_buffer.append(str(e))
    except Exception as e:
        stderr_buffer.append(str(e))
    
    return "\n".join(stdout_buffer), "\n".join(stderr_buffer)


async def _execute_javascript(session: REPLSession, code: str) -> tuple[str, str]:
    return "", "JavaScript REPL not implemented - requires Node.js"


async def _repl_execute(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    command = args.get("command", "")
    session_id = args.get("session_id")
    language = args.get("language", "python")
    code = args.get("code", "")
    create_new = args.get("create_new", False)
    
    if command == "create" or create_new:
        session = await create_session(language)
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "session_id": session.session_id,
                "language": session.language,
                "message": f"REPL session created with ID: {session.session_id}",
            }),
            is_error=False,
        )
    
    if command == "list":
        async with _session_lock:
            active_sessions = [
                {
                    "session_id": s.session_id,
                    "language": s.language,
                    "status": s.status,
                    "history_length": len(s.history),
                }
                for s in _sessions.values()
                if s.status == "active"
            ]
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "sessions": active_sessions,
            }),
            is_error=False,
        )
    
    if command == "history" and session_id:
        session = await get_session(session_id)
        if not session:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Session {session_id} not found",
                is_error=True,
            )
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "session_id": session_id,
                "history": session.history,
                "output": session.output,
            }),
            is_error=False,
        )
    
    if command == "close" and session_id:
        async with _session_lock:
            if session_id in _sessions:
                _sessions[session_id].status = "closed"
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=json.dumps({
                        "success": True,
                        "message": f"Session {session_id} closed",
                    }),
                    is_error=False,
                )
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Session {session_id} not found",
            is_error=True,
        )
    
    if code:
        if not session_id:
            session = await create_session(language)
            session_id = session.session_id
        
        session = await get_session(session_id)
        if not session:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Session {session_id} not found",
                is_error=True,
            )
        
        stdout, stderr = await execute_code(session_id, code)
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "session_id": session_id,
                "stdout": stdout,
                "stderr": stderr,
                "history_length": len(session.history),
            }),
            is_error=bool(stderr),
        )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="Error: Invalid command. Use command: 'create', 'list', 'history', 'close', or provide code to execute.",
        is_error=True,
    )


REPL_TOOL = ToolDef(
    name=TOOL_NAME,
    description="Interactive REPL (Read-Eval-Print Loop) for exploratory programming in Python or JavaScript",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["create", "list", "history", "close"],
                "description": "REPL command: create (new session), list (show sessions), history (session history), close (end session)",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for continuing a REPL session",
            },
            "language": {
                "type": "string",
                "enum": ["python", "javascript"],
                "description": "Programming language for the REPL",
            },
            "code": {
                "type": "string",
                "description": "Code to execute in the REPL",
            },
            "create_new": {
                "type": "boolean",
                "description": "Create a new REPL session",
            },
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_repl_execute,
)


__all__ = ["REPL_TOOL", "REPLSession", "create_session", "get_session", "execute_code"]
