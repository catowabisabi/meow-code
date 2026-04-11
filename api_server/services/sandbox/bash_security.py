"""
Bash security validation module.

Implements command security checks including:
- Command substitution detection
- Shell metacharacter validation
- Dangerous pattern detection
- Incomplete command detection
- Quoting and escape analysis
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SecurityCheckId(Enum):
    """Numeric IDs for security checks (to avoid logging strings)."""
    INCOMPLETE_COMMANDS = 1
    JQ_SYSTEM_FUNCTION = 2
    JQ_FILE_ARGUMENTS = 3
    OBFUSCATED_FLAGS = 4
    SHELL_METACHARACTERS = 5
    DANGEROUS_VARIABLES = 6
    NEWLINES = 7
    DANGEROUS_PATTERNS_COMMAND_SUBSTITUTION = 8
    DANGEROUS_PATTERNS_INPUT_REDIRECTION = 9
    DANGEROUS_PATTERNS_OUTPUT_REDIRECTION = 10
    IFS_INJECTION = 11
    GIT_COMMIT_SUBSTITUTION = 12
    PROC_ENVIRON_ACCESS = 13
    MALFORMED_TOKEN_INJECTION = 14
    BACKSLASH_ESCAPED_WHITESPACE = 15
    BRACE_EXPANSION = 16
    CONTROL_CHARACTERS = 17
    UNICODE_WHITESPACE = 18
    MID_WORD_HASH = 19
    ZSH_DANGEROUS_COMMANDS = 20
    BACKSLASH_ESCAPED_OPERATORS = 21
    COMMENT_QUOTE_DESYNC = 22
    QUOTED_NEWLINE = 23


class SecurityBehavior(Enum):
    """Security validation behavior results."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    PASSTHROUGH = "passthrough"


@dataclass
class SecurityResult:
    """Result of a security validation check."""
    behavior: SecurityBehavior
    message: Optional[str] = None
    updated_command: Optional[str] = None
    decision_reason: Optional[dict] = None
    blocked_path: Optional[str] = None
    suggestions: Optional[list] = None

    def to_permission_result(self) -> dict:
        """Convert to permission result dict format."""
        result = {"behavior": self.behavior.value}
        if self.message:
            result["message"] = self.message
        if self.updated_command:
            result["updated_input"] = {"command": self.updated_command}
        if self.decision_reason:
            result["decision_reason"] = self.decision_reason
        if self.blocked_path:
            result["blocked_path"] = self.blocked_path
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result


# Command substitution patterns
COMMAND_SUBSTITUTION_PATTERNS = [
    (re.compile(r"<\("), "process substitution <()"),
    (re.compile(r">\("), "process substitution >()"),
    (re.compile(r"=\("), "Zsh process substitution =()"),
    (re.compile(r"(?:^|[\s;&|])=[a-zA-Z_]"), "Zsh equals expansion (=cmd)"),
    (re.compile(r"\$\("), "$() command substitution"),
    (re.compile(r"\$\{"), "${} parameter substitution"),
    (re.compile(r"\$\["), "$[] legacy arithmetic expansion"),
    (re.compile(r"~\["), "Zsh-style parameter expansion"),
    (re.compile(r"\(e:"), "Zsh-style glob qualifiers"),
    (re.compile(r"\(\+"), "Zsh glob qualifier with command execution"),
    (re.compile(r"}\s*always\s*\{"), "Zsh always block (try/always construct)"),
    (re.compile(r"<#"), "PowerShell comment syntax"),
]

# Zsh-specific dangerous commands
ZSH_DANGEROUS_COMMANDS = {
    "zmodload", "emulate", "sysopen", "sysread", "syswrite", "sysseek",
    "zpty", "ztcp", "zsocket", "mapfile", "zf_rm", "zf_mv", "zf_ln",
    "zf_chmod", "zf_chown", "zf_mkdir", "zf_rmdir", "zf_chgrp",
}


