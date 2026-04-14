"""Enhanced permissions system - bridging gap with TypeScript permissions.ts"""
import re
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional, List, Dict, Any, Tuple
from enum import Enum
from pathlib import Path


class PermissionMode(Enum):
    DEFAULT = "default"
    ASK = "ask"
    BYPASS = "bypass"
    RESTRICTED = "restricted"


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionDecision:
    behavior: PermissionBehavior
    message: Optional[str] = None
    updated_input: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


@dataclass
class PermissionRule:
    pattern: str
    tool: str
    behavior: PermissionBehavior
    source: str = "user"
    created_at: Optional[str] = None


@dataclass 
class PermissionContext:
    mode: PermissionMode = PermissionMode.DEFAULT
    always_allow_rules: Dict[str, List[PermissionRule]] = field(default_factory=dict)
    always_deny_rules: Dict[str, List[PermissionRule]] = field(default_factory=dict)
    always_ask_rules: Dict[str, List[PermissionRule]] = field(default_factory=dict)
    bypass_permissions_available: bool = False
    additional_working_directories: Dict[str, str] = field(default_factory=dict)


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

PROTECTED_PATHS = {
    "/", "/etc", "/usr", "/bin", "/sbin", "/var", "/srv",
    "C:\\", "C:\\Windows", "C:\\Program Files",
}


@dataclass
class PathValidationResult:
    is_valid: bool
    reason: Optional[str] = None
    is_read_only: bool = False


def validate_path_safety(
    path: str,
    context: PermissionContext,
    operation: str = "read",
) -> PathValidationResult:
    """
    Validate path safety for file operations.
    
    TypeScript equivalent: pathValidation.ts
    Python gap: Entire filesystem permission system missing.
    """
    path_obj = Path(path)
    
    try:
        resolved = path_obj.resolve()
    except (OSError, RuntimeError):
        return PathValidationResult(False, f"Cannot resolve path: {path}")
    
    resolved_str = str(resolved)
    
    if operation == "write":
        for protected in PROTECTED_PATHS:
            if resolved_str == protected or resolved_str.startswith(protected + "/"):
                return PathValidationResult(False, f"Cannot write to protected path: {protected}")
    
    return PathValidationResult(True, is_read_only=False)


def check_shell_rule_matching(command: str, rules: List[PermissionRule]) -> Optional[PermissionRule]:
    """
    Match command against permission rules.
    
    TypeScript equivalent: shellRuleMatching.ts
    Python gap: No Python equivalent - core permission rule parsing missing.
    """
    command_lower = command.lower().strip()
    
    for rule in rules:
        pattern = rule.pattern.lower()
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if command_lower.startswith(prefix):
                return rule
        elif pattern in command_lower:
            return rule
        
        try:
            if re.search(pattern, command_lower):
                return rule
        except re.error:
            pass
    
    return None


def check_command_safety(command: str) -> Tuple[bool, str]:
    """Basic command safety check with pattern matching."""
    lower_cmd = command.lower().strip()
    
    if any(re.search(pattern, lower_cmd) for pattern in DENYLIST_PATTERNS):
        return False, "Command matches blocked pattern"
    
    first_word = lower_cmd.split()[0] if lower_cmd.split() else ""
    if first_word in SANDBOX_BLOCKED_COMMANDS:
        return False, f"Command '{first_word}' is blocked"
    
    return True, ""


def strip_safe_wrappers(command: str) -> str:
    """Strip safe wrapper patterns from commands."""
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


@dataclass
class YoloClassifierResult:
    """Result from YOLO auto-mode classifier."""
    decision: PermissionBehavior
    confidence: float
    reason: str


