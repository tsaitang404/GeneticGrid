"""Derivative cache wrapper tests."""

import os
import sys
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.derivative_cache import DerivativeDataCacheService


class SpyStore:
    def __init__(self):
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(('get', kwargs))
        return kwargs

    def set(self, data, **kwargs):
        self.calls.append(('set', data, kwargs))
        return True

    def get_series(self, **kwargs):
        self.calls.append(('get_series', kwargs))
        return [kwargs]

    def set_series(self, data, **kwargs):
        self.calls.append(('set_series', data, kwargs))
        return True


def _manager():
    return SimpleNamespace(
        funding_rate=SpyStore(),
        funding_history=SpyStore(),
        basis=SpyStore(),
        basis_history=SpyStore(),
        clear_all_calls=[],
        clear_all=lambda pattern: 2 if pattern.startswith('funding') else 1,
    )


def test_derivative_cache_delegates_current_value_calls(monkeypatch):
    manager = _manager()
    monkeypatch.setattr('core.derivative_cache.get_cache_manager', lambda: manager)

    assert DerivativeDataCacheService.get_funding_rate_from_cache('okx', 'BTCUSDT') == {
        'source': 'okx',
        'symbol': 'BTCUSDT',
    }
    DerivativeDataCacheService.save_funding_rate_to_cache('okx', 'BTCUSDT', {'rate': 0.1})
    assert DerivativeDataCacheService.get_basis_from_cache('okx', 'BTCUSDT', 'perpetual') == {
        'source': 'okx',
        'symbol': 'BTCUSDT',
        'contract_type': 'perpetual',
    }
    DerivativeDataCacheService.save_basis_to_cache('okx', 'BTCUSDT', 'perpetual', {'basis': 1.2})

    assert manager.funding_rate.calls[0] == ('get', {'source': 'okx', 'symbol': 'BTCUSDT'})
    assert manager.basis.calls[1] == ('set', {'basis': 1.2}, {'source': 'okx', 'symbol': 'BTCUSDT', 'contract_type': 'perpetual'})


def test_derivative_cache_delegates_history_calls_and_granularity(monkeypatch):
    manager = _manager()
    monkeypatch.setattr('core.derivative_cache.get_cache_manager', lambda: manager)

    history = DerivativeDataCacheService.get_funding_history_from_cache('okx', 'BTCUSDT')
    basis_history = DerivativeDataCacheService.get_basis_history_from_cache('okx', 'BTCUSDT', 'perpetual', '1h')
    DerivativeDataCacheService.save_funding_history_to_cache('okx', 'BTCUSDT', [{'rate': 1}])
    DerivativeDataCacheService.save_basis_history_to_cache('okx', 'BTCUSDT', 'perpetual', [{'basis': 1}], '1h')

    assert history == [{'source': 'okx', 'symbol': 'BTCUSDT'}]
    assert basis_history == [{'source': 'okx', 'symbol': 'BTCUSDT', 'contract_type': 'perpetual:1h'}]
    assert manager.basis_history.calls[-1] == (
        'set_series',
        [{'basis': 1}],
        {'source': 'okx', 'symbol': 'BTCUSDT', 'contract_type': 'perpetual:1h'},
    )


def test_derivative_cache_clear_all_aggregates_counts(monkeypatch):
    manager = _manager()
    calls = []
    manager.clear_all = lambda pattern: calls.append(pattern) or (2 if pattern.startswith('funding') else 1)
    monkeypatch.setattr('core.derivative_cache.get_cache_manager', lambda: manager)

    deleted = DerivativeDataCacheService.clear_all_derivative_cache()

    assert deleted == 6
    assert calls == ['funding_rate:*', 'funding_history:*', 'basis:*', 'basis_history:*']
