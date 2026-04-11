"""
Memory API routes.

Note: This module uses a simple JSON file storage in ~/.claude/memory/
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["memory"])

# --- Configuration ---

MEMORY_DIR = Path.home() / ".claude" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# --- Pydantic Models ---


class Memory(BaseModel):
    id: str
    type: str = "user"
    name: str
    description: str = ""
    content: str
    createdAt: str
    updatedAt: str


class CreateMemoryRequest(BaseModel):
    type: str = "user"
    name: str
    description: str = ""
    content: str


class ListMemoriesResponse(BaseModel):
    memories: list[Memory]
    count: int


class SearchMemoriesResponse(BaseModel):
    results: list[Memory]
    count: int


class MemoryIndexResponse(BaseModel):
    index: str


class DeleteResponse(BaseModel):
    ok: bool


class ErrorResponse(BaseModel):
    error: str


# --- Storage Helpers ---


def _get_memory_file(memory_id: str) -> Path:
    """Get the file path for a memory ID."""
    return MEMORY_DIR / f"{memory_id}.json"


def _list_memory_files() -> list[Path]:
    """List all memory JSON files."""
    if not MEMORY_DIR.exists():
        return []
    return list(MEMORY_DIR.glob("*.json"))


def _load_memory(memory_id: str) -> Memory | None:
    """Load a single memory by ID."""
    file_path = _get_memory_file(memory_id)
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Memory(**data)
    except (json.JSONDecodeError, OSError):
        return None


def _save_memory(memory: Memory) -> Memory:
    """Save a memory to disk."""
    file_path = _get_memory_file(memory.id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(memory.model_dump(), f, indent=2, ensure_ascii=False)
    return memory


def _delete_memory_file(memory_id: str) -> bool:
    """Delete a memory file. Returns True if deleted."""
    file_path = _get_memory_file(memory_id)
    if file_path.exists():
        file_path.unlink()
        return True
    return False


# --- Service Layer Stubs (implement later) ---


async def list_memories() -> list[Memory]:
    """List all memories."""
    memories: list[Memory] = []
    for file_path in _list_memory_files():
        memory_id = file_path.stem
        memory = _load_memory(memory_id)
        if memory:
            memories.append(memory)
    # Sort by updatedAt descending
    memories.sort(key=lambda m: m.updatedAt, reverse=True)
    return memories


async def get_memory(memory_id: str) -> Memory | None:
    """Get a single memory by ID."""
    return _load_memory(memory_id)


async def save_memory(data: CreateMemoryRequest) -> Memory:
    """Create a new memory."""
    now = datetime.utcnow().isoformat()
    memory = Memory(
        id=str(uuid.uuid4()),
        type=data.type,
        name=data.name,
        description=data.description,
        content=data.content,
        createdAt=now,
        updatedAt=now,
    )
    return _save_memory(memory)


async def delete_memory(memory_id: str) -> bool:
    """Delete a memory by ID."""
    return _delete_memory_file(memory_id)


async def search_memories(query: str) -> list[Memory]:
    """Search memories by query string (simple substring match)."""
    if not query:
        return await list_memories()

    query_lower = query.lower()
    all_memories = await list_memories()
    results = []

    for memory in all_memories:
        if (
            query_lower in memory.name.lower()
            or query_lower in memory.description.lower()
            or query_lower in memory.content.lower()
        ):
            results.append(memory)

    return results


async def get_memory_index() -> str:
    """Get MEMORY.md content from memory directory."""
    index_path = MEMORY_DIR / "MEMORY.md"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return ""


# --- Routes ---


@router.get("", response_model=ListMemoriesResponse)
async def list_all_memories() -> ListMemoriesResponse:
    """List all memories."""
    memories = await list_memories()
    return ListMemoriesResponse(memories=memories, count=len(memories))


@router.get("/search", response_model=SearchMemoriesResponse)
async def search(
    q: Annotated[str, Query(description="Search query")] = "",
) -> SearchMemoriesResponse:
    """Search memories by query string."""
    results = await search_memories(q)
    return SearchMemoriesResponse(results=results, count=len(results))


@router.get("/index", response_model=MemoryIndexResponse)
async def get_index() -> MemoryIndexResponse:
    """Get MEMORY.md content."""
    index = await get_memory_index()
    return MemoryIndexResponse(index=index)


@router.get("/{memory_id}", response_model=Memory)
async def get_memory_by_id(memory_id: str) -> Memory:
    """Get a single memory by ID."""
    memory = await get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.post("", response_model=Memory)
async def create_memory(request: CreateMemoryRequest) -> Memory:
    """Create a new memory."""
    return await save_memory(request)


@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory_by_id(memory_id: str) -> DeleteResponse:
    """Delete a memory by ID."""
    deleted = await delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return DeleteResponse(ok=True)
