# -*- coding: utf-8 -*-
"""
插件系统初始化

在 Django 应用启动时自动扫描并加载所有插件。
"""

from .plugins.manager import get_plugin_manager
import logging

logger = logging.getLogger(__name__)


def initialize_plugins():
    """初始化并注册所有数据源插件（自动扫描）"""
    manager = get_plugin_manager()
    
    # 自动扫描 sources 目录下的所有插件
    result = manager.auto_discover_plugins()
    
    success = result['success']
    failed = result['failed']
    
    if success > 0:
        logger.info(f"✅ 插件系统初始化完成，成功加载 {success} 个插件")
        logger.info(f"   可用插件: {', '.join(manager.list_plugin_names())}")
    
    if failed > 0:
        logger.warning(f"⚠️  {failed} 个插件加载失败（不影响系统运行）")
        for plugin_name, error in result['errors'].items():
            logger.warning(f"   - {plugin_name}: {error}")
    
    if success == 0 and failed == 0:
        logger.warning("⚠️  未发现任何插件文件")


# 在模块导入时执行初始化
try:
    initialize_plugins()
except Exception as e:
    logger.error(f"插件系统初始化失败: {e}")
    # 不抛出异常，允许系统继续运行
