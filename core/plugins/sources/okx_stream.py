# -*- coding: utf-8 -*-
"""OKX 实时 K 线 WebSocket 管理器"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

from core.proxy_config import get_websocket_proxy_kwargs
from ..base import CandleData

try:  # pragma: no cover - 运行环境需安装 websocket-client
    import websocket  # type: ignore
except ImportError:  # pragma: no cover
    websocket = None  # type: ignore

logger = logging.getLogger(__name__)


def _build_proxy_kwargs() -> Dict[str, object]:
    """构建 websocket-client 代理参数"""
    return get_websocket_proxy_kwargs()


@dataclass
class _RealtimeStats:
    last_message_ts: float = 0
    reconnects: int = 0


class OKXStreamWorker:
    """管理单个 instId@interval 的 OKX 实时订阅"""

    PUBLIC_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    BUSINESS_WS_URL = "wss://ws.okx.com:8443/ws/v5/business"
    BUFFER_SIZE = 7200  # 约 2 小时的 1s 数据

    def __init__(self, inst_id: str, interval: str = "1S", inst_type: Optional[str] = None) -> None:
        self.inst_id = inst_id.upper()
        self.interval = interval.lower()
        self.channel = f"candle{self.interval}"
        # OKX candlestick channels (including 1m/1s) use the business websocket.
        self._ws_url = self.BUSINESS_WS_URL
        self.inst_type = inst_type.upper() if inst_type else None
        self._buffer: Deque[CandleData] = deque(maxlen=self.BUFFER_SIZE)
        self._buffer_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._stats = _RealtimeStats()
        self._proxy_kwargs = _build_proxy_kwargs()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def alive(self) -> bool:
        return self._thread.is_alive() and not self._stop_event.is_set()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        if websocket is None:
            logger.warning("websocket-client 未安装，OKX 实时流不可用")
            return

        while not self._stop_event.is_set():
            try:
                ws = websocket.WebSocketApp(  # type: ignore
                    self._ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                logger.info("🔌 OKX WS 连接: %s %s", self.inst_id, self.channel)
                ws.run_forever(ping_interval=20, ping_timeout=10, **self._proxy_kwargs)
            except Exception as exc:  # pragma: no cover - 网络异常
                logger.warning("OKX WS 连接异常，将重试: %s", exc)
            finally:
                self._stats.reconnects += 1
                if not self._stop_event.is_set():
                    time.sleep(5)

    def _on_open(self, ws) -> None:
        try:
            args = {
                "channel": self.channel,
                "instId": self.inst_id,
            }

            payload = {
                "op": "subscribe",
                "args": [args]
            }
            ws.send(json.dumps(payload))
            logger.info("✅ OKX WS 订阅: %s %s", self.inst_id, self.channel)
        except Exception as exc:  # pragma: no cover - 运行期异常
            logger.warning("OKX WS 订阅失败: %s", exc)

    def _on_message(self, ws, message: str) -> None:
        if not message:
            return

        if message == "pong":
            return

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            logger.debug("忽略非 JSON 消息: %s", message[:60])
            return

        event = payload.get("event")
        if event == "ping":
            try:
                ws.send(json.dumps({"op": "pong"}))
            except Exception:
                logger.debug("OKX WS pong 发送失败")
            return
        if event == "error":  # pragma: no cover - 调试
            logger.warning("OKX WS 错误: %s", payload)
            return
        if event in {"subscribe", "unsubscribe"}:
            return

        data = payload.get("data")
        arg = payload.get("arg", {})
        if not data or arg.get("channel") != self.channel or arg.get("instId") != self.inst_id:
            return

        for item in data:
            try:
                candle = CandleData(
                    time=int(item[0]) // 1000,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]) if len(item) > 5 else 0.0,
                )
            except (IndexError, ValueError, TypeError):
                continue

            with self._buffer_lock:
                if self._buffer and self._buffer[-1].time == candle.time:
                    self._buffer[-1] = candle
                else:
                    self._buffer.append(candle)
            self._stats.last_message_ts = time.time()

    def _on_error(self, _ws, error: Exception) -> None:  # pragma: no cover - 调试
        logger.warning("OKX WS 错误 (%s %s): %s", self.inst_id, self.channel, error)

    def _on_close(self, _ws, *_args) -> None:  # pragma: no cover - 调试
        logger.info("OKX WS 已关闭 (%s %s)", self.inst_id, self.channel)

    def get_latest(self, limit: int) -> List[CandleData]:
        with self._buffer_lock:
            if not self._buffer:
                return []
            return list(self._buffer)[-limit:]


class OKXRealtimeStreamManager:
    """集中管理 OKX 实时订阅"""

    def __init__(self) -> None:
        self._streams: Dict[str, OKXStreamWorker] = {}
        self._lock = threading.Lock()

    def _stream_key(self, inst_id: str, interval: str) -> str:
        return f"{inst_id.upper()}::{interval.upper()}"

    def _ensure_stream(self, inst_id: str, interval: str) -> Optional[OKXStreamWorker]:
        if websocket is None:
            return None

        key = self._stream_key(inst_id, interval)
        with self._lock:
            worker = self._streams.get(key)
            if worker and worker.alive:
                return worker
            worker = OKXStreamWorker(inst_id, interval)
            self._streams[key] = worker
            return worker

    def get_latest_candles(self, inst_id: str, interval: str, limit: int = 200) -> List[CandleData]:
        worker = self._ensure_stream(inst_id, interval)
        if not worker:
            return []
        return worker.get_latest(limit)

    @property
    def enabled(self) -> bool:
        return websocket is not None


_okx_realtime_manager: Optional[OKXRealtimeStreamManager] = None


def get_realtime_manager() -> OKXRealtimeStreamManager:
    global _okx_realtime_manager
    if _okx_realtime_manager is None:
        _okx_realtime_manager = OKXRealtimeStreamManager()
    return _okx_realtime_manager
