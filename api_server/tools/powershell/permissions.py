import re
from typing import Tuple

POWERSHELL_DANGEROUS_PATTERNS: list[Tuple[str, str]] = [
    (r"format-volume\s+", "format-volume modifies disk structure"),
    (r"clear-disk\s+", "clear-disk erases disk data"),
    (r"remove-item\s+.*\\\*\s+.*-recurse", "recursive remove-item can delete many files"),
    (r"remove-item\s+-[a-z]+\s+[A-Z]:\\", "remove-item targeting root directory"),
    (r"\$\.PSDrive\s*=\s*", "PSDrive manipulation"),
    (r"set-executionpolicy\s+bypass", "bypass execution policy"),
    (r"set-executionpolicy\s+unrestricted", "unrestricted execution policy"),
    (r"invoke-expression\s+.*\$\(", "invoke-expression with subexpression"),
    (r"invoke-webrequest\s+.*-uri\s+http", "web request can leak network information"),
    (r"invoke-restmethod\s+.*-uri\s+http", "REST method can leak network information"),
    (r"start-process\s+.*-verb\s+runas", "start-process with runas elevation"),
    (r"stop-computer\s+", "stop-computer shuts down the machine"),
    (r"restart-computer\s+", "restart-computer restarts the machine"),
    (r"shutdown\s+", "shutdown command"),
    (r"stop-process\s+.*-force", "force stop-process can cause data loss"),
    (r"kill\s+", "kill terminates processes"),
    (r"remove-module\s+.*-force", "force remove-module can break things"),
    (r"uninstall-module\s+", "uninstall-module removes PowerShell modules"),
    (r"register-psrepository\s+", "register-psrepository adds package sources"),
    (r"set-psbreakpoint\s+", "set-psbreakpoint modifies debugging state"),
]


def powershell_has_permission(command: str, dry_run: bool = False) -> Tuple[bool, str | None]:
    if not command or not command.strip():
        return (True, None)

    trimmed = command.strip()

    for pattern, reason in POWERSHELL_DANGEROUS_PATTERNS:
        if re.search(pattern, trimmed, re.IGNORECASE):
            if dry_run:
                return (True, None)
            return (False, reason)

    return (True, None)


def check_powershell_command(command: str) -> Tuple[bool, str | None]:
    return powershell_has_permission(command, dry_run=False)