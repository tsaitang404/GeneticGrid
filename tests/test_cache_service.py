"""Candlestick cache service unit tests."""

import os
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import django  # type: ignore
import pytest  # type: ignore
from django.db.utils import OperationalError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.cache_service import CandlestickCacheService
from core.services import MarketAPIError


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.ops = []

    def zremrangebyscore(self, key, low, high):
        self.ops.append(('zremrangebyscore', (key, low, high)))
        return self

    def zadd(self, key, mapping):
        self.ops.append(('zadd', (key, mapping)))
        return self

    def expire(self, key, ttl):
        self.ops.append(('expire', (key, ttl)))
        return self

    def execute(self):
        for name, args in self.ops:
            getattr(self.client, name)(*args)
        self.ops.clear()
        return []


class FakeRedis:
    def __init__(self):
        self.zsets = {}
        self.expirations = {}

    def pipeline(self, transaction=False):
        return FakePipeline(self)

    def zremrangebyscore(self, key, low, high):
        bucket = self.zsets.setdefault(key, {})
        removed = [member for member, score in bucket.items() if low <= score <= high]
        for member in removed:
            del bucket[member]
        return len(removed)

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)
        return len(mapping)

    def expire(self, key, ttl):
        self.expirations[key] = ttl
        return True

    def zcard(self, key):
        return len(self.zsets.get(key, {}))

    def zremrangebyrank(self, key, start, end):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda item: (item[1], item[0]))
        if end == -1:
            end = len(items) - 1
        for member, _ in items[start:end + 1]:
            self.zsets[key].pop(member, None)
        return len(items[start:end + 1])

    def exists(self, key):
        return key in self.zsets and bool(self.zsets[key])

    def zrevrangebyscore(self, key, max_score, min_score, start=0, num=None):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda item: (item[1], item[0]), reverse=True)
        def in_range(score):
            high = float('inf') if max_score == '+inf' else max_score
            low = float('-inf') if min_score == '-inf' else min_score
            return low <= score <= high
        filtered = [member for member, score in items if in_range(score)]
        sliced = filtered[start:] if num is None else filtered[start:start + num]
        return sliced


def test_normalize_candle_payload_supports_dict_and_object():
    candle = {'time': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 3}
    obj = SimpleNamespace(time=2, open=2, high=3, low=1, close=2.5, volume=4)

    assert CandlestickCacheService._normalize_candle_payload(candle) == {
        'time': 1,
        'open': 1.0,
        'high': 2.0,
        'low': 0.5,
        'close': 1.5,
        'volume': 3.0,
    }
    assert CandlestickCacheService._normalize_candle_payload(obj)['time'] == 2


def test_normalize_candle_payload_requires_time():
    with pytest.raises(ValueError):
        CandlestickCacheService._normalize_candle_payload({'close': 1.2})


def test_normalize_candle_payload_handles_none_values():
    payload = CandlestickCacheService._normalize_candle_payload({'time': 1, 'open': None, 'high': None, 'low': None, 'close': None, 'volume': None})
    assert payload == {'time': 1, 'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': 0.0, 'volume': 0.0}


