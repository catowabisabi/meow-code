import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum

class BlackboardEntryType(Enum):
    FACT = "fact"
    GOAL = "goal"
    HYPOTHESIS = "hypothesis"
    PLAN = "plan"
    RESULT = "result"
    OBSERVATION = "observation"

class AccessLevel(Enum):
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"

@dataclass
class BlackboardEntry:
    id: str
    entry_type: BlackboardEntryType
    key: str
    value: Any
    author_agent: str
    access_level: AccessLevel = AccessLevel.TEAM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    parent_id: Optional[str] = None

class SharedBlackboard:
    def __init__(self):
        self._entries: Dict[str, BlackboardEntry] = {}
        self._key_index: Dict[str, Set[str]] = {}
        self._agent_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def write(
        self,
        entry_type: BlackboardEntryType,
        key: str,
        value: Any,
        author_agent: str,
        access_level: AccessLevel = AccessLevel.TEAM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        
        async with self._locks[key]:
            entry_id = str(uuid.uuid4())
            
            existing = self._get_by_key(key)
            if existing:
                existing.value = value
                existing.updated_at = time.time()
                existing.version += 1
                entry_id = existing.id
            else:
                entry = BlackboardEntry(
                    id=entry_id,
                    entry_type=entry_type,
                    key=key,
                    value=value,
                    author_agent=author_agent,
                    access_level=access_level,
                    tags=tags or [],
                    metadata=metadata or {},
                    parent_id=parent_id,
                )
                self._entries[entry_id] = entry
                self._index_entry(entry)
            
            await self._notify_subscribers(key, entry_type, value)
            
            return entry_id

    def _index_entry(self, entry: BlackboardEntry):
        if entry.key not in self._key_index:
            self._key_index[entry.key] = set()
        self._key_index[entry.key].add(entry.id)
        
        if entry.author_agent not in self._agent_index:
            self._agent_index[entry.author_agent] = set()
        self._agent_index[entry.author_agent].add(entry.id)
        
        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(entry.id)

    def _get_by_key(self, key: str) -> Optional[BlackboardEntry]:
        entry_ids = self._key_index.get(key, set())
        if entry_ids:
            entry_id = list(entry_ids)[0]
            return self._entries.get(entry_id)
        return None

    async def read(
        self,
        key: str,
        agent_id: str,
        version: Optional[int] = None,
    ) -> Optional[Any]:
        entry = self._get_by_key(key)
        if not entry:
            return None
        
        if entry.access_level == AccessLevel.PRIVATE:
            if entry.author_agent != agent_id:
                return None
        
        if version and entry.version != version:
            return None
        
        return entry.value

    async def read_by_id(
        self,
        entry_id: str,
        agent_id: str,
    ) -> Optional[BlackboardEntry]:
        entry = self._entries.get(entry_id)
        if not entry:
            return None
        
        if entry.access_level == AccessLevel.PRIVATE:
            if entry.author_agent != agent_id:
                return None
        
        return entry

    async def find_by_tags(
        self,
        tags: List[str],
        agent_id: str,
    ) -> List[BlackboardEntry]:
        matching_ids: Set[str] = None
        
        for tag in tags:
            tag_ids = self._tag_index.get(tag, set())
            if matching_ids is None:
                matching_ids = tag_ids
            else:
                matching_ids &= tag_ids
        
        if matching_ids is None:
            return []
        
        results = []
        for entry_id in matching_ids:
            entry = self._entries.get(entry_id)
            if entry:
                if entry.access_level == AccessLevel.PRIVATE:
                    if entry.author_agent != agent_id:
                        continue
                results.append(entry)
        
        return results

    async def find_by_agent(
        self,
        author_agent: str,
        agent_id: str,
    ) -> List[BlackboardEntry]:
        entry_ids = self._agent_index.get(author_agent, set())
        results = []
        
        for entry_id in entry_ids:
            entry = self._entries.get(entry_id)
            if entry:
                if entry.access_level == AccessLevel.PRIVATE:
                    if entry.author_agent != agent_id:
                        continue
                results.append(entry)
        
        return results

    async def find_by_type(
        self,
        entry_type: BlackboardEntryType,
        agent_id: str,
    ) -> List[BlackboardEntry]:
        results = []
        
        for entry in self._entries.values():
            if entry.entry_type == entry_type:
                if entry.access_level == AccessLevel.PRIVATE:
                    if entry.author_agent != agent_id:
                        continue
                results.append(entry)
        
        return results

    async def subscribe(
        self,
        agent_id: str,
        key_pattern: str,
        callback: Callable,
    ):
        subscription_key = f"{agent_id}:{key_pattern}"
        if subscription_key not in self._subscribers:
            self._subscribers[subscription_key] = []
        self._subscribers[subscription_key].append(callback)

    async def _notify_subscribers(
        self,
        key: str,
        entry_type: BlackboardEntryType,
        value: Any,
    ):
        for sub_key, callbacks in self._subscribers.items():
            agent_id, pattern = sub_key.split(":", 1)
            
            if pattern == "*" or key == pattern:
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(key, entry_type, value)
                        else:
                            callback(key, entry_type, value)
                    except Exception:
                        pass

    async def delete(
        self,
        entry_id: str,
        agent_id: str,
    ) -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        
        if entry.author_agent != agent_id:
            return False
        
        del self._entries[entry_id]
        
        if entry.key in self._key_index:
            self._key_index[entry.key].discard(entry_id)
        
        if entry.author_agent in self._agent_index:
            self._agent_index[entry.author_agent].discard(entry_id)
        
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(entry_id)
        
        return True

    async def get_history(
        self,
        key: str,
        limit: int = 10,
    ) -> List[BlackboardEntry]:
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "unique_keys": len(self._key_index),
            "unique_agents": len(self._agent_index),
            "total_tags": len(self._tag_index),
            "by_type": {
                et.value: sum(1 for e in self._entries.values() if e.entry_type == et)
                for et in BlackboardEntryType
            },
        }

_blackboard: Optional[SharedBlackboard] = None

def get_shared_blackboard() -> SharedBlackboard:
    global _blackboard
    if _blackboard is None:
        _blackboard = SharedBlackboard()
    return _blackboard