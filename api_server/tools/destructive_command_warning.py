"""
Detects potentially destructive PowerShell commands and returns a warning string.
"""

import re

DESTRUCTIVE_PATTERNS = [
    (re.compile(r'(?:^|[|;&\n({])\s*(?:Remove-Item|rm|del|rd|rmdir|ri)\b[^|;&\n}]*-Recurse\b[^|;&\n}]*-Force\b', re.I), 'Note: may recursively force-remove files'),
    (re.compile(r'(?:^|[|;&\n({])\s*(?:Remove-Item|rm|del|rd|rmdir|ri)\b[^|;&\n}]*-Force\b[^|;&\n}]*-Recurse\b', re.I), 'Note: may recursively force-remove files'),
    (re.compile(r'(?:^|[|;&\n({])\s*(?:Remove-Item|rm|del|rd|rmdir|ri)\b[^|;&\n}]*-Recurse\b', re.I), 'Note: may recursively remove files'),
    (re.compile(r'(?:^|[|;&\n({])\s*(?:Remove-Item|rm|del|rd|rmdir|ri)\b[^|;&\n}]*-Force\b', re.I), 'Note: may force-remove files'),
    (re.compile(r'\bClear-Content\b[^|;&\n]*\*', re.I), 'Note: may clear content of multiple files'),
    (re.compile(r'\bFormat-Volume\b', re.I), 'Note: may format a disk volume'),
    (re.compile(r'\bClear-Disk\b', re.I), 'Note: may clear a disk'),
    (re.compile(r'\bgit\s+reset\s+--hard\b', re.I), 'Note: may discard uncommitted changes'),
    (re.compile(r'\bgit\s+push\b[^|;&\n]*\s+--force\b', re.I), 'Note: may overwrite remote history'),
    (re.compile(r'\bgit\s+push\b[^|;&\n]*\s+--force-with-lease\b', re.I), 'Note: may overwrite remote history'),
    (re.compile(r'\bgit\s+clean\b(?![^|;&\n]*(?:-[a-zA-Z]*n|--dry-run))[^|;&\n]*-[a-zA-Z]*f', re.I), 'Note: may permanently delete untracked files'),
    (re.compile(r'\bgit\s+stash\s+(?:drop|clear)\b', re.I), 'Note: may permanently remove stashed changes'),
    (re.compile(r'\b(?:DROP|TRUNCATE)\s+(?:TABLE|DATABASE|SCHEMA)\b', re.I), 'Note: may drop or truncate database objects'),
    (re.compile(r'\bStop-Computer\b', re.I), 'Note: will shut down the computer'),
    (re.compile(r'\bRestart-Computer\b', re.I), 'Note: will restart the computer'),
    (re.compile(r'\bClear-RecycleBin\b', re.I), 'Note: permanently deletes recycled files'),
]


def get_destructive_command_warning(command: str) -> str | None:
    for pattern, warning in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return warning
    return None