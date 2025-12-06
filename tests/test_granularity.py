#!/usr/bin/env python
"""测试标准粒度协议"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.manager import get_plugin_manager
from core.plugins.base import Granularity

def test_standard_granularities():
    """测试标准粒度协议"""
    print("="*60)
    print("标准粒度协议测试")
    print("="*60)
    
    # 显示标准粒度
    print(f"\n📊 标准粒度列表 ({len(Granularity.PRIORITY)} 种):")
    for i, bar in enumerate(Granularity.PRIORITY, 1):
        seconds = Granularity.to_seconds(bar)
        if seconds == 0:
            time_str = "实时tick"
        elif seconds < 3600:
            time_str = f"{seconds // 60}分钟"
        elif seconds < 86400:
            time_str = f"{seconds // 3600}小时"
        else:
            time_str = f"{seconds // 86400}天"
        print(f"   {i:2d}. {bar:4s} = {time_str}")
    
    # 显示推荐粒度
    print(f"\n✅ 推荐粒度 ({len(Granularity.RECOMMENDED)} 种):")
    print(f"   {', '.join(Granularity.RECOMMENDED)}")
    
    # 加载插件并检查
    print("\n" + "="*60)
    print("插件粒度检查")
    print("="*60)
    
    manager = get_plugin_manager()
    
    plugin_names = ["okx", "binance", "bybit", "coinbase", "kraken", "coingecko"]
    
    for plugin_name in plugin_names:
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            continue
            
        print(f"\n🔌 插件: {plugin_name}")
        
        if plugin._capability.supports_candlesticks:
            granularities = plugin._capability.candlestick_granularities
            print(f"   支持 {len(granularities)} 种粒度:")
            print(f"   {', '.join(granularities)}")
            
            # 验证粒度
            is_valid, invalid = Granularity.validate_list(granularities)
            if is_valid:
                print(f"   ✅ 所有粒度符合标准协议")
            else:
                print(f"   ⚠️ 非标准粒度: {', '.join(invalid)}")
        else:
            print(f"   不支持 K线数据")
    
    # 测试粒度聚合
    print("\n" + "="*60)
    print("粒度聚合测试")
    print("="*60)
    
    okx = manager.get_plugin("okx")
    if okx:
        print(f"\n测试 OKX 插件聚合功能...")
        print(f"OKX 支持的粒度: {', '.join(okx._capability.candlestick_granularities)}")
        
        # 测试聚合功能
        test_cases = [
            ("10m", "应该从 5m 聚合", True),
            ("2d", "应该从 1d 聚合", True),
            ("2h", "已直接支持", False),
            ("6h", "已直接支持", False),
        ]
        
        for requested_bar, desc, should_aggregate in test_cases:
            print(f"\n🔄 请求粒度: {requested_bar} ({desc})")
            try:
                candles = okx.get_candlesticks("BTCUSDT", requested_bar, limit=5)
                print(f"   ✅ 成功获取 {len(candles)} 条数据")
                if candles:
                    from datetime import datetime
                    latest = candles[-1]
                    print(f"   最新时间: {datetime.fromtimestamp(latest.time)}")
                    print(f"   价格: {latest.close}")
                    if should_aggregate:
                        print(f"   (通过粒度聚合获得)")
            except Exception as e:
                print(f"   ⚠️ {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    test_standard_granularities()
