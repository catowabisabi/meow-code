"""Compact/memory service - bridging gap with TypeScript services/compact/"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import json
import hashlib


logger = logging.getLogger(__name__)


@dataclass
class CompactMessage:
    id: str
    role: str
    content: Any
    timestamp: float
    token_count: int


@dataclass
class CompactResult:
    messages: List[CompactMessage]
    total_tokens: int
    cache_edits: int


class MicroCompact:
    """
    Cached microcompact with cache_edits.
    
    TypeScript equivalent: microCompact.ts
    Python gap: No cached microcompact implementation.
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _compute_key(self, messages: List[Dict[str, Any]]) -> str:
        content = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def compact(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 100000
    ) -> CompactResult:
        key = self._compute_key(messages)
        
        if key in self._cache:
            self._cache_hits += 1
            cached_result = self._cache[key]
            return CompactResult(
                messages=[CompactMessage(**json.loads(cached_result))],
                total_tokens=0,
                cache_edits=1
            )
        
        self._cache_misses += 1
        
        compacted_messages = self._do_compact(messages, max_tokens)
        total_tokens = sum(m.token_count for m in compacted_messages)
        
        if compacted_messages:
            first_msg = compacted_messages[0]
            self._cache[key] = json.dumps({
                "id": first_msg.id,
                "role": first_msg.role,
                "content": first_msg.content,
                "timestamp": first_msg.timestamp,
                "token_count": first_msg.token_count
            })
        
        return CompactResult(
            messages=compacted_messages,
            total_tokens=total_tokens,
            cache_edits=0
        )
    
    def _do_compact(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int
    ) -> List[CompactMessage]:
        result: List[CompactMessage] = []
        total_tokens = 0
        
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                text_content = " ".join(
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            else:
                text_content = str(content)
            
            token_count = len(text_content.split()) * 1.3
            
            if total_tokens + token_count > max_tokens:
                break
            
            result.append(CompactMessage(
                id=msg.get("id", ""),
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", 0),
                token_count=int(token_count)
            ))
            total_tokens += token_count
        
        return result
    
    def get_cache_stats(self) -> Dict[str, int]:
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._cache)
        }
    
    def clear_cache(self) -> None:
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


class SessionStorage:
    """
    Session storage with buffering and UUID deduplication.
    
    TypeScript equivalent: sessionStorage.ts
    Python gap: Simple JSON files - missing buffering, UUID dedup.
    """
    
    def __init__(self, storage_dir: str = "~/.claude/sessions"):
        self.storage_dir = storage_dir
        self._buffer: Dict[str, Dict[str, Any]] = {}
        self._dirty: set = set()
        self._uuids_seen: set = set()
    
    def put(self, session_id: str, data: Dict[str, Any]) -> None:
        messages = data.get("messages", [])
        deduped_messages = self._dedupe_messages(messages)
        data["messages"] = deduped_messages
        
        self._buffer[session_id] = data
        self._dirty.add(session_id)
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._buffer.get(session_id)
    
    def _dedupe_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        
        for msg in messages:
            msg_id = msg.get("id", "")
            
            if msg_id and msg_id in self._uuids_seen:
                continue
            
            if msg_id:
                self._uuids_seen.add(msg_id)
            
            result.append(msg)
        
        return result
    
    async def flush(self) -> None:
        for session_id in self._dirty:
            data = self._buffer.get(session_id)
            if data:
                await self._write_to_disk(session_id, data)
        
        self._dirty.clear()
    
    async def _write_to_disk(self, session_id: str, data: Dict[str, Any]) -> None:
        import os
        from pathlib import Path
        
        session_path = Path(self.storage_dir).expanduser() / f"{session_id}.json"
        session_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffered_sessions": len(self._buffer),
            "dirty_sessions": len(self._dirty),
            "unique_uuids": len(self._uuids_seen)
        }


_micro_compact: Optional[MicroCompact] = None
_session_storage: Optional[SessionStorage] = None


def get_micro_compact() -> MicroCompact:
    global _micro_compact
    if _micro_compact is None:
        _micro_compact = MicroCompact()
    return _micro_compact


def get_session_storage() -> SessionStorage:
    global _session_storage
    if _session_storage is None:
        _session_storage = SessionStorage()
    return _session_storage
