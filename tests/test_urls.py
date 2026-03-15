"""URL configuration tests."""

import os
import sys

import django  # type: ignore
from django.urls import resolve, reverse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core import views


def test_core_and_project_urls_resolve_expected_views():
    assert reverse('index') == '/'
    assert reverse('api_ticker') == '/api/ticker/'
    assert resolve('/').func == views.index
    assert resolve('/market/').func == views.market_view
    assert resolve('/api/sources/').func == views.api_sources
