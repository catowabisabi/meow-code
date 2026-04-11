"""Tool execution logic for async tool execution - complete implementation.

This module provides comprehensive tool execution functionality including:
- Tool executor base class with async execution
- Streaming tool execution for model response streaming
- Permission hooks integration
- Telemetry spans for analytics
- Progress messages during long operations
- Pre-tool and post-tool hooks
- Concurrency control (parallel vs serial execution)
- Tool timeout handling
- Result streaming back to client
"""
from __future__ import annotations

import asyncio
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Optional, Awaitable

from ..tools.types import ToolDef, ToolContext, ToolResult
from .tool_types import (
    ContentBlock,
    ToolProgress,
    ToolUseBlock,
    AssistantMessage,
    PermissionDecision,
    ExecutionContext,
    McpServerType,
    MessageUpdateLazy,
    HookResult,
    ContextModifier,
)


# Constants
HOOK_TIMING_DISPLAY_THRESHOLD_MS = 500
SLOW_PHASE_LOG_THRESHOLD_MS = 2000
DEFAULT_TIMEOUT_MS = 600000  # 10 minutes


@dataclass
class ExecutionMetrics:
    """Metrics collected during tool execution."""
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    pre_tool_hook_duration_ms: Optional[float] = None
    post_tool_hook_duration_ms: Optional[float] = None
    permission_duration_ms: Optional[float] = None


@dataclass
class ToolExecutionContext:
    """Context for tool execution tracking."""
    session_id: str
    user_id: Optional[str]
    tool_id: str
    start_time: datetime = field(default_factory=datetime.now)
    attempt: int = 1
    max_attempts: int = 3


@dataclass
class ToolExecutionResult:
    """Result from tool execution."""
    tool_use_id: str
    content: list[ContentBlock]
    is_error: bool = False
    error_message: Optional[str] = None
    metrics: Optional[ExecutionMetrics] = None


@dataclass
class PermissionContext:
    """Context for permission checks."""
    tool_name: str
    input_data: dict[str, Any]
    session_id: str
    user_id: Optional[str] = None


@dataclass
class PermissionHookResult:
    """Result from a permission hook."""
    approved: bool
    reason: Optional[str] = None
    skip_hooks: bool = False


@dataclass
class PreToolHook:
    """Pre-tool execution hook."""
    name: str
    handler: Callable[[ToolDef, dict[str, Any]], Awaitable[PreHookResult]]


@dataclass
class PostToolHook:
    """Post-tool execution hook."""
    name: str
    handler: Callable[[ToolDef, dict[str, Any], ToolResult], Awaitable[None]]


@dataclass
class PreHookResult:
    """Result from pre-tool hook execution."""
    allowed: bool = True
    message: Optional[str] = None
    updated_input: Optional[dict[str, Any]] = None
    prevent_continuation: bool = False
    stop_reason: Optional[str] = None
    permission_behavior: Optional[str] = None


@dataclass
class StopHookInfo:
    """Information about a stop hook for summary display."""
    command: str
    duration_ms: float


# Telemetry/Analytics event types (placeholders for integration)
class TelemetryEvent:
    """Telemetry event for OTel tracing."""
    
    @staticmethod
    def log_event(name: str, attributes: dict[str, Any]) -> None:
        """Log a telemetry event."""
        # Integration point for telemetry service
        pass
    
    @staticmethod
    def log_otel_event(name: str, attributes: dict[str, Any]) -> None:
        """Log an OTel event."""
        # Integration point for OpenTelemetry tracing
        pass


# Standalone telemetry functions for analytics
def log_tool_event(
    event_name: str,
    tool_name: str,
    tool_use_id: str,
    is_mcp: bool = False,
    **kwargs: Any,
) -> None:
    """Log a tool-related analytics event."""
    event_data = {
        'event_name': event_name,
        'tool_name': tool_name,
        'tool_use_id': tool_use_id,
        'is_mcp': is_mcp,
        **kwargs,
    }
    TelemetryEvent.log_event(event_name, event_data)


def log_otel_event(name: str, attributes: dict[str, Any]) -> None:
    """Log an OpenTelemetry event."""
    TelemetryEvent.log_otel_event(name, attributes)


# Error classification utilities
def classify_tool_error(error: Exception) -> str:
    """Classify a tool execution error into a telemetry-safe string.
    
    Args:
        error: The exception to classify
        
    Returns:
        A string identifier for the error suitable for telemetry
    """
    error_name = getattr(error, 'name', None)
    if error_name and error_name != 'Error' and len(error_name) > 3:
        return error_name[:60]
    
    if hasattr(error, 'telemetry_message'):
        return str(error.telemetry_message)[:200]
    
    if hasattr(error, 'errno') or hasattr(error, 'code'):
        code = getattr(error, 'code', None) or getattr(error, 'errno', None)
        if code:
            return f"Error:{code}"
    
    return 'Error'


def error_message(error: Exception) -> str:
    """Get the error message from an exception."""
    return str(error) if error else "Unknown error"


def get_errno_code(error: Exception) -> Optional[str]:
    """Extract errno code from a Node.js-style error."""
    return getattr(error, 'code', None)


# ============================================================================
# ERROR TYPES FOR TOOL EXECUTION
# ============================================================================

class TelemetrySafeError(Exception):
    """Error with a safe telemetry message for analytics."""
    
    def __init__(self, message: str, telemetry_message: Optional[str] = None):
        super().__init__(message)
        self.telemetry_message = telemetry_message or message


class McpAuthError(Exception):
    """Error indicating MCP server needs re-authorization."""
    
    def __init__(self, message: str, server_name: str):
        super().__init__(message)
        self.server_name = server_name


class McpToolCallError(Exception):
    """Error from MCP tool call with metadata."""
    
    def __init__(self, message: str, mcp_meta: Optional[Any] = None):
        super().__init__(message)
        self.mcp_meta = mcp_meta


class ShellError(Exception):
    """Error from shell command execution."""
    pass


class AbortError(Exception):
    """Error indicating operation was aborted by user."""
    pass


# ============================================================================
# TELEMETRY & ANALYTICS
# ============================================================================

# Global stats store for duration tracking (integration point)
_stats_store: Optional[Any] = None


def set_stats_store(store: Any) -> None:
    """Set the global stats store for duration tracking."""
    global _stats_store
    _stats_store = store


def add_to_tool_duration(duration_ms: float) -> None:
    """Add tool duration to stats store.
    
    Args:
        duration_ms: Tool execution duration in milliseconds
    """
    global _stats_store
    if _stats_store:
        observer = getattr(_stats_store, 'observe', None)
        if observer:
            observer('tool_duration_ms', duration_ms)


def start_session_activity(activity_name: str) -> None:
    """Start a session activity.
    
    Args:
        activity_name: Name of the activity (e.g., 'tool_exec')
    """
    # Integration point for session activity tracking
    pass


def stop_session_activity(activity_name: str) -> None:
    """Stop a session activity.
    
    Args:
        activity_name: Name of the activity to stop
    """
    # Integration point for session activity tracking
    pass


def is_beta_tracing_enabled() -> bool:
    """Check if beta tracing is enabled.
    
    Returns:
        True if beta tracing is enabled
    """
    env_value = os.environ.get("CLAUDE_CODE_BETA_TRACING", "")
    return env_value.lower() in ('true', '1', 'yes')


def is_tool_details_logging_enabled() -> bool:
    """Check if tool details logging is enabled.
    
    Returns:
        True if tool details logging is enabled
    """
    env_value = os.environ.get("OTEL_LOG_TOOL_DETAILS", "")
    return env_value.lower() in ('true', '1', 'yes')


# ============================================================================
# OTel SOURCE MAPPING
# ============================================================================

def rule_source_to_otel_source(
    rule_source: str,
    behavior: str,
) -> str:
    """Map a rule's origin to the documented OTel `source` vocabulary.
    
    Args:
        rule_source: Source of the rule ('session', 'localSettings', 'userSettings', etc.)
        behavior: Rule behavior ('allow' or 'deny')
        
    Returns:
        OTel source label (user_temporary, user_permanent, user_reject, config)
    """
    if rule_source == 'session':
        return 'user_temporary' if behavior == 'allow' else 'user_reject'
    elif rule_source in ('localSettings', 'userSettings'):
        return 'user_permanent' if behavior == 'allow' else 'user_reject'
    else:
        return 'config'


