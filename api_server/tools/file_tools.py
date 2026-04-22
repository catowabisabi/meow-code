"""File operations tool - read, write, edit files.

Based on TypeScript FileEditTool, FileReadTool, FileWriteTool implementations.
Provides safe file operations with conflict detection and backup.
"""
import difflib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .types import ToolDef, ToolResult, ToolContext


BLOCKED_DEVICE_PATHS = frozenset([
    "/dev/zero",
    "/dev/random",
    "/dev/urandom",
    "/dev/full",
    "/dev/stdin",
    "/dev/tty",
    "/dev/console",
    "/dev/stdout",
    "/dev/stderr",
    "/dev/fd/0",
    "/dev/fd/1",
    "/dev/fd/2",
])

THIN_SPACE = "\u202f"

MAX_FILE_READ_SIZE_BYTES = 256 * 1024
MAX_FILE_READ_TOKENS = 25000

OFFSET_INSTRUCTION_DEFAULT = (
    ". To read a specific range, use the offset and limit parameters."
)

OFFSET_INSTRUCTION_TARGETED = (
    ". For large files, use offset and limit to read specific portions."
)


def is_blocked_device_path(file_path: str) -> bool:
    if file_path in BLOCKED_DEVICE_PATHS:
        return True
    if file_path.startswith("/proc/") and file_path.endswith(("/fd/0", "/fd/1", "/fd/2")):
        return True
    return False


def expand_path(file_path: str) -> str:
    return os.path.abspath(os.path.expanduser(file_path))


def detect_session_file_type(file_path: str) -> Optional[str]:
    config_home = os.path.expanduser("~/.claude")
    if not file_path.startswith(config_home):
        return None
    normalized = file_path.replace(os.sep, "/")
    if "/session-memory/" in normalized and normalized.endswith(".md"):
        return "session_memory"
    if "/projects/" in normalized and normalized.endswith(".jsonl"):
        return "session_transcript"
    return None


def estimate_tokens(content: str) -> int:
    return math.ceil(len(content) / 4)


def format_file_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def add_line_numbers(content: str, start_line: int = 1) -> str:
    lines = content.split("\n")
    numbered = []
    for i, line in enumerate(lines):
        line_no = start_line + i
        numbered.append(f"{line_no}\t{line}")
    return "\n".join(numbered)


def normalize_line_endings(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def count_lines(content: str) -> int:
    if not content:
        return 0
    return content.count("\n") + (1 if not content.endswith("\n") else 0)


class MaxFileReadTokenExceededError(Exception):
    def __init__(self, token_count: int, max_tokens: int):
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            f"File content ({token_count} tokens) exceeds maximum allowed tokens ({max_tokens}). "
            "Use offset and limit parameters to read specific portions of the file."
        )


class FileTooLargeError(Exception):
    def __init__(self, size_bytes: int, max_size_bytes: int):
        self.size_bytes = size_bytes
        self.max_size_bytes = max_size_bytes
        super().__init__(
            f"File content ({format_file_size(size_bytes)}) exceeds maximum allowed size "
            f"({format_file_size(max_size_bytes)}). Use offset and limit parameters."
        )


class EditConflictError(Exception):
    pass


@dataclass
class FileReadResult:
    content: str
    num_lines: int
    start_line: int
    total_lines: int
    file_path: str
    is_truncated: bool = False
    token_count: int = 0


@dataclass
class FileWriteResult:
    type: str
    file_path: str
    content: str
    line_count: int
    byte_count: int
    original_file: Optional[str] = None


@dataclass
class FileEditResult:
    file_path: str
    old_string: str
    new_string: str
    original_file: str
    occurrences: int
    replace_all: bool = False


@dataclass
class StructuredDiffLine:
    """A single line in a structured diff."""
    type: str  # 'context', 'add', 'remove'
    content: str


@dataclass
class StructuredDiffPatch:
    """Structured diff representation matching Claude Code CLI format."""
    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    lines: list[StructuredDiffLine]


@dataclass 
class FileEditOutput:
    """Enhanced output from file_edit with structured diff."""
    filePath: str
    oldString: str
    newString: str
    originalFile: str
    structuredPatch: list[StructuredDiffPatch]
    userModified: bool = False
    replaceAll: bool = False
    gitDiff: Optional[dict] = None


