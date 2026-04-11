"""
Tool permissions for auto-memory operations.

Provides a can_use_tool function that restricts tools to:
- Read/Grep/Glob: unrestricted
- Bash: read-only commands only
- Edit/Write: only within the memory directory
"""
import re
from pathlib import Path
from typing import Any, Callable, Dict


FILE_READ_TOOL_NAME = "FileRead"
GREP_TOOL_NAME = "Grep"
GLOB_TOOL_NAME = "Glob"
BASH_TOOL_NAME = "Bash"
FILE_EDIT_TOOL_NAME = "FileEdit"
FILE_WRITE_TOOL_NAME = "FileWrite"

READ_ONLY_BASH_PATTERNS = [
    r"^ls",
    r"^pwd",
    r"^cat\s",
    r"^head\s",
    r"^tail\s",
    r"^grep\s",
    r"^find\s",
    r"^diff\s",
    r"^git\s+status",
    r"^git\s+log",
    r"^git\s+diff",
    r"^git\s+show",
]


def _is_read_only_bash(input_data: Dict[str, Any]) -> bool:
    """Check if a bash command is read-only."""
    command = input_data.get("command", "")
    if not isinstance(command, str):
        return False
    
    for pattern in READ_ONLY_BASH_PATTERNS:
        if re.match(pattern, command.strip()):
            return True
    
    if "read" in command.lower() or "list" in command.lower():
        return True
    
    write_indicators = [" > ", " >> ", "| grep", "tee ", "write("]
    for indicator in write_indicators:
        if indicator in command:
            return False
    
    return False


def _is_path_in_dir(file_path: str, memory_dir: str) -> bool:
    """Check if a file path is within the memory directory."""
    if not file_path or not memory_dir:
        return False
    
    try:
        file_p = Path(file_path).resolve()
        mem_p = Path(memory_dir).resolve()
        return str(file_p).startswith(str(mem_p))
    except (OSError, ValueError):
        return False


def create_auto_mem_can_use_tool(
    memory_dir: str,
) -> Callable[[Any, Dict[str, Any]], Dict[str, Any]]:
    """
    Create a canUseTool function for auto-memory operations.
    
    This adapts the existing extract_memories function but with
    additional restrictions for the auto-dream context.
    
    Args:
        memory_dir: The memory directory path.
    
    Returns:
        A canUseTool function.
    """
    def can_use_tool(tool: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = getattr(tool, 'name', str(tool))
        
        if tool_name in (FILE_READ_TOOL_NAME, GREP_TOOL_NAME, GLOB_TOOL_NAME):
            return {"behavior": "allow", "updated_input": input_data}
        
        if tool_name == BASH_TOOL_NAME:
            if _is_read_only_bash(input_data):
                return {"behavior": "allow", "updated_input": input_data}
            return {
                "behavior": "deny",
                "message": "Only read-only shell commands are permitted in auto dream context",
                "decision_reason": {"type": "other", "reason": "write bash command not allowed"},
            }
        
        if tool_name in (FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME):
            file_path = input_data.get("file_path", "")
            if isinstance(file_path, str) and _is_path_in_dir(file_path, memory_dir):
                return {"behavior": "allow", "updated_input": input_data}
            return {
                "behavior": "deny",
                "message": f"Only file operations within {memory_dir} are permitted",
                "decision_reason": {"type": "other", "reason": "path outside memory dir"},
            }
        
        return {
            "behavior": "deny",
            "message": f"Tool {tool_name} is not permitted in auto dream context",
            "decision_reason": {"type": "other", "reason": "tool not allowed"},
        }
    
    return can_use_tool
