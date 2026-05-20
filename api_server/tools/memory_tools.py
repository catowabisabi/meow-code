"""Memory Tools — allow the AI to save and retrieve persistent memories."""
from typing import Dict, Any

from ..services.memory import MemoryService
from .types import ToolDef, ToolResult, ToolContext


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

            service = MemoryService()
            memory_id = await service.store_memory(
                content=content,
                memory_type=memory_type,
                user_id="default",
                metadata={"name": name, "description": description},
            )
            return ToolResult(
                tool_call_id="",
                output=f"Memory saved successfully. ID: {memory_id}, Name: {name}",
                is_error=False,
            )

        elif action == "list":
            return ToolResult(tool_call_id="", output="No memories stored.", is_error=False)

        elif action == "search":
            query = args.get("query")
            if not query:
                return ToolResult(tool_call_id="", output="Missing required field: query", is_error=True)

            service = MemoryService()
            results = await service.search_memories(query=query, user_id="default")
            if not results:
                return ToolResult(
                    tool_call_id="",
                    output=f'No memories found matching "{query}".',
                    is_error=False,
                )

            formatted = "\n".join(
                f"- {r.get('document', '')[:100]}"
                for r in results
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
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "list", "search", "delete"],
                "description": "Action to perform",
            },
            "type": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "content": {"type": "string"},
            "query": {"type": "string"},
            "id": {"type": "string"},
        },
    },
    is_read_only=False,
    risk_level="low",
    execute=_memory_write_execute,
)


MEMORY_READ_INPUT_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["get", "list", "search", "index"],
            "description": "Action to perform",
        },
        "id": {"type": "string"},
        "query": {"type": "string"},
    },
}


async def _memory_read_execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    try:
        action = args.get("action")

        if action == "get":
            memory_id = args.get("id")
            if not memory_id:
                return ToolResult(tool_call_id="", output="Missing required field: id", is_error=True)

            service = MemoryService()
            results = await service.search_memories(query=memory_id, user_id="default")
            if not results:
                return ToolResult(tool_call_id="", output=f"Memory {memory_id} not found.", is_error=True)

            return ToolResult(
                tool_call_id="",
                output=results[0].get("document", ""),
                is_error=False,
            )

        elif action == "list":
            return ToolResult(tool_call_id="", output="No memories stored.", is_error=False)

        elif action == "search":
            query = args.get("query")
            if not query:
                return ToolResult(tool_call_id="", output="Missing required field: query", is_error=True)

            service = MemoryService()
            results = await service.search_memories(query=query, user_id="default")
            if not results:
                return ToolResult(
                    tool_call_id="",
                    output=f'No memories found matching "{query}".',
                    is_error=False,
                )

            formatted = "\n".join(
                f"- {r.get('document', '')[:100]}"
                for r in results
            )
            return ToolResult(
                tool_call_id="",
                output=f"{len(results)} memories found:\n{formatted}",
                is_error=False,
            )

        elif action == "index":
            return ToolResult(tool_call_id="", output="Memory index", is_error=False)

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
