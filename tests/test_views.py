"""View layer unit tests."""

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import mock_open

import django  # type: ignore
import requests  # type: ignore
from django.test import RequestFactory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import views
from core.services import MarketAPIError


class FakePluginManager:
    def __init__(self, plugin_map):
        self.plugin_map = plugin_map

    def get_plugin(self, name):
        return self.plugin_map.get(name)

    def get_all_plugins(self):
        return self.plugin_map


class FakePlugin:
    def __init__(self):
        self.metadata = SimpleNamespace(
            display_name='OKX',
            requires_proxy=False,
            to_dict=lambda: {'display_name': 'OKX', 'requires_proxy': False},
        )
        self.capability = SimpleNamespace(
            supports_funding_rate=True,
            supports_contract_basis=True,
            to_dict=lambda: {'supports_funding_rate': True, 'supports_contract_basis': True},
        )

    def get_metadata(self):
        return self.metadata

    def get_capability(self):
        return self.capability

    def get_funding_rate(self, symbol):
        return SimpleNamespace(to_dict=lambda: {'symbol': symbol, 'rate': 0.01})

    def get_funding_rate_history(self, symbol, limit):
        return [{'symbol': symbol, 'rate': 0.01}] * limit

    def get_contract_basis(self, symbol, contract_type):
        return SimpleNamespace(to_dict=lambda: {'symbol': symbol, 'contract_type': contract_type, 'basis': 1.23})

    def get_contract_basis_history(self, symbol, contract_type, limit, granularity):
        return [{'symbol': symbol, 'contract_type': contract_type, 'granularity': granularity}] * limit


def _json(response):
    return json.loads(response.content.decode('utf-8'))


def test_index_returns_built_html(monkeypatch):
    request = RequestFactory().get('/')
    monkeypatch.setattr('builtins.open', mock_open(read_data='<html>ok</html>'))

    response = views.index(request)

    assert response.status_code == 200
    assert response.content == b'<html>ok</html>'


def test_market_view_delegates_to_index(monkeypatch):
    request = RequestFactory().get('/market/')
    monkeypatch.setattr(views, 'index', lambda req: views.HttpResponse('ok'))

    response = views.market_view(request)

    assert response.status_code == 200
    assert response.content == b'ok'


def test_api_candlesticks_rejects_invalid_mode():
    request = RequestFactory().get('/api/candlesticks/', {'mode': 'margin'})

    response = views.api_candlesticks(request)

    assert response.status_code == 400
    assert _json(response)['error'] == '不支持的交易模式: margin'


def test_api_candlesticks_returns_data_with_short_cache(monkeypatch):
    request = RequestFactory().get(
        '/api/candlesticks/',
        {'symbol': 'BTCUSDT', 'bar': '1h', 'source': 'okx', 'mode': 'spot'},
    )
    monkeypatch.setattr(
        views.CandlestickCacheService,
        'get_with_auto_fetch',
        staticmethod(lambda **kwargs: [{'time': 1000, 'close': 12.3}]),
    )
    monkeypatch.setattr(
        views.CandlestickCacheService,
        'get_cache_range',
        staticmethod(lambda *args, **kwargs: {'count': 1, 'oldest': 1000, 'newest': 1000}),
    )

    response = views.api_candlesticks(request)

    assert response.status_code == 200
    assert response['Cache-Control'] == 'public, max-age=5'
    assert _json(response)['data'][0]['close'] == 12.3


def test_api_candlesticks_returns_history_cache_header(monkeypatch):
    request = RequestFactory().get('/api/candlesticks/', {'before': '2000'})
    monkeypatch.setattr(
        views.CandlestickCacheService,
        'get_with_auto_fetch',
        staticmethod(lambda **kwargs: []),
    )
    monkeypatch.setattr(
        views.CandlestickCacheService,
        'get_cache_range',
        staticmethod(lambda *args, **kwargs: {'count': 0, 'oldest': None, 'newest': None}),
    )

    response = views.api_candlesticks(request)

    assert response.status_code == 200
    assert response['Cache-Control'] == 'public, max-age=300'


def test_api_candlesticks_handles_market_api_error(monkeypatch):
    request = RequestFactory().get('/api/candlesticks/')
    monkeypatch.setattr(
        views.CandlestickCacheService,
        'get_with_auto_fetch',
        staticmethod(lambda **kwargs: (_ for _ in ()).throw(MarketAPIError('boom'))),
    )

    response = views.api_candlesticks(request)

    assert response.status_code == 500
    assert _json(response)['error'] == 'boom'


