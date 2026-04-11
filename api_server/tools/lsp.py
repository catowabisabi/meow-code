"""
LSPTool - Language Server Protocol tool for code intelligence.

Provides LSP operations:
- goToDefinition: Jump to symbol definition
- findReferences: Find all references to a symbol
- hover: Get hover information
- documentSymbol: Get document symbols
- workspaceSymbol: Search workspace symbols
- goToImplementation: Go to implementation
- prepareCallHierarchy: Prepare call hierarchy
- incomingCalls: Find incoming calls
- outgoingCalls: Find outgoing calls

Based on the TypeScript LSPTool implementation in _claude_code_leaked_source_code.
"""
from enum import Enum
from typing import Any, Optional
from urllib.parse import unquote

try:
    from ..lsp import (
        get_lsp_server_manager,
        get_initialization_status,
        wait_for_initialization,
        go_to_definition as lsp_go_to_definition,
        find_references as lsp_find_references,
        hover as lsp_hover,
        document_symbol as lsp_document_symbol,
        workspace_symbol as lsp_workspace_symbol,
        go_to_implementation as lsp_go_to_implementation,
        prepare_call_hierarchy as lsp_prepare_call_hierarchy,
        incoming_calls as lsp_incoming_calls,
        outgoing_calls as lsp_outgoing_calls,
    )
    HAS_LSP = True
except ImportError:
    HAS_LSP = False

from .types import ToolDef, ToolContext, ToolResult


class LSLOperation(Enum):
    GO_TO_DEFINITION = "goToDefinition"
    FIND_REFERENCES = "findReferences"
    HOVER = "hover"
    DOCUMENT_SYMBOL = "documentSymbol"
    WORKSPACE_SYMBOL = "workspaceSymbol"
    GO_TO_IMPLEMENTATION = "goToImplementation"
    PREPARE_CALL_HIERARCHY = "prepareCallHierarchy"
    INCOMING_CALLS = "incomingCalls"
    OUTGOING_CALLS = "outgoingCalls"


LSP_TOOL_NAME = "lsp"


def _uri_to_file_path(uri: str) -> str:
    """Convert file:// URI to file path, decoding percent-encoded characters."""
    if not uri.startswith("file://"):
        return uri
    
    path = uri[7:]
    
    # On Windows, file:///C:/path becomes /C:/path - strip the leading slash
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    
    try:
        path = unquote(path)
    except Exception:
        pass
    
    return path


def _count_unique_files(locations: list) -> int:
    """Count unique files from an array of locations."""
    uris = set()
    for loc in locations:
        if hasattr(loc, "uri"):
            uris.add(loc.uri)
        elif isinstance(loc, dict) and "uri" in loc:
            uris.add(loc["uri"])
    return len(uris)


