"""Plugin adapter unit tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore
import pytest  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugin_adapter import PluginAdapter, UnifiedMarketService, get_unified_service
from core.plugins.base import CandleData, PluginError, TickerData
from core.services import MarketAPIError


class FakePluginManager:
    def __init__(self, plugin=None, error=None):
        self.plugin = plugin
        self.error = error

    def get_plugin(self, source):
        if self.error:
            raise self.error
        return self.plugin


class FakePlugin:
    def __init__(self):
        self.candle_calls = []
        self.ticker_calls = []

    def get_candlesticks(self, symbol, bar, limit, before, mode):
        self.candle_calls.append((symbol, bar, limit, before, mode))
        return [CandleData(time=1, open=1, high=2, low=0.5, close=1.5, volume=3)]

    def get_ticker(self, symbol, mode):
        self.ticker_calls.append((symbol, mode))
        return TickerData(
            inst_id=symbol,
            last=100,
            bid=99,
            ask=101,
            high_24h=110,
            low_24h=90,
            change_24h_pct=25,
            volume_24h=1234,
        )


def test_plugin_adapter_converts_candle_and_ticker():
    candle = CandleData(time=1, open=1, high=2, low=0.5, close=1.5, volume=3)
    ticker = TickerData(
        inst_id='BTC-USDT',
        last=100,
        bid=99,
        ask=101,
        high_24h=110,
        low_24h=90,
        change_24h_pct=25,
        volume_24h=1234,
    )

    assert PluginAdapter.candle_to_dict(candle) == candle.to_dict()
    assert PluginAdapter.candles_to_dict_list([candle]) == [candle.to_dict()]

    payload = PluginAdapter.ticker_to_dict(ticker)
    assert payload['instId'] == 'BTC-USDT'
    assert payload['last'] == '100'
    assert payload['high24h'] == '110'
    assert payload['high_24h'] == '110'
    assert payload['vol24h'] == '1234'
    assert payload['open24h'] == '80.0'


def test_plugin_error_to_api_error():
    error = PluginAdapter.plugin_error_to_api_error(PluginError('boom'))

    assert isinstance(error, MarketAPIError)
    assert str(error) == 'boom'


def test_unified_market_service_uses_plugin(monkeypatch):
    plugin = FakePlugin()
    monkeypatch.setattr('core.plugin_adapter.get_plugin_manager', lambda: FakePluginManager(plugin=plugin))

    service = UnifiedMarketService('okx')
    candles = service.get_candlesticks('BTC-USDT', '1H', limit=10, before=5000, mode='contract')
    ticker = service.get_ticker('BTC-USDT', mode='spot')

    assert service.is_using_plugin is True
    assert candles == [{'time': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 3}]
    assert plugin.candle_calls == [('BTC-USDT', '1H', 10, 5, 'contract')]
    assert ticker['instId'] == 'BTC-USDT'
    assert plugin.ticker_calls == [('BTC-USDT', 'spot')]


def test_unified_market_service_converts_plugin_errors(monkeypatch):
    class ErrorPlugin:
        def get_candlesticks(self, **kwargs):
            raise PluginError('bad plugin')

        def get_ticker(self, **kwargs):
            raise RuntimeError('broken')

    monkeypatch.setattr('core.plugin_adapter.get_plugin_manager', lambda: FakePluginManager(plugin=ErrorPlugin()))
    service = UnifiedMarketService('okx')

    with pytest.raises(MarketAPIError, match='bad plugin'):
        service.get_candlesticks()

    with pytest.raises(MarketAPIError, match='插件系统错误: broken'):
        service.get_ticker()


def test_unified_market_service_falls_back_to_legacy_service(monkeypatch):
    legacy_service = SimpleNamespace(
        get_candlesticks=lambda inst_id, bar, limit, before: [{'legacy': True, 'before': before}],
        get_ticker=lambda inst_id: {'legacy': True, 'instId': inst_id},
    )
    monkeypatch.setattr('core.plugin_adapter.get_plugin_manager', lambda: FakePluginManager(plugin=None))
    monkeypatch.setattr('core.services.get_market_service', lambda source: legacy_service)

    service = UnifiedMarketService('okx')

    assert service.is_using_plugin is False
    assert service.get_candlesticks(before=5000) == [{'legacy': True, 'before': 5000}]
    assert service.get_ticker('BTC-USDT') == {'legacy': True, 'instId': 'BTC-USDT'}


def test_get_unified_service_wraps_init_error(monkeypatch):
    monkeypatch.setattr('core.plugin_adapter.UnifiedMarketService', lambda source: (_ for _ in ()).throw(RuntimeError('init failed')))

    with pytest.raises(MarketAPIError, match='初始化数据源 okx 失败: init failed'):
        get_unified_service('okx')
