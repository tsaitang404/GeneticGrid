# -*- coding: utf-8 -*-
"""
插件系统初始化

在 Django 应用启动时自动扫描并加载所有插件。
"""

from typing import Optional

try:  # pragma: no cover - 运行环境均应安装 Django，此处为防御性降级
    from django.conf import settings  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from types import SimpleNamespace

    settings = SimpleNamespace(  # type: ignore
        REALTIME_INGESTION_AUTO_START=False,
        REALTIME_INGESTION_STREAMS=[],
    )

from .plugins.manager import get_plugin_manager
from .services import MarketAPIError, RealtimeIngestionService
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

    _auto_start_realtime_streams()


# 在模块导入时执行初始化
try:
    initialize_plugins()
except Exception as e:
    logger.error(f"插件系统初始化失败: {e}")
    # 不抛出异常，允许系统继续运行


def _auto_start_realtime_streams() -> None:
    """根据 Django 配置自动启动实时采集服务"""

    auto_start = getattr(settings, "REALTIME_INGESTION_AUTO_START", False)
    streams = getattr(settings, "REALTIME_INGESTION_STREAMS", [])

    if not auto_start or not streams:
        return

    service = RealtimeIngestionService.get_default()

    for entry in streams:
        stream_cfg = _normalize_stream_entry(entry)
        if not stream_cfg:
            logger.warning("忽略无效的实时采集配置: %s", entry)
            continue

        try:
            service.start_stream(**stream_cfg)
        except MarketAPIError as exc:
            logger.warning(
                "实时采集流启动失败 (%s/%s/%s): %s",
                stream_cfg.get("source"),
                stream_cfg.get("symbol"),
                stream_cfg.get("bar"),
                exc,
            )
        except Exception as exc:  # pragma: no cover - 防御性日志
            logger.error(
                "实时采集流发生未知错误 (%s/%s/%s): %s",
                stream_cfg.get("source"),
                stream_cfg.get("symbol"),
                stream_cfg.get("bar"),
                exc,
                exc_info=True,
            )


def _normalize_stream_entry(entry) -> Optional[dict]:
    """解析 settings 中的实时采集配置"""

    if isinstance(entry, str):
        parts = [p.strip() for p in entry.split(":") if p.strip()]
        if not parts:
            return None
        data = {
            "source": parts[0].lower(),
            "symbol": parts[1] if len(parts) > 1 else "BTCUSDT",
            "bar": parts[2] if len(parts) > 2 else "1s",
        }
        if len(parts) > 3:
            data["poll_interval"] = float(parts[3])
        if len(parts) > 4:
            data["batch_size"] = int(parts[4])
        return data

    if isinstance(entry, dict):
        source = entry.get("source")
        symbol = entry.get("symbol")
        if not source or not symbol:
            return None
        data = {
            "source": str(source).lower(),
            "symbol": str(symbol).upper().replace("-", "").replace("/", ""),
            "bar": str(entry.get("bar", "1s")).lower(),
            "poll_interval": float(entry.get("poll_interval", 1.0)),
            "batch_size": int(entry.get("batch_size", 300)),
        }
        return data

    return None
