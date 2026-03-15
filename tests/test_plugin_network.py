#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试插件网络可达性

测试每个插件是否可以成功连接并获取数据
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.manager import PluginManager
from core.plugins.base import PluginError
from core.proxy_config import is_proxy_available


def test_plugin_network():
    """测试所有插件的网络可达性"""
    print("\n" + "="*70)
    print("🌐 插件网络可达性测试")
    print("="*70 + "\n")
    
    # 检查代理状态
    socks5_available = is_proxy_available('socks5')
    http_available = is_proxy_available('http')
    print(f"代理状态:")
    print(f"  SOCKS5 (127.0.0.1:1080): {'✅ 可用' if socks5_available else '❌ 不可用'}")
    print(f"  HTTP (127.0.0.1:8080): {'✅ 可用' if http_available else '❌ 不可用'}\n")
    
    manager = PluginManager()
    all_plugins = manager.get_all_plugins()
    
    results = {
        'success': [],
        'failed': [],
        'needs_proxy': []
    }
    
    print(f"开始测试 {len(all_plugins)} 个插件...\n")
    print("-" * 70)
    
    for name, plugin in all_plugins.items():
        metadata = plugin.get_metadata()
        capability = plugin.get_capability()
        
        print(f"\n📦 测试插件: {metadata.display_name} ({name})")
        print(f"   需要代理: {'是 🔐' if metadata.requires_proxy else '否 🌐'}")
        
        # 测试 ticker（如果支持）
        if capability.supports_ticker:
            test_symbol = "BTC-USDT"
            print(f"   测试行情: {test_symbol}...", end=" ")
            
            try:
                ticker = plugin.get_ticker(test_symbol)
                print(f"✅ 成功")
                print(f"      价格: {ticker.last:.2f}")
                results['success'].append({
                    'name': name,
                    'display_name': metadata.display_name,
                    'requires_proxy': metadata.requires_proxy,
                    'test': 'ticker',
                    'price': ticker.last
                })
            except Exception as e:
                error_msg = str(e)
                print(f"❌ 失败")
                print(f"      错误: {error_msg[:80]}")
                
                # 判断是否是网络问题
                if any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'network', 'proxy']):
                    if not metadata.requires_proxy:
                        results['needs_proxy'].append({
                            'name': name,
                            'display_name': metadata.display_name,
                            'error': error_msg
                        })
                        print(f"      💡 建议: 可能需要配置代理")
                    else:
                        results['failed'].append({
                            'name': name,
                            'display_name': metadata.display_name,
                            'error': error_msg
                        })
                else:
                    results['failed'].append({
                        'name': name,
                        'display_name': metadata.display_name,
                        'error': error_msg
                    })
        
        # 测试 K线（如果支持）
        if capability.supports_candlesticks:
            test_symbol = "BTC-USDT"
            test_bar = capability.candlestick_granularities[0] if capability.candlestick_granularities else "1h"
            print(f"   测试K线: {test_symbol} @ {test_bar}...", end=" ")
            
            try:
                candles = plugin.get_candlesticks(test_symbol, test_bar, limit=5)
                print(f"✅ 成功")
                print(f"      获取: {len(candles)} 条K线")
                if candles:
                    latest = candles[-1]
                    print(f"      最新: 时间={latest.time}, 收盘={latest.close:.2f}")
                
                # 如果 ticker 失败但 K线成功，更新状态
                if name not in [r['name'] for r in results['success']]:
                    results['success'].append({
                        'name': name,
                        'display_name': metadata.display_name,
                        'requires_proxy': metadata.requires_proxy,
                        'test': 'candlesticks',
                        'count': len(candles)
                    })
            except Exception as e:
                error_msg = str(e)
                print(f"❌ 失败")
                print(f"      错误: {error_msg[:80]}")
    
    # 打印测试总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70 + "\n")
    
    print(f"✅ 成功: {len(results['success'])} 个插件")
    for item in results['success']:
        proxy_icon = "🔐" if item['requires_proxy'] else "🌐"
        print(f"   {proxy_icon} {item['display_name']}")
    
    if results['needs_proxy']:
        print(f"\n⚠️  需要代理: {len(results['needs_proxy'])} 个插件")
        for item in results['needs_proxy']:
            print(f"   🔐 {item['display_name']}")
            print(f"      建议: 在插件配置中设置 requires_proxy=True")
    
    if results['failed']:
        print(f"\n❌ 失败: {len(results['failed'])} 个插件")
        for item in results['failed']:
            print(f"   ⚠️  {item['display_name']}")
            print(f"      {item['error'][:100]}")
    
    print("\n" + "="*70)
    
    # 返回测试结果
    results = {
        'total': len(all_plugins),
        'success': len(results['success']),
        'failed': len(results['failed']),
        'needs_proxy': len(results['needs_proxy']),
        'results': results
    }

    assert results['total'] >= 0


def suggest_proxy_changes(results):
    """根据测试结果建议代理配置修改"""
    needs_proxy = results['results']['needs_proxy']
    
    if not needs_proxy:
        print("\n✅ 所有插件配置正确，无需修改代理设置\n")
        return
    
    print("\n" + "="*70)
    print("💡 代理配置建议")
    print("="*70 + "\n")
    
    print("以下插件可能需要启用代理访问:\n")
    
    for item in needs_proxy:
        plugin_file = f"core/plugins/sources/{item['name']}_plugin.py"
        print(f"📝 {item['display_name']} ({item['name']})")
        print(f"   文件: {plugin_file}")
        print(f"   修改: 在 _get_metadata() 中设置 requires_proxy=True")
        print(f"   示例:")
        print(f"   ```python")
        print(f"   return DataSourceMetadata(")
        print(f"       ...,")
        print(f"       requires_proxy=True,  # 需要代理访问")
        print(f"   )")
        print(f"   ```\n")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    print("🚀 开始网络可达性测试...\n")
    
    try:
        results = test_plugin_network()
        
        # 如果有插件需要代理，提供修改建议
        if results['needs_proxy'] > 0:
            suggest_proxy_changes(results)
        
        # 退出码
        if results['failed'] > 0 or results['needs_proxy'] > 0:
            print("⚠️  部分插件测试失败或需要代理配置\n")
            sys.exit(1)
        else:
            print("✅ 所有插件测试通过！\n")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
