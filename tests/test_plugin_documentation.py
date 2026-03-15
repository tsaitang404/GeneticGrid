"""Plugin documentation generator tests."""

import os
import sys
from datetime import datetime

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.base import Capability, DataSourceMetadata, SourceType
from core.plugins.documentation import DocumentationGenerator


class FakePlugin:
    def __init__(self, name='okx', display_name='OKX', active=True):
        self.name = name
        self.display_name = display_name
        self._metadata = DataSourceMetadata(
            name=name,
            display_name=display_name,
            description='A test exchange plugin.',
            source_type=SourceType.EXCHANGE,
            website='https://example.com',
            api_base_url='https://api.example.com',
            plugin_version='1.2.3',
            author='tester',
            last_updated=datetime(2026, 3, 16, 12, 0, 0),
            is_active=active,
            is_experimental=True,
        )
        self._capability = Capability(
            supports_candlesticks=True,
            candlestick_granularities=['1m', '1h'],
            candlestick_limit=500,
            candlestick_max_history_days=30,
            supports_ticker=True,
            ticker_update_frequency=3,
            supported_symbols=['BTCUSDT', 'ETHUSDT'],
            symbol_format='BASEQUOTE',
            requires_api_key=True,
            requires_authentication=True,
            has_rate_limit=True,
            rate_limit_per_minute=120,
            supports_real_time=True,
            supports_websocket=True,
            supports_funding_rate=True,
            funding_rate_interval_hours=8,
            funding_rate_quote_currency='USDT',
            supports_contract_basis=True,
            contract_basis_types=['perpetual'],
            contract_basis_tenors=['current_quarter'],
        )

    def get_metadata(self):
        return self._metadata

    def get_capability(self):
        return self._capability


class FakeManager:
    def __init__(self, plugins):
        self._plugins = plugins

    def get_all_plugins(self):
        return self._plugins


def test_generate_plugin_doc_includes_main_sections():
    plugin = FakePlugin()

    doc = DocumentationGenerator.generate_plugin_doc(plugin)

    assert '# OKX' in doc
    assert '## 基本信息' in doc
    assert '**标签**: 🧪 实验性' in doc
    assert '## K线数据' in doc
    assert '## 行情数据' in doc
    assert '## 资金费率' in doc
    assert '## 合约基差' in doc
    assert '## 支持的交易对' in doc
    assert '## 高级特性' in doc
    assert '## API 使用示例' in doc
    assert '## 维护信息' in doc


def test_generate_plugin_doc_handles_unrestricted_symbols_and_no_requirements():
    plugin = FakePlugin(name='free', display_name='Free', active=False)
    plugin._metadata.is_experimental = False
    plugin._metadata.website = None
    plugin._metadata.api_base_url = None
    plugin._metadata.author = None
    plugin._metadata.last_updated = None
    plugin._capability.supported_symbols = []
    plugin._capability.requires_api_key = False
    plugin._capability.requires_authentication = False
    plugin._capability.has_rate_limit = False
    plugin._capability.supports_real_time = False
    plugin._capability.supports_websocket = False

    doc = DocumentationGenerator.generate_plugin_doc(plugin)

    assert '**状态**: ❌ 已禁用' in doc
    assert '## 资源' not in doc
    assert '所有交易对（无特定限制）' in doc
    assert '- ✅ 无特殊要求（公开数据）' in doc
    assert '## 高级特性' not in doc


def test_generate_all_plugins_doc_and_comparison_table():
    manager = FakeManager({'okx': FakePlugin(), 'free': FakePlugin(name='free', display_name='Free', active=False)})

    doc = DocumentationGenerator.generate_all_plugins_doc(manager)

    assert '# 数据源插件文档' in doc
    assert '## 目录' in doc
    assert '- [OKX](#okx)' in doc
    assert '## 能力对比表' in doc
    assert '| 插件 | K线 | Ticker | 粒度数 | 速率限制 | 状态 |' in doc
    assert '| OKX | ✅ | ✅ | 2 | 120/min | ✅ |' in doc
    assert '| Free | ✅ | ✅ | 2 | 120/min | ❌ |' in doc


def test_generate_comparison_table_handles_empty_manager():
    manager = FakeManager({})

    table = DocumentationGenerator._generate_comparison_table(manager)

    assert table == '*没有已注册的插件*'


def test_generate_features_section_and_capabilities_json():
    plugin = FakePlugin()
    manager = FakeManager({'okx': plugin})

    features = DocumentationGenerator._generate_features_section(plugin.get_capability())
    payload = DocumentationGenerator.generate_capabilities_json(manager)

    assert '- ✅ K线数据 (OHLCV)' in features
    assert '- ✅ 行情数据 (Ticker)' in features
    assert '- ✅ 资金费率 (Funding Rate)' in features
    assert '- ✅ 合约基差 (Basis)' in features
    assert payload['plugins']['okx']['metadata']['display_name'] == 'OKX'
    assert payload['plugins']['okx']['capability']['supports_websocket'] is True
    assert 'generated_at' in payload