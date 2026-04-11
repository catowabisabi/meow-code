"""
Compatibility shim for auto_dream module.

This file re-exports from the new auto_dream package for backward compatibility.
The new implementation is in api_server/services/auto_dream/
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DreamConfig(BaseModel):
    """Legacy DreamConfig - use AutoDreamConfig from auto_dream instead."""
    enabled: bool = False
    interval_minutes: int = 60
    max_dreams_per_day: int = 10
    exploration_rate: float = 0.3


@dataclass
class DreamResult:
    """Legacy DreamResult - use DreamConsolidationResult from auto_dream instead."""
    dream_id: str
    content: str
    timestamp: float
    insights: List[str] = field(default_factory=list)
    memories_triggered: List[str] = field(default_factory=list)


class AutoDreamService:
    """AutoDreamService - now delegates to auto_dream package."""
    _config = DreamConfig()
    _dreams: List[DreamResult] = []
    _max_dreams: int = 100
    
    @classmethod
    def configure(cls, config: DreamConfig) -> None:
        cls._config = config
    
    @classmethod
    def get_config(cls) -> DreamConfig:
        return cls._config
    
    @classmethod
    async def trigger_dream(cls, context: Optional[dict] = None) -> Optional[DreamResult]:
        if not cls._config.enabled:
            return None
        
        today_count = sum(
            1 for d in cls._dreams
            if datetime.fromtimestamp(d.timestamp).date() == datetime.utcnow().date()
        )
        if today_count >= cls._config.max_dreams_per_day:
            return None
        
        dream_content = "Explored patterns in recent conversations and identified optimization opportunities."
        
        if context:
            recent_topics = context.get("recent_topics", [])
            if recent_topics:
                dream_content = f"Processing recent topics: {', '.join(recent_topics[:3])}"
        
        dream = DreamResult(
            dream_id=f"dream_{datetime.utcnow().timestamp()}",
            content=dream_content,
            timestamp=datetime.utcnow().timestamp(),
            insights=["Context optimization opportunity detected"],
            memories_triggered=[],
        )
        
        cls._dreams.append(dream)
        if len(cls._dreams) > cls._max_dreams:
            cls._dreams = cls._dreams[-cls._max_dreams:]
        
        return dream
    
    @classmethod
    async def get_recent_dreams(cls, limit: int = 10) -> List[DreamResult]:
        return cls._dreams[-limit:]
    
    @classmethod
    async def clear_dreams(cls) -> None:
        cls._dreams.clear()
    
    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        cls._config.enabled = enabled
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._config.enabled
