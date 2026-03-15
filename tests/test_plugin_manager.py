"""Plugin manager unit tests."""

import os
import sys
from datetime import datetime
from types import SimpleNamespace

import django  # type: ignore
import pytest  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.base import Capability, DataSourceMetadata, MarketDataSourcePlugin, PluginError, SourceType
from core.plugins import manager as plugin_manager_module


class DummyPlugin(MarketDataSourcePlugin):
    def __init__(self, name='dummy', display_name='Dummy Plugin'):
        self._name = name
        self._display_name = display_name
        super().__init__()

    def _get_metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            name=self._name,
            display_name=self._display_name,
            description='Test plugin',
            source_type=SourceType.EXCHANGE,
            plugin_version='test',
            last_updated=datetime(2026, 3, 16, 0, 0, 0),
        )

    def _get_capability(self) -> Capability:
        return Capability(supports_ticker=True, supports_candlesticks=True, candlestick_granularities=['1m'])

    def _get_candlesticks_impl(self, symbol: str, bar: str, limit: int = 100, before: int = None):
        return []

    def _get_ticker_impl(self, symbol: str):
        return None


class BrokenPlugin(DummyPlugin):
    def __init__(self):
        raise RuntimeError('broken init')


@pytest.fixture(autouse=True)
def _isolate_plugin_manager_singletons():
    original_instance = plugin_manager_module.PluginManager._instance
    original_initialized = plugin_manager_module.PluginManager._initialized
    original_global_manager = plugin_manager_module._plugin_manager

    plugin_manager_module.PluginManager._instance = None
    plugin_manager_module.PluginManager._initialized = False
    plugin_manager_module._plugin_manager = None

    yield

    plugin_manager_module.PluginManager._instance = original_instance
    plugin_manager_module.PluginManager._initialized = original_initialized
    plugin_manager_module._plugin_manager = original_global_manager


def test_plugin_manager_singleton_and_global_accessor():
    first = plugin_manager_module.PluginManager()
    second = plugin_manager_module.PluginManager()
    global_manager = plugin_manager_module.get_plugin_manager()

    assert first is second
    assert global_manager is first


def test_register_get_unregister_and_metadata():
    manager = plugin_manager_module.PluginManager()
    plugin = DummyPlugin(name='okx', display_name='OKX')

    manager.register_plugin(plugin)

    assert manager.is_plugin_available('okx') is True
    assert manager.get_plugin('okx') is plugin
    assert manager.get_plugin_capability('okx').supports_ticker is True
    assert manager.get_all_metadata()['okx'].display_name == 'OKX'
    assert manager.list_plugin_names() == ['okx']

    manager.unregister_plugin('okx')

    assert manager.get_plugin('okx') is None


def test_register_plugin_rejects_invalid_instance():
    manager = plugin_manager_module.PluginManager()

    with pytest.raises(PluginError, match='插件必须继承'):
        manager.register_plugin(object())


def test_register_plugin_class_supports_lazy_loading():
    manager = plugin_manager_module.PluginManager()

    manager.register_plugin_class(DummyPlugin, auto_instantiate=False)

    assert manager.is_plugin_available('dummy') is True
    assert manager._plugins['dummy'] is None

    plugin = manager.get_plugin('dummy')

    assert isinstance(plugin, DummyPlugin)
    assert manager._plugins['dummy'] is plugin


def test_register_plugin_class_rejects_invalid_class():
    manager = plugin_manager_module.PluginManager()

    with pytest.raises(PluginError, match='插件类必须继承'):
        manager.register_plugin_class(str)


def test_load_plugins_from_directory_registers_valid_classes(monkeypatch):
    manager = plugin_manager_module.PluginManager()
    fake_module = SimpleNamespace(DummyPlugin=DummyPlugin, Other=object)

    monkeypatch.setattr(plugin_manager_module, 'import_module', lambda module_path: fake_module)

    manager.load_plugins_from_directory('core.plugins.sources')

    assert 'dummy' in manager.list_plugin_names()


def test_load_plugins_from_directory_handles_import_error(monkeypatch):
    manager = plugin_manager_module.PluginManager()

    def _raise_import_error(module_path):
        raise ImportError('no module')

    monkeypatch.setattr(plugin_manager_module, 'import_module', _raise_import_error)

    manager.load_plugins_from_directory('missing.module')

    assert manager.list_plugin_names() == []


def test_auto_discover_plugins_covers_success_and_failures(monkeypatch):
    manager = plugin_manager_module.PluginManager()

    plugin_files = [
        '/tmp/good_plugin.py',
        '/tmp/noclass_plugin.py',
        '/tmp/broken_plugin.py',
        '/tmp/importfail_plugin.py',
    ]
    modules = {
        'core.plugins.sources.good_plugin': SimpleNamespace(GoodPlugin=DummyPlugin),
        'core.plugins.sources.noclass_plugin': SimpleNamespace(NotAPlugin=object),
        'core.plugins.sources.broken_plugin': SimpleNamespace(BrokenPlugin=BrokenPlugin),
    }

    monkeypatch.setattr(plugin_manager_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr(plugin_manager_module.glob, 'glob', lambda pattern: plugin_files)

    def _import(module_name):
        if module_name == 'core.plugins.sources.importfail_plugin':
            raise RuntimeError('cannot import')
        return modules[module_name]

    monkeypatch.setattr(plugin_manager_module, 'import_module', _import)

    result = manager.auto_discover_plugins('/tmp')

    assert result['success'] == 1
    assert result['failed'] == 3
    assert 'dummy' in manager.list_plugin_names()
    assert manager.get_failed_plugins()['noclass_plugin'] == '未找到插件类'
    assert '导入失败' in manager.get_failed_plugins()['importfail_plugin']
    assert '实例化失败' in manager.get_failed_plugins()['broken_plugin']


def test_auto_discover_plugins_handles_missing_directory():
    manager = plugin_manager_module.PluginManager()

    result = manager.auto_discover_plugins('/missing')

    assert result == {'success': 0, 'failed': 0, 'errors': {}}


def test_get_all_plugins_skips_unavailable_and_reset_clears_state():
    manager = plugin_manager_module.PluginManager()
    manager.register_plugin(DummyPlugin(name='okx'))
    manager._plugins['lazy'] = None

    assert list(manager.get_all_plugins().keys()) == ['okx']

    manager.reset()

    assert manager.list_plugin_names() == []
    assert manager.get_failed_plugins() == {}
