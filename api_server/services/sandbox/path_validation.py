"""
Path validation module for filesystem access control.

Implements path access control similar to the TypeScript implementation:
- Path command extraction (cd, ls, find, etc.)
- Path validation against allowed directories
- Redirection validation
"""

import os
import re
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class FileOperationType(Enum):
    """Type of file operation for validation."""
    READ = "read"
    WRITE = "write"
    CREATE = "create"


# Path commands that need validation
PATH_COMMANDS = {
    "cd", "ls", "find", "mkdir", "touch", "rm", "rmdir",
    "mv", "cp", "cat", "head", "tail", "sort", "uniq",
    "wc", "cut", "paste", "column", "tr", "file", "stat",
    "diff", "awk", "strings", "hexdump", "od", "base64",
    "nl", "grep", "rg", "sed", "git", "jq",
    "sha256sum", "sha1sum", "md5sum",
}

# Commands that modify filesystem (write operations)
WRITE_COMMANDS = {
    "mkdir", "touch", "rm", "rmdir", "mv", "cp", "sed",
}

# Commands that create new files/directories
CREATE_COMMANDS = {"mkdir", "touch"}


@dataclass
class PathValidationResult:
    """Result of path validation."""
    allowed: bool
    resolved_path: Optional[str] = None
    decision_reason: Optional[dict] = None
    message: Optional[str] = None


def expand_tilde(path: str) -> str:
    """Expand ~ to user's home directory."""
    if path.startswith("~"):
        return os.path.expanduser(path)
    return path


def is_dangerous_removal_path(path: str) -> bool:
    """
    Check if path is a dangerous removal target.
    
    Returns True for critical system paths that should require
    explicit user approval.
    """
    path = expand_tilde(path)
    
    if not os.path.isabs(path):
        return False
    
    dangerous_paths = [
        "/",
        "/bin",
        "/sbin",
        "/usr",
        "/lib",
        "/lib64",
        "/etc",
        "/var",
        "/tmp",
        "/usr/bin",
        "/usr/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        "/opt",
        "/home",
        "/root",
    ]
    
    # Check if path is or is under a dangerous path
    for dangerous in dangerous_paths:
        if path == dangerous or path.startswith(dangerous + "/"):
            return True
    
    return False


def get_directory_for_path(path: str) -> str:
    """Get the directory containing a path."""
    if os.path.isdir(path):
        return path
    return os.path.dirname(path)


def format_directory_list(directories: list) -> str:
    """Format directory list for error messages."""
    return ", ".join(f"'{d}'" for d in directories)


def filter_out_flags(args: list) -> list:
    """
    Filter out flag arguments, correctly handling -- end-of-options.
    
    SECURITY: Must handle POSIX `--` delimiter to catch paths like `-/../foo`.
    """
    result = []
    after_double_dash = False
    
    for arg in args:
        if after_double_dash:
            result.append(arg)
        elif arg == "--":
            after_double_dash = True
        elif not arg.startswith("-"):
            result.append(arg)
    
    return result


def extract_paths_cd(args: list) -> list:
    """Extract paths from cd command."""
    return [os.path.expanduser(" ".join(args))] if args else [os.path.expanduser("~")]


def extract_paths_ls(args: list) -> list:
    """Extract paths from ls command."""
    paths = filter_out_flags(args)
    return paths if paths else ["."]


def extract_paths_find(args: list) -> list:
    """Extract paths from find command."""
    paths = []
    path_flags = {
        "-newer", "-anewer", "-cnewer", "-mnewer",
        "-samefile", "-path", "-wholename",
        "-ilname", "-lname", "-ipath", "-iwholename",
    }
    
    found_non_global_flag = False
    after_double_dash = False
    
    for i, arg in enumerate(args):
        if after_double_dash:
            paths.append(arg)
            continue
        
        if arg == "--":
            after_double_dash = True
            continue
        
        if arg.startswith("-"):
            if arg in {"-H", "-L", "-P"}:
                continue
            
            found_non_global_flag = True
            
            if arg in path_flags and i + 1 < len(args):
                paths.append(args[i + 1])
            continue
        
        if not found_non_global_flag:
            paths.append(arg)
    
    return paths if paths else ["."]


