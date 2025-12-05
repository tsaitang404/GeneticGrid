from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """应用启动时初始化插件系统"""
        try:
            from .plugin_init import initialize_plugins
            initialize_plugins()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"插件系统初始化失败: {e}")