def has_unescaped_char(content: str, char: str) -> bool:
    """
    Check if content contains an unescaped occurrence of a single character.
    
    Handles bash escape sequences correctly where a backslash escapes the 
    following character.
    """
    if len(char) != 1:
        raise ValueError("has_unescaped_char only works with single characters")
    
    i = 0
    while i < len(content):
        if content[i] == "\\" and i + 1 < len(content):
            i += 2
            continue
        
        if content[i] == char:
            return True
        
        i += 1
    
    return False


def extract_quoted_content(command: str, is_jq: bool = False) -> dict:
    """
    Extract quoted content from command, handling quotes properly.
    
    Returns dict with:
    - withDoubleQuotes: content with double quotes
    - fullyUnquoted: content with all quotes stripped
    - unquotedKeepQuoteChars: content preserving quote delimiter characters
    """
    with_double = ""
    fully_unquoted = ""
    unquoted_keep = ""
    in_single = False
    in_double = False
    escaped = False
    
    for char in command:
        if escaped:
            escaped = False
            if not in_single:
                with_double += char
            if not in_single and not in_double:
                fully_unquoted += char
            if not in_single and not in_double:
                unquoted_keep += char
            continue
        
        if char == "\\" and not in_single:
            escaped = True
            if not in_single:
                with_double += char
            if not in_single and not in_double:
                fully_unquoted += char
            if not in_single and not in_double:
                unquoted_keep += char
            continue
        
        if char == "'" and not in_double:
            in_single = not in_single
            unquoted_keep += char
            continue
        
        if char == '"' and not in_single:
            in_double = not in_double
            unquoted_keep += char
            if not is_jq:
                continue
        
        if not in_single:
            with_double += char
        if not in_single and not in_double:
            fully_unquoted += char
        if not in_single and not in_double:
            unquoted_keep += char
    
    return {
        "withDoubleQuotes": with_double,
        "fullyUnquoted": fully_unquoted,
        "unquotedKeepQuoteChars": unquoted_keep,
    }


def strip_safe_redirections(content: str) -> str:
    """
    Strip safe redirections from command content.
    
    SECURITY: All patterns MUST have trailing boundary to prevent bypass.
    """
    result = content
    result = re.sub(r"\s+2\s*>&\s*1(?=\s|$)", "", result)
    result = re.sub(r"[012]?\s*>\s*\/dev\/null(?=\s|$)", "", result)
    result = re.sub(r"\s*<\s*\/dev\/null(?=\s|$)", "", result)
    return result


def validate_empty(command: str) -> SecurityResult:
    """Check if command is empty."""
    if not command.strip():
        return SecurityResult(
            behavior=SecurityBehavior.ALLOW,
            updated_command=command,
            decision_reason={"type": "other", "reason": "Empty command is safe"},
        )
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="Command is not empty",
    )


def validate_incomplete_commands(command: str) -> SecurityResult:
    """Check for incomplete command fragments."""
    trimmed = command.strip()
    
    # Starts with tab (incomplete fragment)
    if re.match(r"^\s*\t", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command appears to be an incomplete fragment (starts with tab)",
        )
    
    # Starts with flags (incomplete)
    if trimmed.startswith("-"):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command appears to be an incomplete fragment (starts with flags)",
        )
    
    # Starts with operators (continuation line)
    if re.match(r"^\s*(&&|\|\||;|>>?|<)", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command appears to be a continuation line (starts with operator)",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="Command appears complete",
    )


