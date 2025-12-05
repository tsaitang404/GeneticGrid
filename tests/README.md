# 测试脚本目录

本目录包含用于验证插件系统的测试脚本（已归档）。

## 测试脚本

### verify_plugin_system.py
- **用途**: 完整验证插件系统功能
- **功能**: 
  - 验证插件管理器
  - 测试统一服务
  - 验证数据获取
- **状态**: ✅ 已验证通过

### test_plugin_proxy.py
- **用途**: 测试插件代理配置
- **功能**:
  - 检查代理可用性
  - 验证代理注入
  - 测试各插件代理状态
- **状态**: ✅ 已验证通过

## 主要测试工具

位于项目根目录：

### test_plugin_network.py
- **用途**: 网络可达性测试（活跃使用）
- **功能**:
  - 测试所有插件网络连接
  - 验证数据获取
  - 诊断代理问题

## 运行测试

```bash
# 运行网络测试（推荐）
python test_plugin_network.py

# 运行归档的验证测试
python tests/verify_plugin_system.py
python tests/test_plugin_proxy.py
```

## 测试结果

所有插件已通过验证：
- ✅ OKX 交易所 (需要代理)
- ✅ 币安交易所
- ✅ Coinbase 交易所
- ✅ CoinGecko 聚合器
- ✅ TradingView 制图工具
