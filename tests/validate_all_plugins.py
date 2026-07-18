#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整的插件系统验证脚本
"""
import os
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.manager import PluginManager


def main():
    # 获取插件管理器实例
    manager = PluginManager()
    
    # 获取所有插件
    plugins = manager.get_all_plugins()
    failed = manager.get_failed_plugins()
    
    print('=' * 80)
    print('🎉 GeneticGrid 数据源插件系统 - 完整验证报告')
    print('=' * 80)
    print()
    
    # 显示扫描结果
    print('📊 插件扫描统计:')
    print(f'  ✅ 成功加载: {len(plugins)} 个插件')
    if failed:
        print(f'  ❌ 加载失败: {len(failed)} 个插件')
    print()
    
    # 显示所有插件详情
    print('=' * 80)
    print('📦 已加载插件列表')
    print('=' * 80)
    print()
    
    for name, plugin in sorted(plugins.items()):
        metadata = plugin.get_metadata()
        capability = plugin.get_capability()
        
        # 图标
        icon = '🔐' if metadata.requires_proxy else '🌐'
        
        # 功能标记
        kline_mark = '✅' if capability.supports_candlesticks else '❌'
        ticker_mark = '✅' if capability.supports_ticker else '❌'
        
        # 粒度数量
        gran_count = len(capability.candlestick_granularities)
        
        print(f'{icon} {metadata.display_name:20s} ({name:12s})')
        print(f'   K线: {kline_mark}  行情: {ticker_mark}  粒度: {gran_count:2d} 种')
        print(f'   网站: {metadata.website}')
        print()
    
    # 功能测试
    print('=' * 80)
    print('🧪 实时数据测试 (BTC-USDT)')
    print('=' * 80)
    print()
    
    test_symbol = 'BTC-USDT'
    success_list = []
    fail_list = []
    
    for name, plugin in sorted(plugins.items()):
        capability = plugin.get_capability()
        
        # 跳过不支持行情的插件
        if not capability.supports_ticker:
            continue
        
        try:
            ticker = plugin.get_ticker(test_symbol)
            print(f'✅ {name:12s}: ${ticker.last:>10,.2f}', end='')
            if ticker.change_24h_pct:
                sign = '+' if ticker.change_24h_pct > 0 else ''
                print(f'  ({sign}{ticker.change_24h_pct:.2f}%)')
            else:
                print()
            success_list.append(name)
        except Exception:
            print(f'❌ {name:12s}: 网络问题或API不可达')
            fail_list.append(name)
    
    print()
    print('=' * 80)
    print('📈 测试总结')
    print('=' * 80)
    print(f'  总计插件: {len(plugins)} 个')
    print(f'  测试通过: {len(success_list)} 个')
    if fail_list:
        fail_str = ', '.join(fail_list)
        print(f'  网络问题: {len(fail_list)} 个 ({fail_str})')
    print()
    
    if len(success_list) >= 5:
        print('✅ 系统状态: 优秀 - 核心功能正常')
    elif len(success_list) >= 3:
        print('⚠️  系统状态: 良好 - 大部分功能正常')
    else:
        print('❌ 系统状态: 需要检查网络配置')
    
    print('=' * 80)


if __name__ == '__main__':
    main()
