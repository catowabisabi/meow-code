"""Comprehensive Python permissions system - bridging gap with TypeScript permissions/"""
import re
import os
import fnmatch
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class PermissionDecisionReason(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    BYPASS = "bypass"
    RULE = "rule"
    SANDBOX = "sandbox"


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


PROTECTED_PATHS = {
    "/", "/etc", "/usr", "/bin", "/sbin", "/var", "/srv", "/proc", "/sys",
    "C:\\", "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
}

PROTECTED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r":\s*{\s*.*\s*:\s*}",
    r"curl\s+\|\\?\s*sh",
    r"wget\s+.*\|\\?\s*sh",
]


@dataclass
class Redirect:
    op: str
    target: str
    fd: Optional[int] = None


@dataclass
class SimpleCommand:
    argv: List[str]
    env_vars: List[Dict[str, str]]
    redirects: List[Redirect]
    text: str


@dataclass
class PathCheckResult:
    allowed: bool
    decision_reason: Optional[PermissionDecisionReason] = None


@dataclass
class ResolvedPathCheckResult(PathCheckResult):
    resolved_path: str = ""


def expand_tilde(path: str) -> str:
    if path == "~" or path.startswith("~/"):
        return str(Path.home()) + path[1:]
    if os.name == "nt" and path.startswith("~\\"):
        return str(Path.home()) + path[1:]
    return path


def contains_path_traversal(path: str) -> bool:
    normalized = os.path.normpath(path)
    return normalized != path and not normalized.startswith(path)


def get_glob_base_directory(path: str) -> str:
    glob_chars = set("*?[]{}")
    glob_index = -1
    for i, c in enumerate(path):
        if c in glob_chars:
            glob_index = i
            break
    
    if glob_index == -1:
        return path
    
    before_glob = path[:glob_index]
    last_sep = max(before_glob.rfind("/"), before_glob.rfind("\\")) if os.name == "nt" else before_glob.rfind("/")
    
    if last_sep == -1:
        return "."
    return before_glob[:last_sep] or "/"


def check_path_safety_for_auto_edit(path: str, cwd: str) -> PathCheckResult:
    expanded = expand_tilde(path)
    resolved = str(Path(expanded).resolve())
    
    for protected in PROTECTED_PATHS:
        if resolved == protected or resolved.startswith(protected + os.sep):
            return PathCheckResult(False, PermissionDecisionReason.DENIED)
    
    return PathCheckResult(True, PermissionDecisionReason.ALLOWED)


def check_readable_internal_path(path: str) -> bool:
    return True


def check_editable_internal_path(path: str) -> bool:
    return True


def path_in_working_path(path: str, working_path: str) -> bool:
    try:
        path_resolved = str(Path(path).resolve())
        working_resolved = str(Path(working_path).resolve())
        return path_resolved.startswith(working_resolved)
    except (OSError, RuntimeError):
        return False


def path_in_allowed_working_path(path: str, allowed_paths: List[str]) -> bool:
    try:
        path_resolved = str(Path(path).resolve())
        for allowed in allowed_paths:
            allowed_resolved = str(Path(allowed).resolve())
            if path_resolved.startswith(allowed_resolved):
                return True
        return False
    except (OSError, RuntimeError):
        return False


def matching_rule_for_input(
    input_path: str,
    rules: List[Dict[str, str]]
) -> Optional[Dict[str, str]]:
    for rule in rules:
        pattern = rule.get("pattern", "")
        if _match_path_pattern(input_path, pattern):
            return rule
    return None


def _match_path_pattern(path: str, pattern: str) -> bool:
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return path.startswith(prefix)
    elif "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(path, pattern)
    else:
        return path == pattern


def check_command_safety(command: str) -> Tuple[bool, str]:
    lower_cmd = command.lower().strip()
    
    for pattern in PROTECTED_PATTERNS:
        if re.search(pattern, lower_cmd):
            return False, f"Command matches blocked pattern: {pattern}"
    
    dangerous_commands = {
        "sudo", "su", "passwd", "useradd", "userdel", "usermod",
        "shutdown", "reboot", "halt", "poweroff", "telinit",
        "mkfs", "fdisk", "parted",
    }
    
    first_word = lower_cmd.split()[0] if lower_cmd.split() else ""
    if first_word in dangerous_commands:
        return False, f"Dangerous command: {first_word}"
    
    return True, ""


def check_shell_rule_matching(
    command: str,
    rules: List[Dict[str, str]]
) -> Optional[Dict[str, str]]:
    command_lower = command.lower().strip()
    
    for rule in rules:
        pattern = rule.get("pattern", "").lower()
        
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


