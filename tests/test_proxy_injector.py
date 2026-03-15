"""Proxy injector unit tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.proxy_injector import ProxyInjector, inject_proxy_to_service


class DummySession:
    def __init__(self):
        self.mounted = {}
        self.closed = False

    def mount(self, prefix, adapter):
        self.mounted[prefix] = adapter

    def close(self):
        self.closed = True


def setup_function():
    ProxyInjector._proxy_session = None
    ProxyInjector._direct_session = None


def test_get_session_returns_cached_instances(monkeypatch):
    created = []

    def _create(use_proxy=False):
        session = DummySession()
        created.append((use_proxy, session))
        return session

    monkeypatch.setattr(ProxyInjector, '_create_session', classmethod(lambda cls, use_proxy=False: _create(use_proxy)))

    first_proxy = ProxyInjector.get_session(requires_proxy=True)
    second_proxy = ProxyInjector.get_session(requires_proxy=True)
    first_direct = ProxyInjector.get_session(requires_proxy=False)
    second_direct = ProxyInjector.get_session(requires_proxy=False)

    assert first_proxy == second_proxy
    assert first_direct == second_direct
    assert created == [(True, first_proxy), (False, first_direct)]


def test_create_session_mounts_adapters_and_handles_proxy(monkeypatch):
    session = DummySession()
    monkeypatch.setattr('core.plugins.proxy_injector.requests.Session', lambda: session)
    monkeypatch.setattr('core.proxy_config.configure_requests_proxies', lambda s: {'http': 'http://proxy'})

    created = ProxyInjector._create_session(use_proxy=True)

    assert created is session
    assert 'https://' in session.mounted
    assert 'http://' in session.mounted


def test_create_session_handles_proxy_configuration_error(monkeypatch):
    session = DummySession()
    monkeypatch.setattr('core.plugins.proxy_injector.requests.Session', lambda: session)
    monkeypatch.setattr('core.proxy_config.configure_requests_proxies', lambda s: (_ for _ in ()).throw(RuntimeError('bad proxy')))

    created = ProxyInjector._create_session(use_proxy=True)

    assert created is session
    assert 'https://' in session.mounted


def test_reset_closes_existing_sessions():
    proxy = DummySession()
    direct = DummySession()
    ProxyInjector._proxy_session = proxy
    ProxyInjector._direct_session = direct

    ProxyInjector.reset()

    assert proxy.closed is True
    assert direct.closed is True
    assert ProxyInjector._proxy_session is None
    assert ProxyInjector._direct_session is None


def test_inject_proxy_to_service_handles_okx_service():
    class OKXMarketService:
        def __init__(self):
            self.proxy = 'http://proxy'

    service = OKXMarketService()

    inject_proxy_to_service(service, requires_proxy=True)

    assert service.proxy == 'http://proxy'


def test_inject_proxy_to_service_replaces_session(monkeypatch):
    target_session = object()
    service = SimpleNamespace(session='old')
    monkeypatch.setattr(ProxyInjector, 'get_session', classmethod(lambda cls, requires_proxy=False: target_session))

    inject_proxy_to_service(service, requires_proxy=True)

    assert service.session is target_session


def test_inject_proxy_to_service_without_session_attribute():
    service = SimpleNamespace(name='nosession')

    inject_proxy_to_service(service, requires_proxy=False)

    assert hasattr(service, 'name')
