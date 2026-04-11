"""
Read-only command validation module.

Implements allowlist-based validation for read-only commands
similar to the TypeScript implementation.
"""

import re
import shlex
from dataclasses import dataclass
from typing import Optional


# Read-only commands that need flag validation
COMMAND_ALLOWLISTS = {
    "xargs": {
        "safe_flags": {
            "-I": "{}",
            "-n": "number",
            "-P": "number",
            "-L": "number",
            "-s": "number",
            "-E": "EOF",
            "-0": "none",
            "-t": "none",
            "-r": "none",
            "-x": "none",
            "-d": "char",
        },
    },
    "file": {
        "safe_flags": {
            "--brief": "none",
            "-b": "none",
            "--mime": "none",
            "-i": "none",
            "--mime-type": "none",
            "--mime-encoding": "none",
            "--apple": "none",
            "--check-encoding": "none",
            "-c": "none",
            "--exclude": "string",
            "--exclude-quiet": "string",
            "--print0": "none",
            "-0": "none",
            "-f": "string",
            "-F": "string",
            "--separator": "string",
            "--help": "none",
            "--version": "none",
            "-v": "none",
            "--no-dereference": "none",
            "-h": "none",
            "--dereference": "none",
            "-L": "none",
            "--magic-file": "string",
            "-m": "string",
            "--keep-going": "none",
            "-k": "none",
            "--list": "none",
            "-l": "none",
            "--no-buffer": "none",
            "-n": "none",
            "--preserve-date": "none",
            "-p": "none",
            "--raw": "none",
            "-r": "none",
            "-s": "none",
            "--special-files": "none",
            "--uncompress": "none",
            "-z": "none",
        },
    },
    "sed": {
        "safe_flags": {
            "--expression": "string",
            "-e": "string",
            "--quiet": "none",
            "--silent": "none",
            "-n": "none",
            "--regexp-extended": "none",
            "-r": "none",
            "--posix": "none",
            "-E": "none",
            "--line-length": "number",
            "-l": "number",
            "--zero-terminated": "none",
            "-z": "none",
            "--separate": "none",
            "-s": "none",
            "--unbuffered": "none",
            "-u": "none",
            "--debug": "none",
            "--help": "none",
            "--version": "none",
        },
    },
    "sort": {
        "safe_flags": {
            "--ignore-leading-blanks": "none",
            "-b": "none",
            "--dictionary-order": "none",
            "-d": "none",
            "--ignore-case": "none",
            "-f": "none",
            "--general-numeric-sort": "none",
            "-g": "none",
            "--human-numeric-sort": "none",
            "-h": "none",
            "--ignore-nonprinting": "none",
            "-i": "none",
            "--month-sort": "none",
            "-M": "none",
            "--numeric-sort": "none",
            "-n": "none",
            "--random-sort": "none",
            "-R": "none",
            "--reverse": "none",
            "-r": "none",
            "--sort": "string",
            "--stable": "none",
            "-s": "none",
            "--unique": "none",
            "-u": "none",
            "--version-sort": "none",
            "-V": "none",
            "--zero-terminated": "none",
            "-z": "none",
            "--key": "string",
            "-k": "string",
            "--field-separator": "string",
            "-t": "string",
            "--check": "none",
            "-c": "none",
            "--check-char-order": "none",
            "-C": "none",
            "--merge": "none",
            "-m": "none",
            "--buffer-size": "string",
            "-S": "string",
            "--parallel": "number",
            "--batch-size": "number",
            "--help": "none",
            "--version": "none",
        },
    },
    "grep": {
        "safe_flags": {
            "-e": "string",
            "--regexp": "string",
            "-f": "string",
            "--file": "string",
            "-F": "none",
            "--fixed-strings": "none",
            "-G": "none",
            "--basic-regexp": "none",
            "-E": "none",
            "--extended-regexp": "none",
            "-P": "none",
            "--perl-regexp": "none",
            "-i": "none",
            "--ignore-case": "none",
            "--no-ignore-case": "none",
            "-v": "none",
            "--invert-match": "none",
            "-w": "none",
            "--word-regexp": "none",
            "-x": "none",
            "--line-regexp": "none",
            "-c": "none",
            "--count": "none",
            "--color": "string",
            "--colour": "string",
            "-L": "none",
            "--files-without-match": "none",
            "-l": "none",
            "--files-with-matches": "none",
            "-m": "number",
            "--max-count": "number",
            "-o": "none",
            "--only-matching": "none",
            "-q": "none",
            "--quiet": "none",
            "--silent": "none",
            "-s": "none",
            "--no-messages": "none",
            "-b": "none",
            "--byte-offset": "none",
            "-H": "none",
            "--with-filename": "none",
            "-h": "none",
            "--no-filename": "none",
            "--label": "string",
            "-n": "none",
            "--line-number": "none",
            "-T": "none",
            "--initial-tab": "none",
            "-u": "none",
            "--unix-byte-offsets": "none",
            "-Z": "none",
            "--null": "none",
            "-z": "none",
            "--null-data": "none",
            "-A": "number",
            "--after-context": "number",
            "-B": "number",
            "--before-context": "number",
            "-C": "number",
            "--context": "number",
            "--group-separator": "string",
            "--no-group-separator": "none",
            "-a": "none",
            "--text": "none",
            "--binary-files": "string",
            "-D": "string",
            "--devices": "string",
            "-d": "string",
            "--directories": "string",
            "--exclude": "string",
            "--exclude-from": "string",
            "--exclude-dir": "string",
            "--include": "string",
            "-r": "none",
            "--recursive": "none",
            "-R": "none",
            "--dereference-recursive": "none",
            "--line-buffered": "none",
            "-U": "none",
            "--binary": "none",
            "--help": "none",
            "-V": "none",
            "--version": "none",
        },
    },
    "rg": {
        "safe_flags": {
            "-e": "string",
            "--regexp": "string",
            "-f": "string",
            "--file": "string",
            "-t": "string",
            "--type": "string",
            "-T": "string",
            "--type-not": "string",
            "-g": "string",
            "--glob": "string",
            "-m": "number",
            "--max-count": "number",
            "--max-depth": "number",
            "-r": "string",
            "--replace": "string",
            "-A": "number",
            "--after-context": "number",
            "-B": "number",
            "--before-context": "number",
            "-C": "number",
            "--context": "number",
            "--help": "none",
            "--version": "none",
        },
    },
}


