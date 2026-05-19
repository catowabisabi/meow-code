import uuid
from typing import Optional, List, Dict, Any
from .embedding_service import get_embedding_service, EmbeddingService
from .vector_store import get_vector_store, VectorStore

class MemoryService:
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self._embedding = embedding_service or get_embedding_service()
        self._vector = vector_store or get_vector_store()

    async def store_memory(
        self,
        content: str,
        memory_type: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        embedding = await self._embedding.embed_text(content)
        
        doc_metadata = {
            "memory_type": memory_type,
            "user_id": user_id,
            "tags": tags or [],
        }
        if metadata:
            doc_metadata.update(metadata)
        
        await self._vector.add(
            ids=[memory_id],
            embeddings=[embedding.tolist()],
            documents=[content],
            metadatas=[doc_metadata],
        )
        
        return memory_id

    async def search_memories(
        self,
        query: str,
        user_id: str,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        query_embedding = await self._embedding.embed_text(query)
        
        where_filters = [{"user_id": user_id}]
        if memory_type:
            where_filters.append({"memory_type": memory_type})
        
        results = await self._vector.search(
            query_embedding=query_embedding.tolist(),
            n_results=n_results,
        )
        
        filtered = [
            r for r in results
            if r["metadata"].get("user_id") == user_id
        ]
        
        if tags:
            filtered = [
                r for r in filtered
                if any(tag in r["metadata"].get("tags", []) for tag in tags)
            ]
        
        return filtered

    async def get_memory(self, memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        results = await self._vector.get(ids=[memory_id])
        if not results:
            return None
        
        memory = results[0]
        if memory["metadata"].get("user_id") != user_id:
            return None
        
        return memory

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        memory = await self.get_memory(memory_id, user_id)
        if not memory:
            return False
        
        await self._vector.delete(ids=[memory_id])
        return True

    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        memory = await self.get_memory(memory_id, user_id)
        if not memory:
            return None
        
        new_content = content or memory["document"]
        new_embedding = await self._embedding.embed_text(new_content)
        
        update_metadata = memory["metadata"].copy()
        if metadata:
            update_metadata.update(metadata)
        
        await self._vector.update(
            ids=[memory_id],
            embeddings=[new_embedding.tolist()],
            documents=[new_content],
            metadatas=[update_metadata],
        )
        
        return await self.get_memory(memory_id, user_id)

    async def get_memories_by_type(
        self,
        user_id: str,
        memory_type: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = await self._vector.get(
            where={"user_id": user_id, "memory_type": memory_type},
            limit=limit,
        )
        return results

_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service