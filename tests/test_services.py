"""Service layer tests."""

import os
import sys
import threading
from types import SimpleNamespace

import django  # type: ignore
import pytest  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.base import CandleData
from core.services import MarketAPIError, RealtimeIngestionConfig, RealtimeIngestionService, get_market_service, get_realtime_ingestion_service


@pytest.fixture(autouse=True)
def _reset_default_singleton():
    original = RealtimeIngestionService._default_instance
    RealtimeIngestionService._default_instance = None
    yield
    RealtimeIngestionService._default_instance = original


class FakePlugin:
    def __init__(self, supports_websocket=True, valid_granularity=True, realtime_manager=None):
        self._supports_websocket = supports_websocket
        self._valid_granularity = valid_granularity
        self._realtime = realtime_manager

    def get_capability(self):
        return SimpleNamespace(supports_websocket=self._supports_websocket)

    def validate_granularity(self, bar):
        return self._valid_granularity

    def _normalize_symbol(self, symbol, mode='spot'):
        return symbol

    def _normalize_granularity(self, bar):
        return bar


class FakeRealtimeManager:
    def __init__(self, batches=None, raise_error=False, enabled=True):
        self._batches = list(batches or [])
        self.raise_error = raise_error
        self.enabled = enabled

    def get_latest_candles(self, inst_id, interval, limit):
        if self.raise_error:
            raise RuntimeError('stream error')
        if not self._batches:
            return []
        return self._batches.pop(0)


def _candle(ts, close):
    return CandleData(time=ts, open=close - 1, high=close + 1, low=close - 2, close=close, volume=10)


def test_realtime_ingestion_config_validation_and_normalize():
    cfg = RealtimeIngestionConfig(source='OKX', symbol='btc-usdt', mode='SPOT', bar='1S')
    assert cfg.source == 'okx'
    assert cfg.symbol == 'BTCUSDT'
    assert cfg.mode == 'spot'
    assert cfg.bar == '1s'

    with pytest.raises(ValueError):
        RealtimeIngestionConfig(source='okx', symbol='BTCUSDT', poll_interval=0)
    with pytest.raises(ValueError):
        RealtimeIngestionConfig(source='okx', symbol='BTCUSDT', batch_size=0)


def test_start_stream_validates_plugin_capability_and_manager():
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: None), cache_service=SimpleNamespace())
    with pytest.raises(MarketAPIError, match='未找到数据源插件'):
        service.start_stream('okx', 'BTCUSDT')

    plugin = FakePlugin(supports_websocket=False, realtime_manager=FakeRealtimeManager())
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: plugin), cache_service=SimpleNamespace(get_cache_range=lambda *a: None))
    with pytest.raises(MarketAPIError, match='不支持 websocket'):
        service.start_stream('okx', 'BTCUSDT')

    plugin = FakePlugin(supports_websocket=True, valid_granularity=False, realtime_manager=FakeRealtimeManager())
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: plugin), cache_service=SimpleNamespace(get_cache_range=lambda *a: None))
    with pytest.raises(MarketAPIError, match='不支持粒度'):
        service.start_stream('okx', 'BTCUSDT')

    plugin = FakePlugin(supports_websocket=True, valid_granularity=True, realtime_manager=None)
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: plugin), cache_service=SimpleNamespace(get_cache_range=lambda *a: None))
    with pytest.raises(MarketAPIError, match='未提供实时流管理器'):
        service.start_stream('okx', 'BTCUSDT')


def test_start_stream_existing_context_autostart(monkeypatch):
    plugin = FakePlugin(realtime_manager=FakeRealtimeManager())
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: plugin), cache_service=SimpleNamespace(get_cache_range=lambda *a: {'newest': 10}))

    key = service.start_stream('okx', 'BTCUSDT', autostart=False)
    assert key in service._streams

    class DeadThread:
        def is_alive(self):
            return False

    service._streams[key].thread = DeadThread()
    monkeypatch.setattr(service, '_spawn_thread', lambda k: 'spawned-thread')
    returned = service.start_stream('okx', 'BTCUSDT', autostart=True)

    assert returned == key
    assert service._streams[key].thread == 'spawned-thread'