def classify_with_yolo(command: str) -> str:
    safe_indicators = [
        "ls", "pwd", "echo", "cat", "head", "tail", "grep", "find",
        "git status", "git log", "git diff", "git show",
        "whoami", "date", "time", "which", "where", "npm --version",
        "python --version", "node --version",
    ]
    
    dangerous_indicators = [
        "rm -rf", "mkfs", "dd if=", "shutdown", "reboot",
        "curl | sh", "wget | sh", ":(){:|:&};:",
        "> /dev/", "2> /dev/", "&& rm", "; rm",
    ]
    
    lower_cmd = command.lower().strip()
    
    for indicator in dangerous_indicators:
        if indicator in lower_cmd:
            return "deny"
    
    for indicator in safe_indicators:
        if indicator in lower_cmd:
            return "allow"
    
    return "ask"


def validate_path(
    path: str,
    operation: str = "read",
    cwd: str = "."
) -> ResolvedPathCheckResult:
    expanded = expand_tilde(path)
    
    try:
        if not os.path.isabs(expanded):
            expanded = os.path.join(cwd, expanded)
        resolved = str(Path(expanded).resolve())
    except (OSError, RuntimeError):
        return ResolvedPathCheckResult(False, PermissionDecisionReason.DENIED, path)
    
    if operation == "write":
        for protected in PROTECTED_PATHS:
            if resolved == protected or resolved.startswith(protected + os.sep):
                return ResolvedPathCheckResult(False, PermissionDecisionReason.DENIED, resolved)
    
    return ResolvedPathCheckResult(True, PermissionDecisionReason.ALLOWED, resolved)


class PermissionManager:
    def __init__(self):
        self.always_allow_rules: Dict[str, List[Dict[str, str]]] = {}
        self.always_deny_rules: Dict[str, List[Dict[str, str]]] = {}
        self.always_ask_rules: Dict[str, List[Dict[str, str]]] = {}
        self.additional_directories: List[str] = []
        self.bypass_available: bool = True
    
    def add_rule(self, tool: str, pattern: str, behavior: str, source: str = "user") -> None:
        rule = {"pattern": pattern, "tool": tool, "behavior": behavior, "source": source}
        
        if behavior == "allow":
            self.always_allow_rules.setdefault(tool, []).append(rule)
        elif behavior == "deny":
            self.always_deny_rules.setdefault(tool, []).append(rule)
        elif behavior == "ask":
            self.always_ask_rules.setdefault(tool, []).append(rule)
    
    def remove_rule(self, tool: str, pattern: str) -> bool:
        for rules in [self.always_allow_rules, self.always_deny_rules, self.always_ask_rules]:
            if tool in rules:
                for i, rule in enumerate(rules[tool]):
                    if rule["pattern"] == pattern:
                        rules[tool].pop(i)
                        return True
        return False
    
    def check_shell(self, command: str) -> Tuple[bool, str]:
        if self.always_deny_rules.get("shell"):
            matched = check_shell_rule_matching(command, self.always_deny_rules["shell"])
            if matched:
                return False, f"Denied by rule: {matched['pattern']}"
        
        if self.always_allow_rules.get("shell"):
            matched = check_shell_rule_matching(command, self.always_allow_rules["shell"])
            if matched:
                return True, f"Allowed by rule: {matched['pattern']}"
        
        is_safe, reason = check_command_safety(command)
        if is_safe:
            return True, "allowed"
        
        return False, reason
    
    def check_path(self, path: str, operation: str = "read") -> PathCheckResult:
        if operation == "write":
            if self.always_deny_rules.get("write"):
                matched = matching_rule_for_input(path, self.always_deny_rules["write"])
                if matched:
                    return PathCheckResult(False, PermissionDecisionReason.DENIED)
            
            if self.always_allow_rules.get("write"):
                matched = matching_rule_for_input(path, self.always_allow_rules["write"])
                if matched:
                    return PathCheckResult(True, PermissionDecisionReason.RULE)
        
        return check_path_safety_for_auto_edit(path, os.getcwd())
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        if "permissions" in data:
            perms = data["permissions"]
            
            for rule in perms.get("allow", []):
                self.add_rule(rule.get("tool", "shell"), rule.get("pattern", ""), "allow")
            
            for rule in perms.get("deny", []):
                self.add_rule(rule.get("tool", "shell"), rule.get("pattern", ""), "deny")
            
            for rule in perms.get("ask", []):
                self.add_rule(rule.get("tool", "shell"), rule.get("pattern", ""), "ask")
            
            self.additional_directories = perms.get("additionalDirectories", [])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "permissions": {
                "allow": self.always_allow_rules.get("shell", []),
                "deny": self.always_deny_rules.get("shell", []),
                "ask": self.always_ask_rules.get("shell", []),
                "additionalDirectories": self.additional_directories,
            }
        }


_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
