import re
from typing import Tuple

from .canonical import (
    PS_SEARCH_COMMANDS,
    PS_READ_COMMANDS,
    PS_SEMANTIC_NEUTRAL_COMMANDS,
    resolve_to_canonical,
)
from .types import CommandCategory

WRITE_COMMANDS: set[str] = {
    "set-content",
    "add-content",
    "out-file",
    "new-item",
    "copy-item",
    "move-item",
    "rename-item",
    "remove-item",
    "clear-item",
    "clear-content",
    "set-item",
}

MODIFY_COMMANDS: set[str] = {
    "set-location",
    "push-location",
    "pop-location",
    "set-item",
    "clear-item",
    "invoke-expression",
    "invoke-webrequest",
    "invoke-restmethod",
    "start-process",
    "stop-process",
    "restart-service",
    "start-service",
    "stop-service",
}

EXECUTE_COMMANDS: set[str] = {
    "start-process",
    "invoke-expression",
    "invoke-command",
    "iex",
}


def classify_command(command: str) -> CommandCategory:
    if not command or not command.strip():
        return CommandCategory.UNKNOWN

    parts = re.split(r"\s*[;|]\s*", command.strip())
    if not parts:
        return CommandCategory.UNKNOWN

    has_search = False
    has_read = False
    has_non_neutral = False

    for part in parts:
        part = part.strip()
        if not part:
            continue

        tokens = part.split()
        if not tokens:
            continue

        base_command = tokens[0]
        canonical = resolve_to_canonical(base_command)

        if canonical in PS_SEMANTIC_NEUTRAL_COMMANDS:
            continue

        has_non_neutral = True

        if canonical in PS_SEARCH_COMMANDS:
            has_search = True
        elif canonical in PS_READ_COMMANDS:
            has_read = True
        elif canonical in WRITE_COMMANDS:
            return CommandCategory.WRITE
        elif canonical in MODIFY_COMMANDS:
            return CommandCategory.MODIFY
        elif canonical in EXECUTE_COMMANDS:
            return CommandCategory.EXECUTE
        else:
            return CommandCategory.UNKNOWN

    if not has_non_neutral:
        return CommandCategory.UNKNOWN

    if has_search:
        return CommandCategory.SEARCH
    if has_read:
        return CommandCategory.READ

    return CommandCategory.UNKNOWN


def is_read_only_command(command: str) -> bool:
    category = classify_command(command)
    return category in (CommandCategory.SEARCH, CommandCategory.READ)


def has_sync_security_concerns(command: str) -> bool | str:
    if not command or not command.strip():
        return False

    trimmed = command.strip()

    if re.search(r"\$\(", trimmed):
        return "Command contains subexpression $(...) which can execute arbitrary code"

    if re.search(r"(?:^|[^\w.])@[\w]+", trimmed):
        return "Command contains splatting @variable which can pass arbitrary parameters"

    if re.search(r"\.\w+\s*\(", trimmed):
        return "Command contains member invocation .Method() which can call arbitrary .NET methods"

    if re.search(r"\$\w+\s*[+\-*/]?=", trimmed):
        return "Command contains assignment which can modify state"

    if re.search(r"--%", trimmed):
        return "Command contains stop-parsing symbol --% which passes everything raw to native commands"

    if re.search(r"\\\\", trimmed) or re.search(r"(?<!:)\/\/", trimmed):
        return "Command contains UNC path which can trigger network requests and leak credentials"

    if re.search(r"::", trimmed):
        return "Command contains static method call :: which can invoke arbitrary .NET methods"

    dangerous_disk_patterns = [
        (r"format-volume\s+-[a-z]+\s+-[a-z]+\s*\$?\w*:?\\?", "format-volume with disk access"),
        (r"clear-disk\s+", "clear-disk command"),
        (r"remove-item\s+.*\s+-recurse\s+.*[A-Z]:\\(windows|system)", "remove-item targeting system directories"),
        (r"\$\.PSDrive\s*=\s*\$null", "PSDrive removal"),
    ]

    for pattern, description in dangerous_disk_patterns:
        if re.search(pattern, trimmed, re.IGNORECASE):
            return f"Command contains dangerous pattern: {description}"

    return False