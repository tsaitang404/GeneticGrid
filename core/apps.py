from django.apps import AppConfig
import os
import sys


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    _plugins_ready = False
    
    def ready(self):
        """应用启动时初始化插件系统"""
        if self.__class__._plugins_ready:
            return

        # runserver 的自动重载会启动父进程与子进程；仅在子进程中执行一次。
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .plugin_init import initialize_plugins
            initialize_plugins()
            self.__class__._plugins_ready = True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"插件系统初始化失败: {e}")
