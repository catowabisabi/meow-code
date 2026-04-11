"""
Review tools for code analysis.

Provides tools for:
- PR review (review_pr)
- Ultra review (advanced bug finding)
- Security review (security analysis)
"""

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

from .types import ToolDef, ToolResult, ToolContext


ISSUE_SEVERITY = ["critical", "high", "medium", "low", "info"]

ISSUE_CATEGORIES = [
    "correctness",
    "security",
    "performance", 
    "maintainability",
    "style",
    "testing",
    "documentation",
]


@dataclass
class ReviewIssue:
    """A single issue found during review."""
    severity: str
    category: str
    file: str
    line: Optional[int]
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ReviewResult:
    """Result of a code review."""
    tool: str
    summary: str
    issues: list[ReviewIssue]
    statistics: dict[str, int]


def _run_command(cmd: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def _check_gh_available() -> bool:
    """Check if GitHub CLI is available."""
    returncode, _, _ = _run_command(["gh", "--version"])
    return returncode == 0


REVIEW_PR_TOOL = ToolDef(
    name="review_pr",
    description=(
        "Review a pull request. Analyzes PR diff for code quality, correctness, "
        "and potential issues. Returns structured review findings."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "pr_number": {"type": "number", "description": "Pull request number"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _review_pr(args, ctx),
)


async def _review_pr(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Review a pull request."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not _check_gh_available():
        return ToolResult(
            tool_call_id=tool_call_id,
            output="GitHub CLI (gh) is not installed. Install it from https://cli.github.com/",
            is_error=True,
        )
    
    pr_number = args.get("pr_number")
    
    if pr_number is None:
        returncode, stdout, stderr = _run_command(["gh", "pr", "list", "--json", "number,title,state"])
        if returncode != 0:
            return ToolResult(tool_call_id=tool_call_id, output=f"Error: {stderr}", is_error=True)
        
        prs = json.loads(stdout) if stdout.strip() else []
        if not prs:
            return ToolResult(tool_call_id=tool_call_id, output="No open pull requests found.", is_error=False)
        
        output = "Open Pull Requests:\n\n"
        for pr in prs:
            output += f"#{pr['number']}: {pr['title']} ({pr['state']})\n"
        
        return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
    
    returncode, details, stderr = _run_command([
        "gh", "pr", "view", str(pr_number), 
        "--json", "title,body,author,state,additions,deletions,changedFiles"
    ])
    if returncode != 0:
        return ToolResult(tool_call_id=tool_call_id, output=f"PR not found: {stderr}", is_error=True)
    
    pr_details = json.loads(details)
    
    returncode, diff, stderr = _run_command(["gh", "pr", "diff", str(pr_number)])
    if returncode != 0:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error getting diff: {stderr}", is_error=True)
    
    issues = _analyze_diff_for_issues(diff)
    
    summary = f"## PR #{pr_number}: {pr_details['title']}\n\n"
    summary += f"**Author:** {pr_details.get('author', {}).get('login', 'unknown')}\n"
    summary += f"**State:** {pr_details['state']}\n"
    summary += f"**Changes:** +{pr_details.get('additions', 0)}/-{pr_details.get('deletions', 0)} ({pr_details.get('changedFiles', 0)} files)\n\n"
    
    if issues:
        summary += f"## Issues Found ({len(issues)})\n\n"
        for issue in issues[:10]:
            summary += f"### [{issue.severity.upper()}] {issue.file}"
            if issue.line:
                summary += f":{issue.line}"
            summary += f"\n{issue.description}\n"
            if issue.suggestion:
                summary += f"Suggestion: {issue.suggestion}\n"
            summary += "\n"
    else:
        summary += "## No Issues Found\n\nCode looks good! No obvious issues detected.\n"
    
    result = ReviewResult(
        tool="review_pr",
        summary=summary,
        issues=issues,
        statistics={
            "total_issues": len(issues),
            "critical": len([i for i in issues if i.severity == "critical"]),
            "high": len([i for i in issues if i.severity == "high"]),
            "medium": len([i for i in issues if i.severity == "medium"]),
            "low": len([i for i in issues if i.severity == "low"]),
        },
    )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=summary,
        is_error=False,
        metadata={"review_result": {
            "tool": result.tool,
            "statistics": result.statistics,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "description": i.description,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
        }},
    )


def _analyze_diff_for_issues(diff: str) -> list[ReviewIssue]:
    """Analyze a diff for potential issues."""
    issues = []
    
    lines = diff.split("\n")
    current_file = None
    current_line = 0
    
    file_changes = {}
    for line in lines:
        if line.startswith("diff --git"):
            match = re.match(r"diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)
                file_changes[current_file] = {"additions": 0, "deletions": 0, "add_lines": [], "del_lines": []}
        elif line.startswith("@@"):
            match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                file_changes.setdefault(current_file, {"additions": 0, "deletions": 0})["additions"] += 1
                code = line[1:].strip()
                if len(code) > 0 and not code.startswith("//") and not code.startswith("/*"):
                    issues.extend(_check_code_issues(code, current_file, current_line, "add"))
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            if current_file:
                file_changes.setdefault(current_file, {"additions": 0, "deletions": 0})["deletions"] += 1
            current_line += 1
        elif not line.startswith("\\"):
            current_line += 1
    
    for file, changes in file_changes.items():
        if changes["additions"] > 100:
            issues.append(ReviewIssue(
                severity="medium",
                category="maintainability",
                file=file,
                line=None,
                description=f"Large file change: {changes['additions']} lines added",
                suggestion="Consider breaking this into smaller, focused changes",
            ))
    
    return issues[:20]


def _check_code_issues(code: str, file: str, line: int, change_type: str) -> list[ReviewIssue]:
    """Check code for specific issues."""
    issues = []
    
    if re.search(r"(?<!_)console\.(log|debug|info)", code):
        issues.append(ReviewIssue(
            severity="low",
            category="maintainability",
            file=file,
            line=line,
            description="Console logging found",
            suggestion="Remove console logging or use a proper logging framework",
        ))
    
    if re.search(r"\btodo\b", code, re.IGNORECASE):
        issues.append(ReviewIssue(
            severity="info",
            category="documentation",
            file=file,
            line=line,
            description="TODO comment found",
            suggestion="Ensure TODO is addressed or tracked in issue tracker",
        ))
    
    if re.search(r"except\s*:\s*raise", code) or re.search(r"except\s*:\s*print", code):
        issues.append(ReviewIssue(
            severity="medium",
            category="correctness",
            file=file,
            line=line,
            description="Bare except clause found",
            suggestion="Catch specific exceptions instead of bare except",
        ))
    
    if re.search(r"==\s*(True|False|null|None)|is\s+not\s+(True|False|null|None)", code):
        issues.append(ReviewIssue(
            severity="low",
            category="style",
            file=file,
            line=line,
            description="Explicit comparison to singletons",
            suggestion="Use 'is' for None/True/False comparisons",
        ))
    
    if re.search(r"password|secret|api_key|apikey|token|auth", code, re.IGNORECASE):
        issues.append(ReviewIssue(
            severity="critical",
            category="security",
            file=file,
            line=line,
            description="Potential sensitive data in code",
            suggestion="Move sensitive data to environment variables or config files",
        ))
    
    if "eval(" in code or "exec(" in code:
        issues.append(ReviewIssue(
            severity="critical",
            category="security",
            file=file,
            line=line,
            description="Use of eval() or exec() detected",
            suggestion="Avoid dynamic code execution",
        ))
    
    if re.search(r"\.join\([^)]*\)", code) and "os.path.join" not in code:
        issues.append(ReviewIssue(
            severity="low",
            category="maintainability",
            file=file,
            line=line,
            description="String concatenation in loop",
            suggestion="Consider using list and join for better performance",
        ))
    
    return issues


ULTRAReview_TOOL = ToolDef(
    name="ultrareview",
    description=(
        "Advanced bug finding review. Performs deep analysis of code changes "
        "to identify potential bugs, edge cases, and subtle issues that might "
        "be missed in a standard review."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to analyze (file or directory)"},
            "deep": {"type": "boolean", "description": "Enable deep analysis mode"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _ultra_review(args, ctx),
)


async def _ultra_review(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Perform advanced bug finding review."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    args.get("path", ctx.cwd or ".")  # Reserved for future targeted analysis
    deep = args.get("deep", False)
    
    returncode, diff, stderr = _run_command(["git", "diff", "HEAD"])
    if returncode != 0:
        returncode, diff, stderr = _run_command(["git", "diff", "--cached"])
        if returncode != 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="No changes found to review. Make sure you're in a git repository.",
                is_error=True,
            )
    
    issues = _deep_analyze_diff(diff, deep)
    
    summary = "## UltraReview Results\n\n"
    summary += f"**Mode:** {'Deep' if deep else 'Standard'} analysis\n"
    summary += f"**Issues Found:** {len(issues)}\n\n"
    
    if issues:
        by_severity = {}
        for issue in issues:
            by_severity.setdefault(issue.severity, []).append(issue)
        
        for severity in ["critical", "high", "medium", "low", "info"]:
            if severity in by_severity:
                summary += f"### {severity.upper()} ({len(by_severity[severity])})\n\n"
                for issue in by_severity[severity][:5]:
                    summary += f"**{issue.file}"
                    if issue.line:
                        summary += f":{issue.line}"
                    summary += f"**\n{issue.description}\n"
                    if issue.suggestion:
                        summary += f"*Suggestion:* {issue.suggestion}\n"
                    if issue.code_snippet:
                        summary += f"```\n{issue.code_snippet}\n```\n"
                    summary += "\n"
    else:
        summary += "No issues found. Code looks clean!\n"
    
    result = ReviewResult(
        tool="ultrareview",
        summary=summary,
        issues=issues,
        statistics={
            "total": len(issues),
            "deep_mode": deep,
        },
    )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=summary,
        is_error=False,
        metadata={"review_result": {
            "tool": result.tool,
            "statistics": result.statistics,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "description": i.description,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
        }},
    )


def _deep_analyze_diff(diff: str, deep: bool) -> list[ReviewIssue]:
    """Perform deep analysis on diff."""
    issues = _analyze_diff_for_issues(diff)
    
    if deep:
        deep_issues = _find_complexity_issues(diff)
        issues.extend(deep_issues)
        
        race_issues = _find_race_conditions(diff)
        issues.extend(race_issues)
        
        memory_issues = _find_memory_issues(diff)
        issues.extend(memory_issues)
    
    return issues[:30]


def _find_complexity_issues(diff: str) -> list[ReviewIssue]:
    """Find code complexity issues."""
    issues = []
    
    lines = diff.split("\n")
    current_file = None
    
    for line in lines:
        if line.startswith("diff --git"):
            match = re.match(r"diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)
        elif line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            
            if code.count("if") > 3:
                issues.append(ReviewIssue(
                    severity="medium",
                    category="maintainability",
                    file=current_file or "unknown",
                    line=None,
                    description="Nested if statements detected",
                    suggestion="Consider extracting to separate functions",
                ))
            
            if code.count("for") > 2 or code.count("while") > 2:
                issues.append(ReviewIssue(
                    severity="low",
                    category="performance",
                    file=current_file or "unknown",
                    line=None,
                    description="Multiple nested loops detected",
                    suggestion="Check for optimization opportunities",
                ))
    
    return issues


def _find_race_conditions(diff: str) -> list[ReviewIssue]:
    """Find potential race conditions."""
    issues = []
    
    patterns = [
        (r"global\s+\w+", "global variable"),
        (r"threading\.Lock\(\)", "Lock without context manager"),
        (r"\+=.*\+=.*\+=", "non-atomic compound assignment"),
    ]
    
    lines = diff.split("\n")
    current_file = None
    
    for line in lines:
        if line.startswith("diff --git"):
            match = re.match(r"diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)
        elif line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            for pattern, desc in patterns:
                if re.search(pattern, code):
                    issues.append(ReviewIssue(
                        severity="high",
                        category="correctness",
                        file=current_file or "unknown",
                        line=None,
                        description=f"Potential race condition: {desc}",
                        suggestion="Ensure thread-safe access",
                    ))
    
    return issues


def _find_memory_issues(diff: str) -> list[ReviewIssue]:
    """Find potential memory issues."""
    issues = []
    
    patterns = [
        (r"append\(.*append\(", "nested append calls"),
        (r"\[[^\]]*\[[^\]]*\][^\]]*\]", "deeply nested list comprehension"),
        (r"\+=.*['\"]", "string concatenation in loop"),
    ]
    
    lines = diff.split("\n")
    current_file = None
    
    for line in lines:
        if line.startswith("diff --git"):
            match = re.match(r"diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)
        elif line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            for pattern, desc in patterns:
                if re.search(pattern, code):
                    issues.append(ReviewIssue(
                        severity="low",
                        category="performance",
                        file=current_file or "unknown",
                        line=None,
                        description=f"Potential memory issue: {desc}",
                        suggestion="Consider more efficient approach",
                    ))
    
    return issues


SECURITY_REVIEW_TOOL = ToolDef(
    name="security_review",
    description=(
        "Security-focused review. Analyzes code for common security vulnerabilities "
        "including injection, authentication issues, sensitive data exposure, "
        "and OWASP Top 10 concerns."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to analyze"},
            "check_owasp": {"type": "boolean", "description": "Check OWASP Top 10 patterns"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _security_review(args, ctx),
)


async def _security_review(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Perform security review."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    args.get("path", ctx.cwd or ".")  # Reserved for future targeted analysis
    check_owasp = args.get("check_owasp", True)
    
    returncode, diff, stderr = _run_command(["git", "diff", "HEAD"])
    if returncode != 0:
        returncode, diff, stderr = _run_command(["git", "diff", "--cached"])
        if returncode != 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="No changes found to review.",
                is_error=True,
            )
    
    issues = _analyze_security_issues(diff, check_owasp)
    
    summary = "## Security Review Results\n\n"
    summary += f"**Issues Found:** {len(issues)}\n\n"
    
    if issues:
        by_category = {}
        for issue in issues:
            by_category.setdefault(issue.category, []).append(issue)
        
        for category in ["injection", "authentication", "sensitive_data", "crypto", "access_control"]:
            if category in by_category:
                summary += f"### {category.replace('_', ' ').title()} ({len(by_category[category])})\n\n"
                for issue in by_category[category][:5]:
                    summary += f"**{issue.file}"
                    if issue.line:
                        summary += f":{issue.line}"
                    summary += f"** [{issue.severity}]\n{issue.description}\n"
                    if issue.suggestion:
                        summary += f"*Fix:* {issue.suggestion}\n"
                    summary += "\n"
    else:
        summary += "No security issues found. Code looks secure!\n"
    
    result = ReviewResult(
        tool="security_review",
        summary=summary,
        issues=issues,
        statistics={
            "total": len(issues),
            "critical": len([i for i in issues if i.severity == "critical"]),
            "high": len([i for i in issues if i.severity == "high"]),
        },
    )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=summary,
        is_error=False,
        metadata={"review_result": {
            "tool": result.tool,
            "statistics": result.statistics,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "description": i.description,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ],
        }},
    )


def _analyze_security_issues(diff: str, check_owasp: bool) -> list[ReviewIssue]:
    """Analyze diff for security issues."""
    issues = []
    
    security_patterns = [
        (r"eval\s*\(", "eval() usage", "critical", "injection", "Avoid eval() - it can execute arbitrary code"),
        (r"exec\s*\(", "exec() usage", "critical", "injection", "Avoid exec() - it can execute arbitrary code"),
        (r"os\.system\s*\(", "os.system() usage", "high", "injection", "Use subprocess.run() instead"),
        (r"subprocess\.\w+\s*\(\s*shell\s*=\s*True", "shell=True in subprocess", "high", "injection", "Avoid shell=True to prevent command injection"),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password", "critical", "sensitive_data", "Move passwords to environment variables"),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret", "critical", "sensitive_data", "Move secrets to environment variables"),
        (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key", "critical", "sensitive_data", "Move API keys to environment variables"),
        (r"token\s*=\s*['\"][^'\"]+['\"]", "Hardcoded token", "critical", "sensitive_data", "Move tokens to environment variables"),
        (r"SQL\s+\w+\s+WHERE", "Potential SQL in string", "high", "injection", "Use parameterized queries"),
        (r"\.format\s*\(\s*.*%", "String formatting with %", "medium", "injection", "Consider f-strings or parameterized queries"),
        (r"pickle\.loads?", "Pickle deserialization", "high", "injection", "Avoid unpickling untrusted data"),
        (r"hashlib\.(md5|sha1)\s*\(", "Weak hash algorithm", "medium", "crypto", "Use SHA-256 or stronger"),
        (r"Crypto\.", "Use of Crypto library", "medium", "crypto", "Use cryptography library instead"),
        (r"random\.", "Use of random for security", "high", "crypto", "Use secrets module for security"),
        (r"urllib\.urlopen", "urllib.urlopen usage", "medium", "injection", "Use urllib.request instead"),
        (r"requests\.\w+\(.*verify\s*=\s*False", "SSL verification disabled", "high", "sensitive_data", "Enable SSL verification"),
        (r"\.disable_ssl_warnings?\(", "SSL warnings disabled", "low", "sensitive_data", "Don't disable SSL warnings"),
        (r"if\s+user\s*==\s*['\"]admin['\"]", "Hardcoded admin check", "medium", "access_control", "Use proper authentication"),
        (r"request\.args\.get\(", "URL parameter access", "medium", "injection", "Validate and sanitize input"),
        (r"request\.form\.get\(", "Form parameter access", "medium", "injection", "Validate and sanitize input"),
    ]
    
    if check_owasp:
        owasp_patterns = [
            (r"innerHTML\s*=", "XSS: innerHTML assignment", "high", "injection"),
            (r"dangerouslySetInnerHTML", "XSS: dangerouslySetInnerHTML", "high", "injection"),
            (r"document\.cookie", "Cookie access", "medium", "sensitive_data"),
            (r"localStorage\.", "localStorage usage", "low", "sensitive_data"),
            (r"sessionStorage\.", "sessionStorage usage", "low", "sensitive_data"),
            (r"crypto\.pbkdf2", "PBKDF2 usage", "low", "crypto"),
        ]
        security_patterns.extend(owasp_patterns)
    
    lines = diff.split("\n")
    current_file = None
    
    for line in lines:
        if line.startswith("diff --git"):
            match = re.match(r"diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)
        elif line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            for pattern, desc, severity, category, suggestion in security_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append(ReviewIssue(
                        severity=severity,
                        category=category,
                        file=current_file or "unknown",
                        line=None,
                        description=desc,
                        suggestion=suggestion,
                        code_snippet=code[:100] if len(code) > 100 else code,
                    ))
    
    return issues[:25]


REVIEW_TOOLS: list[ToolDef] = [
    REVIEW_PR_TOOL,
    ULTRAReview_TOOL,
    SECURITY_REVIEW_TOOL,
]

__all__ = [
    "REVIEW_TOOLS",
    "REVIEW_PR_TOOL",
    "ULTRAReview_TOOL",
    "SECURITY_REVIEW_TOOL",
    "ReviewIssue",
    "ReviewResult",
]
