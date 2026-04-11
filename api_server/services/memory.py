"""
Memory System Service.
Stores memories as markdown files with YAML frontmatter in ~/.claude/memory/.
Provides CRUD and keyword search over saved memories.
"""
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel


class Memory(BaseModel):
    id: str
    type: str = "user"
    name: str
    description: str = ""
    content: str
    createdAt: int
    updatedAt: int


class MemoryInput(BaseModel):
    type: str = "user"
    name: str
    description: str = ""
    content: str


def _get_memory_dir() -> Path:
    return Path.home() / ".claude" / "memory"


def _get_index_path() -> Path:
    return _get_memory_dir() / "MEMORY.md"


async def _ensure_memory_dir() -> None:
    memory_dir = _get_memory_dir()
    memory_dir.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(r"[^a-z0-9]+", "-")
        .replace(r"^-+|-+$", "")
    )[:60]


def _memory_filename(memory_type: str, name: str) -> str:
    return f"{memory_type}_{_slugify(name)}.md"


def _memory_id(memory_type: str, name: str) -> str:
    return hashlib.sha256(f"{memory_type}:{name}".encode()).hexdigest()[:12]


def _serialize_memory(memory: Memory) -> str:
    lines = [
        "---",
        f"id: {memory.id}",
        f"type: {memory.type}",
        f"name: {memory.name}",
        f"description: {memory.description}",
        f"createdAt: {memory.createdAt}",
        f"updatedAt: {memory.updatedAt}",
        "---",
        "",
        memory.content,
    ]
    return "\n".join(lines)


def _parse_memory(raw: str) -> Optional[Memory]:
    fm_match = re.match(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$", raw)
    if not fm_match:
        return None

    frontmatter = fm_match.group(1)
    content = fm_match.group(2).strip()

    fields: dict[str, str] = {}
    for line in frontmatter.split("\n"):
        colon_idx = line.index(":")
        if colon_idx == -1:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1 :].strip()
        fields[key] = value

    if not fields.get("id") or not fields.get("type") or not fields.get("name"):
        return None

    return Memory(
        id=fields["id"],
        type=fields["type"],
        name=fields["name"],
        description=fields.get("description", ""),
        content=content,
        createdAt=int(fields.get("createdAt", "0")),
        updatedAt=int(fields.get("updatedAt", "0")),
    )


class MemoryService:
    @staticmethod
    async def save_memory(memory_input: MemoryInput) -> Memory:
        await _ensure_memory_dir()

        now = int(datetime.utcnow().timestamp() * 1000)
        memory_id = _memory_id(memory_input.type, memory_input.name)

        memory = Memory(
            id=memory_id,
            type=memory_input.type,
            name=memory_input.name,
            description=memory_input.description,
            content=memory_input.content,
            createdAt=now,
            updatedAt=now,
        )

        existing = await MemoryService.get_memory(memory_id)
        if existing:
            memory.createdAt = existing.createdAt

        filename = _memory_filename(memory_input.type, memory_input.name)
        file_path = _get_memory_dir() / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(_serialize_memory(memory))

        await _rebuild_index()
        return memory

    @staticmethod
    async def get_memory(memory_id: str) -> Optional[Memory]:
        memories = await MemoryService.list_memories()
        return next((m for m in memories if m.id == memory_id), None)

    @staticmethod
    async def list_memories() -> List[Memory]:
        await _ensure_memory_dir()

        dir_path = _get_memory_dir()
        memories: List[Memory] = []

        try:
            entries = list(dir_path.glob("*.md"))
        except OSError:
            return []

        for entry in entries:
            if entry.name == "MEMORY.md":
                continue
            try:
                with open(entry, "r", encoding="utf-8") as f:
                    raw = f.read()
                memory = _parse_memory(raw)
                if memory:
                    memories.append(memory)
            except OSError:
                continue

        memories.sort(key=lambda m: m.updatedAt, reverse=True)
        return memories

    @staticmethod
    async def delete_memory(memory_id: str) -> None:
        await _ensure_memory_dir()

        dir_path = _get_memory_dir()
        try:
            entries = list(dir_path.glob("*.md"))
        except OSError:
            return

        for entry in entries:
            if entry.name == "MEMORY.md":
                continue
            try:
                with open(entry, "r", encoding="utf-8") as f:
                    raw = f.read()
                memory = _parse_memory(raw)
                if memory and memory.id == memory_id:
                    entry.unlink()
                    break
            except OSError:
                continue

        await _rebuild_index()

    @staticmethod
    async def search_memories(query: str) -> List[Memory]:
        memories = await MemoryService.list_memories()
        terms = query.lower().split()

        if not terms:
            return memories

        return [
            m
            for m in memories
            if all(
                term in f"{m.name} {m.description} {m.content}".lower()
                for term in terms
            )
        ]


async def _rebuild_index() -> None:
    memories = await MemoryService.list_memories()
    lines = ["# Memory Index", ""]

    groups: dict[str, List[Memory]] = {}
    for m in memories:
        group_list = groups.get(m.type, [])
        group_list.append(m)
        groups[m.type] = group_list

    for memory_type, mems in groups.items():
        lines.append(f"## {memory_type}")
        lines.append("")
        for m in mems:
            lines.append(f"- **{m.name}** ({m.id}): {m.description}")
        lines.append("")

    if not memories:
        lines.append("No memories stored yet.")
        lines.append("")

    index_path = _get_index_path()
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def get_memory_index() -> str:
    await _ensure_memory_dir()

    index_path = _get_index_path()
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")

    await _rebuild_index()
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")

    return "# Memory Index\n\nNo memories stored yet.\n"
