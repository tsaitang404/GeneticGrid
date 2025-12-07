# -*- coding: utf-8 -*-
"""
文档生成系统

根据插件的元数据和能力自动生成文档。
"""

from typing import Dict, List
from datetime import datetime

from .base import MarketDataSourcePlugin, DataSourceMetadata, Capability
from .manager import PluginManager


class DocumentationGenerator:
    """文档生成器"""
    
    @staticmethod
    def generate_plugin_doc(plugin: MarketDataSourcePlugin) -> str:
        """
        为单个插件生成 Markdown 文档
        
        Args:
            plugin: 数据源插件
        
        Returns:
            Markdown 格式的文档
        """
        metadata = plugin.get_metadata()
        capability = plugin.get_capability()
        
        doc = []
        doc.append(f"# {metadata.display_name}")
        doc.append("")
        
        # 基本信息
        doc.append("## 基本信息")
        doc.append("")
        doc.append(f"**标识符**: `{metadata.name}`")
        doc.append(f"**类型**: {metadata.source_type.value}")
        doc.append(f"**插件版本**: {metadata.plugin_version}")
        doc.append(f"**状态**: {'✅ 活跃' if metadata.is_active else '❌ 已禁用'}")
        if metadata.is_experimental:
            doc.append("**标签**: 🧪 实验性")
        doc.append("")
        
        # 描述
        if metadata.description:
            doc.append("## 描述")
            doc.append("")
            doc.append(metadata.description)
            doc.append("")
        
        # 官网和 API
        if metadata.website or metadata.api_base_url:
            doc.append("## 资源")
            doc.append("")
            if metadata.website:
                doc.append(f"- **官网**: [{metadata.website}]({metadata.website})")
            if metadata.api_base_url:
                doc.append(f"- **API 基础 URL**: `{metadata.api_base_url}`")
            doc.append("")
        
        # 支持的功能
        doc.append("## 支持的功能")
        doc.append("")
        doc.append(DocumentationGenerator._generate_features_section(capability))
        doc.append("")
        
        # K线数据支持
        if capability.supports_candlesticks:
            doc.append("## K线数据")
            doc.append("")
            doc.append(f"**支持粒度**: {', '.join(capability.candlestick_granularities) or '无限制'}")
            doc.append("")
            doc.append(f"**单次请求最大条数**: {capability.candlestick_limit}")
            if capability.candlestick_max_history_days:
                doc.append(f"**历史数据回溯**: 最多 {capability.candlestick_max_history_days} 天")
            doc.append("")
        
        # Ticker 数据支持
        if capability.supports_ticker:
            doc.append("## 行情数据")
            doc.append("")
            if capability.ticker_update_frequency:
                doc.append(f"**更新频率**: 每 {capability.ticker_update_frequency} 秒更新一次")
            doc.append("")
        
        if capability.supports_funding_rate:
            doc.append("## 资金费率")
            doc.append("")
            if capability.funding_rate_interval_hours:
                doc.append(f"**结算周期**: 每 {capability.funding_rate_interval_hours} 小时")
            if capability.funding_rate_quote_currency:
                doc.append(f"**结算货币**: {capability.funding_rate_quote_currency}")
            doc.append("**约定字段**: funding_rate, next_funding_time, predicted_funding_rate, index_price")
            doc.append("")
        
        if capability.supports_contract_basis:
            doc.append("## 合约基差")
            doc.append("")
            if capability.contract_basis_types:
                doc.append(f"**支持的合约类型**: {', '.join(capability.contract_basis_types)}")
            if capability.contract_basis_tenors:
                doc.append(f"**支持的到期类型**: {', '.join(capability.contract_basis_tenors)}")
            doc.append("**约定字段**: basis, basis_rate, contract_price, reference_price")
            doc.append("")
        
        # 交易对
        if capability.supported_symbols:
            doc.append("## 支持的交易对")
            doc.append("")
            doc.append(f"**格式**: `{capability.symbol_format}`")
            doc.append(f"**总数**: {len(capability.supported_symbols)} 个")
            doc.append("")
            doc.append("**列表** (前 20 个):")
            doc.append("")
            for symbol in capability.supported_symbols[:20]:
                doc.append(f"- `{symbol}`")
            if len(capability.supported_symbols) > 20:
                doc.append(f"- ... 及其他 {len(capability.supported_symbols) - 20} 个")
            doc.append("")
        else:
            doc.append("## 交易对")
            doc.append("")
            doc.append(f"**格式**: `{capability.symbol_format}`")
            doc.append("**支持**: 所有交易对（无特定限制）")
            doc.append("")
        
        # 限制和要求
        doc.append("## 限制和要求")
        doc.append("")
        
        requirements = []
        if capability.requires_api_key:
            requirements.append("- ⚠️ 需要 API Key")
        if capability.requires_authentication:
            requirements.append("- ⚠️ 需要身份验证")
        if capability.has_rate_limit:
            rate_info = f"每分钟 {capability.rate_limit_per_minute} 次请求" if capability.rate_limit_per_minute else "有速率限制"
            requirements.append(f"- 🔄 速率限制: {rate_info}")
        
        if requirements:
            for req in requirements:
                doc.append(req)
        else:
            doc.append("- ✅ 无特殊要求（公开数据）")
        
        doc.append("")
        
        # 高级特性
        advanced = []
        if capability.supports_real_time:
            advanced.append("- 📡 支持实时数据")
        if capability.supports_websocket:
            advanced.append("- 🔗 支持 WebSocket")
        
        if advanced:
            doc.append("## 高级特性")
            doc.append("")
            for feature in advanced:
                doc.append(feature)
            doc.append("")
        
        # API 示例
        doc.append("## API 使用示例")
        doc.append("")
        doc.append("### 获取 K线数据")
        doc.append("")
        doc.append("```bash")
        doc.append(f"curl 'http://localhost:8000/api/candlesticks/?source={metadata.name}&symbol=BTC-USDT&bar=1h&limit=10'")
        doc.append("```")
        doc.append("")
        
        doc.append("### 获取行情数据")
        doc.append("")
        doc.append("```bash")
        doc.append(f"curl 'http://localhost:8000/api/ticker/?source={metadata.name}&symbol=BTC-USDT'")
        doc.append("```")
        doc.append("")
        
        # 维护信息
        if metadata.author or metadata.last_updated:
            doc.append("## 维护信息")
            doc.append("")
            if metadata.author:
                doc.append(f"**维护者**: {metadata.author}")
            if metadata.last_updated:
                doc.append(f"**最后更新**: {metadata.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
            doc.append("")
        
        return "\n".join(doc)
    
    @staticmethod
    def generate_all_plugins_doc(plugin_manager: PluginManager) -> str:
        """
        为所有插件生成合并文档
        
        Args:
            plugin_manager: 插件管理器
        
        Returns:
            Markdown 格式的合并文档
        """
        doc = []
        doc.append("# 数据源插件文档")
        doc.append("")
        doc.append(f"*生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        doc.append("")
        doc.append("本文档自动生成，展示所有已注册数据源插件的能力和特性。")
        doc.append("")
        
        # 目录
        plugins = plugin_manager.get_all_plugins()
        if plugins:
            doc.append("## 目录")
            doc.append("")
            for name, plugin in plugins.items():
                doc.append(f"- [{plugin.display_name}](#{plugin.name})")
            doc.append("")
        
        # 插件详情
        for name, plugin in plugins.items():
            plugin_doc = DocumentationGenerator.generate_plugin_doc(plugin)
            doc.append(plugin_doc)
            doc.append("")
            doc.append("---")
            doc.append("")
        
        # 总结表格
        doc.append("## 能力对比表")
        doc.append("")
        doc.append(DocumentationGenerator._generate_comparison_table(plugin_manager))
        
        return "\n".join(doc)
    
    @staticmethod
    def _generate_features_section(capability: Capability) -> str:
        """生成功能列表"""
        features = []
        if capability.supports_candlesticks:
            features.append("- ✅ K线数据 (OHLCV)")
        else:
            features.append("- ❌ K线数据")
        
        if capability.supports_ticker:
            features.append("- ✅ 行情数据 (Ticker)")
        else:
            features.append("- ❌ 行情数据")
        
        if capability.supports_funding_rate:
            features.append("- ✅ 资金费率 (Funding Rate)")
        else:
            features.append("- ❌ 资金费率")
        
        if capability.supports_contract_basis:
            features.append("- ✅ 合约基差 (Basis)")
        else:
            features.append("- ❌ 合约基差")
        
        if capability.supports_real_time:
            features.append("- ✅ 实时数据")
        
        if capability.supports_websocket:
            features.append("- ✅ WebSocket")
        
        return "\n".join(features)
    
    @staticmethod
    def _generate_comparison_table(plugin_manager: PluginManager) -> str:
        """生成能力对比表"""
        plugins = plugin_manager.get_all_plugins()
        
        if not plugins:
            return "*没有已注册的插件*"
        
        # 构建表头
        lines = []
        lines.append("| 插件 | K线 | Ticker | 粒度数 | 速率限制 | 状态 |")
        lines.append("|------|-----|--------|--------|---------|------|")
        
        # 构建行
        for name, plugin in plugins.items():
            capability = plugin.get_capability()
            metadata = plugin.get_metadata()
            
            candlestick = "✅" if capability.supports_candlesticks else "❌"
            ticker = "✅" if capability.supports_ticker else "❌"
            granularity_count = len(capability.candlestick_granularities) if capability.candlestick_granularities else "∞"
            rate_limit = f"{capability.rate_limit_per_minute}/min" if capability.has_rate_limit and capability.rate_limit_per_minute else "❌"
            status = "✅" if metadata.is_active else "❌"
            
            lines.append(f"| {metadata.display_name} | {candlestick} | {ticker} | {granularity_count} | {rate_limit} | {status} |")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_capabilities_json(plugin_manager: PluginManager) -> Dict:
        """
        生成所有插件能力的 JSON 格式
        
        Returns:
            能力描述字典
        """
        result = {
            'generated_at': datetime.now().isoformat(),
            'plugins': {}
        }
        
        plugins = plugin_manager.get_all_plugins()
        for name, plugin in plugins.items():
            result['plugins'][name] = {
                'metadata': plugin.get_metadata().to_dict(),
                'capability': plugin.get_capability().to_dict(),
            }
        
        return result
