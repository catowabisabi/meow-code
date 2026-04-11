from ..tools.types import ToolDef, ToolContext
from .execute import execute_agent_tool


def agent_tool_def() -> ToolDef:
    return ToolDef(
        name="agent",
        description="Spawn and manage sub-agents",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["spawn", "status", "send_message", "terminate", "list"],
                    "description": "The operation to perform",
                },
                "name": {"type": "string", "description": "Name for the spawned agent"},
                "agent_type": {
                    "type": "string",
                    "description": "Type of agent to spawn (e.g., 'general', 'explore', 'plan')",
                },
                "model": {"type": "string", "description": "Optional model override"},
                "prompt": {"type": "string", "description": "The task prompt for the agent"},
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tool names to enable for this agent",
                },
                "max_turns": {"type": "integer", "description": "Maximum number of turns"},
                "cwd": {"type": "string", "description": "Working directory for the agent"},
                "worktree_path": {
                    "type": "string",
                    "description": "Git worktree path for isolation",
                },
                "description": {
                    "type": "string",
                    "description": "A short description of the task",
                },
                "agent_id": {"type": "string", "description": "Agent ID for status/terminate"},
                "message": {
                    "type": "object",
                    "description": "Message to send to running agent",
                },
            },
            "required": ["operation"],
        },
        execute=execute_agent_tool,
    )