def generate_structured_diff(
    original_content: str,
    new_content: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> list[StructuredDiffPatch]:
    """
    Generate a structured diff between original and new content.
    
    Uses difflib to compute unified diff and transforms it into
    Claude Code CLI's structured patch format.
    """
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    matcher = difflib.SequenceMatcher(None, original_lines, new_lines)
    
    patches = []
    for group in matcher.get_grouped_opcodes(0):
        old_start = group[0][1] + 1
        old_lines_count = group[-1][2] - group[0][1]
        new_start = group[0][3] + 1
        new_lines_count = group[-1][4] - group[0][3]
        
        diff_lines = []
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in original_lines[i1:i2]:
                    diff_lines.append(StructuredDiffLine(type='context', content=line.rstrip('\n\r')))
            elif tag == 'replace' or tag == 'delete':
                for line in original_lines[i1:i2]:
                    diff_lines.append(StructuredDiffLine(type='remove', content=line.rstrip('\n\r')))
            elif tag == 'insert':
                for line in new_lines[j1:j2]:
                    diff_lines.append(StructuredDiffLine(type='add', content=line.rstrip('\n\r')))
        
        patches.append(StructuredDiffPatch(
            oldStart=old_start,
            oldLines=old_lines_count,
            newStart=new_start,
            newLines=new_lines_count,
            lines=diff_lines,
        ))
    
    return patches


def format_unified_diff(patches: list[StructuredDiffPatch], file_path: str) -> str:
    """Format structured patches as a unified diff string."""
    lines = []
    for patch in patches:
        old_range = f"{patch.oldStart},{patch.oldLines}" if patch.oldLines > 1 else str(patch.oldStart)
        new_range = f"{patch.newStart},{patch.newLines}" if patch.newLines > 1 else str(patch.newStart)
        
        lines.append(f"--- a/{file_path}")
        lines.append(f"+++ b/{file_path}")
        lines.append(f"@@ -{old_range} +{new_range} @@")
        
        for diff_line in patch.lines:
            prefix = ' ' if diff_line.type == 'context' else '+' if diff_line.type == 'add' else '-'
            lines.append(f"{prefix} {diff_line.content}")
    
    return '\n'.join(lines)


def _read_file_range(
    file_path: str,
    offset: int = 0,
    limit: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> FileReadResult:
    path = Path(file_path)
    stat = path.stat()
    total_bytes = stat.st_size
    
    if stat.is_dir():
        raise ValueError(f"EISDIR: illegal operation on a directory, read '{file_path}'")
    
    content = path.read_text(encoding="utf-8", errors="replace")
    content = normalize_line_endings(content)
    
    lines = content.split("\n")
    total_lines = len(lines)
    
    if offset < 0:
        offset = 0
    if offset >= total_lines:
        return FileReadResult(
            content="",
            num_lines=0,
            start_line=offset + 1,
            total_lines=total_lines,
            file_path=file_path,
        )
    
    end_line = total_lines if limit is None else offset + limit
    selected_lines = lines[offset:end_line]
    selected_content = "\n".join(selected_lines)
    
    is_truncated = False
    if max_bytes is not None and len(selected_content.encode("utf-8")) > max_bytes:
        truncated_bytes = 0
        result_lines = []
        for line in selected_lines:
            line_bytes = len(line.encode("utf-8")) + 1
            if truncated_bytes + line_bytes > max_bytes:
                is_truncated = True
                break
            result_lines.append(line)
            truncated_bytes += line_bytes
        selected_content = "\n".join(result_lines)
        selected_lines = result_lines
    
    num_lines = len(selected_lines)
    start_line = offset + 1
    token_count = estimate_tokens(selected_content)
    
    return FileReadResult(
        content=selected_content,
        num_lines=num_lines,
        start_line=start_line,
        total_lines=total_lines,
        file_path=file_path,
        is_truncated=is_truncated,
        token_count=token_count,
    )


FILE_READ_TOOL = ToolDef(
    name="file_read",
    description=(
        "Read the contents of a file. Returns content with line numbers. "
        "Supports offset and limit for partial reads. "
        f"Files larger than {format_file_size(MAX_FILE_READ_SIZE_BYTES)} will return an error."
        + OFFSET_INSTRUCTION_DEFAULT
    ),
    input_schema={
        "type": "object",
        "required": ["file_path"],
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the file to read"},
            "offset": {"type": "number", "description": "Line number to start reading from (1-based). Only provide if the file is too large to read at once."},
            "limit": {"type": "number", "description": "Number of lines to read. Only provide if the file is too large to read at once."},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _file_read(args, ctx),
)


async def _file_read(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        file_path = args["file_path"]
        full_path = expand_path(file_path)
        
        if is_blocked_device_path(full_path):
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Cannot read '{file_path}': this device file would block or produce infinite output.",
                is_error=True,
            )
        
        path = Path(full_path)
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"File does not exist: {file_path}",
                is_error=True,
            )
        
        stat = path.stat()
        if stat.st_size > MAX_FILE_READ_SIZE_BYTES:
            raise FileTooLargeError(stat.st_size, MAX_FILE_READ_SIZE_BYTES)
        
        offset = args.get("offset", 1)
        if offset < 1:
            offset = 1
        offset -= 1
        
        limit = args.get("limit")
        
        result = _read_file_range(
            full_path,
            offset=offset,
            limit=limit,
            max_bytes=MAX_FILE_READ_SIZE_BYTES,
        )
        
        token_count = estimate_tokens(result.content)
        if token_count > MAX_FILE_READ_TOKENS:
            raise MaxFileReadTokenExceededError(token_count, MAX_FILE_READ_TOKENS)
        
        formatted_content = add_line_numbers(result.content, result.start_line)
        
        if result.is_truncated:
            formatted_content += "\n[Truncated by byte limit]"
        
        if result.content:
            output = formatted_content
        else:
            if result.total_lines == 0:
                output = "<system-reminder>Warning: the file exists but the contents are empty.</system-reminder>"
            else:
                output = f"<system-reminder>Warning: the file exists but is shorter than the provided offset ({result.start_line}). The file has {result.total_lines} lines.</system-reminder>"
        
        return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
    except MaxFileReadTokenExceededError as e:
        return ToolResult(tool_call_id=tool_call_id, output=str(e), is_error=True)
    except FileTooLargeError as e:
        return ToolResult(tool_call_id=tool_call_id, output=str(e), is_error=True)
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {err}", is_error=True)


FILE_WRITE_TOOL = ToolDef(
    name="file_write",
    description=(
        "Write content to a file. Creates parent directories if needed. "
        "Overwrites existing files. Returns detailed result with line count and bytes written."
    ),
    input_schema={
        "type": "object",
        "required": ["file_path", "content"],
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to write to"},
            "content": {"type": "string", "description": "Content to write to the file"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=lambda args, ctx: _file_write(args, ctx),
)


async def _file_write(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        file_path = args["file_path"]
        content = args["content"]
        full_path = expand_path(file_path)

        # Restrict writes to the project working directory
        if ctx.cwd:
            allowed_root = os.path.abspath(ctx.cwd)
            if not full_path.startswith(allowed_root + os.sep) and full_path != allowed_root:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Error: cannot write outside project directory ({allowed_root}). Path: {full_path}",
                    is_error=True,
                )

        path = Path(full_path)
        original_content = None
        file_existed = path.exists()
        
        if file_existed:
            original_content = path.read_text(encoding="utf-8", errors="replace")
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        normalized_content = normalize_line_endings(content)
        path.write_text(normalized_content, encoding="utf-8")
        
        line_count = count_lines(normalized_content)
        byte_count = len(normalized_content.encode("utf-8"))
        
        if original_content is not None:
            output = f"Updated file: {file_path}\nLines: {line_count}\nBytes: {byte_count}"
        else:
            output = f"Created file: {file_path}\nLines: {line_count}\nBytes: {byte_count}"
        
        return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {err}", is_error=True)


FILE_EDIT_TOOL = ToolDef(
    name="file_edit",
    description=(
        "Edit a file by replacing an exact string match. "
        "Validates that old_string exists and is unique before making changes. "
        "Supports replace_all to replace all occurrences."
    ),
    input_schema={
        "type": "object",
        "required": ["file_path", "old_string", "new_string"],
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the file"},
            "old_string": {"type": "string", "description": "Exact text to replace"},
            "new_string": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "description": "Replace all occurrences (default: false)"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=lambda args, ctx: _file_edit(args, ctx),
)


async def _file_edit(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        file_path = args["file_path"]
        old_str = args["old_string"]
        new_str = args["new_string"]
        replace_all = args.get("replace_all", False)
        full_path = expand_path(file_path)

        if ctx.cwd:
            allowed_root = os.path.abspath(ctx.cwd)
            if not full_path.startswith(allowed_root + os.sep) and full_path != allowed_root:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Error: cannot edit outside project directory ({allowed_root}). Path: {full_path}",
                    is_error=True,
                )

        if old_str == new_str:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="No changes to make: old_string and new_string are exactly the same.",
                is_error=True,
            )
        
        path = Path(full_path)
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"File does not exist: {file_path}",
                is_error=True,
            )
        
        content = path.read_text(encoding="utf-8", errors="replace")
        normalized_content = normalize_line_endings(content)
        
        count = normalized_content.count(old_str)
        
        if count == 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"String to replace not found in file.\nString: {old_str}",
                is_error=True,
            )
        
        if count > 1 and not replace_all:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Found {count} matches of the string to replace, but replace_all is false. "
                       f"To replace all occurrences, set replace_all to true. "
                       f"To replace only one occurrence, please provide more context to uniquely identify the instance.\n"
                       f"String: {old_str}",
                is_error=True,
            )
        
        if replace_all:
            new_content = normalized_content.replace(old_str, new_str)
            occurrences = count
        else:
            first_idx = normalized_content.index(old_str)
            new_content = normalized_content[:first_idx] + new_str + normalized_content[first_idx + len(old_str):]
            occurrences = 1
        
        patches = generate_structured_diff(
            normalized_content,
            new_content,
            old_str,
            new_str,
            replace_all,
        )
        
        path.write_text(new_content, encoding="utf-8")
        
        unified_diff = format_unified_diff(patches, file_path)
        
        if replace_all:
            output = f"Replaced all {occurrences} occurrences in {file_path}\n\n```diff\n{unified_diff}\n```"
        else:
            output = f"Replaced 1 occurrence in {file_path}\n\n```diff\n{unified_diff}\n```"
        
        metadata = {
            "exitCode": 0,
            "occurrences": occurrences,
            "structuredPatch": [
                {
                    "oldStart": patch.oldStart,
                    "oldLines": patch.oldLines,
                    "newStart": patch.newStart,
                    "newLines": patch.newLines,
                    "lines": [{"type": line.type, "content": line.content} for line in patch.lines],
                }
                for patch in patches
            ],
        }
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=output,
            is_error=False,
            metadata=metadata,
        )
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {err}", is_error=True)


