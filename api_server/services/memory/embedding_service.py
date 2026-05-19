import os
import numpy as np
from typing import List, Optional
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

class EmbeddingService:
    def __init__(self):
        self._model = None
        self._model_name = _get_model_name()

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    async def embed_text(self, text: str) -> np.ndarray:
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding

    async def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        self._load_model()
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    async def embed_code(self, code: str, language: Optional[str] = None) -> np.ndarray:
        prefix = f"{language or 'code'}: " if language else ""
        return await self.embed_text(prefix + code)

    def get_embedding_dimension(self) -> int:
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service