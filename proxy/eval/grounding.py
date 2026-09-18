import math
import re
from collections import Counter
from typing import Protocol


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class GroundingStore(Protocol):
    def add(self, collection: str, doc_id: str, text: str) -> None: ...
    def query(self, collection: str, query_text: str, k: int = 3) -> list[str]: ...


class InMemoryTFIDFStore:
    """Deterministic, dependency-free grounding store (D-018). Process-local, non-persistent."""

    def __init__(self):
        self._docs: dict[str, dict[str, str]] = {}

    def add(self, collection: str, doc_id: str, text: str) -> None:
        self._docs.setdefault(collection, {})[doc_id] = text

    def query(self, collection: str, query_text: str, k: int = 3) -> list[str]:
        docs = self._docs.get(collection, {})
        if not docs:
            return []
        q_vec = Counter(_tokenize(query_text))
        scored = [(doc_id, _cosine(q_vec, Counter(_tokenize(text)))) for doc_id, text in docs.items()]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [docs[doc_id] for doc_id, score in scored[:k] if score > 0]


class ChromaStore:
    """Persisted grounding store (D-008/OD-011 resolution: D-029). Requires `chromadb`
    (lazy import, like provider.py's Groq/Gemini clients, so it's not a hard dependency
    for callers that stick with InMemoryTFIDFStore)."""

    def __init__(self, persist_dir: str):
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_dir)

    def _collection(self, name: str):
        return self._client.get_or_create_collection(name)

    def add(self, collection: str, doc_id: str, text: str) -> None:
        self._collection(collection).upsert(ids=[doc_id], documents=[text])

    def query(self, collection: str, query_text: str, k: int = 3) -> list[str]:
        col = self._collection(collection)
        if col.count() == 0:
            return []
        result = col.query(query_texts=[query_text], n_results=min(k, col.count()))
        return result["documents"][0] if result["documents"] else []


_store: GroundingStore | None = None


def get_grounding_store() -> GroundingStore:
    """D-029: uses ChromaStore when settings.chroma_persist_dir is set and chromadb is
    importable; falls back to InMemoryTFIDFStore otherwise (dev/test default)."""
    global _store
    if _store is None:
        try:
            from proxy.config import settings

            _store = ChromaStore(settings.chroma_persist_dir)
        except Exception:
            _store = InMemoryTFIDFStore()
    return _store
