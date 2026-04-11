"""
GrepTool - Search file contents using regex patterns (ripgrep).

Provides powerful regex-based search with:
- Pattern matching with regex support
- File filtering via glob patterns
- Context lines (before/after/both)
- Multiple output modes (content, files_with_matches, count)
- Case insensitive and multiline modes

Based on the TypeScript GrepTool implementation in _claude_code_leaked_source_code.
"""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from .types import ToolDef, ToolContext, ToolResult


# VCS directories to exclude from searches
VCS_DIRECTORIES_TO_EXCLUDE = [".git", ".svn", ".hg", ".bzr", ".jj", ".sl"]

# Default cap on grep results when head_limit is unspecified
DEFAULT_HEAD_LIMIT = 250

# Max line length to prevent base64/minified content from cluttering output
MAX_COLUMNS = 500


class OutputMode:
    CONTENT = "content"
    FILES_WITH_MATCHES = "files_with_matches"
    COUNT = "count"


@dataclass
class GrepInput:
    """Input schema for grep tool."""
    pattern: str
    path: Optional[str] = None
    glob: Optional[str] = None
    output_mode: str = OutputMode.FILES_WITH_MATCHES
    context_before: Optional[int] = None  # -B
    context_after: Optional[int] = None  # -A
    context: Optional[int] = None  # -C (symmetric)
    show_line_numbers: bool = True  # -n
    case_insensitive: bool = False  # -i
    type_filter: Optional[str] = None  # --type
    head_limit: Optional[int] = DEFAULT_HEAD_LIMIT
    offset: int = 0
    multiline: bool = False


@dataclass
class GrepResult:
    """Result from grep operation."""
    mode: str = OutputMode.FILES_WITH_MATCHES
    num_files: int = 0
    filenames: list[str] = field(default_factory=list)
    content: Optional[str] = None
    num_lines: Optional[int] = None
    num_matches: Optional[int] = None
    applied_limit: Optional[int] = None
    applied_offset: Optional[int] = None


def _apply_head_limit(
    items: list[Any],
    limit: Optional[int],
    offset: int = 0,
) -> tuple[list[Any], Optional[int]]:
    """
    Apply head_limit to a list of items.
    
    Returns (sliced_items, applied_limit) where applied_limit is only
    set when truncation actually occurred.
    """
    # Explicit 0 = unlimited escape hatch
    if limit == 0:
        return items[offset:], None
    
    effective_limit = limit if limit is not None else DEFAULT_HEAD_LIMIT
    sliced = items[offset : offset + effective_limit]
    
    # Only report appliedLimit when truncation actually occurred
    was_truncated = len(items) - offset > effective_limit
    return sliced, effective_limit if was_truncated else None


def _format_limit_info(applied_limit: Optional[int], applied_offset: Optional[int]) -> str:
    """Format limit/offset information for display in tool results."""
    parts = []
    if applied_limit is not None:
        parts.append(f"limit: {applied_limit}")
    if applied_offset:
        parts.append(f"offset: {applied_offset}")
    return ", ".join(parts)


def _build_rg_command(input_data: GrepInput, cwd: str) -> tuple[list[str], str]:
    """
    Build ripgrep command arguments.
    
    Returns (args, search_path).
    """
    args = ["rg", "--hidden"]
    
    # Exclude VCS directories to avoid noise
    for dir_name in VCS_DIRECTORIES_TO_EXCLUDE:
        args.extend(["--glob", f"!{dir_name}"])
    
    # Limit line length
    args.extend(["--max-columns", str(MAX_COLUMNS)])
    
    # Multiline mode
    if input_data.multiline:
        args.extend(["-U", "--multiline-dotall"])
    
    # Case insensitive
    if input_data.case_insensitive:
        args.append("-i")
    
    # Output mode
    if input_data.output_mode == OutputMode.FILES_WITH_MATCHES:
        args.append("-l")
    elif input_data.output_mode == OutputMode.COUNT:
        args.append("-c")
    
    # Line numbers for content mode
    if input_data.show_line_numbers and input_data.output_mode == OutputMode.CONTENT:
        args.append("-n")
    
    # Context flags
    if input_data.output_mode == OutputMode.CONTENT:
        if input_data.context is not None:
            args.extend(["-C", str(input_data.context)])
        else:
            if input_data.context_before is not None:
                args.extend(["-B", str(input_data.context_before)])
            if input_data.context_after is not None:
                args.extend(["-A", str(input_data.context_after)])
    
    # If pattern starts with dash, use -e flag
    if input_data.pattern.startswith("-"):
        args.extend(["-e", input_data.pattern])
    else:
        args.append(input_data.pattern)
    
    # Type filter
    if input_data.type_filter:
        args.extend(["--type", input_data.type_filter])
    
    # Glob patterns
    if input_data.glob:
        # Split on commas and spaces
        glob_patterns = []
        raw_patterns = input_data.glob.split()
        for raw_pattern in raw_patterns:
            if "{" in raw_pattern and "}" in raw_pattern:
                glob_patterns.append(raw_pattern)
            else:
                glob_patterns.extend(p for p in raw_pattern.split(",") if p)
        
        for glob_pattern in glob_patterns:
            args.extend(["--glob", glob_pattern])
    
    # Determine search path
    search_path = input_data.path if input_data.path else cwd
    
    return args, search_path