def classify_with_yolo(command: str) -> YoloClassifierResult:
    """
    YOLO mode classifier for auto-approval of safe commands.
    
    TypeScript equivalent: yoloClassifier.ts
    Python gap: No Python YOLO auto-mode classifier equivalent.
    """
    safe_indicators = [
        "ls", "pwd", "echo", "cat", "head", "tail", "grep", "find",
        "git status", "git log", "git diff", "git show",
        "whoami", "date", "time", "which", "where",
    ]
    
    dangerous_indicators = [
        "rm -rf", "mkfs", "dd if=", "shutdown", "reboot",
        "curl | sh", "wget | sh", ":(){:|:&};:",
    ]
    
    lower_cmd = command.lower().strip()
    
    for indicator in dangerous_indicators:
        if indicator in lower_cmd:
            return YoloClassifierResult(PermissionBehavior.DENY, 0.9, f"Dangerous pattern: {indicator}")
    
    for indicator in safe_indicators:
        if indicator in lower_cmd:
            return YoloClassifierResult(PermissionBehavior.ALLOW, 0.8, f"Safe pattern: {indicator}")
    
    return YoloClassifierResult(PermissionBehavior.ASK, 0.5, "No clear classification")


@dataclass
class PermissionRequest:
    tool_name: str
    input_args: Dict[str, Any]
    description: str
    reason: str


async def has_permission(
    command: str,
    ctx: Optional[PermissionContext] = None,
    request_permission: Optional[Callable[[str, Dict[str, Any], str], Awaitable[bool]]] = None,
) -> PermissionDecision:
    """Main permission check entry point."""
    is_safe, reason = check_command_safety(command)
    
    if is_safe:
        if ctx and ctx.mode == PermissionMode.BYPASS:
            return PermissionDecision(PermissionBehavior.ALLOW, reason="bypass mode")
        return PermissionDecision(PermissionBehavior.ALLOW)
    
    if ctx and ctx.always_allow_rules.get("shell"):
        matched_rule = check_shell_rule_matching(command, ctx.always_allow_rules["shell"])
        if matched_rule:
            return PermissionDecision(PermissionBehavior.ALLOW, reason=f"Rule: {matched_rule.pattern}")
    
    if request_permission:
        allowed = await request_permission("shell", {"command": command}, reason)
        if allowed:
            return PermissionDecision(PermissionBehavior.ALLOW)
    
    return PermissionDecision(PermissionBehavior.DENY, message=f"Permission denied: {reason}")


class PermissionManager:
    """
    Central permission management with rule persistence.
    
    TypeScript equivalent: permissions.ts main export
    """
    def __init__(self):
        self.context = PermissionContext()
        self._rules: Dict[str, List[PermissionRule]] = {
            "shell": [],
            "edit": [],
            "read": [],
            "write": [],
        }
    
    def add_rule(self, tool: str, rule: PermissionRule) -> None:
        self._rules.setdefault(tool, []).append(rule)
        
        if rule.behavior == PermissionBehavior.ALLOW:
            self.context.always_allow_rules.setdefault(tool, []).append(rule)
        elif rule.behavior == PermissionBehavior.DENY:
            self.context.always_deny_rules.setdefault(tool, []).append(rule)
        elif rule.behavior == PermissionBehavior.ASK:
            self.context.always_ask_rules.setdefault(tool, []).append(rule)
    
    def remove_rule(self, tool: str, pattern: str) -> bool:
        rules = self._rules.get(tool, [])
        for i, rule in enumerate(rules):
            if rule.pattern == pattern:
                rules.pop(i)
                return True
        return False
    
    def get_rules(self, tool: str) -> List[PermissionRule]:
        return self._rules.get(tool, [])
    
    async def check(self, tool: str, input_args: Dict[str, Any], request_permission: Optional[Callable] = None) -> PermissionDecision:
        if tool == "shell" and "command" in input_args:
            return await has_permission(input_args["command"], self.context, request_permission)
        
        return PermissionDecision(PermissionBehavior.ALLOW)
    
    def set_mode(self, mode: PermissionMode) -> None:
        self.context.mode = mode
    
    def load_from_settings(self, settings: Dict[str, Any]) -> None:
        """Load permission rules from settings."""
        permission_rules = settings.get("permissionRules", [])
        for rule_data in permission_rules:
            rule = PermissionRule(
                pattern=rule_data.get("pattern", ""),
                tool=rule_data.get("tool", "shell"),
                behavior=PermissionBehavior[rule_data.get("behavior", "ALLOW").upper()],
                source=rule_data.get("source", "user"),
            )
            self.add_rule(rule.tool, rule)
