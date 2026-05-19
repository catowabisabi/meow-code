import asyncio
from typing import Optional, Callable, Awaitable, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    memory_id: str
    content: str
    extraction_type: str
    confidence: float
    entities: List[str]
    timestamp: float

class MemoryExtractionPipeline:
    def __init__(self, memory_service=None, auto_dream_service=None):
        self._memory = memory_service
        self._auto_dream = auto_dream_service
        self._processors: List[Callable] = []
        self._is_initialized = False

    async def initialize(self):
        if self._is_initialized:
            return
        
        if self._auto_dream and not self._memory:
            from .memory_service import get_memory_service
            self._memory = get_memory_service()
        
        self._is_initialized = True

    async def extract_and_store(
        self,
        content: str,
        extraction_type: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        await self.initialize()
        
        entities = await self._extract_entities(content)
        
        memory_id = await self._memory.store_memory(
            content=content,
            memory_type=extraction_type,
            user_id=user_id,
            metadata={
                **(metadata or {}),
                "entities": entities,
                "extraction_type": extraction_type,
            },
        )
        
        result = ExtractionResult(
            memory_id=memory_id,
            content=content,
            extraction_type=extraction_type,
            confidence=0.9,
            entities=entities,
            timestamp=asyncio.get_event_loop().time(),
        )
        
        for processor in self._processors:
            asyncio.create_task(processor(result))
        
        return result

    async def _extract_entities(self, content: str) -> List[str]:
        words = content.split()
        entities = [
            w for w in words
            if w[0].isupper() and len(w) > 2
        ]
        return entities[:20]

    async def process_dream_output(self, dream_result) -> List[str]:
        if not self._memory:
            return []
        
        memory_ids = []
        
        if hasattr(dream_result, 'content'):
            memory_id = await self._memory.store_memory(
                content=dream_result.content,
                memory_type="dream_synthesis",
                user_id="system",
                metadata={
                    "dream_id": getattr(dream_result, 'dream_id', 'unknown'),
                    "memories_extracted": getattr(dream_result, 'memories_extracted', 0),
                },
            )
            memory_ids.append(memory_id)
        
        return memory_ids

    def register_processor(self, processor: Callable[[ExtractionResult], Awaitable[None]]):
        self._processors.append(processor)

    async def batch_extract(
        self,
        contents: List[str],
        extraction_type: str,
        user_id: str,
    ) -> List[ExtractionResult]:
        results = []
        for content in contents:
            result = await self.extract_and_store(
                content=content,
                extraction_type=extraction_type,
                user_id=user_id,
            )
            results.append(result)
        return results

_pipeline: Optional[MemoryExtractionPipeline] = None

def get_extraction_pipeline() -> MemoryExtractionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = MemoryExtractionPipeline()
    return _pipeline