async def execute_grep(
    input_data: GrepInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
) -> GrepResult:
    """
    Execute a grep search.
    
    Args:
        input_data: GrepInput with search parameters
        cwd: Current working directory
        abort_signal: Optional abort signal
        
    Returns:
        GrepResult with matches
    """
    work_dir = cwd or os.getcwd()
    
    args, search_path = _build_rg_command(input_data, work_dir)
    
    # Expand path if relative
    if not os.path.isabs(search_path):
        search_path = os.path.join(work_dir, search_path)
    
    try:
        # Run ripgrep
        process = await asyncio.create_subprocess_exec(
            "rg",
            *args,
            search_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
        )
        
        try:
            if abort_signal:
                # Wait with abort support
                done, pending = await asyncio.wait(
                    [process.communicate()],
                    timeout=120,  # 2 minute timeout
                )
                
                if not done:
                    process.terminate()
                    await process.wait()
                    return GrepResult()
                
                stdout, stderr = done.pop().result()
            else:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120,
                )
        except asyncio.TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            return GrepResult()
        
        output = stdout.decode("utf-8", errors="replace")
        
        if process.returncode not in (0, 1):
            # ripgrep error
            return GrepResult()
        
    except FileNotFoundError:
        return GrepResult()
    
    # Parse results based on output mode
    if input_data.output_mode == OutputMode.CONTENT:
        return _parse_content_results(output, input_data)
    elif input_data.output_mode == OutputMode.COUNT:
        return _parse_count_results(output, input_data)
    else:
        return _parse_files_results(output, input_data)


def _parse_content_results(output: str, input_data: GrepInput) -> GrepResult:
    """Parse content mode output."""
    lines = [line for line in output.strip().split("\n") if line]
    
    # Apply head_limit
    limited_lines, applied_limit = _apply_head_limit(
        lines, input_data.head_limit, input_data.offset
    )
    
    # Convert absolute paths to relative
    final_lines = []
    for line in limited_lines:
        colon_index = line.index(":") if ":" in line else -1
        if colon_index > 0:
            file_path = line[:colon_index]
            rest = line[colon_index:]
            try:
                rel_path = os.path.relpath(file_path)
                final_lines.append(rel_path + rest)
            except ValueError:
                final_lines.append(line)
        else:
            final_lines.append(line)
    
    result = GrepResult(
        mode=OutputMode.CONTENT,
        num_files=0,
        filenames=[],
        content="\n".join(final_lines),
        num_lines=len(final_lines),
        applied_limit=applied_limit,
        applied_offset=input_data.offset if input_data.offset > 0 else None,
    )
    
    return result


def _parse_count_results(output: str, input_data: GrepInput) -> GrepResult:
    """Parse count mode output."""
    lines = [line for line in output.strip().split("\n") if line]
    
    # Apply head_limit
    limited_lines, applied_limit = _apply_head_limit(
        lines, input_data.head_limit, input_data.offset
    )
    
    # Convert absolute paths to relative and parse counts
    final_lines = []
    total_matches = 0
    file_count = 0
    
    for line in limited_lines:
        last_colon_index = line.rindex(":") if ":" in line else -1
        if last_colon_index > 0:
            file_path = line[:last_colon_index]
            count_str = line[last_colon_index + 1 :]
            try:
                count = int(count_str)
                total_matches += count
                file_count += 1
                rel_path = os.path.relpath(file_path)
                final_lines.append(f"{rel_path}:{count}")
            except ValueError:
                final_lines.append(line)
        else:
            final_lines.append(line)
    
    result = GrepResult(
        mode=OutputMode.COUNT,
        num_files=file_count,
        filenames=[],
        content="\n".join(final_lines),
        num_matches=total_matches,
        applied_limit=applied_limit,
        applied_offset=input_data.offset if input_data.offset > 0 else None,
    )
    
    return result


