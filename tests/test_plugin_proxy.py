#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试插件代理配置

验证每个插件是否根据 requires_proxy 配置正确使用代理
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geneticgrid.settings')
django.setup()

from core.plugins.manager import PluginManager


def test_plugin_proxy_config():
    """测试插件代理配置"""
    print("\n" + "="*60)
    print("📋 插件代理配置测试")
    print("="*60 + "\n")
    
    manager = PluginManager()
    
    # 检查每个插件的代理配置
    print("🔍 检查各插件代理配置:\n")
    
    proxy_plugins = []
    direct_plugins = []
    
    for name, plugin in manager.get_all_plugins().items():
        metadata = plugin.get_metadata()
        capability = plugin.get_capability()
        
        requires_proxy = metadata.requires_proxy or capability.requires_proxy
        
        if requires_proxy:
            proxy_plugins.append(name)
            print(f"  🔐 {metadata.display_name:20} - 需要代理")
        else:
            direct_plugins.append(name)
            print(f"  🌐 {metadata.display_name:20} - 直接连接")
    
    print("\n📊 统计:")
    print(f"  - 需要代理: {len(proxy_plugins)} 个 {proxy_plugins}")
    print(f"  - 直接连接: {len(direct_plugins)} 个 {direct_plugins}")
    
    # 测试代理注入
    print("\n🧪 测试代理注入:\n")
    
    test_plugins = []
    if proxy_plugins:
        test_plugins.append(proxy_plugins[0])  # 至少测试一个需要代理的
    if direct_plugins:
        test_plugins.append(direct_plugins[0])  # 至少测试一个不需要代理的
    
    for name in test_plugins:
        plugin = manager.get_plugin(name)
        requires_proxy = plugin.get_metadata().requires_proxy
        
        print(f"正在测试插件: {name}")
        
        try:
            capability = plugin.get_capability()
            
            # 直接访问 _service (这会触发 @property 并创建服务)
            try:
                service = plugin._service
                print(f"  ✓ 服务类型: {type(service).__name__}")
                
                # OKX 服务特殊处理（使用 SDK）
                if type(service).__name__ == 'OKXMarketService':
                    has_proxy = bool(service.proxy)
                    
                    status = "✅" if has_proxy == requires_proxy else "❌"
                    proxy_info = f"OKX SDK 代理: {service.proxy}" if has_proxy else "无代理"
                    
                    print(f"  {status} {plugin.get_metadata().display_name}")
                    print(f"     配置要求: {'🔐 需要代理' if requires_proxy else '🌐 直连'}")
                    print(f"     实际状态: {proxy_info}\n")
                    continue
                
                # 检查 session 配置（其他服务）
                if hasattr(service, 'session'):
                    session = service.session
                    has_proxy = bool(session.proxies)
                    
                    status = "✅" if has_proxy == requires_proxy else "❌"
                    proxy_info = f"{list(session.proxies.keys())}" if has_proxy else "无代理"
                    
                    print(f"  {status} {plugin.get_metadata().display_name}")
                    print(f"     配置要求: {'🔐 需要代理' if requires_proxy else '🌐 直连'}")
                    print(f"     实际状态: {proxy_info}\n")
                else:
                    print("  ⚠️  服务没有 session 属性\n")
            except AttributeError as e:
                print(f"  ⚠️  插件没有 _service 属性: {e}\n")
                
        except Exception as e:
            import traceback
            print(f"  ❌ 测试失败: {e}")
            traceback.print_exc()
            print()
    
    print("="*60)


def test_proxy_availability():
    """测试代理可用性"""
    from core.proxy_config import print_proxy_status
    
    print("\n" + "="*60)
    print("🌐 代理可用性测试")
    print("="*60)
    
    print_proxy_status()
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("🚀 开始测试插件代理系统...\n")
    
    # 测试代理可用性
    test_proxy_availability()
    
    # 测试插件代理配置
    test_plugin_proxy_config()
    
    print("\n✅ 测试完成！\n")