# Simple read-only commands (regex patterns)
READONLY_COMMAND_REGEXES = [
    r"^cal(?:\s*$|\s+\d+\s*$|\s+-yjh?\s*$)",
    r"^uptime(?:\s*$)",
    r"^cat(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^head(?:\s+-n\s+\d+|\s+-\d+|\s+-c\s+\d+|\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^tail(?:\s+-n\s+\d+|\s+-\d+|\s+-c\s+\d+|\s+-f|\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^wc(?:\s+-[clwL]\s*)*$",
    r"^stat(?:\s+-[a-z]+\s*)*$",
    r"^strings(?:\s+-[a-z]+\s*)*$",
    r"^hexdump(?:\s+-[a-z]+\s*)*$",
    r"^od(?:\s+-[a-zA-Z]+\s*)*$",
    r"^nl(?:\s+-[a-z]+\s*)*$",
    r"^id(?:\s+[a-z]+\s*)*$",
    r"^uname(?:\s+-a\s*)*$",
    r"^free(?:\s+-[a-z]+\s*)*$",
    r"^df(?:\s+-[a-z]+\s*)*$",
    r"^du(?:\s+-[a-z]+\s*)*$",
    r"^locale(?:\s+[a-zA-Z_-]+\s*)*$",
    r"^groups(?:\s+[a-z]+\s*)*$",
    r"^nproc(?:\s*)$",
    r"^basename(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^dirname(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^realpath(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^cut(?:\s+-[a-z]+\s*)*$",
    r"^paste(?:\s+-[a-z]+\s*)*$",
    r"^tr(?:\s+['\"][^\"\']+['\"]\s+['\"][^\"\']+['\"]\s*)*$",
    r"^column(?:\s+-[a-z]+\s*)*$",
    r"^tac(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^rev(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^fold(?:\s+-[a-z]+\s*)*$",
    r"^expand(?:\s+-[a-z]+\s*)*$",
    r"^unexpand(?:\s+-[a-z]+\s*)*$",
    r"^fmt(?:\s+-[a-z]+\s*)*$",
    r"^comm(?:\s+-[a-z123]+\s*)*$",
    r"^cmp(?:\s+-[a-z]+\s*)*$",
    r"^numfmt(?:\s+-[a-z]+\s*)*$",
    r"^readlink(?:\s+-[a-z]+\s*)*$",
    r"^diff(?:\s+-[a-z]+\s*)*$",
    r"^true(?:\s*)$",
    r"^false(?:\s*)$",
    r"^sleep(?:\s+\d+\s*)*$",
    r"^which(?:\s+[a-zA-Z0-9_-]+\s*)*$",
    r"^type(?:\s+[a-zA-Z0-9_-]+\s*)*$",
    r"^expr(?:\s+.+\s*)*$",
    r"^test(?:\s+.+\s*)*$",
    r"^getconf(?:\s+-[a-zA-Z_]+\s*)*$",
    r"^seq(?:\s+\d+(\s+\d+)*\s*)*$",
    r"^tsort(?:\s+[^\s|&;`$<>(){}]+\s*)*$",
    r"^pr(?:\s+-[a-z]+\s*)*$",
    r"^pwd$",
    r"^whoami$",
    r"^history(?:\s+\d+)?\s*$",
    r"^alias(?:\s*)$",
    r"^arch(?:\s+--help|-h)?\s*$",
]


