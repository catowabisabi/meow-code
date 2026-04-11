import re
from dataclasses import dataclass
from typing import Callable, Awaitable

DENYLIST_PATTERNS = [
    r"rm\s+-rf\s+/",
    r":\s*{\s*.*\s*:\s*}",
    r"curl\s+\|\\?\s*sh",
    r"wget\s+.*\|\\?\s*sh",
    r"shutdown",
    r"reboot",
    r"init\s+6",
    r"mkfs",
    r"dd\s+if=.*of=/dev/",
]

SANDBOX_BLOCKED_COMMANDS = {
    "sudo", "su", "passwd", "useradd", "userdel", "usermod",
    "shutdown", "reboot", "halt", "poweroff", "telinit",
    "mount", "umount", "fsck", "mkfs", "fdisk", "parted",
    "iptables", "ip", "ifconfig", "route", "netstat",
}


@dataclass
class PermissionDecision:
    behavior: str
    message: str | None = None
    updated_input: dict | None = None


@dataclass 
class PermissionContext:
    request_permission: Callable[[str, dict, str], Awaitable[bool]] | None = None
    tool_permission_context: dict | None = None


def check_command_safety(command: str) -> tuple[bool, str]:
    lower_cmd = command.lower().strip()
    
    if any(re.search(pattern, lower_cmd) for pattern in DENYLIST_PATTERNS):
        return False, "Command matches blocked pattern"
    
    first_word = lower_cmd.split()[0] if lower_cmd.split() else ""
    if first_word in SANDBOX_BLOCKED_COMMANDS:
        return False, f"Command '{first_word}' is blocked"
    
    return True, ""


def strip_safe_wrappers(command: str) -> str:
    patterns_to_strip = [
        r"^\s*&&\s*",
        r"^\s*\|\s*",
        r"^\s*;\s*",
        r"^\s*2>&1\s*",
        r"^\s*>\s*/dev/null\s*",
        r"^\s*>\s*null\s*",
        r"^\s*--\s*",
    ]
    
    result = command
    for pattern in patterns_to_strip:
        result = re.sub(pattern, "", result)
    
    return result.strip()


async def has_permission(
    command: str,
    ctx: PermissionContext | None = None,
    request_permission: Callable[[str, dict, str], Awaitable[bool]] | None = None,
) -> PermissionDecision:
    is_safe, reason = check_command_safety(command)
    
    if is_safe:
        return PermissionDecision(behavior="allow")
    
    if request_permission:
        allowed = await request_permission("shell", {"command": command}, reason)
        if allowed:
            return PermissionDecision(behavior="allow")
    
    return PermissionDecision(behavior="deny", message=f"Permission denied: {reason}")