def decision_reason_to_otel_source(
    reason: Optional[Any],
    behavior: str,
) -> str:
    """Map PermissionDecisionReason to the OTel `source` label.
    
    Args:
        reason: PermissionDecisionReason object or None
        behavior: Decision behavior ('allow' or 'deny')
        
    Returns:
        OTel source label
    """
    if reason is None:
        return 'config'
    
    reason_type = getattr(reason, 'type', None)
    
    if reason_type == 'permissionPromptTool':
        # Check for decisionClassification on toolResult
        tool_result = getattr(reason, 'tool_result', None)
        if tool_result and isinstance(tool_result, dict):
            classified = tool_result.get('decisionClassification')
            if classified in ('user_temporary', 'user_permanent', 'user_reject'):
                return classified
        return 'user_temporary' if behavior == 'allow' else 'user_reject'
    
    elif reason_type == 'rule':
        rule_source = getattr(getattr(reason, 'rule', None), 'source', 'config')
        return rule_source_to_otel_source(rule_source, behavior)
    
    elif reason_type == 'hook':
        return 'hook'
    
    elif reason_type in ('mode', 'classifier', 'subcommandResults', 'asyncAgent', 
                          'sandboxOverride', 'workingDir', 'safetyCheck', 'other'):
        return 'config'
    
    return 'config'


# ============================================================================
# SPAN TRACKING FOR TOOL EXECUTION
# ============================================================================

# Global span state (simplified - integration point for real OTel)
_tool_span_stack: list[dict[str, Any]] = []


def start_tool_span(
    tool_name: str,
    attributes: Optional[dict[str, Any]] = None,
    input_json: Optional[str] = None,
) -> None:
    """Start a tool execution span for telemetry.
    
    Args:
        tool_name: Name of the tool
        attributes: Optional span attributes
        input_json: Optional JSON-stringified input (for beta tracing)
    """
    span = {
        'tool_name': tool_name,
        'attributes': attributes or {},
        'input_json': input_json,
        'start_time': time.time() * 1000,
    }
    _tool_span_stack.append(span)
    TelemetryEvent.log_event('tool_span_start', {
        'tool_name': tool_name,
        'attributes': attributes,
    })


def end_tool_span(
    result: Optional[str] = None,
    success: bool = True,
) -> None:
    """End a tool execution span.
    
    Args:
        result: Optional result string
        success: Whether the tool succeeded
    """
    if _tool_span_stack:
        span = _tool_span_stack.pop()
        duration_ms = time.time() * 1000 - span['start_time']
        TelemetryEvent.log_event('tool_span_end', {
            'tool_name': span['tool_name'],
            'duration_ms': duration_ms,
            'success': success,
            'result': result,
        })


def start_tool_blocked_on_user_span() -> None:
    """Start tracking time blocked waiting for user permission."""
    # Integration point for blocked span tracking
    pass


def end_tool_blocked_on_user_span(
    decision: str = 'unknown',
    source: str = 'unknown',
) -> None:
    """End tracking time blocked waiting for user.
    
    Args:
        decision: Permission decision ('allow', 'deny', 'ask')
        source: Decision source
    """
    # Integration point for blocked span tracking
    pass


def start_tool_execution_span() -> None:
    """Start tracking tool execution time."""
    # Integration point for execution span tracking
    pass


