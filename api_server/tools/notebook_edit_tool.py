"""Jupyter notebook editing tool.

Based on TypeScript NotebookEditTool implementation.
Edits Jupyter notebook cells with conflict detection.
"""
import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class NotebookCell:
    id: str
    cell_type: Literal["code", "markdown"] = "code"
    source: str = ""
    outputs: list = field(default_factory=list)


@dataclass
class Notebook:
    cells: list[NotebookCell] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def parse_notebook(content: str) -> Notebook:
    try:
        data = json.loads(content)
        cells = []
        for i, cell in enumerate(data.get("cells", [])):
            cells.append(NotebookCell(
                id=cell.get("id", f"cell-{i}"),
                cell_type=cell.get("cell_type", "code"),
                source="".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else cell.get("source", ""),
                outputs=cell.get("outputs", []),
            ))
        return Notebook(cells=cells, metadata=data.get("metadata", {}))
    except json.JSONDecodeError:
        return Notebook(cells=[], metadata={})


def serialize_notebook(notebook: Notebook) -> str:
    return json.dumps({
        "cells": [
            {
                "id": c.id,
                "cell_type": c.cell_type,
                "source": [c.source],
                "outputs": c.outputs or [],
            }
            for c in notebook.cells
        ],
        "metadata": notebook.metadata,
    }, indent=2)


def generate_cell_id() -> str:
    return f"cell-{secrets.token_hex(8)}"


async def execute_notebook_edit(
    notebook_path: str,
    new_source: str,
    cell_id: str | None = None,
    cell_type: str = "code",
    edit_mode: str = "replace",
    original_file: str = "",
) -> dict:
    path = Path(notebook_path)
    
    if not path.exists():
        return {
            "error": f"Notebook not found: {notebook_path}",
            "is_error": True,
        }
    
    content = path.read_text()
    notebook = parse_notebook(content)
    
    if edit_mode == "delete":
        if cell_id:
            notebook.cells = [c for c in notebook.cells if c.id != cell_id]
        result_cell = None
    elif edit_mode == "insert":
        new_cell = NotebookCell(
            id=cell_id or generate_cell_id(),
            cell_type=cell_type,
            source=new_source,
        )
        if cell_id:
            idx = next((i for i, c in enumerate(notebook.cells) if c.id == cell_id), -1)
            if idx >= 0:
                notebook.cells.insert(idx + 1, new_cell)
            else:
                notebook.cells.append(new_cell)
        else:
            notebook.cells.insert(0, new_cell)
        result_cell = new_cell
    else:
        if cell_id:
            for c in notebook.cells:
                if c.id == cell_id:
                    c.source = new_source
                    if cell_type in ("code", "markdown"):
                        c.cell_type = cell_type
                    result_cell = c
                    break
            else:
                return {"error": f"Cell not found: {cell_id}", "is_error": True}
        else:
            notebook.cells.append(NotebookCell(
                id=generate_cell_id(),
                cell_type=cell_type if cell_type in ("code", "markdown") else "code",
                source=new_source,
            ))
            result_cell = notebook.cells[-1]
    
    path.write_text(serialize_notebook(notebook))
    
    return {
        "new_source": result_cell.source if result_cell else new_source,
        "cell_id": result_cell.id if result_cell else cell_id,
        "cell_type": result_cell.cell_type if result_cell else cell_type,
        "language": "python",
        "edit_mode": edit_mode,
        "notebook_path": notebook_path,
        "original_file": original_file or content[:200],
        "is_error": False,
    }