def test_write_and_read_redis_series(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(CandlestickCacheService, '_redis_client', staticmethod(lambda: client))
    monkeypatch.setattr(CandlestickCacheService, '_redis_max_entries', 2)

    CandlestickCacheService._write_to_redis('okx', 'BTCUSDT', '1h', 'spot', [
        {'time': 1, 'close': 1.0},
        {'time': 2, 'close': 2.0},
        {'time': 3, 'close': 3.0},
    ])

    result = CandlestickCacheService._get_from_redis('okx', 'BTCUSDT', '1h', 'spot', 10, None, None)

    assert result == [
        {'time': 2, 'close': 2.0},
        {'time': 3, 'close': 3.0},
    ]
    assert client.expirations['candles:okx:BTCUSDT:spot:1h'] == CandlestickCacheService._redis_ttl_seconds


def test_get_from_redis_returns_none_when_cache_absent(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, '_redis_client', staticmethod(lambda: FakeRedis()))

    assert CandlestickCacheService._get_from_redis('okx', 'BTCUSDT', '1h', 'spot', 10, None, None) is None


def test_get_from_redis_returns_none_without_client(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, '_redis_client', staticmethod(lambda: None))
    assert CandlestickCacheService._get_from_redis('okx', 'BTCUSDT', '1h', 'spot', 10, None, None) is None


def test_get_from_redis_returns_empty_list_on_no_items(monkeypatch):
    class EmptyRedis(FakeRedis):
        def exists(self, key):
            return True

        def zrevrangebyscore(self, *args, **kwargs):
            return []

    monkeypatch.setattr(CandlestickCacheService, '_redis_client', staticmethod(lambda: EmptyRedis()))
    assert CandlestickCacheService._get_from_redis('okx', 'BTCUSDT', '1h', 'spot', 10, None, None) == []


def test_get_from_redis_handles_json_error(monkeypatch):
    class BadRedis(FakeRedis):
        def exists(self, key):
            return True

        def zrevrangebyscore(self, *args, **kwargs):
            return ['{bad json']

    monkeypatch.setattr(CandlestickCacheService, '_redis_client', staticmethod(lambda: BadRedis()))
    assert CandlestickCacheService._get_from_redis('okx', 'BTCUSDT', '1h', 'spot', 10, None, None) is None


def test_get_from_cache_returns_redis_result_directly(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, '_get_from_redis', staticmethod(lambda *args, **kwargs: [{'time': 1}]))
    assert CandlestickCacheService.get_from_cache('okx', 'BTCUSDT', '1h') == [{'time': 1}]


def test_get_from_cache_uses_db_when_redis_miss(monkeypatch):
    class FakeCandle:
        def __init__(self, time, open_, high, low, close, volume):
            self.time = time
            self.open = open_
            self.high = high
            self.low = low
            self.close = close
            self.volume = volume

    class FakeQuerySet:
        def __init__(self, candles):
            self.candles = candles

        def filter(self, **kwargs):
            if 'time__lt' in kwargs:
                self.candles = [c for c in self.candles if c.time < kwargs['time__lt']]
            if 'time__gt' in kwargs:
                self.candles = [c for c in self.candles if c.time > kwargs['time__gt']]
            return self

        def order_by(self, field):
            reverse = field.startswith('-')
            self.candles = sorted(self.candles, key=lambda c: c.time, reverse=reverse)
            return self

        def __getitem__(self, item):
            return self.candles[item]

    candles = [
        FakeCandle(1, 1, 2, 0.5, 1.5, 10),
        FakeCandle(2, 2, 3, 1.5, 2.5, 20),
        FakeCandle(3, 3, 4, 2.5, 3.5, 30),
    ]
    prime_calls = []

    monkeypatch.setattr(CandlestickCacheService, '_get_from_redis', staticmethod(lambda *args, **kwargs: None))
    monkeypatch.setattr(
        'core.cache_service.CandlestickCache.objects',
        SimpleNamespace(filter=lambda **kwargs: FakeQuerySet(candles.copy())),
    )
    monkeypatch.setattr(CandlestickCacheService, '_maybe_prime_redis', staticmethod(lambda *args: prime_calls.append(args)))

    result = CandlestickCacheService.get_from_cache('okx', 'BTCUSDT', '1h', mode='spot', limit=2, before=3)

    assert result == [
        {'time': 1, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 10.0},
        {'time': 2, 'open': 2.0, 'high': 3.0, 'low': 1.5, 'close': 2.5, 'volume': 20.0},
    ]
    assert len(prime_calls) == 1


def test_get_cache_range_uses_aggregate(monkeypatch):
    monkeypatch.setattr(
        'core.cache_service.CandlestickCache.objects',
        SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(aggregate=lambda **agg_kwargs: {'oldest': 1, 'newest': 9, 'count': 3})),
    )

    result = CandlestickCacheService.get_cache_range('okx', 'BTCUSDT', '1h')

    assert result == {'oldest': 1, 'newest': 9, 'count': 3}


