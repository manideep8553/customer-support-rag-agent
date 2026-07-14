import hashlib
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("gigacorp.cache")


class LRUCache:
    """Simple LRU cache with TTL support, thread-safe."""

    def __init__(self, maxsize: int = 1024, ttl: float = 0):
        self._lock = threading.Lock()
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: dict[str, tuple[float, object]] = {}
        self._access: dict[str, float] = {}

    def get(self, key: str) -> Optional[object]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, value = entry
            if self._ttl > 0 and time.monotonic() - ts > self._ttl:
                del self._cache[key]
                del self._access[key]
                return None
            self._access[key] = time.monotonic()
            return value

    def set(self, key: str, value: object) -> None:
        with self._lock:
            now = time.monotonic()
            self._cache[key] = (now, value)
            self._access[key] = now
            if len(self._cache) > self._maxsize:
                self._evict()

    def _evict(self) -> None:
        oldest = min(self._access.items(), key=lambda kv: kv[1])
        del self._cache[oldest[0]]
        del self._access[oldest[0]]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._access.clear()

    def __len__(self) -> int:
        return len(self._cache)


class EmbeddingCache:
    """Cache for text → embedding vector mappings.

    Speeds up repeated queries that share identical phrasing
    (common in multi-turn conversations like 'tell me more').
    """

    def __init__(self, maxsize: int = 2048):
        self._cache = LRUCache(maxsize=maxsize)

    def get(self, text: str) -> Optional[list[float]]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return self._cache.get(key)

    def set(self, text: str, embedding: list[float]) -> None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._cache.set(key, embedding)

    @property
    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


class ResponseCache:
    """Cache for (context, query) → response text.

    Prevents redundant LLM generation when the same question
    is asked with the same context within a session or across sessions.
    """

    def __init__(self, maxsize: int = 512, ttl: float = 300):
        self._cache = LRUCache(maxsize=maxsize, ttl=ttl)

    def _make_key(self, session_id: str, query: str, context_preview: str) -> str:
        raw = f"{session_id}|{query}|{context_preview[:200]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, session_id: str, query: str, context_preview: str) -> Optional[str]:
        key = self._make_key(session_id, query, context_preview)
        return self._cache.get(key)

    def set(self, session_id: str, query: str, context_preview: str, response: str) -> None:
        key = self._make_key(session_id, query, context_preview)
        self._cache.set(key, response)

    @property
    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


class TokenCache:
    """Cache for text → token count to avoid repeated tiktoken calls."""

    def __init__(self, maxsize: int = 4096):
        self._cache = LRUCache(maxsize=maxsize)

    def get(self, text: str) -> Optional[int]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return self._cache.get(key)

    def set(self, text: str, count: int) -> None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._cache.set(key, count)

    @property
    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


class WriteCoalescer:
    """Coalesces session save requests into batched disk writes.

    Instead of writing to disk on every add_turn call, this buffers
    writes and flushes them periodically or when a threshold is reached.
    """

    def __init__(self, flush_interval: float = 2.0, batch_threshold: int = 10):
        self._lock = threading.RLock()
        self._dirty: set[str] = set()
        self._flush_interval = flush_interval
        self._batch_threshold = batch_threshold
        self._timer: Optional[threading.Timer] = None
        self._save_fn = None
        self._running = True

    def set_save_fn(self, save_fn):
        self._save_fn = save_fn

    def mark_dirty(self, session_id: str) -> None:
        with self._lock:
            self._dirty.add(session_id)
            if len(self._dirty) >= self._batch_threshold:
                self._flush()
            elif self._timer is None:
                self._timer = threading.Timer(self._flush_interval, self._flush)
                self._timer.daemon = True
                self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            dirty = self._dirty.copy()
            self._dirty.clear()
            if self._timer:
                self._timer.cancel()
                self._timer = None
        if self._save_fn and dirty:
            for sid in dirty:
                try:
                    self._save_fn(sid)
                except Exception as e:
                    logger.warning("WriteCoalescer failed to save session %s: %s", sid, e)

    def flush_now(self) -> None:
        self._flush()

    def shutdown(self) -> None:
        self._running = False
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
        self._flush()


# Global cache singletons
embedding_cache = EmbeddingCache()
response_cache = ResponseCache()
token_cache = TokenCache()
