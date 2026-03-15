"""Protocol converter unit tests."""

import os
import sys

import django  # type: ignore
import pytest  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.protocol import ProtocolConverter


def test_parse_symbol_supports_multiple_formats():
    assert ProtocolConverter.parse_symbol('BTCUSDT') == {'base': 'BTC', 'quote': 'USDT'}
    assert ProtocolConverter.parse_symbol('BTC-USDT') == {'base': 'BTC', 'quote': 'USDT'}
    assert ProtocolConverter.parse_symbol('btc/usd') == {'base': 'BTC', 'quote': 'USD'}


def test_parse_symbol_uses_fallback_for_unknown_quote():
    assert ProtocolConverter.parse_symbol('ABCDE1234') == {'base': 'ABCDE', 'quote': '1234'}


def test_parse_symbol_rejects_too_short_symbol():
    with pytest.raises(ValueError):
        ProtocolConverter.parse_symbol('BTC')


def test_to_source_symbol_handles_special_sources():
    assert ProtocolConverter.to_source_symbol('BTCUSDT', 'okx') == 'BTC-USDT'
    assert ProtocolConverter.to_source_symbol('BTCUSDT', 'kraken') == 'XBTUSDT'
    assert ProtocolConverter.to_source_symbol('BTCUSDT', 'coingecko') == 'bitcoin'


def test_granularity_and_timestamp_conversion():
    assert ProtocolConverter.to_source_granularity('1h', 'okx') == '1H'
    assert ProtocolConverter.to_source_granularity('1h', 'unknown') == '1h'
    assert ProtocolConverter.to_source_timestamp(2000, 'coinbase') == 2
    assert ProtocolConverter.to_source_timestamp(2000, 'okx') == 2000
    assert ProtocolConverter.to_source_timestamp(None, 'okx') is None
    assert ProtocolConverter.from_source_timestamp(2, 'coinbase') == 2000
    assert ProtocolConverter.from_source_timestamp(2, 'okx') == 2


def test_normalize_request_params_and_response_data():
    normalized = ProtocolConverter.normalize_request_params(
        symbol='BTCUSDT',
        bar='1h',
        source='coinbase',
        before=2000,
        after=1000,
        limit=50,
    )

    assert normalized == {
        'symbol': 'BTC-USDT',
        'bar': '3600',
        'before': 2,
        'after': 1,
        'limit': 50,
        'source': 'coinbase',
        'original_symbol': 'BTCUSDT',
    }

    assert ProtocolConverter.normalize_response_data({'time': 2, 'close': 1.1}, 'coinbase') == {
        'time': 2000,
        'close': 1.1,
    }
    assert ProtocolConverter.normalize_response_data([
        {'time': 1, 'close': 1.0},
        {'time': 2, 'close': 2.0},
    ], 'coinbase') == [
        {'time': 1000, 'close': 1.0},
        {'time': 2000, 'close': 2.0},
    ]


def test_get_supported_granularities_and_validate_request():
    granularities = ProtocolConverter.get_supported_granularities('okx')

    assert '1h' in granularities
    assert ProtocolConverter.validate_request('BTCUSDT', '1h', 'okx') == (True, None)
    assert ProtocolConverter.validate_request('BTCUSDT', '1h', 'unknown') == (
        False,
        '不支持的数据源: unknown',
    )

    valid, error = ProtocolConverter.validate_request('BTCUSDT', '7h', 'okx')
    assert valid is False
    assert '不支持粒度' in error
