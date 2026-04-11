"""Memory Tools — allow the AI to save and retrieve persistent memories."""
from typing import Dict, Any

from ..services.memory import (
    MemoryService,
    MemoryInput,
    get_memory_index,
)
from .types import ToolDef, ToolResult, ToolContext


# ─── Memory Write Tool ───────────────────────────────────────

MEMORY_WRITE_INPUT_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["save", "list", "search", "delete"],
            "description": "Action to perform",
        },
        "type": {
            "type": "string",
            "enum": ["user", "feedback", "project", "reference"],
            "description": "Memory type (required for save)",
        },
        "name": {
            "type": "string",
            "description": "Short name/title for the memory (required for save)",
        },
        "description": {
            "type": "string",
            "description": "Brief description of what this memory contains (required for save)",
        },
        "content": {
            "type": "string",
            "description": "Full content of the memory (required for save)",
        },
        "query": {
            "type": "string",
            "description": "Search query (required for search)",
        },
        "id": {
            "type": "string",
            "description": "Memory ID (required for delete)",
        },
    },
}


async def _memory_write_execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    try:
        action = args.get("action")

        if action == "save":
            memory_type = args.get("type")
            name = args.get("name")
            description = args.get("description")
            content = args.get("content")

            if not all([memory_type, name, description, content]):
                return ToolResult(
                    tool_call_id="",
                    output="Missing required fields for save: type, name, description, content",
                    is_error=True,
                )

            memory_input = MemoryInput(
                type=memory_type,
                name=name,
                description=description,
                content=content,
            )
            memory = await MemoryService.save_memory(memory_input)
            return ToolResult(
                tool_call_id="",
                output=f"Memory saved successfully. ID: {memory.id}, Name: {memory.name}",
                is_error=False,
            )

        elif action == "list":
            memories = await MemoryService.list_memories()
            if not memories:
                return ToolResult(tool_call_id="", output="No memories stored.", is_error=False)

            formatted = "\n".join(
                f"- [{m.type}] {m.name} ({m.id}): {m.description}"
                for m in memories
            )
            return ToolResult(
                tool_call_id="",
                output=f"{len(memories)} memories found:\n{formatted}",
                is_error=False,
            )

        elif action == "search":
            query = args.get("query")
            if not query:
                return ToolResult(tool_call_id="", output="Missing required field: query", is_error=True)

            results = await MemoryService.search_memories(query)
            if not results:
                return ToolResult(
                    tool_call_id="",
                    output=f'No memories found matching "{query}".',
                    is_error=False,
                )

            formatted = "\n".join(
                f"- [{m.type}] {m.name} ({m.id}): {m.description}\n  {m.content[:200]}"
                for m in results
            )
            return ToolResult(
                tool_call_id="",
                output=f"{len(results)} memories found:\n{formatted}",
                is_error=False,
            )

        elif action == "delete":
            memory_id = args.get("id")
            if not memory_id:
                return ToolResult(tool_call_id="", output="Missing required field: id", is_error=True)

            await MemoryService.delete_memory(memory_id)
            return ToolResult(tool_call_id="", output=f"Memory {memory_id} deleted.", is_error=False)

        else:
            return ToolResult(
                tool_call_id="",
                output=f"Unknown action: {action}. Use save, list, search, or delete.",
                is_error=True,
            )

    except Exception as err:
        return ToolResult(
            tool_call_id="",
            output=f"Memory write error: {str(err)}",
            is_error=True,
        )


memory_write_tool = ToolDef(
    name="memory_write",
    description=(
        "Save, delete, list, or search persistent memories. "
        "Use this to remember user preferences, project context, important decisions, and reference material."
    ),
    input_schema=MEMORY_WRITE_INPUT_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_memory_write_execute,
)


# ─── Memory Read Tool ────────────────────────────────────────

MEMORY_READ_INPUT_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["get", "list", "search", "index"],
            "description": "Action to perform",
        },
        "id": {
            "type": "string",
            "description": "Memory ID (required for get)",
        },
        "query": {
            "type": "string",
            "description": "Search query (required for search)",
        },
    },
}


async def _memory_read_execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    try:
        action = args.get("action")

        if action == "get":
            memory_id = args.get("id")
            if not memory_id:
                return ToolResult(tool_call_id="", output="Missing required field: id", is_error=True)

            memory = await MemoryService.get_memory(memory_id)
            if not memory:
                return ToolResult(tool_call_id="", output=f"Memory {memory_id} not found.", is_error=True)

            return ToolResult(
                tool_call_id="",
                output=f"[{memory.type}] {memory.name}\n{memory.description}\n\n{memory.content}",
                is_error=False,
            )

        elif action == "list":
            memories = await MemoryService.list_memories()
            if not memories:
                return ToolResult(tool_call_id="", output="No memories stored.", is_error=False)

            formatted = "\n".join(
                f"- [{m.type}] {m.name} ({m.id}): {m.description}"
                for m in memories
            )
            return ToolResult(
                tool_call_id="",
                output=f"{len(memories)} memories found:\n{formatted}",
                is_error=False,
            )

        elif action == "search":
            query = args.get("query")
            if not query:
                return ToolResult(tool_call_id="", output="Missing required field: query", is_error=True)

            results = await MemoryService.search_memories(query)
            if not results:
                return ToolResult(
                    tool_call_id="",
                    output=f'No memories found matching "{query}".',
                    is_error=False,
                )

            formatted = "\n".join(
                f"- [{m.type}] {m.name} ({m.id}): {m.description}\n  {m.content[:200]}"
                for m in results
            )
            return ToolResult(
                tool_call_id="",
                output=f"{len(results)} memories found:\n{formatted}",
                is_error=False,
            )

        elif action == "index":
            index = await get_memory_index()
            return ToolResult(tool_call_id="", output=index, is_error=False)

        else:
            return ToolResult(
                tool_call_id="",
                output=f"Unknown action: {action}. Use get, list, search, or index.",
                is_error=True,
            )

    except Exception as err:
        return ToolResult(
            tool_call_id="",
            output=f"Memory read error: {str(err)}",
            is_error=True,
        )


memory_read_tool = ToolDef(
    name="memory_read",
    description=(
        "Read persistent memories — get a specific memory by ID, list all, search by keyword, "
        "or get the memory index."
    ),
    input_schema=MEMORY_READ_INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_memory_read_execute,
)
