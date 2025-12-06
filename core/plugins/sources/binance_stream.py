# -*- coding: utf-8 -*-
"""Binance 实时 K 线 WebSocket 管理器"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional
from urllib.parse import urlparse

from core.proxy_config import get_proxy
from ..base import CandleData

try:  # pragma: no cover - 依赖在运行环境中安装
    import websocket  # type: ignore
except ImportError:  # pragma: no cover
    websocket = None  # type: ignore

logger = logging.getLogger(__name__)


def _build_proxy_kwargs() -> Dict[str, object]:
    """构建 websocket-client 需要的代理参数"""
    proxy_url = get_proxy()
    if not proxy_url:
        return {}

    parsed = urlparse(proxy_url)
    if not parsed.hostname or not parsed.port:
        return {}

    proxy_kwargs: Dict[str, object] = {
        "http_proxy_host": parsed.hostname,
        "http_proxy_port": parsed.port,
    }
    if parsed.username:
        proxy_kwargs["http_proxy_auth"] = (parsed.username, parsed.password)
    if parsed.scheme.lower().startswith("socks"):
        proxy_kwargs["proxy_type"] = parsed.scheme
    return proxy_kwargs


@dataclass
class _RealtimeStats:
    last_message_ts: float = 0
    reconnects: int = 0


class BinanceStreamWorker:
    """单个 symbol@interval 的实时订阅"""

    BUFFER_SIZE = 7200  # 约两小时的 1s K 线

    def __init__(self, symbol: str, interval: str) -> None:
        self.symbol = symbol.lower()
        self.interval = interval
        self._buffer: Deque[CandleData] = deque(maxlen=self.BUFFER_SIZE)
        self._buffer_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stats = _RealtimeStats()
        self._proxy_kwargs = _build_proxy_kwargs()
        self._thread.start()

    @property
    def alive(self) -> bool:
        return self._thread.is_alive() and not self._stop_event.is_set()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        if websocket is None:
            logger.warning("websocket-client 未安装，Binance 实时流不可用")
            return

        stream_name = f"{self.symbol}@kline_{self.interval}"
        url = f"wss://stream.binance.com:9443/ws/{stream_name}"

        while not self._stop_event.is_set():
            try:
                ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                logger.info("🔌 Binance WS 连接: %s", stream_name)
                ws.run_forever(ping_interval=20, ping_timeout=10, **self._proxy_kwargs)
            except Exception as exc:  # pragma: no cover - 网络异常
                logger.warning("Binance WS 连接异常，将重试: %s", exc)
            finally:
                self._stats.reconnects += 1
                if not self._stop_event.is_set():
                    time.sleep(5)

    def _on_message(self, _ws, message: str) -> None:
        try:
            payload = json.loads(message)
            kline = payload.get("k")
            if not kline:
                return

            candle = CandleData(
                time=int(kline.get("t", 0)) // 1000,
                open=float(kline.get("o", 0)),
                high=float(kline.get("h", 0)),
                low=float(kline.get("l", 0)),
                close=float(kline.get("c", 0)),
                volume=float(kline.get("v", 0)),
            )

            with self._buffer_lock:
                if self._buffer and self._buffer[-1].time == candle.time:
                    self._buffer[-1] = candle
                else:
                    self._buffer.append(candle)
            self._stats.last_message_ts = time.time()
        except Exception as exc:  # pragma: no cover - 解析异常
            logger.debug("忽略无效 WS 消息: %s", exc)

    def _on_error(self, _ws, error: Exception) -> None:  # pragma: no cover - 调试辅助
        logger.warning("Binance WS 错误 (%s@%s): %s", self.symbol, self.interval, error)

    def _on_close(self, _ws, *_args) -> None:  # pragma: no cover - 调试辅助
        logger.info("Binance WS 已关闭 (%s@%s)", self.symbol, self.interval)

    def get_latest(self, limit: int) -> List[CandleData]:
        with self._buffer_lock:
            if not self._buffer:
                return []
            data = list(self._buffer)[-limit:]
        return data


class BinanceRealtimeStreamManager:
    """管理 Binance 实时 WebSocket 订阅"""

    def __init__(self) -> None:
        self._streams: Dict[str, BinanceStreamWorker] = {}
        self._lock = threading.Lock()

    def _stream_key(self, symbol: str, interval: str) -> str:
        return f"{symbol.lower()}::{interval}"

    def _ensure_stream(self, symbol: str, interval: str) -> Optional[BinanceStreamWorker]:
        if websocket is None:
            return None

        key = self._stream_key(symbol, interval)
        with self._lock:
            worker = self._streams.get(key)
            if worker and worker.alive:
                return worker
            worker = BinanceStreamWorker(symbol, interval)
            self._streams[key] = worker
            return worker

    def get_latest_candles(self, symbol: str, interval: str, limit: int = 200) -> List[CandleData]:
        worker = self._ensure_stream(symbol, interval)
        if not worker:
            return []
        return worker.get_latest(limit)

    @property
    def enabled(self) -> bool:
        return websocket is not None


# 单例，避免重复订阅
_realtime_manager: Optional[BinanceRealtimeStreamManager] = None


def get_realtime_manager() -> BinanceRealtimeStreamManager:
    global _realtime_manager
    if _realtime_manager is None:
        _realtime_manager = BinanceRealtimeStreamManager()
    return _realtime_manager
