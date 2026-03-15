"""Plugin initialization tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import plugin_init
from core.services import MarketAPIError


def test_normalize_stream_entry_for_string_and_dict():
    assert plugin_init._normalize_stream_entry('okx:BTCUSDT:1m:2:10') == {
        'source': 'okx',
        'symbol': 'BTCUSDT',
        'bar': '1m',
        'poll_interval': 2.0,
        'batch_size': 10,
    }
    assert plugin_init._normalize_stream_entry({'source': 'OKX', 'symbol': 'btc-usdt'}) == {
        'source': 'okx',
        'symbol': 'BTCUSDT',
        'bar': '1s',
        'poll_interval': 1.0,
        'batch_size': 300,
    }


def test_normalize_stream_entry_rejects_invalid_data():
    assert plugin_init._normalize_stream_entry('') is None
    assert plugin_init._normalize_stream_entry({'source': 'okx'}) is None
    assert plugin_init._normalize_stream_entry(123) is None


def test_auto_start_realtime_streams_noop_when_disabled(monkeypatch):
    called = []
    monkeypatch.setattr(plugin_init, 'settings', SimpleNamespace(REALTIME_INGESTION_AUTO_START=False, REALTIME_INGESTION_STREAMS=['okx:BTCUSDT:1s']))
    monkeypatch.setattr(plugin_init.RealtimeIngestionService, 'get_default', staticmethod(lambda: called.append('service')))

    plugin_init._auto_start_realtime_streams()

    assert called == []


def test_auto_start_realtime_streams_starts_valid_entries_and_handles_errors(monkeypatch):
    calls = []

    class FakeService:
        def start_stream(self, **kwargs):
            calls.append(kwargs)
            if kwargs['source'] == 'fail':
                raise MarketAPIError('bad stream')
            if kwargs['source'] == 'boom':
                raise RuntimeError('unknown')

    monkeypatch.setattr(
        plugin_init,
        'settings',
        SimpleNamespace(
            REALTIME_INGESTION_AUTO_START=True,
            REALTIME_INGESTION_STREAMS=[
                'okx:BTCUSDT:1s',
                {'source': 'fail', 'symbol': 'BTCUSDT', 'bar': '1m'},
                {'source': 'boom', 'symbol': 'ETHUSDT', 'bar': '5m'},
                {'source': None, 'symbol': 'BTCUSDT'},
            ],
        ),
    )
    monkeypatch.setattr(plugin_init.RealtimeIngestionService, 'get_default', staticmethod(lambda: FakeService()))

    plugin_init._auto_start_realtime_streams()

    assert calls[0]['source'] == 'okx'
    assert calls[1]['source'] == 'fail'
    assert calls[2]['source'] == 'boom'


def test_initialize_plugins_invokes_discovery_and_autostart(monkeypatch):
    manager = SimpleNamespace(
        auto_discover_plugins=lambda: {'success': 1, 'failed': 1, 'errors': {'bad': 'failed'}},
        list_plugin_names=lambda: ['okx'],
    )
    auto_calls = []
    monkeypatch.setattr(plugin_init, 'get_plugin_manager', lambda: manager)
    monkeypatch.setattr(plugin_init, '_auto_start_realtime_streams', lambda: auto_calls.append('started'))

    plugin_init.initialize_plugins()

    assert auto_calls == ['started']