def extract_paths_grep(args: list) -> list:
    """Extract paths from grep/rg commands."""
    paths = []
    pattern_found = False
    after_double_dash = False
    
    for i, arg in enumerate(args):
        if after_double_dash:
            paths.append(arg)
            continue
        
        if arg == "--":
            after_double_dash = True
            continue
        
        if arg.startswith("-"):
            flag = arg.split("=")[0]
            if flag in {"-e", "--regexp", "-f", "--file", "--include", "--exclude"}:
                pattern_found = True
            continue
        
        if not pattern_found:
            pattern_found = True
            continue
        
        paths.append(arg)
    
    return paths if paths else ["."]


def extract_paths_sed(args: list) -> list:
    """Extract paths from sed command."""
    paths = []
    skip_next = False
    script_found = False
    after_double_dash = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        
        if after_double_dash:
            paths.append(arg)
            continue
        
        if arg == "--":
            after_double_dash = True
            continue
        
        if not after_double_dash and arg.startswith("-"):
            if arg in {"-f", "--file"}:
                if i + 1 < len(args):
                    paths.append(args[i + 1])
                skip_next = True
            script_found = True
            continue
        
        if not script_found:
            script_found = True
            continue
        
        paths.append(arg)
    
    return paths


def extract_paths_rm(args: list) -> list:
    """Extract paths from rm/rmdir commands."""
    return filter_out_flags(args)


def extract_paths_git(args: list) -> list:
    """Extract paths from git command."""
    if args and args[0] == "diff":
        if "--no-index" in args:
            return filter_out_flags(args[1:])[:2]
    return []


# Path extractor functions for each command
PATH_EXTRACTORS = {
    "cd": extract_paths_cd,
    "ls": extract_paths_ls,
    "find": extract_paths_find,
    "grep": extract_paths_grep,
    "rg": extract_paths_grep,
    "sed": extract_paths_sed,
    "rm": extract_paths_rm,
    "rmdir": extract_paths_rm,
    "mkdir": extract_paths_rm,
    "touch": extract_paths_rm,
    "mv": extract_paths_rm,
    "cp": extract_paths_rm,
    "cat": extract_paths_rm,
    "head": extract_paths_rm,
    "tail": extract_paths_rm,
    "git": extract_paths_git,
}

# Default extractors for simple commands
def default_path_extractor(args: list) -> list:
    """Default path extraction for simple commands."""
    return filter_out_flags(args)


# Fill in extractors for remaining commands
for cmd in PATH_COMMANDS:
    if cmd not in PATH_EXTRACTORS:
        PATH_EXTRACTORS[cmd] = default_path_extractor


def get_command_operation_type(command: str) -> FileOperationType:
    """Determine the operation type for a command."""
    if command in WRITE_COMMANDS:
        return FileOperationType.WRITE
    if command in CREATE_COMMANDS:
        return FileOperationType.CREATE
    return FileOperationType.READ


def validate_path(
    path: str,
    cwd: str,
    allowed_directories: list,
    denied_directories: list,
    operation_type: FileOperationType,
) -> PathValidationResult:
    """
    Validate a single path against allowed/denied directories.
    
    Args:
        path: Path to validate
        cwd: Current working directory
        allowed_directories: List of allowed directory paths
        denied_directories: List of denied directory paths
        operation_type: Type of operation (read/write/create)
    
    Returns:
        PathValidationResult with allowed status and details
    """
    if not path:
        return PathValidationResult(allowed=True)
    
    # Expand ~ and resolve to absolute path
    clean_path = expand_tilde(path)
    if not os.path.isabs(clean_path):
        clean_path = os.path.join(cwd, clean_path)
    
    resolved = os.path.normpath(clean_path)
    
    # Check against denied directories first
    for denied in denied_directories:
        denied_norm = os.path.normpath(os.path.expanduser(denied))
        if resolved.startswith(denied_norm + os.sep) or resolved == denied_norm:
            return PathValidationResult(
                allowed=False,
                resolved_path=resolved,
                decision_reason={"type": "rule", "reason": f"Path in denied directory: {denied}"},
                message=f"Path '{resolved}' is in a denied directory",
            )
    
    # Check against allowed directories
    if allowed_directories:
        allowed = False
        for allowed_dir in allowed_directories:
            allowed_dir_norm = os.path.normpath(os.path.expanduser(allowed_dir))
            if resolved.startswith(allowed_dir_norm + os.sep) or resolved == allowed_dir_norm:
                allowed = True
                break
        
        if not allowed:
            return PathValidationResult(
                allowed=False,
                resolved_path=resolved,
                decision_reason={"type": "other", "reason": "Path not in allowed directories"},
                message=f"Path '{resolved}' is not in allowed directories",
            )
    
    return PathValidationResult(
        allowed=True,
        resolved_path=resolved,
    )


