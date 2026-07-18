#!/usr/bin/env python3
"""测试 OKX API 连通性"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests

# 配置 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
import django
django.setup()

from core.proxy_config import (
    print_proxy_status, get_proxy_dict, get_websocket_proxy_kwargs,
)
from core.plugins.sources.okx_plugin import OKXMarketPlugin
from core.plugins.base import SymbolMode


def test_rest_api():
    print("\n=== OKX REST API 测试 ===")

    plugin = OKXMarketPlugin()
    base_url = plugin.BASE_URL

    # 1. 测试连通性 - 获取服务器时间
    print("\n--- 测试 1: 服务器时间 ---")
    proxies = get_proxy_dict()
    try:
        resp = requests.get(
            f"{base_url}/public/time",
            proxies=proxies,
            timeout=15,
        )
        result = resp.json()
        if result.get("code") == "0":
            ts = result["data"][0]["ts"]
            print(f"  ✅ OKX 时间: {ts}")
        else:
            print(f"  ❌ 错误: {result}")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")

    # 2. 测试 Ticker
    print("\n--- 测试 2: BTC-USDT Ticker ---")
    try:
        result = plugin._request("/market/ticker", {"instId": "BTC-USDT"})
        if result.get("code") == "0":
            ticker = result["data"][0]
            print(f"  ✅ 最新价: {ticker.get('last')}")
            print(f"     24h最高: {ticker.get('high24h')}")
            print(f"     24h最低: {ticker.get('low24h')}")
            print(f"     24h成交量: {ticker.get('vol24h')}")
        else:
            print(f"  ❌ 错误: {result.get('msg')}")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")

    # 3. 测试 K 线 (1m)
    print("\n--- 测试 3: BTC-USDT K线 (1m) ---")
    try:
        candles = plugin._get_candlesticks_impl(
            "BTC-USDT", "1m", limit=5, mode=SymbolMode.SPOT.value
        )
        if candles:
            print(f"  ✅ 获取到 {len(candles)} 条 K 线")
            for c in candles[:3]:
                print(f"     时间:{c.time} O:{c.open} H:{c.high} L:{c.low} C:{c.close} V:{c.volume}")
        else:
            print("  ❌ 未获取到数据")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")

    # 4. 测试资金费率 (合约)
    print("\n--- 测试 4: BTC-USDT 永续合约资金费率 ---")
    try:
        result = plugin._request("/public/funding-rate", {"instId": "BTC-USDT-SWAP"})
        if result.get("code") == "0":
            data = result["data"][0]
            print(f"  ✅ 当前资金费率: {data.get('fundingRate')}")
            print(f"     下次资金费率: {data.get('nextFundingRate')}")
        else:
            print(f"  ❌ 错误: {result.get('msg')}")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")

    # 5. 测试合约基差
    print("\n--- 测试 5: 合约基差 ---")
    try:
        basis = plugin._get_contract_basis_impl("BTCUSDT", "perpetual")
        print(f"  ✅ 基差: {basis.basis:.2f}")
        print(f"     基差率: {basis.basis_rate:.4f}%")
        print(f"     合约价: {basis.contract_price}")
        print(f"     现货价: {basis.reference_price}")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")


def test_websocket():
    print("\n=== OKX WebSocket 连通性测试 ===")

    try:
        import websocket
    except ImportError:
        print("  ⚠️ websocket-client 未安装，跳过 WebSocket 测试")
        return

    proxy_kwargs = get_websocket_proxy_kwargs()
    print(f"  WebSocket 代理参数: {proxy_kwargs or '无代理'}")

    connected = [False]
    messages = []
    stop = [False]

    def on_open(ws):
        connected[0] = True
        print("  ✅ WebSocket 已连接")
        sub = {
            "op": "subscribe",
            "args": [{"channel": "tickers", "instId": "BTC-USDT"}]
        }
        ws.send(json.dumps(sub))
        print("  📡 已订阅 BTC-USDT ticker")

    def on_message(ws, msg):
        messages.append(msg)
        try:
            payload = json.loads(msg)
            event = payload.get("event")
            if event == "subscribe":
                print(f"  ✅ 订阅成功: {payload.get('arg')}")
            elif event == "pong" or payload.get("op") == "pong":
                pass
            elif payload.get("arg", {}).get("channel") == "tickers":
                data = payload.get("data", [])
                if data:
                    print("  ✅ 收到 ticker 数据:")
                    print(f"     最新价: {data[0].get('last')}")
                    print(f"     买一价: {data[0].get('bidPx')}")
                    print(f"     卖一价: {data[0].get('askPx')}")
                    ws.close()
        except json.JSONDecodeError:
            pass

    def on_error(ws, error):
        print(f"  ❌ WebSocket 错误: {error}")

    def on_close(ws, *args):
        print("  🔒 WebSocket 连接关闭")
        stop[0] = True

    ws = websocket.WebSocketApp(
        "wss://ws.okx.com:8443/ws/v5/public",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    print("  🔌 正在连接 wss://ws.okx.com:8443/ws/v5/public ...")
    ws.run_forever(
        ping_interval=20,
        ping_timeout=10,
        **proxy_kwargs,
    )

    if not connected[0]:
        print("  ❌ WebSocket 连接失败")

    return len(messages) > 0


def main():
    print("=" * 50)
    print("  OKX API 连通性测试")
    print("=" * 50)

    print_proxy_status()

    test_rest_api()
    test_websocket()

    print("\n" + "=" * 50)
    print("  测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
