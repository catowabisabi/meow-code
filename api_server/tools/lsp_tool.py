"""LSP (Language Server Protocol) tool for code intelligence.

Based on TypeScript LSPTool implementation.
Provides symbol search, diagnostics, and code intelligence.
"""
from enum import Enum
from typing import Any

from ..lsp import (
    initialize_lsp_server_manager,
    get_lsp_server_manager,
    get_initialization_status,
    is_lsp_connected,
    wait_for_initialization,
    go_to_definition,
    find_references,
    hover,
    document_symbol,
    workspace_symbol,
    go_to_implementation,
    prepare_call_hierarchy,
    incoming_calls,
    outgoing_calls,
)
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


def lsp_tool_def() -> ToolDef:
    return ToolDef(
        name="lsp",
        description="Language Server Protocol tool for code intelligence (definitions, references, hover, symbols)",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["goToDefinition", "findReferences", "hover", "documentSymbol", "workspaceSymbol", "goToImplementation", "prepareCallHierarchy", "incomingCalls", "outgoingCalls"],
                    "description": "The LSP operation to perform",
                },
                "filePath": {
                    "type": "string",
                    "description": "The absolute or relative path to the file",
                },
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "The line number (1-based)",
                },
                "character": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "The character offset (1-based)",
                },
            },
            "required": ["operation", "filePath", "line", "character"],
        },
        is_read_only=True,
        risk_level="low",
        execute=_lsp_execute,
    )


async def _lsp_execute(args: dict, ctx: ToolContext | None) -> dict:
    operation = args.get("operation", "")
    file_path = args.get("filePath", "")
    line = args.get("line", 1)
    character = args.get("character", 1)
    query = args.get("query", "")

    status = get_initialization_status()
    if status.status.value == "pending":
        await wait_for_initialization()

    manager = get_lsp_server_manager()
    if not manager:
        return ToolResult(
            tool_call_id="",
            output="LSP server manager not initialized. This may indicate a startup issue.",
            is_error=True,
        ).model_dump()

    try:
        op = LSLOperation(operation)
    except ValueError:
        return ToolResult(
            tool_call_id="",
            output=f"Unknown operation: {operation}",
            is_error=True,
        ).model_dump()

    try:
        result: Any = None
        if op == LSLOperation.GO_TO_DEFINITION:
            result = await go_to_definition(file_path, line, character)
        elif op == LSLOperation.FIND_REFERENCES:
            result = await find_references(file_path, line, character)
        elif op == LSLOperation.HOVER:
            result = await hover(file_path, line, character)
        elif op == LSLOperation.DOCUMENT_SYMBOL:
            result = await document_symbol(file_path)
        elif op == LSLOperation.WORKSPACE_SYMBOL:
            result = await workspace_symbol(query)
        elif op == LSLOperation.GO_TO_IMPLEMENTATION:
            result = await go_to_implementation(file_path, line, character)
        elif op == LSLOperation.PREPARE_CALL_HIERARCHY:
            result = await prepare_call_hierarchy(file_path, line, character)
        elif op == LSLOperation.INCOMING_CALLS:
            result = await incoming_calls(file_path, line, character)
        elif op == LSLOperation.OUTGOING_CALLS:
            result = await outgoing_calls(file_path, line, character)

        if result is None:
            return ToolResult(
                tool_call_id="",
                output=f"No LSP server available for file type",
                is_error=False,
            ).model_dump()

        return ToolResult(
            tool_call_id="",
            output=str(result),
            is_error=False,
        ).model_dump()
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            output=str(e),
            is_error=True,
        ).model_dump()


async def execute_lsp_operation(
    operation: LSLOperation,
    file_path: str,
    line: int = 1,
    character: int = 1,
    query: str = "",
) -> dict:
    """Execute an LSP operation and return a ToolResult dict."""
    args = {
        "operation": operation.value,
        "filePath": file_path,
        "line": line,
        "character": character,
        "query": query,
    }
    return await _lsp_execute(args, None)