def validate_shell_metacharacters(unquoted_content: str) -> SecurityResult:
    """Check for shell metacharacters in arguments."""
    # Pattern: metacharacters inside quotes
    if re.search(r'(?:^|\s)["\'][^"\']*[;&][^"\']*["\'](?:\s|$)', unquoted_content):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains shell metacharacters (;, |, or &) in arguments",
        )
    
    # find-style metacharacter patterns
    glob_patterns = [
        re.compile(r"-name\s+[\"'][^\"']*[;&][^\"']*[\"']"),
        re.compile(r"-path\s+[\"'][^\"']*[;&][^\"']*[\"']"),
        re.compile(r"-iname\s+[\"'][^\"']*[;&][^\"']*[\"']"),
    ]
    
    for pattern in glob_patterns:
        if pattern.test(unquoted_content):
            return SecurityResult(
                behavior=SecurityBehavior.ASK,
                message="Command contains shell metacharacters (;, |, or &) in arguments",
            )
    
    if re.search(r"-regex\s+[\"'][^\"']*[;&][^\"']*[\"']", unquoted_content):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains shell metacharacters (;, |, or &) in arguments",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No metacharacters",
    )


def validate_dangerous_variables(fully_unquoted: str) -> SecurityResult:
    """Check for dangerous variable usage in redirections/pipes."""
    if re.search(r"[<>|]\s*\$[A-Za-z_]", fully_unquoted):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains variables in dangerous contexts (redirections or pipes)",
        )
    
    if re.search(r"\$[A-Za-z_][A-Za-z0-9_]*\s*[|<>]", fully_unquoted):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains variables in dangerous contexts (redirections or pipes)",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No dangerous variables",
    )


def validate_dangerous_patterns(unquoted_content: str) -> SecurityResult:
    """Check for dangerous patterns like command substitution."""
    # Check for unescaped backticks
    if has_unescaped_char(unquoted_content, "`"):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains backticks (`) for command substitution",
        )
    
    # Check other command substitution patterns
    for pattern, message in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(unquoted_content):
            return SecurityResult(
                behavior=SecurityBehavior.ASK,
                message=f"Command contains {message}",
            )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No dangerous patterns",
    )


def validate_redirections(fully_unquoted: str) -> SecurityResult:
    """Check for input/output redirections."""
    if "<" in fully_unquoted:
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains input redirection (<) which could read sensitive files",
        )
    
    if ">" in fully_unquoted:
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains output redirection (>) which could write to arbitrary files",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No redirections",
    )


def validate_newlines(command: str) -> SecurityResult:
    """Check for newlines that could separate multiple commands."""
    if not re.search(r"[\n\r]", command):
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="No newlines",
        )
    
    # Flag any newline followed by non-whitespace, except backslash-newline
    if re.search(r"(?<![\s\\])[\n\r]\s*\S", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains newlines that could separate multiple commands",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="Newlines appear to be within data",
    )


def validate_carriage_return(command: str) -> SecurityResult:
    """Check for carriage return which shell-quote and bash tokenize differently."""
    if "\r" not in command:
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="No carriage return",
        )
    
    # Check if CR appears outside double quotes
    in_single = False
    in_double = False
    escaped = False
    
    for char in command:
        if escaped:
            escaped = False
            continue
        if char == "\\" and not in_single:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "\r" and not in_double:
            return SecurityResult(
                behavior=SecurityBehavior.ASK,
                message="Command contains carriage return (\\r) which shell-quote and bash tokenize differently",
            )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="CR only inside double quotes",
    )


def validate_ifs_injection(command: str) -> SecurityResult:
    """Detect IFS variable usage which could bypass validation."""
    if re.search(r"\$IFS|\$\{[^}]*IFS", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains IFS variable usage which could bypass security validation",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No IFS injection detected",
    )


def validate_proc_environ_access(command: str) -> SecurityResult:
    """Check for /proc/*/environ access which could expose environment variables."""
    if re.search(r"\/proc\/.*\/environ", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command accesses /proc/*/environ which could expose sensitive environment variables",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No /proc/environ access detected",
    )


def validate_jq_command(command: str, base_command: str) -> SecurityResult:
    """Check for dangerous jq command patterns."""
    if base_command != "jq":
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="Not jq",
        )
    
    if re.search(r"\bsystem\s*\(", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="jq command contains system() function which executes arbitrary commands",
        )
    
    # Check for dangerous flags
    after_jq = command[3:].strip()
    dangerous_flags = [
        "-f", "--from-file", "--rawfile", "--slurpfile", 
        "-L", "--library-path"
    ]
    
    for flag in dangerous_flags:
        if re.search(rf"(?:^|\s){re.escape(flag)}\b", after_jq):
            return SecurityResult(
                behavior=SecurityBehavior.ASK,
                message="jq command contains dangerous flags that could execute code or read arbitrary files",
            )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="jq command is safe",
    )


def validate_git_commit(command: str, base_command: str) -> SecurityResult:
    """Check for git commit command substitution patterns."""
    if base_command != "git" or not re.match(r"^git\s+commit\s+", command):
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="Not a git commit",
        )
    
    # Backslashes make validation complex - bail to full validation
    if "\\" in command:
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="Git commit contains backslash, needs full validation",
        )
    
    # Match git commit -m "message" pattern
    message_match = re.match(
        r"^git[ \t]+commit[ \t]+[^;&|`$<>()\n\r]*?-m[ \t]+([\"'])([\s\S]*?)\1(.*)$",
        command,
    )
    
    if message_match:
        quote = message_match.group(1)
        message_content = message_match.group(2)
        remainder = message_match.group(3)
        
        if quote == '"' and message_content:
            if re.search(r"\$\(|`|\$\{", message_content):
                return SecurityResult(
                    behavior=SecurityBehavior.ASK,
                    message="Git commit message contains command substitution patterns",
                )
        
        # Check remainder for shell operators
        if remainder and re.search(r"[;|&`$]|\$\(|\$\{", remainder):
            return SecurityResult(
                behavior=SecurityBehavior.PASSTHROUGH,
                message="Git commit remainder contains shell metacharacters",
            )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="Git commit needs validation",
    )


