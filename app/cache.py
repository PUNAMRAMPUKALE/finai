# app/cache.py
import json
import os
from typing import Any, Optional
import redis

# Example: redis://localhost:6379/0
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    global _redis
    if _redis is not None:
        return _redis
    try:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
        # quick ping so misconfig fails fast
        _redis.ping()
        return _redis
    except Exception:
        # no Redis → app still works, just without cache
        _redis = None
        return None


def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if not r:
        return None
    val = r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        # fail open – never block main path on cache errors
        pass


def cache_delete_prefix(prefix: str) -> None:
    """
    Simple invalidation: delete all keys that start with prefix.
    Suitable for small-ish key spaces.
    """
    r = get_redis()
    if not r:
        return
    try:
        for k in r.scan_iter(match=f"{prefix}*"):
            r.delete(k)
    except Exception:
        pass