def make_safe_command_regex(command: str) -> str:
    """Create a regex pattern for safe command matching."""
    return f"^{command}(?:\\s|$)[^<>()$`|{{}}&;\\n\\r]*$"


def is_readonly_command(command: str) -> bool:
    """
    Check if command is a read-only command.
    
    Uses both allowlist-based flag validation and regex matching.
    """
    if not command:
        return False
    
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    
    if not parts:
        return False
    
    base_cmd = parts[0]
    
    if base_cmd in COMMAND_ALLOWLISTS:
        return True
    
    for regex_pattern in READONLY_COMMAND_REGEXES:
        if re.match(regex_pattern, command):
            return True
    
    return False


def is_command_safe_via_flag_parsing(command: str) -> bool:
    """
    Validate command using flag-based allowlist parsing.
    
    Returns True if command passes allowlist validation.
    """
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    
    if not parts:
        return False
    
    base_cmd = parts[0]
    
    if base_cmd not in COMMAND_ALLOWLISTS:
        return False
    
    config = COMMAND_ALLOWLISTS[base_cmd]
    safe_flags = config.get("safe_flags", {})
    
    for i, arg in enumerate(parts[1:], start=1):
        if arg.startswith("--"):
            flag_name = arg.split("=")[0]
            if flag_name not in safe_flags:
                return False
            if safe_flags[flag_name] != "none" and "=" not in arg:
                pass
        elif arg.startswith("-"):
            if len(arg) > 2:
                for j, c in enumerate(arg[1:], start=1):
                    if c not in safe_flags:
                        return False
            else:
                if arg not in safe_flags:
                    return False
    
    return True


@dataclass
class ReadOnlyValidationResult:
    """Result of read-only validation."""
    is_readonly: bool
    message: Optional[str] = None


def validate_readonly_command(command: str) -> ReadOnlyValidationResult:
    """
    Validate if a command is read-only.
    
    Returns ReadOnlyValidationResult with is_readonly status.
    """
    if is_readonly_command(command):
        return ReadOnlyValidationResult(
            is_readonly=True,
            message="Command is read-only",
        )
    
    if is_command_safe_via_flag_parsing(command):
        return ReadOnlyValidationResult(
            is_readonly=True,
            message="Command is read-only (via flag parsing)",
        )
    
    return ReadOnlyValidationResult(
        is_readonly=False,
        message="Command may modify filesystem",
    )