def test_save_to_cache_persists_and_writes_redis(monkeypatch):
    class FakeObjects:
        def __init__(self):
            self.calls = []

        def update_or_create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(), len(self.calls) == 1

    fake_objects = FakeObjects()
    redis_calls = []

    @contextmanager
    def fake_atomic():
        yield

    monkeypatch.setattr('core.cache_service.close_old_connections', lambda: None)
    monkeypatch.setattr('core.cache_service.transaction.atomic', fake_atomic)
    monkeypatch.setattr('core.cache_service.CandlestickCache.objects', fake_objects)
    monkeypatch.setattr(CandlestickCacheService, '_write_to_redis', staticmethod(lambda *args: redis_calls.append(args)))

    saved = CandlestickCacheService.save_to_cache(
        'okx',
        'BTCUSDT',
        '1h',
        candles=[
            {'time': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10},
            {'time': 2, 'open': 2, 'high': 3, 'low': 1.5, 'close': 2.5, 'volume': 20},
        ],
        mode='spot',
    )

    assert saved == 1
    assert len(fake_objects.calls) == 2
    assert len(redis_calls) == 1


def test_save_to_cache_returns_zero_for_empty_or_invalid(monkeypatch):
    assert CandlestickCacheService.save_to_cache('okx', 'BTCUSDT', '1h', candles=[]) == 0

    monkeypatch.setattr(CandlestickCacheService, '_normalize_candle_payload', staticmethod(lambda candle: (_ for _ in ()).throw(ValueError('bad'))))
    assert CandlestickCacheService.save_to_cache('okx', 'BTCUSDT', '1h', candles=[{'close': 1}]) == 0


def test_save_to_cache_returns_zero_when_max_retries_zero():
    saved = CandlestickCacheService.save_to_cache('okx', 'BTCUSDT', '1h', candles=[{'time': 1, 'close': 1}], max_retries=0)
    assert saved == 0


def test_save_to_cache_retries_on_database_locked(monkeypatch):
    attempts = {'count': 0}

    class FakeObjects:
        def update_or_create(self, **kwargs):
            attempts['count'] += 1
            if attempts['count'] == 1:
                raise OperationalError('database is locked')
            return SimpleNamespace(), True

    @contextmanager
    def fake_atomic():
        yield

    monkeypatch.setattr('core.cache_service.close_old_connections', lambda: None)
    monkeypatch.setattr('core.cache_service.transaction.atomic', fake_atomic)
    monkeypatch.setattr('core.cache_service.CandlestickCache.objects', FakeObjects())
    monkeypatch.setattr('core.cache_service.time.sleep', lambda _s: None)
    monkeypatch.setattr(CandlestickCacheService, '_write_to_redis', staticmethod(lambda *args: None))

    saved = CandlestickCacheService.save_to_cache(
        'okx',
        'BTCUSDT',
        '1h',
        candles=[{'time': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10}],
        mode='spot',
        max_retries=2,
    )

    assert saved == 1
    assert attempts['count'] == 2


def test_save_to_cache_raises_when_operational_error_not_lock(monkeypatch):
    class FakeObjects:
        def update_or_create(self, **kwargs):
            raise OperationalError('other db error')

    @contextmanager
    def fake_atomic():
        yield

    monkeypatch.setattr('core.cache_service.close_old_connections', lambda: None)
    monkeypatch.setattr('core.cache_service.transaction.atomic', fake_atomic)
    monkeypatch.setattr('core.cache_service.CandlestickCache.objects', FakeObjects())

    with pytest.raises(OperationalError):
        CandlestickCacheService.save_to_cache(
            'okx',
            'BTCUSDT',
            '1h',
            candles=[{'time': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10}],
            mode='spot',
            max_retries=1,
        )


def test_maybe_prime_redis_only_on_latest_range(monkeypatch):
    calls = []
    monkeypatch.setattr(CandlestickCacheService, '_write_to_redis', staticmethod(lambda *args: calls.append(args)))

    CandlestickCacheService._maybe_prime_redis('okx', 'BTCUSDT', '1h', 'spot', [{'time': 1}], None, None)
    CandlestickCacheService._maybe_prime_redis('okx', 'BTCUSDT', '1h', 'spot', [{'time': 1}], 10, None)
    CandlestickCacheService._maybe_prime_redis('okx', 'BTCUSDT', '1h', 'spot', [], None, None)

    assert len(calls) == 1


