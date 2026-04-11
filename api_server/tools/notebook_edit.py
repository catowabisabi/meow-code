"""NotebookEditTool - Edit Jupyter notebook cells."""
import json
import secrets
from pathlib import Path
from typing import Dict, Any

from .types import ToolDef, ToolResult, ToolContext


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "notebook_path": {"type": "string"},
        "cell_index": {"type": "number"},
        "new_content": {"type": "string"},
        "cell_type": {"type": "string", "enum": ["code", "markdown"]},
    },
    "required": ["notebook_path", "cell_index", "new_content"]
}


def _generate_cell_id() -> str:
    return secrets.token_hex(8)


def _parse_notebook(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"cells": [], "metadata": {}}


def _serialize_notebook(notebook: Dict[str, Any]) -> str:
    return json.dumps(notebook, indent=2)


async def execute_notebook_edit(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    notebook_path = args.get("notebook_path")
    cell_index = args.get("cell_index")
    new_content = args.get("new_content")
    cell_type = args.get("cell_type", "code")

    if not notebook_path:
        return ToolResult(tool_call_id="", output="notebook_path is required", is_error=True)
    if cell_index is None:
        return ToolResult(tool_call_id="", output="cell_index is required", is_error=True)
    if new_content is None:
        return ToolResult(tool_call_id="", output="new_content is required", is_error=True)

    path = Path(notebook_path)
    
    if not path.exists():
        return ToolResult(tool_call_id="", output=f"Notebook not found: {notebook_path}", is_error=True)

    original_content = path.read_text()
    notebook = _parse_notebook(original_content)
    cells = notebook.get("cells", [])
    
    idx = int(cell_index)
    if idx < 0 or idx >= len(cells):
        return ToolResult(
            tool_call_id="",
            output=f"Cell index {idx} out of range. Notebook has {len(cells)} cells.",
            is_error=True
        )

    cell = cells[idx]
    cell["source"] = new_content
    
    if cell_type in ("code", "markdown"):
        cell["cell_type"] = cell_type
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    updated_content = _serialize_notebook(notebook)
    path.write_text(updated_content)

    return ToolResult(
        tool_call_id="",
        output=json.dumps({
            "new_content": new_content,
            "cell_index": idx,
            "cell_id": cell.get("id", f"cell-{idx}"),
            "cell_type": cell.get("cell_type", "code"),
            "notebook_path": notebook_path,
            "original_file": original_content[:500],
            "updated_file": updated_content[:500],
        })
    )


TOOL_NOTEBOOK_EDIT = ToolDef(
    name="notebook_edit",
    description="Edit Jupyter notebook cells",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="medium",
    execute=execute_notebook_edit,
)