def end_tool_execution_span(
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """End tracking tool execution time.
    
    Args:
        success: Whether execution succeeded
        error: Optional error message
    """
    # Integration point for execution span tracking
    pass


def add_tool_content_event(
    name: str,
    attributes: dict[str, Any],
) -> None:
    """Add a content event to the current tool span.
    
    Args:
        name: Event name (e.g., 'tool.output')
        attributes: Event attributes
    """
    TelemetryEvent.log_event(f'tool.{name}', attributes)


# ============================================================================
# HOOK RESULT TYPES
# ============================================================================

@dataclass
class HookResultMessage:
    """Hook result containing a message."""
    message: dict[str, Any]


@dataclass
class HookResultPermission:
    """Hook result containing permission decision."""
    hook_permission_result: Any


@dataclass
class HookResultUpdatedInput:
    """Hook result containing updated input."""
    updated_input: dict[str, Any]


@dataclass
class HookResultPreventContinuation:
    """Hook result indicating continuation should be prevented."""
    should_prevent_continuation: bool


@dataclass
class HookResultStop:
    """Hook result indicating stop."""
    stop_reason: Optional[str] = None


@dataclass
class HookResultAdditionalContext:
    """Hook result containing additional context."""
    message: dict[str, Any]


# ============================================================================
# PERMISSION SYSTEM
# ============================================================================

def strip_simulated_sed_edit(
    tool_name: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Strip _simulatedSedEdit from Bash input for security.
    
    Defense-in-depth: This field is internal-only and must only be injected
    by the permission system after user approval.
    
    Args:
        tool_name: Name of the tool
        input_data: Input data to strip from
        
    Returns:
        Input data without _simulatedSedEdit
    """
    if tool_name != 'Bash':
        return input_data
    
    if not isinstance(input_data, dict):
        return input_data
    
    if '_simulatedSedEdit' not in input_data:
        return input_data
    
    result = {k: v for k, v in input_data.items() if k != '_simulatedSedEdit'}
    return result


async def resolve_hook_permission_decision(
    hook_permission_result: Optional[Any],
    tool: Any,
    processed_input: dict[str, Any],
    tool_use_context: Any,
    can_use_tool_fn: Optional[Any],
    assistant_message: dict[str, Any],
    tool_use_id: str,
) -> tuple[Any, dict[str, Any]]:
    """Resolve permission decision from hook result and canUseTool.
    
    Args:
        hook_permission_result: Result from pre-tool hooks
        tool: Tool definition
        processed_input: Processed input data
        tool_use_context: Execution context
        can_use_tool_fn: Permission check function
        assistant_message: Assistant message
        tool_use_id: Tool use ID
        
    Returns:
        Tuple of (permission_decision, final_input)
    """
    final_input = processed_input
    
    if hook_permission_result is not None:
        permission_decision = hook_permission_result
        if hasattr(hook_permission_result, 'updated_input') and hook_permission_result.updated_input:
            final_input = hook_permission_result.updated_input
    elif can_use_tool_fn:
        try:
            if asyncio.iscoroutinefunction(can_use_tool_fn):
                permission_decision = await can_use_tool_fn(
                    tool,
                    final_input,
                    tool_use_context,
                    assistant_message,
                    tool_use_id,
                )
            else:
                permission_decision = can_use_tool_fn(
                    tool,
                    final_input,
                    tool_use_context,
                    assistant_message,
                    tool_use_id,
                )
            
            if hasattr(permission_decision, 'updated_input') and permission_decision.updated_input:
                final_input = permission_decision.updated_input
        except Exception:
            permission_decision = None
    else:
        permission_decision = None
    
    if permission_decision is None:
        risk_level = getattr(tool, 'risk_level', 'low')
        if risk_level in ('medium', 'high'):
            permission_decision = type('PermissionDecision', (), {
                'behavior': 'ask',
                'message': f'Tool {getattr(tool, "name", "unknown")} requires user permission',
            })()
        else:
            permission_decision = type('PermissionDecision', (), {'behavior': 'allow'})()
    
    return permission_decision, final_input


async def execute_permission_denied_hooks(
    tool_name: str,
    tool_use_id: str,
    processed_input: dict[str, Any],
    reason: str,
    tool_use_context: Any,
    permission_mode: str,
    abort_signal: Any,
) -> list[Any]:
    """Execute permission denied hooks for classifier denials.
    
    Args:
        tool_name: Name of the tool
        tool_use_id: Tool use ID
        processed_input: Processed input data
        reason: Denial reason
        tool_use_context: Execution context
        permission_mode: Permission mode ('auto' or 'manual')
        abort_signal: Abort signal
        
    Returns:
        List of hook results with retry indicator
    """
    results = []
    hook_says_retry = False
    
    hook_fn = getattr(tool_use_context, 'execute_permission_denied_hooks', None)
    if hook_fn:
        try:
            async for result in hook_fn(
                tool_name,
                tool_use_id,
                processed_input,
                reason,
                tool_use_context,
                permission_mode,
                abort_signal,
            ):
                if hasattr(result, 'retry') and result.retry:
                    hook_says_retry = True
                results.append(result)
        except Exception:
            pass
    
    return hook_says_retry, results


# ============================================================================
# ANALYTICS & INPUT/OUTPUT PROCESSING
# ============================================================================

CODE_EDIT_TOOL_NAMES = frozenset([
    'FileEdit',
    'NotebookEdit',
    'file_edit',
    'notebook_edit',
])


def is_code_editing_tool(tool_name: str) -> bool:
    """Check if tool is a code editing tool."""
    return tool_name in CODE_EDIT_TOOL_NAMES


def json_stringify(data: Any) -> str:
    """Stringify data for telemetry."""
    import json
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return str(data)


def extract_tool_input_for_telemetry(input_data: Any) -> Optional[str]:
    """Extract tool input for telemetry (sanitized)."""
    if input_data is None:
        return None
    if isinstance(input_data, dict):
        sanitized = {}
        for key, value in input_data.items():
            if key not in ('password', 'token', 'secret', 'api_key', 'credentials'):
                sanitized[key] = value
        return json_stringify(sanitized)
    return str(input_data)


def get_file_extension_for_analytics(file_path: str) -> Optional[str]:
    """Extract file extension from path for analytics."""
    if not file_path:
        return None
    import os
    _, ext = os.path.splitext(file_path)
    return ext.lstrip('.') if ext else None


def get_file_extensions_from_bash_command(
    command: str,
    simulated_sed_edit_path: Optional[str] = None,
) -> Optional[str]:
    """Extract file extensions from bash command for analytics."""
    import re
    extensions = set()
    if simulated_sed_edit_path:
        ext = get_file_extension_for_analytics(simulated_sed_edit_path)
        if ext:
            extensions.add(ext)
    file_pattern = r'[\w\-\.]+\/[\w\-\.\/]+\.(\w+)'
    matches = re.findall(file_pattern, command)
    extensions.update(matches)
    return ','.join(sorted(extensions)) if extensions else None


def parse_git_commit_id(stdout: str) -> Optional[str]:
    """Parse git commit ID from command output."""
    import re
    match = re.search(r'\b([0-9a-f]{40})\b', stdout)
    if match:
        return match.group(1)[:12]
    match = re.search(r'\b([0-9a-f]{12,40})\b', stdout)
    if match:
        return match.group(1)[:12]
    return None


def extract_mcp_tool_details(tool_name: str) -> Optional[dict[str, str]]:
    """Extract MCP tool details from tool name."""
    if not tool_name.startswith('mcp__'):
        return None
    parts = tool_name.split('__')
    if len(parts) >= 3:
        return {
            'serverName': parts[1],
            'mcpToolName': parts[2],
        }
    return None


def extract_skill_name(tool_name: str, input_data: Any) -> Optional[str]:
    """Extract skill name from tool name and input."""
    if 'skill' in tool_name.lower():
        return tool_name
    if isinstance(input_data, dict):
        return input_data.get('skill_name') or input_data.get('skill')
    return None


# Decision info for telemetry
@dataclass
class DecisionInfo:
    """Information about a permission decision."""
    decision: str
    source: str


# Tool decisions tracking
_tool_decisions: dict[str, DecisionInfo] = {}


def get_tool_decision(tool_use_id: str) -> Optional[DecisionInfo]:
    """Get decision info for a tool use."""
    return _tool_decisions.get(tool_use_id)


def set_tool_decision(tool_use_id: str, decision: str, source: str) -> None:
    """Set decision info for a tool use."""
    _tool_decisions[tool_use_id] = DecisionInfo(decision=decision, source=source)


def delete_tool_decision(tool_use_id: str) -> None:
    """Delete decision info for a tool use."""
    _tool_decisions.pop(tool_use_id, None)


async def build_code_edit_tool_attributes(
    tool: Any,
    input_data: Any,
    decision: str,
    source: str,
) -> dict[str, Any]:
    """Build attributes for code edit tool decision tracking."""
    attributes = {
        'decision': decision,
        'source': source,
        'tool_name': getattr(tool, 'name', 'unknown'),
    }
    if isinstance(input_data, dict):
        file_path = input_data.get('file_path')
        if file_path:
            ext = get_file_extension_for_analytics(file_path)
            if ext:
                attributes['file_extension'] = ext
    return attributes


# Code edit decision counter (integration point)
_code_edit_decision_counter: Optional[Any] = None


def set_code_edit_decision_counter(counter: Any) -> None:
    """Set the code edit decision counter."""
    global _code_edit_decision_counter
    _code_edit_decision_counter = counter


def log_for_debugging(message: str, level: str = 'debug') -> None:
    """Log message for debugging."""
    import logging
    logger = logging.getLogger('tool_execution')
    getattr(logger, level, logger.debug)(message)


def log_error(error: Exception) -> None:
    """Log an error."""
    import logging
    logger = logging.getLogger('tool_execution')
    logger.error(str(error), exc_info=True)


# ============================================================================
# MCP SERVER TYPE DETECTION
# ============================================================================

def get_mcp_server_type(tool_name: str, mcp_clients: list[Any]) -> McpServerType:
    """Extract the MCP server transport type from a tool name.
    
    Args:
        tool_name: Name of the tool (e.g., 'mcp__server__tool')
        mcp_clients: List of MCP server connections
        
    Returns:
        Server type (stdio, sse, http, ws, sdk, etc.) or None for non-MCP tools
    """
    if not tool_name.startswith('mcp__'):
        return None
    
    # Parse mcp__serverName__toolName format
    parts = tool_name.split('__')
    if len(parts) < 3:
        return None
    
    server_name = parts[1]
    
    # Find matching client
    for client in mcp_clients:
        client_name = getattr(client, 'name', None)
        if client_name and _normalize_name_for_mcp(client_name) == server_name:
            if hasattr(client, 'config') and hasattr(client.config, 'type'):
                return getattr(client.config, 'type', 'stdio')
            return 'stdio'
    
    return None


def _normalize_name_for_mcp(name: str) -> str:
    """Normalize a name for MCP comparison."""
    return name.lower().replace('.', '_').replace(' ', '_')


def find_mcp_server_connection(
    tool_name: str,
    mcp_clients: list[Any],
) -> Optional[Any]:
    """Find MCP server connection for a tool.
    
    Args:
        tool_name: Name of the tool
        mcp_clients: List of MCP server connections
        
    Returns:
        The matching MCPServerConnection or None
    """
    if not tool_name.startswith('mcp__'):
        return None
    
    parts = tool_name.split('__')
    if len(parts) < 3:
        return None
    
    server_name = parts[1]
    normalized = _normalize_name_for_mcp(server_name)
    
    for client in mcp_clients:
        client_name = getattr(client, 'name', None)
        if client_name and _normalize_name_for_mcp(client_name) == normalized:
            return client
    
    return None


def get_mcp_server_base_url(tool_name: str, mcp_clients: list[Any]) -> Optional[str]:
    """Get MCP server base URL for a tool.
    
    Args:
        tool_name: Name of the tool
        mcp_clients: List of MCP server connections
        
    Returns:
        Base URL or None for stdio servers, built-in tools, or disconnected servers
    """
    connection = find_mcp_server_connection(tool_name, mcp_clients)
    if not connection:
        return None
    
    config = getattr(connection, 'config', None)
    if not config:
        return None
    
    if hasattr(config, 'url'):
        return getattr(config, 'url', None)
    return None


# Tool finding utilities
def find_tool_by_name(tools: list[ToolDef], tool_name: str) -> Optional[ToolDef]:
    """Find a tool by name in the available tools list.
    
    Args:
        tools: List of available tools
        tool_name: Name of the tool to find
        
    Returns:
        The matching ToolDef or None
    """
    for tool in tools:
        if tool.name == tool_name:
            return tool
        # Check aliases
        if hasattr(tool, 'aliases') and tool.aliases:
            if tool_name in tool.aliases:
                return tool
    return None


# Input validation utilities
@dataclass
class ValidationResult:
    """Result from input validation."""
    result: bool = True
    message: Optional[str] = None
    error_code: Optional[str] = None


def validate_input_schema(tool: ToolDef, input_data: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate tool input against schema.
    
    Args:
        tool: The tool definition
        input_data: Input data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    input_schema = getattr(tool, 'input_schema', None)
    if not input_schema:
        return True, None
    
    safe_parse = getattr(input_schema, 'safe_parse', None)
    if safe_parse:
        result = safe_parse(input_data)
        if hasattr(result, 'success'):
            if result.success:
                return True, None
            error = getattr(result, 'error', None)
            if error:
                if hasattr(error, 'message'):
                    return False, error.message
                return False, str(error)
            return False, "Validation failed"
    
    return True, None


async def validate_tool_input(
    tool: ToolDef,
    input_data: dict[str, Any],
    context: ToolContext,
) -> ValidationResult:
    """Validate tool input values.
    
    Args:
        tool: The tool definition
        input_data: Parsed input data
        context: Tool execution context
        
    Returns:
        ValidationResult indicating if the call is valid
    """
    validate_input = getattr(tool, 'validate_input', None)
    if not validate_input:
        return ValidationResult(result=True)
    
    if asyncio.iscoroutinefunction(validate_input):
        result = await validate_input(input_data, context)
    else:
        result = validate_input(input_data, context)
    
    if isinstance(result, dict):
        return ValidationResult(
            result=result.get('result', True),
            message=result.get('message'),
            error_code=result.get('error_code'),
        )
    
    if isinstance(result, bool):
        return ValidationResult(result=result)
    
    return ValidationResult(result=True)


# Backfill observable input
def backfill_observable_input(
    tool: ToolDef,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Backfill legacy/derived fields on input data.
    
    Args:
        tool: The tool definition
        input_data: Input data to backfill
        
    Returns:
        Backfilled input data
    """
    if not hasattr(tool, 'backfill_observable_input'):
        return input_data
    
    backfill_fn = tool.backfill_observable_input
    if not backfill_fn:
        return input_data
    
    if isinstance(input_data, dict) and input_data is not None:
        clone = {**input_data}
        if asyncio.iscoroutinefunction(backfill_fn):
            # Caller must await this separately if needed
            return clone
        else:
            backfill_fn(clone)
        return clone
    
    return input_data


# Tool execution helpers
async def execute_tool_with_timeout(
    tool: ToolDef,
    input_data: dict[str, Any],
    context: ToolContext,
    timeout_ms: Optional[int] = None,
) -> ToolResult:
    """Execute a tool with optional timeout.
    
    Args:
        tool: The tool definition
        input_data: Input data for the tool
        context: Tool execution context
        timeout_ms: Optional timeout in milliseconds
        
    Returns:
        ToolResult from execution
    """
    tool_call = getattr(tool, 'execute', None)
    if not tool_call:
        return ToolResult(
            tool_call_id=getattr(context, 'tool_use_id', ''),
            output=f"Tool {tool.name} has no execute method",
            is_error=True,
        )
    
    if asyncio.iscoroutinefunction(tool_call):
        if timeout_ms:
            result = await asyncio.wait_for(
                tool_call(input_data, context),
                timeout=timeout_ms / 1000.0,
            )
        else:
            result = await tool_call(input_data, context)
    else:
        result = tool_call(input_data, context)
        if asyncio.iscoroutine(result):
            result = await result
    
    # Convert to ToolResult if needed
    if isinstance(result, dict):
        return ToolResult(
            tool_call_id=getattr(context, 'tool_use_id', ''),
            output=result.get('output', str(result)),
            is_error=result.get('is_error', False),
        )
    elif isinstance(result, ToolResult):
        return result
    else:
        return ToolResult(
            tool_call_id=getattr(context, 'tool_use_id', ''),
            output=str(result) if result else '',
            is_error=False,
        )


# Progress message creation
def create_progress_message(
    tool_use_id: str,
    parent_tool_use_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Create a progress message for streaming.
    
    Args:
        tool_use_id: ID of the tool use
        parent_tool_use_id: ID of the parent tool use
        data: Progress data
        
    Returns:
        Progress message dictionary
    """
    return {
        'type': 'progress',
        'tool_use_id': tool_use_id,
        'parent_tool_use_id': parent_tool_use_id,
        'data': data,
    }


def create_tool_result_message(
    tool_use_id: str,
    content: str,
    is_error: bool = False,
) -> dict[str, Any]:
    """Create a tool result message.
    
    Args:
        tool_use_id: ID of the tool use
        content: Result content
        is_error: Whether the result is an error
        
    Returns:
        Tool result message dictionary
    """
    return {
        'type': 'tool_result',
        'content': content,
        'is_error': is_error,
        'tool_use_id': tool_use_id,
    }


CANCEL_MESSAGE = (
    "The user doesn't want to take this action right now. "
    "STOP what you are doing and wait for the user to tell you how to proceed."
)

REJECT_MESSAGE = (
    "The user doesn't want to proceed with this tool use. "
    "The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file). "
    "STOP what you are doing and wait for the user to tell you how to proceed."
)


def create_tool_result_stop_message(tool_use_id: str) -> dict[str, Any]:
    return {
        'type': 'tool_result',
        'content': CANCEL_MESSAGE,
        'is_error': True,
        'tool_use_id': tool_use_id,
    }


def with_memory_correction_hint(message: str) -> str:
    return message


def create_stop_hook_summary_message(
    hook_count: int,
    hook_infos: list[StopHookInfo],
    hook_errors: list[str],
    prevented_continuation: bool,
    stop_reason: Optional[str],
    has_output: bool,
    level: str,
    tool_use_id: Optional[str] = None,
    hook_label: Optional[str] = None,
    total_duration_ms: Optional[float] = None,
) -> dict[str, Any]:
    return {
        'type': 'system',
        'subtype': 'stop_hook_summary',
        'hookCount': hook_count,
        'hookInfos': [{'command': h.command, 'durationMs': h.duration_ms} for h in hook_infos],
        'hookErrors': hook_errors,
        'preventedContinuation': prevented_continuation,
        'stopReason': stop_reason,
        'hasOutput': has_output,
        'level': level,
        'timestamp': datetime.now().isoformat(),
        'toolUseID': tool_use_id,
        'hookLabel': hook_label,
        'totalDurationMs': total_duration_ms,
    }


def create_error_message(
    tool_use_id: str,
    error: str,
    is_meta: bool = False,
) -> dict[str, Any]:
    """Create an error message.
    
    Args:
        tool_use_id: ID of the tool use
        error: Error message
        is_meta: Whether this is a meta message
        
    Returns:
        Error message dictionary
    """
    return {
        'type': 'user',
        'content': [{
            'type': 'tool_result',
            'content': f'<tool_use_error>{error}</tool_use_error>',
            'is_error': True,
            'tool_use_id': tool_use_id,
        }],
        'tool_use_result': f'Error: {error}',
        'is_meta': is_meta,
    }


# Abort controller for cancellation
class AbortController:
    """Controller for aborting tool execution."""
    
    def __init__(self) -> None:
        self._signal = asyncio.Event()
        self._reason: Optional[str] = None
    
    @property
    def signal(self) -> asyncio.Event:
        return self._signal
    
    @property
    def aborted(self) -> bool:
        return self._signal.is_set()
    
    @property
    def reason(self) -> Optional[str]:
        return self._reason
    
    def abort(self, reason: str = "") -> None:
        """Abort the operation.
        
        Args:
            reason: Reason for aborting
        """
        self._reason = reason
        self._signal.set()
    
    def add_event_listener(self, event: str, handler: Callable) -> None:
        """Add an event listener.
        
        Args:
            event: Event name ('abort')
            handler: Handler function
        """
        if event == "abort":
            self._signal.add_done_callback(handler)
    
    def remove_event_listener(self, event: str, handler: Callable) -> None:
        """Remove an event listener.
        
        Args:
            event: Event name
            handler: Handler function
        """
        pass  # asyncio.Event doesn't support this directly


class CancellationError(Exception):
    """Error raised when operation is cancelled."""
    pass


# Base class for tool executors
class ToolExecutor(ABC):
    """Abstract base class for tool execution."""
    
    @abstractmethod
    async def execute(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        """Execute a tool.
        
        Args:
            tool: Tool definition
            input_data: Input data for the tool
            context: Execution context
            
        Returns:
            ToolExecutionResult
        """
        pass


# Main execution result class
@dataclass
class ExecutionResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_use_id: str = ""


@dataclass
class StreamProgress:
    """Progress update for streaming."""
    tool_use_id: str
    data: Any


# ToolExecutor implementation
class DefaultToolExecutor:
    """Default tool executor implementation."""
    
    def __init__(
        self,
        tools: list[ToolDef],
        timeout_ms: Optional[int] = None,
    ) -> None:
        self._tools = tools
        self._timeout_ms = timeout_ms or DEFAULT_TIMEOUT_MS
        self._abort_controller = AbortController()
        self._pre_hooks: list[PreToolHook] = []
        self._post_hooks: list[PostToolHook] = []
        self._permission_hooks: dict[str, Callable] = {}
    
    @property
    def abort_controller(self) -> AbortController:
        return self._abort_controller
    
    def register_pre_hook(self, hook: PreToolHook) -> None:
        """Register a pre-tool execution hook.
        
        Args:
            hook: Pre-tool hook to register
        """
        self._pre_hooks.append(hook)
    
    def register_post_hook(self, hook: PostToolHook) -> None:
        """Register a post-tool execution hook.
        
        Args:
            hook: Post-tool hook to register
        """
        self._post_hooks.append(hook)
    
    def register_permission_hook(
        self,
        tool_name: str,
        handler: Callable[[PermissionContext], Awaitable[PermissionHookResult]],
    ) -> None:
        """Register a permission hook for a tool.
        
        Args:
            tool_name: Name of the tool
            handler: Permission check handler
        """
        self._permission_hooks[tool_name] = handler
    
    async def execute(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
    ) -> ExecutionResult:
        """Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input data for the tool
            context: Execution context
            
        Returns:
            ExecutionResult
        """
        tool = self._find_tool(tool_name)
        if not tool:
            return ExecutionResult(
                success=False,
                error=f"No such tool available: {tool_name}",
            )
        
        try:
            # Validate input
            is_valid, error = validate_input_schema(tool, tool_input)
            if not is_valid:
                return ExecutionResult(
                    success=False,
                    error=f"Input validation failed for {tool_name}: {error}",
                )
            
            # Run pre hooks
            pre_result = await self._run_pre_hooks(tool, tool_input)
            if pre_result and not pre_result.allowed:
                return ExecutionResult(
                    success=False,
                    error=pre_result.message or "Pre-hook prevented execution",
                )
            
            # Update input if hooks modified it
            if pre_result and pre_result.updated_input:
                tool_input = pre_result.updated_input
            
            # Validate call
            validation_result = await validate_tool_input(tool, tool_input, context)
            if not validation_result.result:
                return ExecutionResult(
                    success=False,
                    error=f"Tool validation failed for {tool_name}: {validation_result.message}",
                )
            
            # Execute
            result = await self._execute_with_timeout(tool, tool_input, context)
            
            # Run post hooks
            await self._run_post_hooks(tool, tool_input, result)
            
            return ExecutionResult(
                success=True,
                data=result.output if isinstance(result, ToolResult) else result,
                tool_use_id=getattr(context, 'tool_use_id', ''),
            )
        
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Tool execution timed out after {self._timeout_ms}ms",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Error calling tool {tool_name}: {str(e)}",
            )
    
    async def stream_output(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
        on_progress: Callable[[StreamProgress], None],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a tool with streaming output.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input data for the tool
            context: Execution context
            on_progress: Callback for progress updates
            
        Yields:
            Output chunks
        """
        tool = self._find_tool(tool_name)
        if not tool:
            yield {
                'type': 'error',
                'error': f"No such tool available: {tool_name}",
            }
            return
        
        try:
            # Validate input
            is_valid, error = validate_input_schema(tool, tool_input)
            if not is_valid:
                yield {
                    'type': 'error',
                    'error': f"Input validation failed for {tool_name}: {error}",
                }
                return
            
            # Validate call
            validation_result = await validate_tool_input(tool, tool_input, context)
            if not validation_result.result:
                yield {
                    'type': 'error',
                    'error': f"Tool validation failed for {tool_name}: {validation_result.message}",
                }
                return
            
            # Stream execute
            async for chunk in self._stream_execute(tool, tool_input, context):
                if isinstance(chunk, dict) and chunk.get('type') == 'progress':
                    on_progress(StreamProgress(
                        tool_use_id=chunk.get('tool_use_id', ''),
                        data=chunk.get('data'),
                    ))
                yield chunk
        
        except asyncio.TimeoutError:
            yield {
                'type': 'error',
                'error': f"Tool execution timed out after {self._timeout_ms}ms",
            }
        except Exception as e:
            yield {
                'type': 'error',
                'error': f"Error calling tool {tool_name}: {str(e)}",
            }
    
    async def check_permission(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionHookResult:
        """Check if a tool execution is permitted.
        
        Args:
            tool: Tool definition
            input_data: Input data
            context: Permission context
            
        Returns:
            PermissionHookResult
        """
        handler = self._permission_hooks.get(tool.name)
        if handler:
            return await handler(context)
        
        # Default: allow all tools
        return PermissionHookResult(approved=True)
    
    def handle_timeout(self, tool_name: str) -> dict[str, Any]:
        """Handle tool timeout.
        
        Args:
            tool_name: Name of the timed out tool
            
        Returns:
            Error response dictionary
        """
        return {
            'type': 'tool_result',
            'content': f'<tool_use_error>Tool execution timed out after {self._timeout_ms}ms</tool_use_error>',
            'is_error': True,
            'tool_use_id': '',
        }
    
    def _find_tool(self, tool_name: str) -> Optional[ToolDef]:
        """Find a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            The matching ToolDef or None
        """
        for tool in self._tools:
            if getattr(tool, 'name', None) == tool_name:
                return tool
        return None
    
    async def _run_pre_hooks(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
    ) -> Optional[PreHookResult]:
        """Run pre-tool hooks.
        
        Args:
            tool: Tool definition
            input_data: Input data
            
        Returns:
            PreHookResult or None
        """
        for hook in self._pre_hooks:
            try:
                result = await hook.handler(tool, input_data)
                if result and not result.allowed:
                    return result
            except Exception:
                pass  # Continue with other hooks
        return None
    
    async def _run_post_hooks(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
        result: ToolResult,
    ) -> None:
        """Run post-tool hooks.
        
        Args:
            tool: Tool definition
            input_data: Input data
            result: Tool result
        """
        for hook in self._post_hooks:
            try:
                await hook.handler(tool, input_data, result)
            except Exception:
                pass  # Don't fail execution due to hook errors
    
    async def _execute_with_timeout(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
        context: Any,
    ) -> ToolResult:
        """Execute tool with timeout.
        
        Args:
            tool: Tool definition
            input_data: Input data
            context: Execution context
            
        Returns:
            ToolResult
        """
        tool_call = getattr(tool, 'execute', None)
        if tool_call is None:
            raise ValueError(f"Tool {getattr(tool, 'name', 'unknown')} has no execute method")
        
        if asyncio.iscoroutinefunction(tool_call):
            return await asyncio.wait_for(
                tool_call(input_data, context),
                timeout=self._timeout_ms / 1000.0,
            )
        
        return await tool_call(input_data, context)
    
    async def _stream_execute(
        self,
        tool: ToolDef,
        input_data: dict[str, Any],
        context: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute tool with streaming.
        
        Args:
            tool: Tool definition
            input_data: Input data
            context: Execution context
            
        Yields:
            Output chunks
        """
        tool_call = getattr(tool, 'execute', None)
        if tool_call is None:
            raise ValueError("Tool has no execute method")
        
        result_gen = tool_call(input_data, context)
        if asyncio.iscoroutine(result_gen):
            result = await result_gen
            if hasattr(result, '__iter__'):
                for item in result:
                    yield item
        elif hasattr(result, '__aiter__'):
            async for item in result:
                yield item
        else:
            yield {'type': 'result', 'data': result}


# Streaming tool executor for tools arriving during model response
class StreamingToolExecutor:
    """Executes tools as they arrive during model response streaming.
    
    This executor handles tools that come in during the model's response stream,
    allowing them to be executed in parallel while the response continues.
    """
    
    def __init__(
        self,
        tools: list[ToolDef],
        max_concurrency: int = 10,
        timeout_ms: Optional[int] = None,
    ) -> None:
        self._tools = tools
        self._max_concurrency = max_concurrency
        self._timeout_ms = timeout_ms or DEFAULT_TIMEOUT_MS
        self._pending_tools: list[dict[str, Any]] = []
        self._tool_results: dict[str, ToolResult] = {}
        self._in_progress: set[str] = set()
        self._aborted: bool = False
        self._abort_controller = AbortController()
        self._lock = asyncio.Lock()
        self._executor = DefaultToolExecutor(tools, timeout_ms)
    
    @property
    def aborted(self) -> bool:
        return self._aborted
    
    async def add_tool(self, tool_use: dict[str, Any]) -> None:
        """Add a tool to the execution queue as it streams in.
        
        Args:
            tool_use: Tool use block with id, name, and input
        """
        async with self._lock:
            self._pending_tools.append(tool_use)
    
    async def execute_pending(self) -> AsyncGenerator[ToolProgress, None]:
        """Execute tools, yielding progress messages.
        
        Yields:
            ToolProgress messages for each tool execution
        """
        while self._pending_tools or self._in_progress:
            # Get tools ready to execute
            tools_to_run = []
            async with self._lock:
                while self._pending_tools and len(self._in_progress) < self._max_concurrency:
                    tool = self._pending_tools.pop(0)
                    tool_id = tool.get('id', '')
                    self._in_progress.add(tool_id)
                    tools_to_run.append(tool)
            
            if not tools_to_run and not self._in_progress:
                break
            
            # Execute all tools in parallel
            tasks = [
                self._execute_single_tool(tool)
                for tool in tools_to_run
            ]
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        yield ToolProgress(
                            tool_use_id='',
                            type='error',
                            message=str(result),
                        )
                    elif result:
                        yield result
            
            # Small delay to prevent tight loop
            await asyncio.sleep(0.01)
    
    async def _execute_single_tool(self, tool_use: dict[str, Any]) -> Optional[ToolProgress]:
        """Execute a single tool.
        
        Args:
            tool_use: Tool use block
            
        Returns:
            ToolProgress or None
        """
        tool_name = tool_use.get('name', '')
        tool_use_id = tool_use.get('id', '')
        input_data = tool_use.get('input', {})
        
        try:
            # Create a minimal context
            context = type('Context', (), {
                'tool_use_id': tool_use_id,
                'cwd': getattr(self, 'cwd', '/'),
                'abort_signal': lambda: self._aborted,
            })()
            
            # Execute
            result = await self._executor.execute(tool_name, input_data, context)
            
            async with self._lock:
                self._in_progress.discard(tool_use_id)
            
            if result.success:
                return ToolProgress(
                    tool_use_id=tool_use_id,
                    type='complete',
                    content=[{
                        'type': 'tool_result',
                        'content': result.data,
                        'is_error': False,
                        'tool_use_id': tool_use_id,
                    }],
                )
            else:
                return ToolProgress(
                    tool_use_id=tool_use_id,
                    type='error',
                    message=result.error,
                )
        
        except Exception as e:
            async with self._lock:
                self._in_progress.discard(tool_use_id)
            
            return ToolProgress(
                tool_use_id=tool_use_id,
                type='error',
                message=str(e),
            )
    
    async def cancel_all(self) -> None:
        """Cancel all pending tool executions."""
        self._aborted = True
        self._abort_controller.abort('All tools cancelled')
        
        async with self._lock:
            self._pending_tools.clear()
            self._in_progress.clear()


# Concurrency utilities
def get_max_tool_use_concurrency() -> int:
    """Get maximum tool use concurrency from environment.
    
    Returns:
        Maximum number of concurrent tool uses
    """
    env_value = os.environ.get("CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY", "")
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass
    return 10


def is_concurrency_safe(tool: ToolDef, input_data: dict[str, Any]) -> bool:
    """Check if a tool call is concurrency safe.
    
    Args:
        tool: Tool definition
        input_data: Input data
        
    Returns:
        True if the tool can run in parallel with other tools
    """
    # Read-only tools are concurrency safe by default
    if getattr(tool, 'is_read_only', False):
        return True
    
    # Check for explicit concurrency safety flag
    is_safe_fn = getattr(tool, 'is_concurrency_safe', None)
    if is_safe_fn:
        return is_safe_fn(input_data)
    
    return False


# Permission checking
async def check_tool_permission(
    tool: ToolDef,
    input_data: dict[str, Any],
    context: PermissionContext,
) -> PermissionHookResult:
    """Check if a tool execution is permitted.
    
    Args:
        tool: Tool definition
        input_data: Input data
        context: Permission context
        
    Returns:
        PermissionHookResult indicating if execution is allowed
    """
    # Check risk level
    risk_level = getattr(tool, 'risk_level', 'low')
    if risk_level == 'low':
        return PermissionHookResult(approved=True)
    
    # High risk tools require explicit permission
    if risk_level == 'high':
        # This would integrate with the permission system
        return PermissionHookResult(approved=False, reason=f"Tool {tool.name} requires permission")
    
    return PermissionHookResult(approved=True)


# Hook execution helpers
async def run_pre_hooks(
    tool: ToolDef,
    input_data: dict[str, Any],
    pre_hooks: list[PreToolHook],
) -> PreHookResult:
    """Run pre-tool hooks.
    
    Args:
        tool: Tool definition
        input_data: Input data
        pre_hooks: List of pre-tool hooks
        
    Returns:
        PreHookResult indicating whether to proceed
    """
    result = PreHookResult(allowed=True)
    
    for hook in pre_hooks:
        try:
            hook_result = await hook.handler(tool, input_data)
            if hook_result and not hook_result.allowed:
                return hook_result
            if hook_result and hook_result.updated_input:
                input_data = hook_result.updated_input
                result.updated_input = input_data
        except Exception:
            pass
    
    return result


async def run_post_hooks(
    tool: ToolDef,
    input_data: dict[str, Any],
    tool_result: ToolResult,
    post_hooks: list[PostToolHook],
) -> None:
    """Run post-tool hooks.
    
    Args:
        tool: Tool definition
        input_data: Input data
        tool_result: Result from tool execution
        post_hooks: List of post-tool hooks
    """
    for hook in post_hooks:
        try:
            await hook.handler(tool, input_data, tool_result)
        except Exception:
            pass  # Don't fail execution due to hook errors


# Utility functions
def classify_error(error: Exception) -> str:
    """Classify an error for telemetry.
    
    Args:
        error: Exception to classify
        
    Returns:
        Error classification string
    """
    return classify_tool_error(error)


def get_next_image_paste_id(messages: list[Any]) -> int:
    """Get the next available image paste ID.
    
    Args:
        messages: List of messages
        
    Returns:
        Next available ID
    """
    max_id = 0
    for message in messages:
        if hasattr(message, 'image_paste_ids'):
            for pid in message.image_paste_ids:
                if pid > max_id:
                    max_id = pid
        elif isinstance(message, dict):
            if 'imagePasteIds' in message:
                for pid in message['imagePasteIds']:
                    if pid > max_id:
                        max_id = pid
    return max_id + 1


def sanitize_tool_name(name: str) -> str:
    """Sanitize a tool name for analytics.
    
    Args:
        name: Tool name
        
    Returns:
        Sanitized tool name
    """
    # Remove any potentially sensitive parts
    if name.startswith('mcp__'):
        parts = name.split('__')
        if len(parts) >= 3:
            return f"mcp__{parts[1]}__{parts[2]}"
    return name


# Message creation helpers
def create_user_message(
    content: list[dict[str, Any]],
    tool_use_result: Optional[str] = None,
    image_paste_ids: Optional[list[int]] = None,
    is_meta: bool = False,
    source_tool_assistant_uuid: Optional[str] = None,
) -> dict[str, Any]:
    """Create a user message dictionary.
    
    Args:
        content: Content blocks
        tool_use_result: Tool use result string
        image_paste_ids: List of image paste IDs
        is_meta: Whether this is a meta message
        source_tool_assistant_uuid: UUID of source assistant message
        
    Returns:
        User message dictionary
    """
    msg = {
        'type': 'user',
        'content': content,
    }
    
    if tool_use_result:
        msg['toolUseResult'] = tool_use_result
    if image_paste_ids:
        msg['imagePasteIds'] = image_paste_ids
    if is_meta:
        msg['isMeta'] = is_meta
    if source_tool_assistant_uuid:
        msg['sourceToolAssistantUUID'] = source_tool_assistant_uuid
    
    return msg


def create_attachment_message(
    msg_type: str,
    decision: Optional[str] = None,
    tool_use_id: Optional[str] = None,
    hook_event: Optional[str] = None,
    message: Optional[str] = None,
    hook_name: Optional[str] = None,
) -> dict[str, Any]:
    """Create an attachment message.
    
    Args:
        msg_type: Attachment type
        decision: Decision string
        tool_use_id: Tool use ID
        hook_event: Hook event name
        message: Message content
        hook_name: Hook name
        
    Returns:
        Attachment message dictionary
    """
    att: dict[str, Any] = {'type': msg_type}
    
    if decision:
        att['decision'] = decision
    if tool_use_id:
        att['toolUseID'] = tool_use_id
    if hook_event:
        att['hookEvent'] = hook_event
    if message:
        att['message'] = message
    if hook_name:
        att['hookName'] = hook_name
    
    return {
        'type': 'attachment',
        'attachment': att,
    }


# Zod validation error formatting
def format_zod_validation_error(tool_name: str, error: Any) -> str:
    """Format a Zod validation error.
    
    Args:
        tool_name: Name of the tool
        error: Zod error object
        
    Returns:
        Formatted error message
    """
    if hasattr(error, 'errors'):
        errors = error.errors()
        if errors:
            messages = []
            for err in errors:
                path = '.'.join(str(p) for p in err.get('path', []))
                messages.append(f"{path}: {err.get('message', 'Invalid value')}" if path else err.get('message', 'Invalid value'))
            return f"InputValidationError: {', '.join(messages)}"
    
    if hasattr(error, 'message'):
        return f"InputValidationError: {error.message}"
    
    return f"InputValidationError: Validation failed for {tool_name}"


def format_error(error: Exception) -> str:
    """Format an exception as an error string.
    
    Args:
        error: Exception to format
        
    Returns:
        Formatted error string
    """
    if isinstance(error, asyncio.TimeoutError):
        return "Tool execution timed out"
    
    error_msg = error_message(error)
    error_type = type(error).__name__
    
    if error_type in ('ValueError', 'TypeError', 'KeyError'):
        return f"{error_type}: {error_msg}"
    
    return error_msg


# Telemetry span helpers
class ToolSpan:
    """Context manager for tool execution spans."""
    
    def __init__(
        self,
        tool_name: str,
        attributes: Optional[dict[str, Any]] = None,
    ) -> None:
        self.tool_name = tool_name
        self.attributes = attributes or {}
        self._start_time = 0.0
        self._end_time = 0.0
    
    def __enter__(self) -> 'ToolSpan':
        self._start_time = time.time() * 1000
        # Log span start
        TelemetryEvent.log_event('tool_span_start', {
            'tool_name': self.tool_name,
            'attributes': self.attributes,
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end_time = time.time() * 1000
        duration = self._end_time - self._start_time
        
        if exc_type:
            TelemetryEvent.log_event('tool_span_end', {
                'tool_name': self.tool_name,
                'duration_ms': duration,
                'error': str(exc_val),
            })
        else:
            TelemetryEvent.log_event('tool_span_end', {
                'tool_name': self.tool_name,
                'duration_ms': duration,
            })
    
    @property
    def duration_ms(self) -> float:
        return self._end_time - self._start_time


# Exports
__all__ = [
    'ToolExecutor',
    'DefaultToolExecutor',
    'StreamingToolExecutor',
    'ExecutionResult',
    'StreamProgress',
    'ToolExecutionContext',
    'ToolExecutionResult',
    'ExecutionMetrics',
    'PermissionContext',
    'PermissionHookResult',
    'PreToolHook',
    'PostToolHook',
    'PreHookResult',
    'StopHookInfo',
    'AbortController',
    'CancellationError',
    'HOOK_TIMING_DISPLAY_THRESHOLD_MS',
    'SLOW_PHASE_LOG_THRESHOLD_MS',
    'DEFAULT_TIMEOUT_MS',
    'get_max_tool_use_concurrency',
    'is_concurrency_safe',
    'check_tool_permission',
    'run_pre_hooks',
    'run_post_hooks',
    'classify_tool_error',
    'error_message',
    'validate_input_schema',
    'validate_tool_input',
    'create_progress_message',
    'create_tool_result_message',
    'create_error_message',
    'create_user_message',
    'create_attachment_message',
    'format_zod_validation_error',
    'format_error',
    'ToolSpan',
    'find_tool_by_name',
    'get_mcp_server_type',
    'find_mcp_server_connection',
    'get_mcp_server_base_url',
    'CANCEL_MESSAGE',
    'REJECT_MESSAGE',
    'create_tool_result_stop_message',
    'with_memory_correction_hint',
    'create_stop_hook_summary_message',
    'TelemetrySafeError',
    'McpAuthError',
    'McpToolCallError',
    'ShellError',
    'AbortError',
    'add_to_tool_duration',
    'start_session_activity',
    'stop_session_activity',
    'is_beta_tracing_enabled',
    'is_tool_details_logging_enabled',
    'rule_source_to_otel_source',
    'decision_reason_to_otel_source',
    'start_tool_span',
    'end_tool_span',
    'start_tool_blocked_on_user_span',
    'end_tool_blocked_on_user_span',
    'start_tool_execution_span',
    'end_tool_execution_span',
    'add_tool_content_event',
    'HookResultMessage',
    'HookResultPermission',
    'HookResultUpdatedInput',
    'HookResultPreventContinuation',
    'HookResultStop',
    'HookResultAdditionalContext',
    'strip_simulated_sed_edit',
    'resolve_hook_permission_decision',
    'execute_permission_denied_hooks',
    'json_stringify',
    'extract_tool_input_for_telemetry',
    'get_file_extension_for_analytics',
    'get_file_extensions_from_bash_command',
    'parse_git_commit_id',
    'extract_mcp_tool_details',
    'extract_skill_name',
    'is_code_editing_tool',
    'DecisionInfo',
    'get_tool_decision',
    'set_tool_decision',
    'delete_tool_decision',
    'build_code_edit_tool_attributes',
    'log_tool_event',
    'log_otel_event',
    'log_for_debugging',
    'log_error',
    'build_schema_not_sent_hint',
    'run_tool_use',
    'streamed_check_permissions_and_call_tool',
    'check_permissions_and_call_tool',
]


# Simple async stream implementation for progress streaming
class AsyncStream:
    """Simple async stream for tool execution results."""
    
    def __init__(self) -> None:
        self._queue: list[Any] = []
        self._done = False
        self._lock = asyncio.Lock()
    
    async def enqueue(self, item: Any) -> None:
        async with self._lock:
            self._queue.append(item)
    
    def error(self, exc: Exception) -> None:
        self._done = True
    
    def done(self) -> None:
        self._done = True
    
    def __aiter__(self):
        return self
    
    async def __anext__(self) -> Any:
        while True:
            async with self._lock:
                if self._queue:
                    return self._queue.pop(0)
                if self._done:
                    raise StopAsyncIteration
            await asyncio.sleep(0.01)


async def run_tool_use(
    tool_use: dict[str, Any],
    assistant_message: dict[str, Any],
    can_use_tool_fn: Optional[Any],
    tool_use_context: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Main entry point for tool use execution.
    
    This is the primary async generator that handles tool execution,
    including permission checks, pre/post hooks, and result streaming.
    
    Args:
        tool_use: Tool use block with id, name, and input
        assistant_message: Assistant message containing context
        can_use_tool_fn: Permission check function
        tool_use_context: Tool use context with options and state
        
    Yields:
        Message updates from tool execution
    """
    tool_name = tool_use.get('name', '')
    
    # Find tool in available tools
    tools = getattr(tool_use_context, 'options', {}).get('tools', []) if tool_use_context else []
    tool = find_tool_by_name(tools, tool_name)
    
    # If not found, check aliases
    if not tool:
        all_tools = getattr(tool_use_context, 'all_tools', []) if tool_use_context else []
        fallback = find_tool_by_name(all_tools, tool_name)
        if fallback and hasattr(fallback, 'aliases') and tool_name in (fallback.aliases or []):
            tool = fallback
    
    message_id = assistant_message.get('message', {}).get('id', '') if isinstance(assistant_message, dict) else ''
    request_id = assistant_message.get('requestId', '') if isinstance(assistant_message, dict) else ''
    
    # Get MCP info if this is an MCP tool
    mcp_clients = getattr(tool_use_context, 'options', {}).get('mcpClients', []) if tool_use_context else []
    mcp_server_type = get_mcp_server_type(tool_name, mcp_clients)
    mcp_server_base_url = get_mcp_server_base_url(tool_name, mcp_clients)
    
    # Handle unknown tool
    if not tool:
        yield {
            'message': create_user_message([
                {
                    'type': 'tool_result',
                    'content': f'<tool_use_error>Error: No such tool available: {tool_name}</tool_use_error>',
                    'is_error': True,
                    'tool_use_id': tool_use.get('id', ''),
                }
            ]),
            'toolUseResult': f'Error: No such tool available: {tool_name}',
            'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
        }
        return
    
    tool_input = tool_use.get('input', {})
    
    try:
        # Check for abort
        abort_controller = getattr(tool_use_context, 'abort_controller', None) if tool_use_context else None
        if abort_controller and hasattr(abort_controller, 'signal') and getattr(abort_controller.signal, 'aborted', False):
            yield {
                'message': create_user_message([
                    create_tool_result_stop_message(tool_use.get('id', ''))
                ]),
                'toolUseResult': CANCEL_MESSAGE,
                'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
            }
            return
        
        # Stream permission check and tool call
        async for update in streamed_check_permissions_and_call_tool(
            tool,
            tool_use.get('id', ''),
            tool_input,
            tool_use_context,
            can_use_tool_fn,
            assistant_message,
            message_id,
            request_id,
            mcp_server_type,
            mcp_server_base_url,
        ):
            yield update
            
    except Exception as e:
        error_msg = str(e)
        tool_info = f' ({tool.name})' if tool else ''
        detailed_error = f'Error calling tool{tool_info}: {error_msg}'
        
        yield {
            'message': create_user_message([
                {
                    'type': 'tool_result',
                    'content': f'<tool_use_error>{detailed_error}</tool_use_error>',
                    'is_error': True,
                    'tool_use_id': tool_use.get('id', ''),
                }
            ]),
            'toolUseResult': detailed_error,
            'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
        }


async def streamed_check_permissions_and_call_tool(
    tool: Any,
    tool_use_id: str,
    input_data: dict[str, Any],
    tool_use_context: Any,
    can_use_tool_fn: Optional[Any],
    assistant_message: dict[str, Any],
    message_id: str,
    request_id: str,
    mcp_server_type: Optional[str],
    mcp_server_base_url: Optional[str],
) -> AsyncGenerator[dict[str, Any], None]:
    """Wrapper that streams progress messages alongside final results.
    
    Args:
        tool: Tool definition
        tool_use_id: Tool use ID
        input_data: Input data for the tool
        tool_use_context: Execution context
        can_use_tool_fn: Permission check function
        assistant_message: Assistant message
        message_id: Message ID
        request_id: Request ID
        mcp_server_type: MCP server type
        mcp_server_base_url: MCP server base URL
        
    Yields:
        Progress messages and final results
    """
    stream = AsyncStream()
    
    async def on_progress(progress: Any) -> None:
        await stream.enqueue({
            'message': create_progress_message(
                progress.get('tool_use_id', tool_use_id),
                tool_use_id,
                progress.get('data', {}),
            )
        })
    
    # Start the check_permissions_and_call_tool task
    task = asyncio.create_task(
        check_permissions_and_call_tool(
            tool,
            tool_use_id,
            input_data,
            tool_use_context,
            can_use_tool_fn,
            assistant_message,
            message_id,
            request_id,
            mcp_server_type,
            mcp_server_base_url,
            on_progress,
        )
    )
    
    # Consume the stream
    async for item in stream:
        yield item
    
    # Wait for completion
    try:
        await task
    except Exception as e:
        stream.error(e)


async def check_permissions_and_call_tool(
    tool: Any,
    tool_use_id: str,
    input_data: dict[str, Any],
    tool_use_context: Any,
    can_use_tool_fn: Optional[Any],
    assistant_message: dict[str, Any],
    message_id: str,
    request_id: str,
    mcp_server_type: Optional[str],
    mcp_server_base_url: Optional[str],
    on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> list[dict[str, Any]]:
    """Main tool execution logic with permission checking and hooks.
    
    This handles:
    - Input validation with schema
    - Pre-tool hooks execution
    - Permission resolution
    - Tool execution with timeout
    - Post-tool hooks execution
    - Result formatting and telemetry
    
    Args:
        tool: Tool definition
        tool_use_id: Tool use ID
        input_data: Input data
        tool_use_context: Execution context
        can_use_tool_fn: Permission check function
        assistant_message: Assistant message
        message_id: Message ID
        request_id: Request ID
        mcp_server_type: MCP server type
        mcp_server_base_url: MCP server base URL
        on_progress: Progress callback
        
    Returns:
        List of result messages
    """
    _resulting_messages = []
    
    # Validate input against schema
    input_schema = getattr(tool, 'input_schema', None)
    parsed_input = input_data
    if input_schema:
        safe_parse = getattr(input_schema, 'safe_parse', None)
        if safe_parse:
            result = safe_parse(input_data)
            if hasattr(result, 'success'):
                if result.success:
                    parsed_input = getattr(result, 'data', input_data)
                else:
                    error = getattr(result, 'error', None)
                    error_content = format_zod_validation_error(tool.name, error) if error else 'Validation failed'
                    
                    return [{
                        'message': create_user_message([
                            {
                                'type': 'tool_result',
                                'content': f'<tool_use_error>InputValidationError: {error_content}</tool_use_error>',
                                'is_error': True,
                                'tool_use_id': tool_use_id,
                            }
                        ]),
                        'toolUseResult': f'InputValidationError: {error}',
                        'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
                    }]
    
    # Validate input values (tool-specific validation)
    validate_input = getattr(tool, 'validate_input', None)
    if validate_input:
        validation_result = await validate_input(parsed_input, tool_use_context)
        if isinstance(validation_result, dict) and validation_result.get('result') is False:
            return [{
                'message': create_user_message([
                    {
                        'type': 'tool_result',
                        'content': f'<tool_use_error>{validation_result.get("message", "Validation failed")}</tool_use_error>',
                        'is_error': True,
                        'tool_use_id': tool_use_id,
                    }
                ]),
                'toolUseResult': f'Error: {validation_result.get("message", "Validation failed")}',
                'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
            }]
    
    processed_input = parsed_input
    
    # Backfill observable input if tool supports it
    backfill_fn = getattr(tool, 'backfill_observable_input', None)
    if backfill_fn and isinstance(processed_input, dict):
        clone = {**processed_input}
        if asyncio.iscoroutinefunction(backfill_fn):
            await backfill_fn(clone)
        else:
            backfill_fn(clone)
        processed_input = clone
    
    # Pre-tool hooks would be executed here
    # For now, we run them via the hook system if available
    
    # Resolve permission decision
    permission_decision = None
    
    # Check permission via canUseTool if available
    if can_use_tool_fn:
        try:
            if asyncio.iscoroutinefunction(can_use_tool_fn):
                permission_decision = await can_use_tool_fn(
                    tool,
                    processed_input,
                    tool_use_context,
                    assistant_message,
                    tool_use_id,
                )
            else:
                permission_decision = can_use_tool_fn(
                    tool,
                    processed_input,
                    tool_use_context,
                    assistant_message,
                    tool_use_id,
                )
        except Exception:
            permission_decision = None
    
    # Default permission handling
    if permission_decision is None:
        # Check tool risk level for default permission
        risk_level = getattr(tool, 'risk_level', 'low')
        if risk_level in ('medium', 'high'):
            permission_decision = {
                'behavior': 'ask',
                'message': f'Tool {tool.name} requires user permission',
            }
        else:
            permission_decision = {'behavior': 'allow'}
    
    # Handle denied permission
    if permission_decision.get('behavior') != 'allow':
        error_msg = permission_decision.get('message') or 'Permission denied'
        
        return [{
            'message': create_user_message([
                {
                    'type': 'tool_result',
                    'content': f'<tool_use_error>{error_msg}</tool_use_error>',
                    'is_error': True,
                    'tool_use_id': tool_use_id,
                }
            ], error_msg),
            'toolUseResult': f'Error: {error_msg}',
            'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
        }]
    
    # Use updated input from permission decision if provided
    if permission_decision.get('updated_input') is not None:
        processed_input = permission_decision['updated_input']
    
    # Execute the tool
    start_time = time.time() * 1000
    tool_result = None
    error_result = None
    
    try:
        tool_call = getattr(tool, 'call', None) or getattr(tool, 'execute', None)
        if not tool_call:
            raise ValueError(f'Tool {tool.name} has no call or execute method')
        
        if asyncio.iscoroutinefunction(tool_call):
            tool_result = await tool_call(
                processed_input,
                {
                    **tool_use_context,
                    'tool_use_id': tool_use_id,
                },
                can_use_tool_fn,
                assistant_message,
            )
        else:
            result = tool_call(
                processed_input,
                {
                    **tool_use_context,
                    'tool_use_id': tool_use_id,
                },
                can_use_tool_fn,
                assistant_message,
            )
            if asyncio.iscoroutine(result):
                tool_result = await result
            else:
                tool_result = result
                
    except asyncio.TimeoutError:
        error_result = f'Tool execution timed out after {DEFAULT_TIMEOUT_MS}ms'
    except Exception as e:
        error_result = str(e)
    
    _duration_ms = time.time() * 1000 - start_time
    
    # Handle error case
    if error_result:
        return [{
            'message': create_user_message([
                {
                    'type': 'tool_result',
                    'content': f'<tool_use_error>{error_result}</tool_use_error>',
                    'is_error': True,
                    'tool_use_id': tool_use_id,
                }
            ]),
            'toolUseResult': f'Error: {error_result}',
            'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
        }]
    
    # Format successful result
    if tool_result:
        # Get output data
        output_data = getattr(tool_result, 'data', None) if isinstance(tool_result, object) else tool_result
        if output_data is None and isinstance(tool_result, dict):
            output_data = tool_result.get('data', tool_result)
        
        # Map to tool result block
        content = output_data if isinstance(output_data, str) else str(output_data or '')
        is_error = getattr(tool_result, 'is_error', False) if isinstance(tool_result, object) else False
        
        map_fn = getattr(tool, 'mapToolResultToToolResultBlockParam', None)
        if map_fn:
            try:
                result_block = map_fn(output_data, tool_use_id)
                if isinstance(result_block, dict):
                    content = result_block.get('content', content)
                    is_error = result_block.get('is_error', is_error)
            except Exception:
                pass
        
        return [{
            'message': create_user_message([
                {
                    'type': 'tool_result',
                    'content': content,
                    'is_error': is_error,
                    'tool_use_id': tool_use_id,
                }
            ]),
            'toolUseResult': content,
            'sourceToolAssistantUUID': assistant_message.get('uuid', '') if isinstance(assistant_message, dict) else '',
        }]
    
    return []


# Retry logic for transient failures
class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_ms: float = 100,
        max_delay_ms: float = 5000,
        exponential_base: float = 2,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base


async def execute_with_retry(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    retry_config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic for transient failures.
    
    Args:
        func: Async function to execute
        *args: Positional arguments
        retry_config: Retry configuration
        **kwargs: Keyword arguments
        
    Returns:
        Result from successful execution
        
    Raises:
        Last exception if all retries fail
    """
    config = retry_config or RetryConfig()
    last_error = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            # Check if error is transient
            if not _is_transient_error(e):
                raise
            
            if attempt < config.max_attempts - 1:
                delay = min(
                    config.base_delay_ms * (config.exponential_base ** attempt),
                    config.max_delay_ms,
                )
                await asyncio.sleep(delay / 1000)
    
    raise last_error


def _is_transient_error(error: Exception) -> bool:
    """Determine if an error is transient and worth retrying.
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error is transient
    """
    error_msg = str(error).lower()
    
    transient_patterns = [
        'timeout',
        'temporary',
        'unavailable',
        'connection',
        'network',
        'refused',
        'reset',
    ]
    
    return any(pattern in error_msg for pattern in transient_patterns)


# Build schema not sent hint for deferred tools
def build_schema_not_sent_hint(
    tool: Any,
    messages: list[Any],
    tools: list[Any],
) -> Optional[str]:
    """Build hint for when tool schema wasn't sent to the model.
    
    Args:
        tool: Tool definition
        messages: Message history
        tools: Available tools
        
    Returns:
        Hint string or None
    """
    # Check if this is a deferred tool
    is_deferred = getattr(tool, 'is_deferred', False) or getattr(tool, 'deferred', False)
    if not is_deferred:
        return None
    
    # Check if tool was discovered
    _discovered_names = set()
    for msg in messages:
        if isinstance(msg, dict) and msg.get('type') == 'user':
            content = msg.get('content', [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        pass
    
    # If not discovered, provide hint
    return (
        f"\n\nThis tool's schema was not sent to the API. "
        f"Load the tool first: call ToolSearch with query \"select:{tool.name}\", then retry this call."
    )
