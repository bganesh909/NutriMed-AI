import json
import logging
import os
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class VectorStore:
    """FAISS-based vector store with SentenceTransformer embeddings."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        index_path: Optional[str] = None,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.index_path = Path(index_path or settings.VECTOR_INDEX_PATH)
        self._model: Optional[SentenceTransformer] = None
        self._index: Optional[faiss.IndexFlatIP] = None
        self._documents: list[dict] = []
        self._dimension: Optional[int] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info("Model loaded. Embedding dimension: %d", self._dimension)
        return self._model

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            _ = self.model
        return self._dimension

    def _ensure_index(self):
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dimension)
            logger.info("Created new FAISS index with dimension %d", self.dimension)

    def _embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)

    def create_index(self, documents: list[dict]) -> int:
        """Create a new index from a list of documents.

        Each document should have 'content' and optionally 'metadata'.
        """
        if not documents:
            return 0

        texts = [doc["content"] for doc in documents]
        embeddings = self._embed(texts)

        self._index = faiss.IndexFlatIP(self.dimension)
        self._index.add(embeddings)
        self._documents = [
            {"content": doc["content"], "metadata": doc.get("metadata", {})}
            for doc in documents
        ]

        logger.info("Created index with %d documents", len(documents))
        return len(documents)

    def add_documents(self, documents: list[dict]) -> int:
        """Add documents to the existing index."""
        if not documents:
            return 0

        self._ensure_index()

        texts = [doc["content"] for doc in documents]
        embeddings = self._embed(texts)

        self._index.add(embeddings)
        self._documents.extend(
            {"content": doc["content"], "metadata": doc.get("metadata", {})}
            for doc in documents
        )

        logger.info("Added %d documents. Total: %d", len(documents), len(self._documents))
        return len(documents)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Search the index for similar documents."""
        if self._index is None or self._index.ntotal == 0:
            logger.warning("Search called on empty index")
            return []

        query_embedding = self._embed([query])

        search_k = min(top_k * 3, self._index.ntotal) if filter_metadata else min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_embedding, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._documents):
                continue
            doc = self._documents[idx]

            if filter_metadata:
                match = all(
                    doc["metadata"].get(k) == v for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            results.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": float(score),
            })

            if len(results) >= top_k:
                break

        return results

    def save_index(self, path: Optional[str] = None):
        """Save the index and document metadata to disk."""
        save_path = Path(path) if path else self.index_path
        save_path.mkdir(parents=True, exist_ok=True)

        if self._index is not None:
            faiss.write_index(self._index, str(save_path / "index.faiss"))
            with open(save_path / "documents.json", "w", encoding="utf-8") as f:
                json.dump(self._documents, f, ensure_ascii=False)
            logger.info("Saved index with %d documents to %s", len(self._documents), save_path)
        else:
            logger.warning("No index to save")

    def load_index(self, path: Optional[str] = None) -> bool:
        """Load a previously saved index from disk."""
        load_path = Path(path) if path else self.index_path
        index_file = load_path / "index.faiss"
        docs_file = load_path / "documents.json"

        if not index_file.exists() or not docs_file.exists():
            logger.info("No saved index found at %s", load_path)
            return False

        try:
            self._index = faiss.read_index(str(index_file))
            with open(docs_file, "r", encoding="utf-8") as f:
                self._documents = json.load(f)
            self._dimension = self._index.d
            logger.info(
                "Loaded index with %d documents from %s",
                len(self._documents),
                load_path,
            )
            return True
        except Exception as exc:
            logger.error("Failed to load index from %s: %s", load_path, exc)
            return False

    @property
    def total_documents(self) -> int:
        return len(self._documents)

    @property
    def is_loaded(self) -> bool:
        return self._index is not None and self._index.ntotal > 0


# Module-level singleton
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
