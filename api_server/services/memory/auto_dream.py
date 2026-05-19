import asyncio
import time
from typing import Optional, Callable, Awaitable, Dict, Any
from dataclasses import dataclass

@dataclass
class DreamResult:
    dream_id: str
    content: str
    memories_extracted: int
    status: str
    created_at: float

class AutoDreamService:
    def __init__(self, memory_service=None):
        self._memory_service = memory_service
        self._is_processing = False
        self._last_dream_time: Optional[float] = None
        self._dream_queue: asyncio.Queue = asyncio.Queue()
        self._dream_handlers: list[Callable] = []

    def register_handler(self, handler: Callable[[DreamResult], Awaitable[None]]):
        self._dream_handlers.append(handler)

    async def trigger_manual_dream(
        self,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> DreamResult:
        if self._is_processing:
            raise RuntimeError("Dream already in progress")
        
        self._is_processing = True
        dream_id = f"dream_{int(time.time() * 1000)}"
        
        try:
            memories = await self._extract_relevant_memories(context, user_id)
            
            dream_content = await self._synthesize_dream(
                memories,
                context,
            )
            
            result = DreamResult(
                dream_id=dream_id,
                content=dream_content,
                memories_extracted=len(memories),
                status="completed",
                created_at=time.time(),
            )
            
            for handler in self._dream_handlers:
                asyncio.create_task(handler(result))
            
            self._last_dream_time = time.time()
            return result
            
        finally:
            self._is_processing = False

    async def _extract_relevant_memories(
        self,
        context: Optional[Dict[str, Any]],
        user_id: Optional[str],
    ) -> list[Dict[str, Any]]:
        if not self._memory_service:
            return []
        
        query = context.get("query", "") if context else ""
        if not query:
            query = "recent important context"
        
        memories = await self._memory_service.search_memories(
            query=query,
            user_id=user_id or "default",
            n_results=20,
        )
        
        return memories

    async def _synthesize_dream(
        self,
        memories: list[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        if not memories:
            return "No relevant memories found for dream synthesis."
        
        memory_summary = "\n".join([
            f"- {m['document'][:200]}"
            for m in memories[:10]
        ])
        
        dream_content = (
            f"=== Dream Synthesis ===\n"
            f"Memories analyzed: {len(memories)}\n\n"
            f"Extracted context:\n{memory_summary}\n\n"
            f"Synthesis complete."
        )
        
        return dream_content

    async def schedule_dream(
        self,
        delay_seconds: float,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        await asyncio.sleep(delay_seconds)
        return await self.trigger_manual_dream(context, user_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_processing": self._is_processing,
            "last_dream_time": self._last_dream_time,
            "queue_size": self._dream_queue.qsize(),
            "handlers_registered": len(self._dream_handlers),
        }

_auto_dream_service: Optional[AutoDreamService] = None

def get_auto_dream_service() -> AutoDreamService:
    global _auto_dream_service
    if _auto_dream_service is None:
        _auto_dream_service = AutoDreamService()
    return _auto_dream_service