def test_api_ticker_rejects_invalid_mode():
    request = RequestFactory().get('/api/ticker/', {'mode': 'futures'})

    response = views.api_ticker(request)

    assert response.status_code == 400
    assert _json(response)['error'] == '不支持的交易模式: futures'


def test_api_ticker_returns_unified_service_data(monkeypatch):
    request = RequestFactory().get('/api/ticker/', {'symbol': 'BTCUSDT', 'source': 'okx', 'mode': 'spot'})
    service = SimpleNamespace(
        is_using_plugin=True,
        get_ticker=lambda inst_id, mode: {'last': 123.45, 'inst_id': inst_id, 'mode': mode},
    )
    monkeypatch.setattr(views, 'get_unified_service', lambda source: service)

    response = views.api_ticker(request)

    assert response.status_code == 200
    assert response['Cache-Control'] == 'public, max-age=3'
    assert _json(response)['using_plugin'] is True


def test_api_ticker_handles_market_api_error(monkeypatch):
    request = RequestFactory().get('/api/ticker/', {'symbol': 'BTCUSDT', 'source': 'okx', 'mode': 'spot'})
    monkeypatch.setattr(views, 'get_unified_service', lambda source: (_ for _ in ()).throw(MarketAPIError('ticker fail')))

    response = views.api_ticker(request)

    assert response.status_code == 500
    assert _json(response)['error'] == 'ticker fail'


def test_api_proxy_status_returns_proxy_snapshot(monkeypatch):
    request = RequestFactory().get('/api/proxy-status/')
    monkeypatch.setattr(views, 'get_proxy_settings_snapshot', lambda: {
        'enabled': True,
        'http': {'available': True},
        'socks5': {'available': False},
    })

    response = views.api_proxy_status(request)

    assert response.status_code == 200
    payload = _json(response)
    assert payload['data']['http']['available'] is True
    assert payload['data']['socks5']['available'] is False


def test_api_sources_returns_plugin_metadata(monkeypatch):
    request = RequestFactory().get('/api/sources/')
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': FakePlugin()}))

    response = views.api_sources(request)

    assert response.status_code == 200
    payload = _json(response)
    assert payload['total'] == 1
    assert payload['data']['okx']['metadata']['display_name'] == 'OKX'


def test_api_source_capabilities_handles_missing_source(monkeypatch):
    request = RequestFactory().get('/api/sources/unknown/capabilities/')
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({}))

    response = views.api_source_capabilities(request, 'unknown')

    assert response.status_code == 404
    assert '不存在' in _json(response)['error']


def test_api_source_documentation_returns_generated_content(monkeypatch):
    request = RequestFactory().get('/api/documentation/sources/')
    manager = FakePluginManager({'okx': FakePlugin()})
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: manager)
    monkeypatch.setattr(views.DocumentationGenerator, 'generate_all_plugins_doc', staticmethod(lambda m: '# docs'))
    monkeypatch.setattr(views.DocumentationGenerator, 'generate_capabilities_json', staticmethod(lambda m: {'okx': {'name': 'okx'}}))

    response = views.api_source_documentation(request)

    assert response.status_code == 200
    payload = _json(response)
    assert payload['data']['markdown'] == '# docs'
    assert payload['data']['json']['okx']['name'] == 'okx'


def test_api_funding_rate_uses_cache_when_available(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/', {'symbol': 'BTCUSDT', 'source': 'okx'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_rate_from_cache', staticmethod(lambda *args: {'rate': 0.01}))

    response = views.api_funding_rate(request)

    assert response.status_code == 200
    assert response['Cache-Control'] == 'public, max-age=30'
    assert _json(response)['cached'] is True


