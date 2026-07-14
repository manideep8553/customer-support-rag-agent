import pytest
from backend.cache import LRUCache, EmbeddingCache, ResponseCache, TokenCache


def test_lru_cache_basic():
    cache = LRUCache(maxsize=10)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("nonexistent") is None


def test_lru_cache_eviction():
    cache = LRUCache(maxsize=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)

    assert cache.get("a") is None
    assert cache.get("d") == 4


def test_lru_cache_ttl():
    import time
    cache = LRUCache(maxsize=10, ttl=0.1)
    cache.set("key", "value")
    assert cache.get("key") == "value"
    time.sleep(0.15)
    assert cache.get("key") is None


def test_lru_cache_clear():
    cache = LRUCache(maxsize=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert len(cache) == 0


def test_embedding_cache():
    cache = EmbeddingCache()
    text = "hello world"
    embedding = [0.1, 0.2, 0.3]
    cache.set(text, embedding)
    result = cache.get(text)
    assert result == embedding
    assert cache.size == 1


def test_response_cache():
    cache = ResponseCache()
    cache.set("session1", "hello", "context", "Hi there!")
    result = cache.get("session1", "hello", "context")
    assert result == "Hi there!"


def test_token_cache():
    cache = TokenCache()
    cache.set("hello world", 2)
    assert cache.get("hello world") == 2
