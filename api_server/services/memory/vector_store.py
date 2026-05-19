import os
import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any

class VectorStore:
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "cato_memory",
    ):
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.expanduser("~"),
                ".cato",
                "chroma_db",
            )

        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        collection = self._get_collection()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{}] * len(ids),
        )

    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
        )

        return [
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    async def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        results = collection.get(
            ids=ids,
            where=where,
            limit=limit,
        )

        return [
            {
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
            for i in range(len(results["ids"]))
        ]

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ):
        collection = self._get_collection()
        collection.delete(ids=ids, where=where)

    async def update(
        self,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        collection = self._get_collection()
        collection.update(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    async def count(self) -> int:
        collection = self._get_collection()
        return collection.count()

_vector_store: Optional[VectorStore] = None

def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: str = "cato_memory",
) -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(persist_directory, collection_name)
    return _vector_store