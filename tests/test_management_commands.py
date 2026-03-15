"""Management command tests."""

import io
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.management.commands import cache_manager, generate_plugin_docs, proxy_status


class FakeStyle:
    def ERROR(self, text):
        return text

    def SUCCESS(self, text):
        return text

    def WARNING(self, text):
        return text

    def HTTP_INFO(self, text):
        return text


class FakePlugin:
    display_name = 'OKX'


class FakeManager:
    def __init__(self, plugins=None):
        self.plugins = plugins or {}
        self.cleared = []

    def get_cache_stats(self):
        return {'candles': 2, 'ticker': 1}

    def clear_all(self, pattern=None):
        self.cleared.append(pattern)
        return 3

    def get_all_plugins(self):
        return self.plugins

    def get_plugin(self, name):
        return self.plugins.get(name)


def test_cache_manager_reports_redis_disabled(monkeypatch):
    command = cache_manager.Command()
    command.stdout = io.StringIO()
    monkeypatch.setattr(cache_manager, 'redis_cache_enabled', lambda: False)

    command.handle(action='stats', type=None, pattern=None)

    assert 'Redis缓存未启用' in command.stdout.getvalue()


def test_cache_manager_show_stats_and_clear(monkeypatch):
    manager = FakeManager()
    command = cache_manager.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()
    monkeypatch.setattr(cache_manager, 'redis_cache_enabled', lambda: True)
    monkeypatch.setattr(cache_manager, 'get_cache_manager', lambda: manager)

    command.handle(action='stats', type=None, pattern=None)
    command.handle(action='clear', type='ticker', pattern=None)

    output = command.stdout.getvalue()
    assert '缓存统计信息' in output
    assert 'candles' in output
    assert manager.cleared[-1] == 'ticker:*'


def test_cache_manager_handles_invalid_type_and_clear_all(monkeypatch):
    manager = FakeManager()
    command = cache_manager.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()

    command.clear_cache(manager, 'unknown', None)
    assert '未知的数据类型' in command.stdout.getvalue()

    monkeypatch.setattr('builtins.input', lambda prompt: 'no')
    command.clear_all(manager)
    assert manager.cleared == []

    monkeypatch.setattr('builtins.input', lambda prompt: 'yes')
    command.clear_all(manager)
    assert manager.cleared == [None]


def test_generate_plugin_docs_handles_empty_and_missing_source(monkeypatch, tmp_path):
    command = generate_plugin_docs.Command()
    command.stdout = io.StringIO()
    monkeypatch.setattr(generate_plugin_docs, 'color_style', lambda: FakeStyle())

    monkeypatch.setattr(generate_plugin_docs, 'get_plugin_manager', lambda: FakeManager())
    command.handle(format='markdown', output=None, source=None)
    assert '未找到任何已注册的插件' in command.stdout.getvalue()

    manager = FakeManager({'okx': FakePlugin()})
    command.stdout = io.StringIO()
    monkeypatch.setattr(generate_plugin_docs, 'get_plugin_manager', lambda: manager)
    command.handle(format='markdown', output=None, source='missing')
    assert "数据源 'missing' 不存在" in command.stdout.getvalue()


def test_generate_plugin_docs_writes_markdown_and_json(monkeypatch, tmp_path):
    manager = FakeManager({'okx': FakePlugin()})
    command = generate_plugin_docs.Command()
    command.stdout = io.StringIO()
    monkeypatch.setattr(generate_plugin_docs, 'color_style', lambda: FakeStyle())
    monkeypatch.setattr(generate_plugin_docs, 'get_plugin_manager', lambda: manager)
    monkeypatch.setattr(generate_plugin_docs.DocumentationGenerator, 'generate_all_plugins_doc', staticmethod(lambda m: '# docs'))
    monkeypatch.setattr(generate_plugin_docs.DocumentationGenerator, 'generate_capabilities_json', staticmethod(lambda m: {'okx': {'name': 'okx'}}))

    output = tmp_path / 'plugins'
    command.handle(format='both', output=str(output), source=None)

    assert Path(f'{output}.md').read_text(encoding='utf-8') == '# docs'
    assert '"okx"' in Path(f'{output}.json').read_text(encoding='utf-8')


def test_proxy_status_command_and_test_proxy(monkeypatch):
    command = proxy_status.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()

    printed = []
    monkeypatch.setattr(proxy_status, 'print_proxy_status', lambda: printed.append('status'))
    monkeypatch.setattr(proxy_status.Command, 'test_proxy', lambda self: printed.append('test'))

    command.handle(test=True)

    assert printed == ['status', 'test']


def test_proxy_status_test_proxy_without_http_proxy(monkeypatch):
    command = proxy_status.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()
    monkeypatch.setitem(sys.modules, 'httpx', SimpleNamespace(Client=object))
    monkeypatch.setattr('core.proxy_config.get_proxy_url', lambda kind: None)

    command.test_proxy()

    assert 'HTTP 代理不可用' in command.stdout.getvalue()


def test_proxy_status_test_proxy_success(monkeypatch):
    command = proxy_status.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()

    class FakeResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self._payload = payload or {}

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, proxy, timeout, verify):
            self.proxy = proxy

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def get(self, url):
            if url.endswith('/public/time'):
                return FakeResponse(200, {'data': [{'ts': '123'}]})
            return FakeResponse(200)

    monkeypatch.setitem(sys.modules, 'httpx', SimpleNamespace(Client=FakeClient))
    monkeypatch.setattr('core.proxy_config.get_proxy_url', lambda kind: 'http://proxy')

    command.test_proxy()

    assert '所有代理功能测试通过' in command.stdout.getvalue()


def test_proxy_status_test_proxy_handles_runtime_error(monkeypatch):
    command = proxy_status.Command()
    command.stdout = io.StringIO()
    command.style = FakeStyle()

    class FakeClient:
        def __init__(self, proxy, timeout, verify):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def get(self, url):
            raise RuntimeError('network broken')

    monkeypatch.setitem(sys.modules, 'httpx', SimpleNamespace(Client=FakeClient))
    monkeypatch.setattr('core.proxy_config.get_proxy_url', lambda kind: 'http://proxy')

    command.test_proxy()

    assert '代理功能测试失败' in command.stdout.getvalue()
