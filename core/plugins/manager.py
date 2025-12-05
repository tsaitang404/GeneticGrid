# -*- coding: utf-8 -*-
"""
插件管理系统

负责发现、加载、注册和管理数据源插件。
"""

from typing import Dict, List, Optional, Type
from importlib import import_module
import logging

from .base import MarketDataSourcePlugin, PluginError, DataSourceMetadata

logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化管理器"""
        if not self._initialized:
            self._plugins: Dict[str, MarketDataSourcePlugin] = {}
            self._plugin_classes: Dict[str, Type[MarketDataSourcePlugin]] = {}
            self._initialized = True
    
    def register_plugin(self, plugin_instance: MarketDataSourcePlugin) -> None:
        """
        注册一个插件实例
        
        Args:
            plugin_instance: 插件实例
        
        Raises:
            PluginError: 如果插件名称已存在或插件无效
        """
        if not isinstance(plugin_instance, MarketDataSourcePlugin):
            raise PluginError(
                f"插件必须继承 MarketDataSourcePlugin，得到 {type(plugin_instance)}"
            )
        
        plugin_name = plugin_instance.name
        
        if plugin_name in self._plugins:
            logger.warning(f"插件 {plugin_name} 已注册，将覆盖")
        
        self._plugins[plugin_name] = plugin_instance
        logger.info(f"成功注册插件: {plugin_name} ({plugin_instance.display_name})")
    
    def register_plugin_class(
        self,
        plugin_class: Type[MarketDataSourcePlugin],
        auto_instantiate: bool = True,
    ) -> None:
        """
        注册一个插件类
        
        Args:
            plugin_class: 插件类
            auto_instantiate: 是否自动实例化
        """
        if not issubclass(plugin_class, MarketDataSourcePlugin):
            raise PluginError(
                f"插件类必须继承 MarketDataSourcePlugin，得到 {plugin_class}"
            )
        
        if auto_instantiate:
            instance = plugin_class()
            self.register_plugin(instance)
        else:
            # 为了获取名称，需要临时实例化一次
            temp_instance = plugin_class()
            plugin_name = temp_instance.name
            self._plugin_classes[plugin_name] = plugin_class
            self._plugins[plugin_name] = None  # 延迟加载
            logger.info(f"注册插件类: {plugin_name}")
    
    def load_plugins_from_directory(self, module_path: str) -> None:
        """
        从指定目录加载所有插件
        
        Args:
            module_path: 模块路径，如 "core.plugins.sources"
        """
        try:
            module = import_module(module_path)
            # 动态发现并加载所有 MarketDataSourcePlugin 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) 
                    and issubclass(attr, MarketDataSourcePlugin)
                    and attr is not MarketDataSourcePlugin
                ):
                    try:
                        self.register_plugin_class(attr)
                    except Exception as e:
                        logger.error(f"加载插件类 {attr_name} 失败: {e}")
        except ImportError as e:
            logger.error(f"无法导入模块 {module_path}: {e}")
    
    def get_plugin(self, name: str) -> Optional[MarketDataSourcePlugin]:
        """
        获取指定名称的插件
        
        Args:
            name: 插件名称
        
        Returns:
            插件实例，如果不存在则返回 None
        """
        if name not in self._plugins:
            return None
        
        plugin = self._plugins[name]
        
        # 处理延迟加载
        if plugin is None and name in self._plugin_classes:
            plugin = self._plugin_classes[name]()
            self._plugins[name] = plugin
        
        return plugin
    
    def get_all_plugins(self) -> Dict[str, MarketDataSourcePlugin]:
        """
        获取所有已注册的插件
        
        Returns:
            插件名称到实例的映射
        """
        result = {}
        for name in list(self._plugins.keys()):
            plugin = self.get_plugin(name)
            if plugin:
                result[name] = plugin
        return result
    
    def get_all_metadata(self) -> Dict[str, DataSourceMetadata]:
        """
        获取所有插件的元数据
        
        Returns:
            插件名称到元数据的映射
        """
        result = {}
        for plugin in self.get_all_plugins().values():
            result[plugin.name] = plugin.get_metadata()
        return result
    
    def unregister_plugin(self, name: str) -> None:
        """
        注销插件
        
        Args:
            name: 插件名称
        """
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"已注销插件: {name}")
        
        if name in self._plugin_classes:
            del self._plugin_classes[name]
    
    def list_plugin_names(self) -> List[str]:
        """获取所有已注册插件的名称"""
        return list(self._plugins.keys())
    
    def is_plugin_available(self, name: str) -> bool:
        """检查插件是否可用"""
        return name in self._plugins
    
    def get_plugin_capability(self, name: str):
        """获取插件的能力描述"""
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.get_capability()
        return None
    
    def reset(self) -> None:
        """重置管理器（用于测试）"""
        self._plugins.clear()
        self._plugin_classes.clear()
        logger.info("插件管理器已重置")


# 全局插件管理器实例
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
