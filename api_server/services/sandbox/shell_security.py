"""
Shell security integration module.

Integrates bash security validation with the existing sandbox system,
providing comprehensive security checks for shell commands.
"""

import os
from typing import Optional

from ..sandbox.config import SandboxConfig
from .bash_security import is_command_safe
from .dangerous_command import check_destructive_command
from .path_validation import check_path_constraints
from .readonly_validation import validate_readonly_command


def validate_shell_command(
    command: str,
    config: SandboxConfig,
    cwd: Optional[str] = None,
) -> dict:
    """
    Comprehensive shell command validation.
    
    Combines:
    - Command security validation
    - Path access control
    - Read-only validation
    - Destructive command detection
    
    Returns dict with:
    - allowed: bool
    - behavior: str (allow/ask/deny/passthrough)
    - message: str
    - decision_reason: dict
    """
    if not command or not command.strip():
        return {
            "allowed": True,
            "behavior": "allow",
            "message": "Empty command is safe",
            "decision_reason": {"type": "other", "reason": "Empty command is safe"},
        }
    
    working_dir = cwd or os.getcwd()
    
    security_result = is_command_safe(command)
    if not security_result:
        return {
            "allowed": False,
            "behavior": "ask",
            "message": "Command contains security concerns",
            "decision_reason": {
                "type": "other",
                "reason": "Security validation failed",
            },
        }
    
    destructive = check_destructive_command(command)
    if destructive["is_destructive"]:
        return {
            "allowed": False,
            "behavior": "ask",
            "message": destructive["reason"],
            "decision_reason": {
                "type": "other",
                "reason": destructive["reason"],
            },
        }
    
    readonly_result = validate_readonly_command(command)
    if readonly_result.is_readonly:
        return {
            "allowed": True,
            "behavior": "allow",
            "message": readonly_result.message,
            "decision_reason": {
                "type": "other",
                "reason": "Read-only command is allowed",
            },
        }
    
    path_result = check_path_constraints(
        command,
        working_dir,
        config.filesystem.allow_read,
        config.filesystem.deny_read,
    )
    
    if path_result.get("behavior") == "ask":
        return {
            "allowed": False,
            "behavior": "ask",
            "message": path_result["message"],
            "decision_reason": path_result.get(
                "decision_reason",
                {"type": "other", "reason": "Path validation failed"},
            ),
            "blocked_path": path_result.get("blocked_path"),
        }
    
    return {
        "allowed": True,
        "behavior": "passthrough",
        "message": "Command passed validation",
        "decision_reason": {"type": "other", "reason": "Validation complete"},
    }


def is_command_allowed(command: str, config: SandboxConfig) -> bool:
    """Simple boolean check if command is allowed."""
    result = validate_shell_command(command, config)
    return result["allowed"]