GLOB_TOOL = ToolDef(
    name="glob",
    description=(
        'Find files by glob pattern (e.g. "**/*.ts", "src/**/*.tsx"). '
        "Returns matching file paths sorted by modification time (most recent first). "
        "Limited to 200 results."
    ),
    input_schema={
        "type": "object",
        "required": ["pattern"],
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern to match"},
            "path": {"type": "string", "description": "Directory to search in (default: cwd)"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _glob(args, ctx),
)


async def _glob(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        pattern = args["pattern"]
        search_path = args.get("path") or ctx.cwd
        
        base = Path(search_path)
        if not base.is_dir():
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Directory not found: {search_path}",
                is_error=True,
            )
        
        files = []
        for f in base.rglob(pattern):
            if f.is_file():
                try:
                    f.stat()
                    files.append(f)
                except (OSError, PermissionError):
                    continue
        
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        files = files[:200]
        
        if not files:
            return ToolResult(tool_call_id=tool_call_id, output="No files found.", is_error=False)
        
        result_lines = [str(f) for f in files]
        return ToolResult(tool_call_id=tool_call_id, output="\n".join(result_lines), is_error=False)
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {err}", is_error=True)


GREP_TOOL = ToolDef(
    name="grep",
    description=(
        "Search file contents using regex patterns. Returns matching lines with "
        "file paths, line numbers, and surrounding context lines. "
        "Limited to 100 matches. Binary files are skipped."
    ),
    input_schema={
        "type": "object",
        "required": ["pattern"],
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "File or directory to search in (default: cwd)"},
            "include": {"type": "string", "description": "File glob pattern to filter (e.g. '*.ts')"},
            "context": {"type": "number", "description": "Number of context lines before/after match (default: 0)"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: _grep(args, ctx),
)


async def _grep(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        pattern = args["pattern"]
        search_path = args.get("path") or ctx.cwd
        include = args.get("include")
        context_lines = args.get("context", 0)
        
        try:
            regex = re.compile(pattern)
        except re.error as err:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Invalid regex pattern: {err}",
                is_error=True,
            )
        
        base = Path(search_path)
        if not base.exists():
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Path not found: {search_path}",
                is_error=True,
            )
        
        BINARY_EXTENSIONS = {
            ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
            ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
            ".mp3", ".mp4", ".avi", ".mov", ".wav",
            ".pyc", ".class", ".o", ".obj",
        }
        
        def is_binary_file(path: Path) -> bool:
            if path.suffix.lower() in BINARY_EXTENSIONS:
                return True
            try:
                with open(path, "rb") as f:
                    f.read(8192)
                return False
            except:
                return True
        
        files_to_search = []
        if base.is_file():
            if not is_binary_file(base):
                files_to_search.append(base)
        else:
            if include:
                for f in base.rglob(include):
                    if f.is_file() and not is_binary_file(f):
                        files_to_search.append(f)
            else:
                for f in base.rglob("*"):
                    if f.is_file() and not is_binary_file(f):
                        if f.stat().st_size < 10 * 1024 * 1024:
                            files_to_search.append(f)
        
        matches: list[str] = []
        file_matches: dict[str, list[tuple[int, str]]] = {}
        
        for file_path in files_to_search[:500]:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                
                for line_no, line in enumerate(lines, start=1):
                    if regex.search(line):
                        if file_path not in file_matches:
                            file_matches[file_path] = []
                        file_matches[file_path].append((line_no, line))
            except Exception:
                continue
        
        for file_path, lines_data in file_matches.items():
            for line_no, line in lines_data:
                if context_lines > 0:
                    start_context = max(0, line_no - context_lines - 1)
                    end_context = min(len(lines), line_no + context_lines)
                    context_before = lines[max(0, line_no - context_lines - 1):line_no - 1]
                    context_after = lines[line_no:end_context]
                    
                    if context_before:
                        for ctx_line_no, ctx_line in enumerate(context_before, start=start_context + 1):
                            matches.append(f"{file_path}:{ctx_line_no}:{ctx_line}")
                    matches.append(f"{file_path}:{line_no}:{line}")
                    if context_after:
                        for ctx_line_no, ctx_line in enumerate(context_after, start=line_no + 1):
                            matches.append(f"{file_path}:{ctx_line_no}:{ctx_line}")
                    matches.append("---")
                else:
                    matches.append(f"{file_path}:{line_no}:{line}")
                
                if len(matches) >= 100:
                    break
            if len(matches) >= 100:
                break
        
        if context_lines > 0 and matches and matches[-1] == "---":
            matches.pop()
        
        if not matches:
            return ToolResult(tool_call_id=tool_call_id, output="No matches found.", is_error=False)
        
        return ToolResult(tool_call_id=tool_call_id, output="\n".join(matches), is_error=False)
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {err}", is_error=True)


FILE_TOOLS: list[ToolDef] = [
    FILE_READ_TOOL,
    FILE_WRITE_TOOL,
    FILE_EDIT_TOOL,
    GLOB_TOOL,
    GREP_TOOL,
]

__all__ = [
    "FILE_TOOLS",
    "FILE_READ_TOOL",
    "FILE_WRITE_TOOL",
    "FILE_EDIT_TOOL",
    "GLOB_TOOL",
    "GREP_TOOL",
    "MaxFileReadTokenExceededError",
    "FileTooLargeError",
    "EditConflictError",
]