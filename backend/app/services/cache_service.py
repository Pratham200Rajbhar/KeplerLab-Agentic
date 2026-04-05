from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional
from collections import OrderedDict

class TTLCache:
    """
    A simple thread-safe LRU cache with Time-To-Live (TTL).
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            
            self._cache[key] = (value, expiry)
            
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key_prefix: str) -> None:
        with self._lock:
            keys_to_del = [k for k in self._cache.keys() if k.startswith(key_prefix)]
            for k in keys_to_del:
                del self._cache[k]

# Global cache instance
_global_cache = TTLCache(max_size=1000, default_ttl=300)

def get_cached(key: str) -> Optional[Any]:
    """
    Retrieve a value from the cache. Returns None if not found or expired.
    Use for non-personalized, expensive GET endpoints.
    """
    return _global_cache.get(key)

def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """
    Store a value in the cache with a specific TTL.
    """
    _global_cache.set(key, value, ttl_seconds)

def invalidate_cache(key_prefix: str) -> None:
    """
    Invalidate all cache entries starting with the given prefix.
    """
    _global_cache.invalidate(key_prefix)
