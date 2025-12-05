# -*- coding: utf-8 -*-
"""
数据源插件系统

提供标准化的数据源接口和管理框架，允许轻松扩展新的数据源。
"""

from .base import (
    MarketDataSourcePlugin,
    Granularity,
    Capability,
    DataSourceMetadata,
    SourceType,
)
from .manager import PluginManager
from .documentation import DocumentationGenerator

__all__ = [
    'MarketDataSourcePlugin',
    'Granularity',
    'Capability',
    'DataSourceMetadata',
    'SourceType',
    'PluginManager',
    'DocumentationGenerator',
]
