import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class SessionMemoryEntry(BaseModel):
    key: str
    value: Any
    createdAt: int
    updatedAt: int
    session_id: Optional[str] = None
    expiresAt: Optional[int] = None


class CrossSessionMemory(BaseModel):
    user_id: str
    entries: Dict[str, SessionMemoryEntry] = {}
    createdAt: int
    updatedAt: int


def _get_memory_store_path() -> Path:
    return Path.home() / ".claude" / "session_memory.json"


async def _load_memory_store() -> Dict[str, Any]:
    path = _get_memory_store_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"entries": {}, "metadata": {}}
    return {"entries": {}, "metadata": {}}


async def _save_memory_store(store: Dict[str, Any]) -> None:
    path = _get_memory_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


class SessionMemoryService:
    @staticmethod
    async def set(
        key: str,
        value: Any,
        user_id: str = "default",
        session_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        now = int(datetime.utcnow().timestamp() * 1000)
        store = await _load_memory_store()
        
        if user_id not in store:
            store[user_id] = {"entries": {}, "createdAt": now, "updatedAt": now}
        
        expires_at = None
        if ttl_seconds:
            expires_at = now + (ttl_seconds * 1000)
        
        entry = SessionMemoryEntry(
            key=key,
            value=value,
            createdAt=store[user_id]["entries"].get(key, {}).get("createdAt", now),
            updatedAt=now,
            session_id=session_id,
            expiresAt=expires_at,
        )
        store[user_id]["entries"][key] = entry.model_dump()
        store[user_id]["updatedAt"] = now
        
        await _save_memory_store(store)
    
    @staticmethod
    async def get(
        key: str,
        user_id: str = "default",
        default: Any = None,
    ) -> Any:
        store = await _load_memory_store()
        now = int(datetime.utcnow().timestamp() * 1000)
        
        if user_id not in store:
            return default
        
        entry_data = store[user_id]["entries"].get(key)
        if not entry_data:
            return default
        
        if entry_data.get("expiresAt") and entry_data["expiresAt"] < now:
            return default
        
        return entry_data.get("value", default)
    
    @staticmethod
    async def delete(key: str, user_id: str = "default") -> None:
        store = await _load_memory_store()
        if user_id in store and key in store[user_id]["entries"]:
            del store[user_id]["entries"][key]
            store[user_id]["updatedAt"] = int(datetime.utcnow().timestamp() * 1000)
            await _save_memory_store(store)
    
    @staticmethod
    async def clear(user_id: str = "default") -> None:
        store = await _load_memory_store()
        if user_id in store:
            store[user_id]["entries"] = {}
            store[user_id]["updatedAt"] = int(datetime.utcnow().timestamp() * 1000)
            await _save_memory_store(store)
    
    @staticmethod
    async def keys(user_id: str = "default") -> List[str]:
        store = await _load_memory_store()
        now = int(datetime.utcnow().timestamp() * 1000)
        
        if user_id not in store:
            return []
        
        valid_keys = []
        for key, entry_data in store[user_id]["entries"].items():
            if not entry_data.get("expiresAt") or entry_data["expiresAt"] >= now:
                valid_keys.append(key)
        
        return valid_keys
    
    @staticmethod
    async def get_all(user_id: str = "default") -> Dict[str, Any]:
        store = await _load_memory_store()
        now = int(datetime.utcnow().timestamp() * 1000)
        
        if user_id not in store:
            return {}
        
        result = {}
        for key, entry_data in store[user_id]["entries"].items():
            if not entry_data.get("expiresAt") or entry_data["expiresAt"] >= now:
                result[key] = entry_data.get("value")
        
        return result
    
    @staticmethod
    async def increment(key: str, amount: int = 1, user_id: str = "default") -> int:
        current = await SessionMemoryService.get(key, user_id, 0)
        new_value = int(current) + amount
        await SessionMemoryService.set(key, new_value, user_id)
        return new_value
    
    @staticmethod
    async def append_to_list(
        key: str,
        value: Any,
        user_id: str = "default",
        max_size: int = 100,
    ) -> List[Any]:
        current = await SessionMemoryService.get(key, user_id, [])
        if not isinstance(current, list):
            current = []
        current.append(value)
        if len(current) > max_size:
            current = current[-max_size:]
        await SessionMemoryService.set(key, current, user_id)
        return current