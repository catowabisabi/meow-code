"""
Dangerous command detection module.
"""

import re
import shlex
from typing import Optional


DANGEROUS_COMMANDS = {
    "rm", "rmdir", "mkfs", "dd", "fdisk", "parted",
    "format", "shutdown", "reboot", "halt", "poweroff",
    "init", "telinit", "systemctl", "service",
}


DESTRUCTIVE_PATTERNS = [
    (re.compile(r"rm\s+-rf\s+/{0,2}"), "recursive force removal"),
    (re.compile(r"dd\s+if="), "disk clone/write"),
    (re.compile(r":\(\)\{:|:&\}&"), "fork bomb"),
    (re.compile(r">\s*/dev/sda"), "direct disk write"),
]


def detect_dangerous_commands(command: str) -> tuple[bool, Optional[str]]:
    """
    Detect dangerous commands in shell input.
    
    Returns (is_dangerous, reason).
    """
    try:
        parts = shlex.split(command)
    except ValueError:
        return False, None
    
    if not parts:
        return False, None
    
    base_cmd = parts[0]
    
    if base_cmd in DANGEROUS_COMMANDS:
        return True, f"Dangerous command: {base_cmd}"
    
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return True, f"Destructive pattern: {reason}"
    
    return False, None


def check_destructive_command(command: str) -> dict:
    """
    Check if command matches destructive patterns.
    
    Returns dict with:
    - is_destructive: bool
    - reason: Optional[str]
    - behavior: str (ask/allow)
    """
    is_dangerous, reason = detect_dangerous_commands(command)
    
    if is_dangerous:
        return {
            "is_destructive": True,
            "reason": reason,
            "behavior": "ask",
        }
    
    return {
        "is_destructive": False,
        "reason": None,
        "behavior": "passthrough",
    }
