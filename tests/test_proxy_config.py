"""Proxy configuration tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import proxy_config


def setup_function():
    proxy_config._PROXY_CACHE.clear()


class FakeSocket:
    def __init__(self, connect_result=0):
        self.connect_result = connect_result
        self.timeout = None
        self.closed = False

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect_ex(self, addr):
        return self.connect_result

    def close(self):
        self.closed = True


def test_is_proxy_available_uses_cache(monkeypatch):
    calls = {'count': 0}

    def _socket(*args, **kwargs):
        calls['count'] += 1
        return FakeSocket(connect_result=0)

    monkeypatch.setattr(proxy_config.socket, 'socket', _socket)
    proxy_config.PROXY_CONFIG['http'] = {'host': '127.0.0.1', 'port': 8080}

    assert proxy_config.is_proxy_available('http') is True
    assert proxy_config.is_proxy_available('http') is True
    assert calls['count'] == 1


def test_is_proxy_available_handles_invalid_config_and_exception(monkeypatch):
    assert proxy_config.is_proxy_available('missing') is False

    def _raise(*args, **kwargs):
        raise RuntimeError('socket fail')

    monkeypatch.setattr(proxy_config.socket, 'socket', _raise)
    assert proxy_config.is_proxy_available('http') is False


def test_get_proxy_url_and_dict(monkeypatch):
    monkeypatch.setattr(proxy_config, 'is_proxy_available', lambda proxy_type='http': True)
    proxy_config.PROXY_CONFIG['http'] = {'host': '127.0.0.1', 'port': 8080}
    proxy_config.PROXY_CONFIG['socks5'] = {'host': '127.0.0.1', 'port': 1080}

    assert proxy_config.get_proxy_url('http') == 'http://127.0.0.1:8080'
    assert proxy_config.get_proxy_url('socks5') == 'socks5://127.0.0.1:1080'

    monkeypatch.setattr(proxy_config, 'get_proxy_url', lambda proxy_type='http': 'socks5://127.0.0.1:1080')
    proxy_dict = proxy_config.get_proxy_dict()
    assert proxy_dict['http://'] == 'socks5://127.0.0.1:1080'
    assert proxy_dict['https://'] == 'socks5://127.0.0.1:1080'


def test_get_proxy_prefers_http_then_socks5(monkeypatch):
    def _url(proxy_type='http'):
        if proxy_type == 'http':
            return None
        return 'socks5://127.0.0.1:1080'

    monkeypatch.setattr(proxy_config, 'get_proxy_url', _url)
    assert proxy_config.get_proxy() == 'socks5://127.0.0.1:1080'


def test_configure_requests_proxies_updates_session(monkeypatch):
    monkeypatch.setattr(proxy_config, 'get_proxy_dict', lambda: {'http://': 'http://proxy', 'https://': 'http://proxy'})
    session = SimpleNamespace(proxies={})

    result = proxy_config.configure_requests_proxies(session)

    assert result['http://'] == 'http://proxy'
    assert session.proxies['https://'] == 'http://proxy'


def test_print_proxy_status_outputs(monkeypatch, capsys):
    monkeypatch.setattr(proxy_config, 'is_proxy_available', lambda proxy_type='socks5': proxy_type == 'http')
    monkeypatch.setattr(proxy_config, 'get_proxy', lambda: 'http://proxy')
    monkeypatch.setattr(proxy_config, 'get_proxy_dict', lambda: {'http://': 'http://proxy'})

    proxy_config.print_proxy_status()
    output = capsys.readouterr().out

    assert '代理配置状态' in output
    assert 'HTTP' in output
    assert '通用代理' in output
