"""Django app and entrypoint tests."""

import importlib
import os
import sys

import django  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()


def test_core_app_ready_handles_init_error(monkeypatch):
    from core.apps import CoreConfig

    monkeypatch.setattr('core.apps.CoreConfig.name', 'core', raising=False)
    cfg = CoreConfig('core', importlib.import_module('core'))
    monkeypatch.setattr('core.plugin_init.initialize_plugins', lambda: (_ for _ in ()).throw(RuntimeError('boom')))

    cfg.ready()


def test_asgi_and_wsgi_modules_initialize_application(monkeypatch):
    monkeypatch.setattr('django.core.asgi.get_asgi_application', lambda: 'asgi-app')
    monkeypatch.setattr('django.core.wsgi.get_wsgi_application', lambda: 'wsgi-app')

    asgi_module = importlib.reload(importlib.import_module('geneticgrid.asgi'))
    wsgi_module = importlib.reload(importlib.import_module('geneticgrid.wsgi'))

    assert asgi_module.application == 'asgi-app'
    assert wsgi_module.application == 'wsgi-app'