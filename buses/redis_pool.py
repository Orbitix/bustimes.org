import threading

import redis


class SharedConnectionPool(redis.ConnectionPool):
    """Under ASGI, Django's caches handler is task-local, so each request creates
    a new cache backend instance. Sharing the pool between them stops each
    request opening (and dropping) its own Redis connections."""

    _pools = {}
    _lock = threading.Lock()

    @classmethod
    def from_url(cls, url, **kwargs):
        key = (url, frozenset(kwargs.items()))
        with cls._lock:
            if key not in cls._pools:
                cls._pools[key] = super().from_url(url, **kwargs)
            return cls._pools[key]