def test_collect_once_paths_and_payload_filtering():
    cache = SimpleNamespace(save_to_cache=lambda **kwargs: 1, get_cache_range=lambda *a: {'newest': None})
    plugin = FakePlugin(realtime_manager=FakeRealtimeManager())
    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(get_plugin=lambda source: plugin), cache_service=cache)
    key = service.start_stream('okx', 'BTCUSDT', autostart=False)
    ctx = service._streams[key]

    ctx.realtime_manager = FakeRealtimeManager(raise_error=True)
    assert service._collect_once(ctx) is False

    ctx.realtime_manager = FakeRealtimeManager(batches=[[]])
    assert service._collect_once(ctx) is True

    ctx.realtime_manager = FakeRealtimeManager(batches=[[_candle(1, 10)]])
    assert service._collect_once(ctx) is True
    assert ctx.total_persisted == 1

    ctx.last_timestamp = 1
    ctx.last_signature = (9, 11, 8, 10, 10)
    payload = service._prepare_payload(ctx, [_candle(1, 10), _candle(1, 12), _candle(2, 13)])
    assert len(payload) == 2


def test_run_once_list_streams_stop_and_shutdown():
    manager = SimpleNamespace(get_plugin=lambda source: FakePlugin(realtime_manager=FakeRealtimeManager()))
    cache = SimpleNamespace(save_to_cache=lambda **kwargs: 1, get_cache_range=lambda *a: {'newest': None})
    service = RealtimeIngestionService(plugin_manager=manager, cache_service=cache)

    with pytest.raises(MarketAPIError):
        service.run_once('okx', 'BTCUSDT')

    key = service.start_stream('okx', 'BTCUSDT', autostart=False)
    assert service.list_streams()[0]['key'] == key

    class AliveThread:
        def __init__(self):
            self.joined = False

        def is_alive(self):
            return True

        def join(self, timeout=None):
            self.joined = True

    service._streams[key].thread = AliveThread()
    service.stop_stream('okx', 'BTCUSDT', wait=True)
    assert service.list_streams() == []

    key2 = service.start_stream('okx', 'BTCUSDT', autostart=False)
    service._streams[key2].thread = AliveThread()
    service.shutdown(wait=True)
    assert service.list_streams() == []


def test_resolve_realtime_manager_and_cache_range_fallback():
    class GetterPlugin(FakePlugin):
        def get_realtime_manager(self):
            return FakeRealtimeManager(enabled=False)

    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(), cache_service=SimpleNamespace())
    assert service._resolve_realtime_manager(GetterPlugin()) is None

    class TypeErrorPlugin(FakePlugin):
        def get_realtime_manager(self, required_arg):
            return required_arg

    assert callable(service._resolve_realtime_manager(TypeErrorPlugin()))

    service = RealtimeIngestionService(plugin_manager=SimpleNamespace(), cache_service=SimpleNamespace(get_cache_range=lambda *a: (_ for _ in ()).throw(RuntimeError('fail'))))
    assert service._safe_get_cache_range('okx', 'BTCUSDT', '1s', 'spot') is None


def test_deprecated_market_service_and_default_service_access():
    with pytest.raises(DeprecationWarning):
        get_market_service('okx')

    first = get_realtime_ingestion_service()
    second = RealtimeIngestionService.get_default()
    assert first is second


def test_make_key_and_candle_helpers():
    assert RealtimeIngestionService._make_key('OKX', 'btcusdt', '1S', 'SPOT') == 'okx::BTCUSDT::spot::1s'
    candle = _candle(1, 10)
    assert RealtimeIngestionService._candle_to_dict(candle)['time'] == 1
    assert RealtimeIngestionService._signature(candle) == (9, 11, 8, 10, 10)