def test_fetch_and_cache_uses_service_and_swallows_cache_write_failure(monkeypatch):
    service = SimpleNamespace(
        is_using_plugin=True,
        get_candlesticks=lambda **kwargs: [{'time': 1000, 'close': 1.1}],
    )
    monkeypatch.setattr('core.cache_service.get_unified_service', lambda source: service)
    monkeypatch.setattr(CandlestickCacheService, 'save_to_cache', staticmethod(lambda **kwargs: (_ for _ in ()).throw(RuntimeError('cache failed'))))

    data = CandlestickCacheService.fetch_and_cache('okx', 'BTCUSDT', '1h', limit=10)

    assert data == [{'time': 1000, 'close': 1.1}]


def test_fetch_and_cache_re_raises_market_api_error(monkeypatch):
    service = SimpleNamespace(
        is_using_plugin=False,
        get_candlesticks=lambda **kwargs: (_ for _ in ()).throw(MarketAPIError('boom')),
    )
    monkeypatch.setattr('core.cache_service.get_unified_service', lambda source: service)

    with pytest.raises(MarketAPIError):
        CandlestickCacheService.fetch_and_cache('okx', 'BTCUSDT', '1h')


def test_get_with_auto_fetch_prefers_cache(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, 'get_from_cache', staticmethod(lambda *args, **kwargs: [{'time': 1}, {'time': 2}]))
    monkeypatch.setattr(CandlestickCacheService, 'fetch_and_cache', staticmethod(lambda *args, **kwargs: [{'time': 3}]))

    result = CandlestickCacheService.get_with_auto_fetch('okx', 'BTCUSDT', '1h', limit=2)

    assert result == [{'time': 1}, {'time': 2}]


def test_get_with_auto_fetch_filters_after(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, 'get_from_cache', staticmethod(lambda *args, **kwargs: []))
    monkeypatch.setattr(CandlestickCacheService, 'fetch_and_cache', staticmethod(lambda *args, **kwargs: [{'time': 1}, {'time': 5}, {'time': 8}]))

    result = CandlestickCacheService.get_with_auto_fetch('okx', 'BTCUSDT', '1h', limit=3, after=4)

    assert result == [{'time': 5}, {'time': 8}]


def test_get_with_auto_fetch_returns_partial_cache_when_api_fails(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, 'get_from_cache', staticmethod(lambda *args, **kwargs: [{'time': 1}]))
    monkeypatch.setattr(CandlestickCacheService, 'fetch_and_cache', staticmethod(lambda *args, **kwargs: (_ for _ in ()).throw(MarketAPIError('down'))))

    result = CandlestickCacheService.get_with_auto_fetch('okx', 'BTCUSDT', '1h', limit=3)

    assert result == [{'time': 1}]


def test_get_with_auto_fetch_raises_when_cache_empty_and_api_fails(monkeypatch):
    monkeypatch.setattr(CandlestickCacheService, 'get_from_cache', staticmethod(lambda *args, **kwargs: []))
    monkeypatch.setattr(CandlestickCacheService, 'fetch_and_cache', staticmethod(lambda *args, **kwargs: (_ for _ in ()).throw(MarketAPIError('down'))))

    with pytest.raises(MarketAPIError):
        CandlestickCacheService.get_with_auto_fetch('okx', 'BTCUSDT', '1h', limit=3)


def test_fetch_and_cache_logs_legacy_service_path(monkeypatch):
    service = SimpleNamespace(
        is_using_plugin=False,
        get_candlesticks=lambda **kwargs: [{'time': 1000, 'close': 1.1}],
    )
    monkeypatch.setattr('core.cache_service.get_unified_service', lambda source: service)
    monkeypatch.setattr(CandlestickCacheService, 'save_to_cache', staticmethod(lambda **kwargs: 1))

    data = CandlestickCacheService.fetch_and_cache('okx', 'BTCUSDT', '1h', limit=10)

    assert data == [{'time': 1000, 'close': 1.1}]