def validate_zsh_dangerous_commands(command: str) -> SecurityResult:
    """Check for Zsh-specific dangerous commands."""
    tokens = command.strip().split()
    if not tokens:
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="No command tokens",
        )
    
    base_cmd = tokens[0]
    if base_cmd in ZSH_DANGEROUS_COMMANDS:
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message=f"Command contains dangerous Zsh command: {base_cmd}",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No dangerous Zsh commands",
    )


def validate_brace_expansion(command: str) -> SecurityResult:
    """Check for brace expansion which can hide content."""
    # Pattern: {a,b} or {1..5} forms
    if re.search(r"\{[^}]+,[^}]*\}", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains brace expansion which could hide content",
        )
    
    if re.search(r"\{[0-9]+\.\.[0-9]+\}", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains numeric brace expansion",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No brace expansion detected",
    )


def validate_obfuscated_flags(command: str, base_command: str) -> SecurityResult:
    """Check for obfuscated flag patterns."""
    # Echo is safe for obfuscated flags only for simple echo commands
    has_shell_operators = re.search(r"[|&;]", command) is not None
    if base_command == "echo" and not has_shell_operators:
        return SecurityResult(
            behavior=SecurityBehavior.PASSTHROUGH,
            message="echo command is safe and has no dangerous flags",
        )
    
    # ANSI-C quoting ($'...')
    if re.search(r"\$'[^']*'", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains ANSI-C quoting which can hide characters",
        )
    
    # Locale quoting ($"...")
    if re.search(r'\$"[^"]*"', command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains locale quoting which can hide characters",
        )
    
    # Empty ANSI-C or locale quotes followed by dash
    if re.search(r"\$['\"]{2}\s*-", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains empty special quotes before dash (potential bypass)",
        )
    
    # Empty quotes before dash
    if re.search(r"(?:^|\s)(?:''|\"\")+\s*-", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains empty quotes before dash (potential bypass)",
        )
    
    # Homogeneous empty quote pair adjacent to quoted dash
    if re.search(r'(?:""|'')+[\'"]-', command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains empty quote pair adjacent to quoted dash (potential flag obfuscation)",
        )
    
    # 3+ consecutive quotes at word start
    if re.search(r"(?:^|\s)['\"]{3,}", command):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains consecutive quote characters at word start (potential obfuscation)",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No obfuscated flags detected",
    )