def _parse_files_results(output: str, input_data: GrepInput) -> GrepResult:
    """Parse files_with_matches mode output."""
    lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
    
    # Apply head_limit
    limited_lines, applied_limit = _apply_head_limit(
        lines, input_data.head_limit, input_data.offset
    )
    
    # Sort by modification time (most recent first)
    def get_mtime(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0
    
    sorted_paths = sorted(
        limited_lines,
        key=lambda p: (get_mtime(p), p),
    )
    
    # Convert to relative paths
    relative_paths = []
    for path in sorted_paths:
        try:
            rel_path = os.path.relpath(path)
            relative_paths.append(rel_path)
        except ValueError:
            relative_paths.append(path)
    
    result = GrepResult(
        mode=OutputMode.FILES_WITH_MATCHES,
        num_files=len(relative_paths),
        filenames=relative_paths,
        applied_limit=applied_limit,
        applied_offset=input_data.offset if input_data.offset > 0 else None,
    )
    
    return result


async def _grep_execute(args: dict, ctx: ToolContext) -> ToolResult:
    """Execute grep tool."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    # Parse input
    input_data = GrepInput(
        pattern=args.get("pattern", ""),
        path=args.get("path"),
        glob=args.get("glob"),
        output_mode=args.get("output_mode", OutputMode.FILES_WITH_MATCHES),
        context_before=args.get("-B") or args.get("context_before"),
        context_after=args.get("-A") or args.get("context_after"),
        context=args.get("-C") or args.get("context"),
        show_line_numbers=args.get("-n", True),
        case_insensitive=args.get("-i", False),
        type_filter=args.get("type"),
        head_limit=args.get("head_limit", DEFAULT_HEAD_LIMIT),
        offset=args.get("offset", 0),
        multiline=args.get("multiline", False),
    )
    
    if not input_data.pattern:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: pattern is required",
            is_error=True,
        )
    
    # Validate path if provided
    if input_data.path:
        abs_path = os.path.abspath(os.path.join(ctx.cwd, input_data.path))
        if not os.path.exists(abs_path):
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Error: Path does not exist: {input_data.path}",
                is_error=True,
            )
    
    try:
        result = await execute_grep(input_data, ctx.cwd)
        
        # Format output based on mode
        if result.mode == OutputMode.CONTENT:
            limit_info = _format_limit_info(result.applied_limit, result.applied_offset)
            content = result.content or "No matches found"
            if limit_info:
                content = f"{content}\n\n[Showing results with pagination = {limit_info}]"
            
            return ToolResult(
                tool_call_id=tool_call_id,
                output=content,
                is_error=False,
            )
        
        elif result.mode == OutputMode.COUNT:
            limit_info = _format_limit_info(result.applied_limit, result.applied_offset)
            matches = result.num_matches or 0
            files = result.num_files or 0
            content = result.content or "No matches found"
            summary = f"\n\nFound {matches} total {'occurrence' if matches == 1 else 'occurrences'} across {files} {'file' if files == 1 else 'files'}"
            if limit_info:
                summary += f" with pagination = {limit_info}"
            
            return ToolResult(
                tool_call_id=tool_call_id,
                output=content + summary,
                is_error=False,
            )
        
        else:  # files_with_matches
            if result.num_files == 0:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output="No files found",
                    is_error=False,
                )
            
            limit_info = _format_limit_info(result.applied_limit, result.applied_offset)
            output_lines = [f"Found {result.num_files} {'file' if result.num_files == 1 else 'files'}"]
            if limit_info:
                output_lines[0] += f" {limit_info}"
            output_lines.extend(result.filenames)
            
            return ToolResult(
                tool_call_id=tool_call_id,
                output="\n".join(output_lines),
                is_error=False,
            )
            
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Grep error: {str(e)}",
            is_error=True,
        )


GREP_TOOL = ToolDef(
    name="grep",
    description="Search file contents with regex (ripgrep). Supports regex patterns, glob filtering, context lines, and multiple output modes.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The regular expression pattern to search for in file contents",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (rg PATH). Defaults to current working directory.",
            },
            "glob": {
                "type": "string",
                "description": 'Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob',
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
                "description": 'Output mode: "content" shows matching lines, "files_with_matches" shows file paths, "count" shows match counts. Defaults to "files_with_matches".',
            },
            "-B": {
                "type": "integer",
                "description": "Number of lines to show before each match (rg -B). Requires output_mode: content.",
            },
            "-A": {
                "type": "integer",
                "description": "Number of lines to show after each match (rg -A). Requires output_mode: content.",
            },
            "-C": {
                "type": "integer",
                "description": "Alias for context - number of lines before and after match.",
            },
            "context": {
                "type": "integer",
                "description": "Number of lines to show before and after each match (rg -C). Requires output_mode: content.",
            },
            "-n": {
                "type": "boolean",
                "description": "Show line numbers in output (rg -n). Requires output_mode: content. Defaults to true.",
            },
            "-i": {
                "type": "boolean",
                "description": "Case insensitive search (rg -i)",
            },
            "type": {
                "type": "string",
                "description": "File type to search (rg --type). Common types: js, py, rust, go, java, etc.",
            },
            "head_limit": {
                "type": "integer",
                "description": f"Limit output to first N lines/entries. Works across all output modes. Defaults to {DEFAULT_HEAD_LIMIT}. Pass 0 for unlimited.",
            },
            "offset": {
                "type": "integer",
                "description": "Skip first N lines/entries before applying head_limit. Defaults to 0.",
            },
            "multiline": {
                "type": "boolean",
                "description": "Enable multiline mode where . matches newlines and patterns can span lines. Default: false.",
            },
        },
        "required": ["pattern"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_grep_execute,
)


__all__ = ["GREP_TOOL", "GrepInput", "GrepResult", "execute_grep", "OutputMode"]
