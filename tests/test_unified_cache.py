"""Unified cache unit tests."""

import fnmatch
import os
import sys
from typing import Any

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import unified_cache


class FakePipeline:
    def __init__(self, client: 'FakeRedisClient') -> None:
        self.client = client
        self.commands: list[tuple[str, tuple[Any, ...]]] = []

    def delete(self, key: str) -> 'FakePipeline':
        self.commands.append(('delete', (key,)))
        return self

    def zadd(self, key: str, mapping: dict[str, int]) -> 'FakePipeline':
        self.commands.append(('zadd', (key, mapping)))
        return self

    def expire(self, key: str, ttl: int) -> 'FakePipeline':
        self.commands.append(('expire', (key, ttl)))
        return self

    def execute(self) -> list[Any]:
        results = []
        for name, args in self.commands:
            results.append(getattr(self.client, name)(*args))
        self.commands.clear()
        return results


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.zsets: dict[str, dict[str, int]] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self.values[key] = value
        self.expirations[key] = ttl
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                deleted += 1
            if key in self.zsets:
                del self.zsets[key]
                deleted += 1
            self.expirations.pop(key, None)
        return deleted

    def zrange(self, key: str, start: int, end: int) -> list[str]:
        members = self._sorted_members(key)
        if end == -1:
            end = len(members) - 1
        return members[start:end + 1]

    def zadd(self, key: str, mapping: dict[str, int]) -> int:
        bucket = self.zsets.setdefault(key, {})
        bucket.update(mapping)
        return len(mapping)

    def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True

    def pipeline(self, transaction: bool = False) -> FakePipeline:
        return FakePipeline(self)

    def zcard(self, key: str) -> int:
        return len(self.zsets.get(key, {}))

    def zremrangebyrank(self, key: str, start: int, end: int) -> int:
        members = self._sorted_members(key)
        if not members:
            return 0
        if end == -1:
            end = len(members) - 1
        removed = members[start:end + 1]
        for member in removed:
            self.zsets[key].pop(member, None)
        return len(removed)

    def keys(self, pattern: str) -> list[str]:
        keyspace = set(self.values) | set(self.zsets)
        return sorted(key for key in keyspace if fnmatch.fnmatch(key, pattern))

    def _sorted_members(self, key: str) -> list[str]:
        bucket = self.zsets.get(key, {})
        return [member for member, _ in sorted(bucket.items(), key=lambda item: (item[1], item[0]))]


def _use_fake_redis(monkeypatch) -> FakeRedisClient:
    client = FakeRedisClient()
    monkeypatch.setattr(
        unified_cache.BaseCacheService,
        '_redis_client',
        staticmethod(lambda: client),
    )
    monkeypatch.setattr(unified_cache, '_cache_manager', None)
    return client


def test_cache_config_and_key_building():
    candle_config = unified_cache.CacheConfig.for_type(unified_cache.CacheDataType.CANDLESTICK)
    ticker = unified_cache.TickerCache()

    assert candle_config.ttl == 86400
    assert candle_config.max_entries == 5000
    assert ticker.build_key(source='OKX', symbol='btcusdt', mode='CONTRACT') == 'ticker:okx:BTCUSDT:contract'


def test_base_cache_round_trip(monkeypatch):
    client = _use_fake_redis(monkeypatch)
    cache = unified_cache.FundingRateCache()

    assert cache.set({'rate': 0.01}, source='OKX', symbol='btcusdt') is True
    assert cache.get(source='okx', symbol='BTCUSDT') == {'rate': 0.01}
    assert client.expirations['funding_rate:okx:BTCUSDT'] == cache.config.ttl
    assert cache.delete(source='okx', symbol='BTCUSDT') is True
    assert cache.get(source='okx', symbol='BTCUSDT') is None


def test_base_cache_returns_none_without_client(monkeypatch):
    monkeypatch.setattr(
        unified_cache.BaseCacheService,
        '_redis_client',
        staticmethod(lambda: None),
    )
    cache = unified_cache.FundingRateCache()

    assert cache.get(source='okx', symbol='BTCUSDT') is None
    assert cache.set({'rate': 1}, source='okx', symbol='BTCUSDT') is False
    assert cache.delete(source='okx', symbol='BTCUSDT') is False


def test_time_series_cache_set_get_and_trim(monkeypatch):
    _use_fake_redis(monkeypatch)
    config = unified_cache.CacheConfig(ttl=30, max_entries=2, key_prefix='candles')
    cache = unified_cache.CandlestickCache()
    cache.config = config

    series = [
        {'time': 1, 'close': 10},
        {'time': 2, 'close': 11},
        {'time': 3, 'close': 12},
    ]

    assert cache.set_series(series, source='okx', symbol='BTCUSDT', bar='1h') is True
    assert cache.get_series(source='okx', symbol='BTCUSDT', bar='1h') == series[-2:]


def test_time_series_cache_append_respects_order_and_trim(monkeypatch):
    _use_fake_redis(monkeypatch)
    config = unified_cache.CacheConfig(ttl=30, max_entries=2, key_prefix='funding_history')
    cache = unified_cache.FundingHistoryCache()
    cache.config = config

    assert cache.append_to_series({'timestamp': 2, 'rate': 0.2}, source='okx', symbol='BTCUSDT') is True
    assert cache.append_to_series({'timestamp': 1, 'rate': 0.1}, source='okx', symbol='BTCUSDT') is True
    assert cache.append_to_series({'timestamp': 3, 'rate': 0.3}, source='okx', symbol='BTCUSDT') is True

    assert cache.get_series(source='okx', symbol='BTCUSDT') == [
        {'timestamp': 2, 'rate': 0.2},
        {'timestamp': 3, 'rate': 0.3},
    ]


def test_unified_cache_manager_clear_all_and_stats(monkeypatch):
    client = _use_fake_redis(monkeypatch)
    manager = unified_cache.UnifiedCacheManager()

    manager.funding_rate.set({'value': 1}, source='okx', symbol='BTCUSDT')
    manager.ticker.set({'last': 100}, source='okx', symbol='BTCUSDT')
    manager.candlestick.set_series(
        [{'time': 1, 'close': 100}],
        source='okx',
        symbol='BTCUSDT',
        bar='1h',
    )

    stats = manager.get_cache_stats()

    assert stats['funding_rate'] == 1
    assert stats['ticker'] == 1
    assert stats['candles'] == 1
    assert manager.clear_all('ticker:*') == 1
    assert client.keys('ticker:*') == []
    assert manager.clear_all() == 2


def test_get_cache_manager_returns_singleton(monkeypatch):
    _use_fake_redis(monkeypatch)

    first = unified_cache.get_cache_manager()
    second = unified_cache.get_cache_manager()

    assert first is second