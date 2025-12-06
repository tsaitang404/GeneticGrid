# -*- coding: utf-8 -*-
"""Realtime ingestion service unit tests"""

import os
import sys
from datetime import datetime
from typing import List, Optional

import django  # type: ignore
import pytest  # type: ignore

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('REALTIME_INGESTION_AUTO_START', 'false')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.base import (CandleData, Capability, DataSourceMetadata,
                                MarketDataSourcePlugin, SourceType, TickerData)
from core.services import MarketAPIError, RealtimeIngestionService


class DummyRealtimeManager:
    def __init__(self, batches: List[List[CandleData]]) -> None:
        self._batches = list(batches)
        self.requests = []

    def get_latest_candles(self, inst_id: str, interval: str, limit: int) -> List[CandleData]:
        self.requests.append((inst_id, interval, limit))
        if not self._batches:
            return []
        return self._batches.pop(0)

    @property
    def enabled(self) -> bool:
        return True


class DummyPlugin(MarketDataSourcePlugin):
    def __init__(self, realtime: DummyRealtimeManager):
        self._realtime = realtime
        super().__init__()

    def _get_metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            name="okx",
            display_name="OKX",
            description="Dummy",
            source_type=SourceType.EXCHANGE,
            plugin_version="test",
            last_updated=datetime.utcnow(),
        )

    def _get_capability(self) -> Capability:
        return Capability(
            supports_candlesticks=True,
            candlestick_granularities=["1s"],
            supports_real_time=True,
            supports_websocket=True,
            supported_symbols=["BTCUSDT"],
        )

    def _get_candlesticks_impl(self, symbol: str, bar: str, limit: int = 100, before: Optional[int] = None):
        return []

    def _get_ticker_impl(self, symbol: str) -> TickerData:
        raise NotImplementedError

    def get_realtime_manager(self) -> DummyRealtimeManager:  # type: ignore[override]
        return self._realtime

    def _normalize_symbol(self, symbol: str) -> str:
        symbol = symbol.upper().replace('-', '').replace('/', '')
        return f"{symbol[:-4]}-{symbol[-4:]}"


class DummyPluginManager:
    def __init__(self, plugin: Optional[MarketDataSourcePlugin] = None) -> None:
        self._plugin = plugin

    def get_plugin(self, name: str) -> Optional[MarketDataSourcePlugin]:
        if self._plugin and self._plugin.name == name:
            return self._plugin
        return None


class DummyCacheService:
    def __init__(self) -> None:
        self.saved_batches: List[List[dict]] = []
        self._ranges = {}

    def get_cache_range(self, source: str, symbol: str, bar: str):
        return self._ranges.get((source, symbol, bar), {
            'oldest': None,
            'newest': None,
            'count': 0,
        })

    def save_to_cache(self, source: str, symbol: str, bar: str, candles: List[dict], max_retries: int = 3):
        self.saved_batches.append(candles)
        if not candles:
            return 0

        key = (source, symbol, bar)
        existing = self._ranges.get(key)
        if existing:
            oldest = existing['oldest'] if existing['oldest'] is not None else candles[0]['time']
            count = existing['count'] + len(candles)
        else:
            oldest = candles[0]['time']
            count = len(candles)

        self._ranges[key] = {
            'oldest': oldest,
            'newest': candles[-1]['time'],
            'count': count,
        }
        return len(candles)


def _make_candle(ts: int, close: float, open_: float = None) -> CandleData:
    open_price = open_ if open_ is not None else close - 1
    return CandleData(
        time=ts,
        open=open_price,
        high=close + 0.5,
        low=open_price - 0.5,
        close=close,
        volume=1.0,
    )


def test_realtime_service_collects_and_persists():
    batches = [
        [_make_candle(100, 1.0), _make_candle(101, 1.1)],
        [_make_candle(101, 1.2), _make_candle(102, 1.3)],
    ]
    realtime = DummyRealtimeManager(batches)
    plugin = DummyPlugin(realtime)
    manager = DummyPluginManager(plugin)
    cache = DummyCacheService()

    service = RealtimeIngestionService(plugin_manager=manager, cache_service=cache)
    service.start_stream('okx', 'BTCUSDT', bar='1s', autostart=False, batch_size=10)

    assert service.run_once('okx', 'BTCUSDT', '1s') is True
    assert [c['time'] for c in cache.saved_batches[0]] == [100, 101]

    assert service.run_once('okx', 'BTCUSDT', '1s') is True
    assert [c['time'] for c in cache.saved_batches[1]] == [101, 102]
    assert cache.saved_batches[1][0]['close'] == 1.2

    service.shutdown(wait=False)


def test_realtime_service_missing_plugin():
    manager = DummyPluginManager()
    service = RealtimeIngestionService(plugin_manager=manager)

    with pytest.raises(MarketAPIError):
        service.start_stream('unknown', 'BTCUSDT')