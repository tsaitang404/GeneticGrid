"""OKX realtime websocket tests."""

import os
import sys
import json

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('REALTIME_INGESTION_AUTO_START', 'false')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.sources import okx_stream


class DummyThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        return None

    def is_alive(self):
        return True


class DummyWS:
    def __init__(self):
        self.messages = []

    def send(self, message: str):
        self.messages.append(message)


def test_okx_stream_worker_uses_business_ws_for_candles(monkeypatch):
    monkeypatch.setattr(okx_stream, '_build_proxy_kwargs', lambda: {})
    monkeypatch.setattr(okx_stream.threading, 'Thread', DummyThread)

    worker = okx_stream.OKXStreamWorker('BTC-USDT', '1m')

    assert worker._ws_url == okx_stream.OKXStreamWorker.BUSINESS_WS_URL
    assert worker.channel == 'candle1m'


def test_okx_stream_worker_subscribes_without_inst_type(monkeypatch):
    monkeypatch.setattr(okx_stream, '_build_proxy_kwargs', lambda: {})
    monkeypatch.setattr(okx_stream.threading, 'Thread', DummyThread)
    worker = okx_stream.OKXStreamWorker('BTC-USDT-SWAP', '1s')
    ws = DummyWS()

    worker._on_open(ws)

    payload = json.loads(ws.messages[0])
    assert payload['op'] == 'subscribe'
    assert payload['args'][0] == {
        'channel': 'candle1s',
        'instId': 'BTC-USDT-SWAP',
    }