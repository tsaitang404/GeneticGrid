"""Redis cache helper tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import redis_cache


def setup_function():
    redis_cache.reset_redis_client()


def test_redis_cache_enabled_uses_setting(monkeypatch):
    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=True))
    assert redis_cache.redis_cache_enabled() is True

    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=False))
    assert redis_cache.redis_cache_enabled() is False


def test_get_redis_client_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=False))
    assert redis_cache.get_redis_client() is None


def test_get_redis_client_handles_missing_package(monkeypatch):
    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=True))
    monkeypatch.setattr(redis_cache, 'redis', None)
    assert redis_cache.get_redis_client() is None


def test_get_redis_client_creates_singleton_and_pings(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.ping_count = 0

        def ping(self):
            self.ping_count += 1

    fake_client = FakeClient()
    redis_mod = SimpleNamespace(Redis=SimpleNamespace(from_url=lambda *args, **kwargs: fake_client))
    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=True, REDIS_CACHE_URL='redis://x'))
    monkeypatch.setattr(redis_cache, 'redis', redis_mod)

    first = redis_cache.get_redis_client()
    second = redis_cache.get_redis_client()

    assert first is fake_client
    assert second is fake_client
    assert fake_client.ping_count == 1


def test_get_redis_client_handles_connection_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError('connect fail')

    redis_mod = SimpleNamespace(Redis=SimpleNamespace(from_url=_raise))
    monkeypatch.setattr(redis_cache, 'settings', SimpleNamespace(REDIS_CACHE_ENABLED=True, REDIS_CACHE_URL='redis://x'))
    monkeypatch.setattr(redis_cache, 'redis', redis_mod)

    assert redis_cache.get_redis_client() is None
