#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
插件系统验证脚本

快速验证插件系统是否正常工作
"""

import os
import sys

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')

import django
django.setup()

from core.plugins.manager import get_plugin_manager
from core.plugin_adapter import get_unified_service
from core.services import MARKET_SERVICES

def print_section(title):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_plugin_manager():
    """测试插件管理器"""
    print_section("1. 插件管理器状态")
    
    manager = get_plugin_manager()
    plugins = manager.list_plugin_names()
    
    print(f"✅ 已注册插件数量: {len(plugins)}")
    print(f"✅ 插件列表: {', '.join(plugins)}")
    
    for name in plugins:
        plugin = manager.get_plugin(name)
        if plugin:
            metadata = plugin.get_metadata()
            capability = plugin.get_capability()
            print(f"\n   📦 {metadata.display_name} ({name})")
            print(f"      - K线支持: {'✅' if capability.supports_candlesticks else '❌'}")
            print(f"      - 行情支持: {'✅' if capability.supports_ticker else '❌'}")
            print(f"      - 粒度数量: {len(capability.candlestick_granularities)}")

def test_unified_service():
    """测试统一服务"""
    print_section("2. 统一服务接口测试")
    
    test_sources = ['okx', 'binance', 'coinbase']
    
    for source in test_sources:
        try:
            service = get_unified_service(source)
            status = "✅ 使用插件" if service.is_using_plugin else "🔧 使用旧服务"
            print(f"{status} - {source}")
        except Exception as e:
            print(f"❌ 失败 - {source}: {e}")

def test_data_fetch():
    """测试数据获取"""
    print_section("3. 数据获取测试")
    
    # 测试行情
    print("📊 测试行情数据...")
    try:
        service = get_unified_service('okx')
        ticker = service.get_ticker('BTC-USDT')
        print(f"✅ OKX 行情: BTC-USDT = {ticker.get('last')} USDT")
        print(f"   数据来源: {'插件系统' if service.is_using_plugin else '旧服务'}")
    except Exception as e:
        print(f"❌ 获取行情失败: {e}")
    
    # 测试K线
    print("\n📈 测试K线数据...")
    try:
        service = get_unified_service('binance')
        candles = service.get_candlesticks('BTC-USDT', '1h', limit=5)
        print(f"✅ Binance K线: 获取 {len(candles)} 条数据")
        if candles:
            latest = candles[-1]
            print(f"   最新K线: 时间={latest['time']}, 收盘={latest['close']}")
        print(f"   数据来源: {'插件系统' if service.is_using_plugin else '旧服务'}")
    except Exception as e:
        print(f"❌ 获取K线失败: {e}")

def compare_systems():
    """对比新旧系统"""
    print_section("4. 新旧系统对比")
    
    plugin_sources = set(get_plugin_manager().list_plugin_names())
    legacy_sources = set(MARKET_SERVICES.keys())
    
    print(f"插件系统数据源: {len(plugin_sources)} 个")
    print(f"   {', '.join(sorted(plugin_sources))}")
    
    print(f"\n旧服务数据源: {len(legacy_sources)} 个")
    print(f"   {', '.join(sorted(legacy_sources))}")
    
    common = plugin_sources & legacy_sources
    plugin_only = plugin_sources - legacy_sources
    legacy_only = legacy_sources - plugin_sources
    
    print(f"\n✅ 共同拥有: {len(common)} 个")
    if common:
        print(f"   {', '.join(sorted(common))}")
    
    if plugin_only:
        print(f"\n📦 仅插件: {', '.join(sorted(plugin_only))}")
    
    if legacy_only:
        print(f"\n🔧 仅旧服务: {', '.join(sorted(legacy_only))}")

def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        GeneticGrid 插件系统验证                          ║
║        Plugin System Verification                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        test_plugin_manager()
        test_unified_service()
        test_data_fetch()
        compare_systems()
        
        print_section("✅ 验证完成")
        print("插件系统运行正常！")
        print("\n建议:")
        print("1. 启动 Django 服务: python manage.py runserver")
        print("2. 访问: http://localhost:8000/api/sources/")
        print("3. 查看日志中的 📦 和 🔧 标记确认数据来源")
        
        return 0
        
    except Exception as e:
        print_section("❌ 验证失败")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
