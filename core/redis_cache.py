"""Shared Redis client for caching hot candlestick data."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from django.conf import settings

if TYPE_CHECKING:
    import redis
else:
    try:
        import redis  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        redis = None  # type: ignore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    _redis_client: Optional[redis.Redis] = None
else:
    _redis_client = None


def redis_cache_enabled() -> bool:
    """Return whether Redis caching is configured and enabled."""
    return bool(getattr(settings, 'REDIS_CACHE_ENABLED', False))


def get_redis_client():
    """Return a singleton Redis client if caching is enabled and available.
    
    Returns:
        Optional[redis.Redis]: Redis client instance or None if disabled/unavailable.
    """
    global _redis_client

    if not redis_cache_enabled():
        return None

    if redis is None:
        logger.warning("Redis package is not installed; disabling Redis cache layer")
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.Redis.from_url(
            getattr(settings, 'REDIS_CACHE_URL', 'redis://127.0.0.1:6379/0'),
            decode_responses=True,
            health_check_interval=30,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        _redis_client.ping()
    except Exception as exc:  # pragma: no cover - network/runtime failure
        logger.warning("Unable to initialize Redis cache client: %s", exc)
        _redis_client = None

    return _redis_client


def reset_redis_client() -> None:
    """Force the next call to create a new client (mainly for testing)."""
    global _redis_client
    _redis_client = None


__all__ = ["get_redis_client", "redis_cache_enabled", "reset_redis_client"]