def test_api_funding_rate_returns_404_for_missing_source(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/', {'source': 'unknown'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_rate_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({}))

    response = views.api_funding_rate(request)

    assert response.status_code == 404


def test_api_funding_rate_returns_400_when_not_supported(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/', {'source': 'okx'})
    plugin = FakePlugin()
    plugin.capability.supports_funding_rate = False
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_rate_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': plugin}))

    response = views.api_funding_rate(request)

    assert response.status_code == 400


def test_api_funding_rate_handles_plugin_error(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/', {'source': 'okx'})

    class ErrorPlugin(FakePlugin):
        def get_funding_rate(self, symbol):
            raise views.PluginError('plugin fail')

    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_rate_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': ErrorPlugin()}))

    response = views.api_funding_rate(request)

    assert response.status_code == 500
    assert _json(response)['error'] == 'plugin fail'


def test_api_funding_rate_success_path_without_cache(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/', {'symbol': 'BTCUSDT', 'source': 'okx'})
    save_calls = []
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_rate_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views.DerivativeDataCacheService, 'save_funding_rate_to_cache', staticmethod(lambda *args: save_calls.append(args)))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': FakePlugin()}))

    response = views.api_funding_rate(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is False
    assert len(save_calls) == 1


def test_api_funding_rate_history_fetches_and_caches(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/history/', {'symbol': 'BTCUSDT', 'source': 'okx', 'limit': '2'})
    plugin = FakePlugin()
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_history_from_cache', staticmethod(lambda *args: None))
    save_calls = []
    monkeypatch.setattr(views.DerivativeDataCacheService, 'save_funding_history_to_cache', staticmethod(lambda *args: save_calls.append(args)))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': plugin}))

    response = views.api_funding_rate_history(request)

    assert response.status_code == 200
    assert len(_json(response)['data']) == 2
    assert len(save_calls) == 1


def test_api_funding_rate_history_uses_cache_when_sufficient(monkeypatch):
    request = RequestFactory().get('/api/funding-rate/history/', {'symbol': 'BTCUSDT', 'source': 'okx', 'limit': '2'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_funding_history_from_cache', staticmethod(lambda *args: [{'rate': 1}, {'rate': 2}, {'rate': 3}]))

    response = views.api_funding_rate_history(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is True
    assert len(_json(response)['data']) == 2


def test_api_contract_basis_history_returns_404_for_missing_plugin(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/history/', {'source': 'okx'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_history_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({}))

    response = views.api_contract_basis_history(request)

    assert response.status_code == 404


def test_api_contract_basis_history_returns_400_when_not_supported(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/history/', {'source': 'okx'})
    plugin = FakePlugin()
    plugin.capability.supports_contract_basis = False
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_history_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': plugin}))

    response = views.api_contract_basis_history(request)

    assert response.status_code == 400


def test_api_contract_basis_history_success_without_cache(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/history/', {'source': 'okx', 'limit': '2', 'granularity': '1h'})
    save_calls = []
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_history_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views.DerivativeDataCacheService, 'save_basis_history_to_cache', staticmethod(lambda *args: save_calls.append(args)))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': FakePlugin()}))

    response = views.api_contract_basis_history(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is False
    assert len(save_calls) == 1


def test_api_contract_basis_history_handles_plugin_error(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/history/', {'source': 'okx'})

    class ErrorPlugin(FakePlugin):
        def get_contract_basis_history(self, **kwargs):
            raise views.PluginError('basis history fail')

    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_history_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': ErrorPlugin()}))

    response = views.api_contract_basis_history(request)

    assert response.status_code == 500


def test_api_contract_basis_handles_plugin_error(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/', {'source': 'okx'})

    class ErrorPlugin(FakePlugin):
        def get_contract_basis(self, **kwargs):
            raise views.PluginError('basis fail')

    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': ErrorPlugin()}))

    response = views.api_contract_basis(request)

    assert response.status_code == 500


def test_api_contract_basis_history_uses_cache(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/history/', {'symbol': 'BTCUSDT', 'source': 'okx', 'limit': '1'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_history_from_cache', staticmethod(lambda *args: [{'basis': 1.1}]))

    response = views.api_contract_basis_history(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is True


def test_api_contract_basis_fetches_from_plugin(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/', {'symbol': 'BTCUSDT', 'source': 'okx'})
    plugin = FakePlugin()
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_from_cache', staticmethod(lambda *args: None))
    save_calls = []
    monkeypatch.setattr(views.DerivativeDataCacheService, 'save_basis_to_cache', staticmethod(lambda *args: save_calls.append(args)))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': plugin}))

    response = views.api_contract_basis(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is False
    assert len(save_calls) == 1


def test_api_contract_basis_uses_cache_when_available(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/', {'source': 'okx'})
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_from_cache', staticmethod(lambda *args: {'basis': 2.3}))

    response = views.api_contract_basis(request)

    assert response.status_code == 200
    assert _json(response)['cached'] is True


def test_api_contract_basis_returns_400_when_not_supported(monkeypatch):
    request = RequestFactory().get('/api/contract-basis/', {'source': 'okx'})
    plugin = FakePlugin()
    plugin.capability.supports_contract_basis = False
    monkeypatch.setattr(views.DerivativeDataCacheService, 'get_basis_from_cache', staticmethod(lambda *args: None))
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: FakePluginManager({'okx': plugin}))

    response = views.api_contract_basis(request)

    assert response.status_code == 400


def test_api_proxy_status_handles_exception(monkeypatch):
    request = RequestFactory().get('/api/proxy-status/')
    monkeypatch.setattr(views, 'get_proxy_settings_snapshot', lambda: (_ for _ in ()).throw(RuntimeError('boom')))

    response = views.api_proxy_status(request)

    assert response.status_code == 500


def test_api_proxy_config_get_returns_snapshot(monkeypatch):
    request = RequestFactory().get('/api/proxy-config/')
    monkeypatch.setattr(views, 'get_proxy_settings_snapshot', lambda: {'enabled': True})

    response = views.api_proxy_config(request)

    assert response.status_code == 200
    assert _json(response)['data']['enabled'] is True


def test_api_proxy_config_post_updates_proxy(monkeypatch):
    payload = {'enabled': False}
    request = RequestFactory().post(
        '/api/proxy-config/',
        data=json.dumps(payload),
        content_type='application/json',
    )
    monkeypatch.setattr(views, 'update_proxy_settings', lambda data: {'enabled': data['enabled']})

    response = views.api_proxy_config(request)

    assert response.status_code == 200
    assert _json(response)['data']['enabled'] is False


def test_api_proxy_config_post_rejects_bad_json():
    request = RequestFactory().post(
        '/api/proxy-config/',
        data='not-json',
        content_type='application/json',
    )

    response = views.api_proxy_config(request)

    assert response.status_code == 400


def test_api_sources_handles_exception(monkeypatch):
    request = RequestFactory().get('/api/sources/')
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: (_ for _ in ()).throw(RuntimeError('boom')))

    response = views.api_sources(request)

    assert response.status_code == 500


def test_api_source_capabilities_handles_exception(monkeypatch):
    request = RequestFactory().get('/api/sources/okx/capabilities/')

    class BrokenManager:
        def get_plugin(self, name):
            return FakePlugin()

    monkeypatch.setattr(views, 'get_plugin_manager', lambda: BrokenManager())
    monkeypatch.setattr(views.DocumentationGenerator, 'generate_plugin_doc', staticmethod(lambda p: (_ for _ in ()).throw(RuntimeError('doc fail'))))

    response = views.api_source_capabilities(request, 'okx')

    assert response.status_code == 500


def test_api_source_documentation_handles_exception(monkeypatch):
    request = RequestFactory().get('/api/documentation/sources/')
    monkeypatch.setattr(views, 'get_plugin_manager', lambda: (_ for _ in ()).throw(RuntimeError('doc fail')))

    response = views.api_source_documentation(request)

    assert response.status_code == 500


def test_api_positions_rejects_unsupported_source():
    request = RequestFactory().get('/api/positions/', {'source': 'binance'})

    response = views.api_positions(request)

    assert response.status_code == 400
    assert '暂不支持' in _json(response)['error']


def test_api_positions_handles_timeout(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(requests.exceptions.Timeout()))

    response = views.api_positions(request)

    assert response.status_code == 408
    assert _json(response)['error'] == 'OKX API 请求超时'


def test_api_positions_returns_filtered_positions(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                'code': '0',
                'data': [
                    {
                        'instId': 'BTC-USDT-SWAP',
                        'pos': '2',
                        'notionalUsd': '200',
                        'markPx': '100',
                        'lever': '10',
                        'mgnMode': 'cross',
                        'posSide': 'long',
                        'availPos': '1',
                        'frozenQty': '0.5',
                        'upl': '12',
                        'uplRatio': '0.1',
                        'uTime': '123456',
                    },
                    {
                        'instId': 'ETH-USDT-SWAP',
                        'pos': '0',
                    },
                ],
            }

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: FakeResponse())

    response = views.api_positions(request)

    assert response.status_code == 200
    payload = _json(response)
    assert payload['data']['total'] == 1
    assert payload['data']['positions'][0]['symbol'] == 'BTC-USDT-SWAP'


def test_api_positions_handles_non_200_response(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})

    class FakeResponse:
        status_code = 503

        @staticmethod
        def json():
            return {}

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: FakeResponse())

    response = views.api_positions(request)

    assert response.status_code == 503
    assert 'OKX API 返回 503' in _json(response)['error']


def test_api_positions_handles_okx_business_error(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {'code': '1', 'msg': 'bad request'}

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: FakeResponse())

    response = views.api_positions(request)

    assert response.status_code == 400
    assert _json(response)['error'] == 'bad request'


def test_api_positions_handles_request_exception(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(requests.exceptions.RequestException('network error')))

    response = views.api_positions(request)

    assert response.status_code == 500
    assert '网络错误' in _json(response)['error']


def test_api_positions_handles_unexpected_exception(monkeypatch):
    request = RequestFactory().get('/api/positions/', {'source': 'okx'})

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            raise RuntimeError('bad payload')

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: FakeResponse())

    response = views.api_positions(request)

    assert response.status_code == 500
    assert _json(response)['error'] == 'bad payload'