async def _lsp_execute(args: dict, ctx: ToolContext) -> ToolResult:
    """Execute LSP operation."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_LSP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="LSP service not available",
            is_error=True,
        )
    
    operation = args.get("operation", "")
    file_path = args.get("filePath", "")
    line = args.get("line", 1)
    character = args.get("character", 1)
    query = args.get("query", "")
    
    # Wait for initialization if still pending
    status = get_initialization_status()
    if status.status.value == "pending":
        await wait_for_initialization()
    
    manager = get_lsp_server_manager()
    if not manager:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="LSP server manager not initialized. This may indicate a startup issue.",
            is_error=True,
        )
    
    try:
        op = LSLOperation(operation)
    except ValueError:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Unknown operation: {operation}. Valid operations: {[e.value for e in LSLOperation]}",
            is_error=True,
        )
    
    try:
        result = None
        result_count = 0
        file_count = 0
        
        if op == LSLOperation.GO_TO_DEFINITION:
            result = await lsp_go_to_definition(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                else:
                    result_count = 1
                    file_count = 1
                    
        elif op == LSLOperation.FIND_REFERENCES:
            result = await lsp_find_references(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                else:
                    result_count = 1
                    
        elif op == LSLOperation.HOVER:
            result = await lsp_hover(file_path, line, character)
            if result:
                result_count = 1
                file_count = 1
                
        elif op == LSLOperation.DOCUMENT_SYMBOL:
            result = await lsp_document_symbol(file_path)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = 1
                    
        elif op == LSLOperation.WORKSPACE_SYMBOL:
            result = await lsp_workspace_symbol(query)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                    
        elif op == LSLOperation.GO_TO_IMPLEMENTATION:
            result = await lsp_go_to_implementation(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                else:
                    result_count = 1
                    
        elif op == LSLOperation.PREPARE_CALL_HIERARCHY:
            result = await lsp_prepare_call_hierarchy(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                    
        elif op == LSLOperation.INCOMING_CALLS:
            result = await lsp_incoming_calls(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
                    
        elif op == LSLOperation.OUTGOING_CALLS:
            result = await lsp_outgoing_calls(file_path, line, character)
            if result:
                if isinstance(result, list):
                    result_count = len(result)
                    file_count = _count_unique_files(result)
        
        if result is None:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"No LSP server available for file type: {file_path}",
                is_error=False,
            )
        
        # Format result
        if isinstance(result, list):
            formatted_parts = []
            for item in result[:50]:  # Limit to 50 results
                if hasattr(item, "uri"):
                    path = _uri_to_file_path(item.uri)
                    if hasattr(item, "range") and item.range:
                        start = item.range.start
                        formatted_parts.append(f"{path}:{start.line + 1}:{start.character + 1}")
                    else:
                        formatted_parts.append(path)
                elif isinstance(item, dict):
                    path = item.get("uri", "")
                    if path:
                        path = _uri_to_file_path(path)
                    if "range" in item and item["range"]:
                        start = item["range"].get("start", {})
                        formatted_parts.append(f"{path}:{start.get('line', 0) + 1}:{start.get('character', 0) + 1}")
                    else:
                        formatted_parts.append(path)
                else:
                    formatted_parts.append(str(item))
            
            output = "\n".join(formatted_parts)
            if len(result) > 50:
                output += f"\n... and {len(result) - 50} more results"
        else:
            output = str(result)
        
        # Add result metadata
        if result_count > 0:
            output += f"\n\n[Result count: {result_count}, Files: {file_count}]"
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=output,
            is_error=False,
        )
        
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"LSP error for {operation} on {file_path}: {str(e)}",
            is_error=True,
        )


LSP_TOOL = ToolDef(
    name=LSP_TOOL_NAME,
    description="Language Server Protocol tool for code intelligence (definitions, references, hover, symbols, call hierarchy)",
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "goToDefinition",
                    "findReferences",
                    "hover",
                    "documentSymbol",
                    "workspaceSymbol",
                    "goToImplementation",
                    "prepareCallHierarchy",
                    "incomingCalls",
                    "outgoingCalls",
                ],
                "description": "The LSP operation to perform",
            },
            "filePath": {
                "type": "string",
                "description": "The absolute or relative path to the file",
            },
            "line": {
                "type": "integer",
                "minimum": 1,
                "description": "The line number (1-based, as shown in editors)",
            },
            "character": {
                "type": "integer",
                "minimum": 1,
                "description": "The character offset (1-based, as shown in editors)",
            },
            "query": {
                "type": "string",
                "description": "Query string for workspaceSymbol search",
            },
        },
        "required": ["operation", "filePath", "line", "character"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_lsp_execute,
)


async def execute_lsp_operation(
    operation: LSLOperation,
    file_path: str,
    line: int = 1,
    character: int = 1,
    query: str = "",
) -> ToolResult:
    """Execute an LSP operation and return a ToolResult."""
    args = {
        "operation": operation.value,
        "filePath": file_path,
        "line": line,
        "character": character,
        "query": query,
    }
    return await _lsp_execute(args, ToolContext(cwd=""))


__all__ = ["LSP_TOOL", "LSLOperation", "_lsp_execute", "execute_lsp_operation"]
