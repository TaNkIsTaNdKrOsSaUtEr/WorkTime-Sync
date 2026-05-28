# WorkTimeSync/services/cache.py
"""
Простой in‑memory кэш с TTL для демонстрации.
"""
import time
from typing import Any, Optional

_cache = {}

def get_cache(key: str) -> Optional[Any]:
    """Возвращает данные из кэша, если они не устарели."""
    if key in _cache:
        value, timestamp, ttl = _cache[key]
        if time.time() - timestamp < ttl:
            return value
        else:
            del _cache[key]
    return None

def set_cache(key: str, value: Any, ttl: int = 60):
    """Сохраняет данные в кэш на ttl секунд."""
    _cache[key] = (value, time.time(), ttl)

def clear_cache():
    """Очищает весь кэш."""
    _cache.clear()