def validate_output_redirection(
    target: str,
    cwd: str,
    allowed_directories: list,
    denied_directories: list,
) -> PathValidationResult:
    """Validate an output redirection target."""
    # /dev/null is always safe
    if target == "/dev/null":
        return PathValidationResult(allowed=True)
    
    return validate_path(
        target, cwd, allowed_directories, denied_directories, FileOperationType.CREATE
    )


def validate_command_paths(
    command: str,
    cwd: str,
    allowed_directories: list,
    denied_directories: list,
    compound_has_cd: bool = False,
) -> dict:
    """
    Validate all paths in a command.
    
    Returns dict with:
    - allowed: bool
    - message: str
    - blocked_path: Optional[str]
    - decision_reason: Optional[dict]
    """
    try:
        parts = shlex.split(command)
    except ValueError:
        return {
            "allowed": True,
            "message": "Could not parse command",
        }
    
    if not parts:
        return {
            "allowed": True,
            "message": "Empty command",
        }
    
    base_cmd = parts[0]
    
    if base_cmd not in PATH_COMMANDS:
        return {
            "allowed": True,
            "message": f"Command '{base_cmd}' is not a path-restricted command",
        }
    
    extractor = PATH_EXTRACTORS.get(base_cmd, default_path_extractor)
    paths = extractor(parts[1:])
    
    operation_type = get_command_operation_type(base_cmd)
    
    # Block write operations in compound commands containing cd
    if compound_has_cd and operation_type != FileOperationType.READ:
        return {
            "allowed": False,
            "message": "Commands that change directories and perform write operations require explicit approval",
            "decision_reason": {
                "type": "other",
                "reason": "Compound command contains cd with write operation",
            },
        }
    
    for path in paths:
        result = validate_path(
            path, cwd, allowed_directories, denied_directories, operation_type
        )
        
        if not result.allowed:
            return {
                "allowed": False,
                "message": result.message,
                "blocked_path": result.resolved_path,
                "decision_reason": result.decision_reason,
            }
    
    return {
        "allowed": True,
        "message": f"All paths validated for {base_cmd}",
    }


def check_path_constraints(
    command: str,
    cwd: str,
    allowed_directories: list,
    denied_directories: list,
    compound_has_cd: bool = False,
) -> dict:
    """
    Main path validation entry point.
    
    Validates filesystem access for shell commands.
    Returns dict with permission-like result.
    """
    # Check for process substitution
    if re.search(r">\s*\(|<\s*\(", command):
        return {
            "allowed": False,
            "message": "Process substitution (>(...) or <(...)) requires manual approval",
            "decision_reason": {
                "type": "other",
                "reason": "Process substitution requires manual approval",
            },
        }
    
    # Validate command paths
    result = validate_command_paths(
        command, cwd, allowed_directories, denied_directories, compound_has_cd
    )
    
    if not result["allowed"]:
        return {
            "behavior": "ask",
            "message": result["message"],
            "blocked_path": result.get("blocked_path"),
            "decision_reason": result.get("decision_reason"),
        }
    
    return {
        "behavior": "passthrough",
        "message": result["message"],
    }
