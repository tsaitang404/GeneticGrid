# -*- coding: utf-8 -*-
"""
插件系统初始化

在 Django 应用启动时自动加载所有插件。
"""

from .plugins.manager import get_plugin_manager
from .plugins.sources import (
    OKXMarketPlugin,
    BinanceMarketPlugin,
    CoinbaseMarketPlugin,
    CoinGeckoMarketPlugin,
    TradingViewMarketPlugin,
)
import logging

logger = logging.getLogger(__name__)


def initialize_plugins():
    """初始化并注册所有数据源插件"""
    manager = get_plugin_manager()
    
    # 注册所有内置插件
    plugins_to_register = [
        OKXMarketPlugin,
        BinanceMarketPlugin,
        CoinbaseMarketPlugin,
        CoinGeckoMarketPlugin,
        TradingViewMarketPlugin,
    ]
    
    for plugin_class in plugins_to_register:
        try:
            plugin_instance = plugin_class()
            manager.register_plugin(plugin_instance)
            logger.info(f"✅ 插件已加载: {plugin_instance.display_name}")
        except Exception as e:
            logger.error(f"❌ 加载插件 {plugin_class.__name__} 失败: {e}")
    
    logger.info(f"✅ 插件系统初始化完成，共加载 {len(manager.list_plugin_names())} 个插件")
    logger.info(f"   可用插件: {', '.join(manager.list_plugin_names())}")


# 在模块导入时执行初始化
try:
    initialize_plugins()
except Exception as e:
    logger.error(f"插件系统初始化失败: {e}")
