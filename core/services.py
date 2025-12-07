# -*- coding: utf-8 -*-
"""服务层入口

- `RealtimeIngestionService`: 通过插件的 websocket 缓冲持续采集并持久化到数据库。
- `get_market_service`: 遗留接口，保留以兼容旧代码（仍然抛出 DeprecationWarning）。
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .plugins.base import CandleData, MarketDataSourcePlugin
from .plugins.manager import get_plugin_manager

logger = logging.getLogger(__name__)


class MarketAPIError(Exception):
    """行情 API 调用异常"""


@dataclass
class RealtimeIngestionConfig:
    """实时采集配置"""

    source: str
    symbol: str
    mode: str = "spot"
    bar: str = "1s"
    poll_interval: float = 1.0
    batch_size: int = 300

    def __post_init__(self) -> None:
        self.source = self.source.lower()
        self.symbol = self._normalize_symbol(self.symbol)
        self.mode = (self.mode or "spot").lower()
        self.bar = self.bar.lower()

        if self.poll_interval <= 0:
            raise ValueError("poll_interval 必须大于 0")
        if self.batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        std = symbol.upper().replace('-', '').replace('/', '')
        if not std:
            raise ValueError("symbol 不能为空")
        return std


@dataclass
class _StreamContext:
    """实时采集内部上下文"""

    key: str
    config: RealtimeIngestionConfig
    plugin: MarketDataSourcePlugin
    realtime_manager: Any
    normalized_symbol: str
    normalized_bar: str
    mode: str
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None
    last_timestamp: Optional[int] = None
    last_signature: Optional[Tuple[float, float, float, float, float]] = None
    consecutive_failures: int = 0
    total_persisted: int = 0


class RealtimeIngestionService:
    """基于插件 websocket 的持续采集服务"""

    _default_instance: Optional["RealtimeIngestionService"] = None
    _default_lock = threading.Lock()

    def __init__(
        self,
        plugin_manager=None,
        cache_service=None,
        logger_instance: Optional[logging.Logger] = None,
    ) -> None:
        self._plugin_manager = plugin_manager or get_plugin_manager()
        if cache_service is None:
            from .cache_service import CandlestickCacheService as _CacheService

            cache_service = _CacheService
        self._cache_service = cache_service
        self._logger = logger_instance or logger
        self._streams: Dict[str, _StreamContext] = {}
        self._lock = threading.RLock()
        self._global_stop = threading.Event()

    # ------------------------------------------------------------------
    # 单例辅助
    # ------------------------------------------------------------------
    @classmethod
    def get_default(cls) -> "RealtimeIngestionService":
        with cls._default_lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
            return cls._default_instance

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def start_stream(
        self,
        source: str,
        symbol: str,
        bar: str = "1s",
        mode: str = "spot",
        poll_interval: float = 1.0,
        batch_size: int = 300,
        autostart: bool = True,
    ) -> str:
        """启动指定数据源/交易对的实时采集线程"""

        config = RealtimeIngestionConfig(
            source=source,
            symbol=symbol,
            mode=mode,
            bar=bar,
            poll_interval=poll_interval,
            batch_size=batch_size,
        )
        key = self._make_key(config.source, config.symbol, config.bar, config.mode)

        with self._lock:
            existing = self._streams.get(key)
            if existing:
                if autostart and (existing.thread is None or not existing.thread.is_alive()):
                    existing.stop_event.clear()
                    existing.thread = self._spawn_thread(key)
                return key

            plugin = self._resolve_plugin(config.source)
            capability = plugin.get_capability()
            if not capability.supports_websocket:
                raise MarketAPIError(
                    f"数据源 {config.source} 不支持 websocket 实时采集"
                )
            if not plugin.validate_granularity(config.bar):
                raise MarketAPIError(
                    f"数据源 {config.source} 不支持粒度 {config.bar}"
                )

            realtime_manager = self._resolve_realtime_manager(plugin)
            if realtime_manager is None:
                raise MarketAPIError(
                    f"数据源 {config.source} 未提供实时流管理器"
                )

            normalized_symbol = plugin._normalize_symbol(config.symbol, config.mode)
            normalized_bar = plugin._normalize_granularity(config.bar).lower()

            cache_info = self._safe_get_cache_range(
                config.source, config.symbol, config.bar, config.mode
            )

            context = _StreamContext(
                key=key,
                config=config,
                plugin=plugin,
                realtime_manager=realtime_manager,
                normalized_symbol=normalized_symbol,
                normalized_bar=normalized_bar,
                mode=config.mode,
            )
            if cache_info:
                context.last_timestamp = cache_info.get("newest")

            self._streams[key] = context

            if autostart:
                context.thread = self._spawn_thread(key)

        self._logger.info(
            "🚀 启动实时采集: %s/%s/%s",
            config.source,
            config.symbol,
            config.bar,
        )
        return key

    def stop_stream(
        self,
        source: str,
        symbol: str,
        bar: str = "1s",
        mode: str = "spot",
        wait: bool = True,
    ) -> None:
        """停止指定采集线程"""

        key = self._make_key(source, symbol, bar, mode)
        with self._lock:
            context = self._streams.get(key)
            if not context:
                return
            context.stop_event.set()
            thread = context.thread
        if wait and thread and thread.is_alive():
            thread.join(timeout=max(1.0, context.config.poll_interval * 2))
        with self._lock:
            self._streams.pop(key, None)
        self._logger.info("🛑 停止实时采集: %s", key)

    def run_once(self, source: str, symbol: str, bar: str = "1s", mode: str = "spot") -> bool:
        """手动执行一次采集循环（主要用于测试）"""

        key = self._make_key(source, symbol, bar, mode)
        with self._lock:
            context = self._streams.get(key)
        if not context:
            raise MarketAPIError(f"未找到实时采集流: {source}/{symbol}/{bar}")
        return self._collect_once(context)

    def list_streams(self) -> List[Dict[str, Any]]:
        """列出当前所有采集流的状态"""

        with self._lock:
            result = []
            for ctx in self._streams.values():
                result.append({
                    "key": ctx.key,
                    "source": ctx.config.source,
                    "symbol": ctx.config.symbol,
                    "bar": ctx.config.bar,
                    "mode": ctx.config.mode,
                    "poll_interval": ctx.config.poll_interval,
                    "batch_size": ctx.config.batch_size,
                    "last_timestamp": ctx.last_timestamp,
                    "total_persisted": ctx.total_persisted,
                    "thread_alive": bool(ctx.thread and ctx.thread.is_alive()),
                })
            return result

    def shutdown(self, wait: bool = True) -> None:
        """停止所有采集线程"""

        self._global_stop.set()
        with self._lock:
            contexts = list(self._streams.values())
        for ctx in contexts:
            ctx.stop_event.set()
            if wait and ctx.thread and ctx.thread.is_alive():
                ctx.thread.join(timeout=max(1.0, ctx.config.poll_interval * 2))
        with self._lock:
            self._streams.clear()
        self._global_stop.clear()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _spawn_thread(self, key: str) -> threading.Thread:
        thread = threading.Thread(
            target=self._stream_loop,
            args=(key,),
            name=f"RealtimeIngestion[{key}]",
            daemon=True,
        )
        thread.start()
        return thread

    def _stream_loop(self, key: str) -> None:
        with self._lock:
            context = self._streams.get(key)
        if not context:
            return

        while not self._global_stop.is_set() and not context.stop_event.is_set():
            success = self._collect_once(context)
            wait_time = context.config.poll_interval
            if not success:
                wait_time = min(5.0, wait_time * (1 + context.consecutive_failures))
            context.stop_event.wait(wait_time)

        self._logger.info("💤 实时采集线程结束: %s", key)

    def _collect_once(self, context: _StreamContext) -> bool:
        try:
            candles = context.realtime_manager.get_latest_candles(
                context.normalized_symbol,
                context.normalized_bar,
                context.config.batch_size,
            )
        except Exception as exc:
            self._logger.warning("获取实时数据失败 (%s): %s", context.key, exc)
            context.consecutive_failures += 1
            return False

        if not candles:
            return True

        ordered = sorted(candles, key=lambda c: c.time)
        payload = self._prepare_payload(context, ordered)
        if not payload:
            return True

        try:
            self._cache_service.save_to_cache(
                source=context.config.source,
                symbol=context.config.symbol,
                bar=context.config.bar,
                candles=payload,
                mode=context.config.mode,
                max_retries=3,
            )
            context.total_persisted += len(payload)
            context.consecutive_failures = 0
            last = payload[-1]
            context.last_timestamp = last["time"]
            context.last_signature = (
                last["open"],
                last["high"],
                last["low"],
                last["close"],
                last["volume"],
            )
            return True
        except Exception as exc:
            self._logger.error(
                "实时采集写入缓存失败 (%s): %s",
                context.key,
                exc,
                exc_info=True,
            )
            context.consecutive_failures += 1
            return False

    def _prepare_payload(self, context: _StreamContext, candles: List[CandleData]) -> List[Dict[str, float]]:
        payload: List[Dict[str, float]] = []
        last_timestamp = context.last_timestamp
        last_signature = context.last_signature

        for candle in candles:
            signature = self._signature(candle)
            if last_timestamp is None or candle.time > last_timestamp:
                payload.append(self._candle_to_dict(candle))
            elif candle.time == last_timestamp and signature != last_signature:
                payload.append(self._candle_to_dict(candle))

        return payload

    @staticmethod
    def _candle_to_dict(candle: CandleData) -> Dict[str, float]:
        return {
            "time": candle.time,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }

    @staticmethod
    def _signature(candle: CandleData) -> Tuple[float, float, float, float, float]:
        return (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )

    def _resolve_plugin(self, source: str) -> MarketDataSourcePlugin:
        plugin = self._plugin_manager.get_plugin(source)
        if plugin is None:
            raise MarketAPIError(f"未找到数据源插件: {source}")
        return plugin

    @staticmethod
    def _resolve_realtime_manager(plugin: MarketDataSourcePlugin):
        getter = getattr(plugin, "get_realtime_manager", None)
        manager = None
        if callable(getter):
            try:
                manager = getter()
            except TypeError:
                manager = getter
        if manager is None:
            manager = getattr(plugin, "_realtime", None)
        if manager is not None and getattr(manager, "enabled", True) is False:
            return None
        return manager

    def _safe_get_cache_range(self, source: str, symbol: str, bar: str, mode: str) -> Optional[Dict[str, Any]]:
        try:
            return self._cache_service.get_cache_range(source, symbol, bar, mode)
        except Exception as exc:
            self._logger.debug(
                "获取缓存范围失败，将从头开始采集 (%s/%s/%s): %s",
                source,
                symbol,
                bar,
                exc,
            )
            return None

    @staticmethod
    def _make_key(source: str, symbol: str, bar: str, mode: str) -> str:
        return f"{source.lower()}::{symbol.upper()}::{mode.lower()}::{bar.lower()}"


def get_market_service(source: str = "binance"):
    """
    ⚠️ 已废弃: 请使用插件系统

    Args:
        source: 数据源名称

    Raises:
        DeprecationWarning: 此函数已废弃
    """

    logger.error(
        f"❌ get_market_service('{source}') 已废弃！\n"
        f"   请使用插件系统:\n"
        f"   from core.plugins.manager import PluginManager\n"
        f"   manager = PluginManager()\n"
        f"   plugin = manager.get_plugin('{source}')\n"
    )
    raise DeprecationWarning(
        "get_market_service() 已废弃，请使用插件系统。"
        "参考: core/plugins/manager.py"
    )


# 废弃的常量
MARKET_SERVICES = {}


def get_realtime_ingestion_service() -> RealtimeIngestionService:
    """获取默认的实时采集服务实例"""

    return RealtimeIngestionService.get_default()