def validate_backslash_escaped_operators(command: str) -> SecurityResult:
    """Check for backslash-escaped operators that could bypass checks."""
    # Pattern: \<operator> where operator is shell metacharacter
    escaped_ops = re.findall(r"\\([|&;<>])", command)
    if escaped_ops:
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message=f"Command contains backslash-escaped operators: {', '.join(escaped_ops)}",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No backslash-escaped operators",
    )


def validate_mid_word_hash(command: str, unquoted_keep_quote_chars: str) -> SecurityResult:
    """Check for mid-word hash that could be a comment."""
    # Check for # that appears after quote characters without space separation
    if re.search(r"['\"]#", unquoted_keep_quote_chars):
        return SecurityResult(
            behavior=SecurityBehavior.ASK,
            message="Command contains mid-word hash which could be misinterpreted as comment",
        )
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="No mid-word hash detected",
    )


def get_base_command(command: str) -> str:
    """Extract the base command (first word) from a command string."""
    tokens = command.strip().split()
    return tokens[0] if tokens else ""


def validate_command_security(command: str) -> SecurityResult:
    """
    Main security validation entry point.
    
    Validates a shell command for various security concerns including:
    - Command substitution patterns
    - Shell metacharacters
    - Dangerous variable usage
    - Redirections
    - Zsh dangerous commands
    - Obfuscated flags
    - And more
    
    Returns SecurityResult with behavior ALLOW, ASK, DENY, or PASSTHROUGH.
    """
    if not command:
        return validate_empty(command)
    
    # Extract quoted content for analysis
    quoted = extract_quoted_content(command)
    fully_unquoted = quoted["fullyUnquoted"]
    unquoted_keep_quote_chars = quoted["unquotedKeepQuoteChars"]
    fully_unquoted_pre_strip = strip_safe_redirections(fully_unquoted)
    
    # Strip safe redirections for analysis
    fully_unquoted = strip_safe_redirections(fully_unquoted)
    
    base_command = get_base_command(command)
    
    # Run all validators
    validators = [
        validate_incomplete_commands,
        lambda cmd: validate_shell_metacharacters(quoted["fullyUnquoted"]),
        lambda cmd: validate_dangerous_variables(fully_unquoted),
        lambda cmd: validate_dangerous_patterns(quoted["fullyUnquoted"]),
        lambda cmd: validate_redirections(fully_unquoted),
        lambda cmd: validate_newlines(fully_unquoted_pre_strip),
        lambda cmd: validate_carriage_return(command),
        lambda cmd: validate_ifs_injection(command),
        lambda cmd: validate_proc_environ_access(command),
        lambda cmd: validate_jq_command(command, base_command),
        lambda cmd: validate_git_commit(command, base_command),
        lambda cmd: validate_zsh_dangerous_commands(command),
        lambda cmd: validate_brace_expansion(command),
        lambda cmd: validate_obfuscated_flags(command, base_command),
        lambda cmd: validate_backslash_escaped_operators(command),
        lambda cmd: validate_mid_word_hash(command, unquoted_keep_quote_chars),
    ]
    
    for validator in validators:
        result = validator(command)
        if result.behavior != SecurityBehavior.PASSTHROUGH:
            return result
    
    return SecurityResult(
        behavior=SecurityBehavior.PASSTHROUGH,
        message="Command passed security validation",
    )


def is_command_safe(command: str) -> bool:
    """
    Simple boolean check if command passes security validation.
    
    Returns True if command is safe (passthrough or allow),
    False if it triggers ask or deny.
    """
    result = validate_command_security(command)
    return result.behavior in (
        SecurityBehavior.PASSTHROUGH,
        SecurityBehavior.ALLOW,
    )
