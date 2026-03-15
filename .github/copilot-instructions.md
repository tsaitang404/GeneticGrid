# GitHub Copilot 工作指导

## 0. 启动确认
当本文件被成功载入时，首句回复使用：
`已经载入 GitHub Copilot 工作指导，将严格按照指导进行工作。`

## 1. 指令优先级
当规则冲突时，按以下顺序执行：
1. 系统指令
2. 平台/工具指令
3. 本文件
4. 用户当前需求

若出现冲突，先说明冲突点，再给出可执行替代方案。

## 2. 必读上下文
编码前优先阅读：
- `.github/PROJECT.md`：功能目标、范围、里程碑
- `docs/api/*.md`：API 规范（默认遵循 RESTful，除非文档另有说明）
- `docs/database/*.md`：数据模型与字段约束

## 3. 工作流程（必须执行）
1. 明确需求与边界
2. 评估影响文件与依赖
3. 给出最小可行改动方案
4. 实现代码并补充必要测试
5. 运行检查并反馈结果
6. 更新文档与示例（如有 API 或行为变化）

### 3.1 功能迭代流程（严格执行）
1. 阅读代码并观察当前实现，明确本次迭代点。
2. 输出 Todo 清单（按优先级列出）。
3. 生成代码并完成本次迭代。
4. 运行单元测试。
5. 单元测试通过后，提示用户进行本地测试。
6. 等待用户回应。
7. 若用户反馈本地测试不成功：撤销本次迭代修改并重新生成方案与代码。

约束：
- 一次只处理一个主要迭代目标，避免并行推进多个复杂需求。
- 撤销范围仅限本次迭代产生的修改，不影响用户已有改动。

## 4. 代码规范

### Python
- 遵循 PEP 8，最大行长 100
- 必须使用类型注解
- 函数/类使用 Google 风格 docstring
- 使用 `black` 格式化，`ruff` 检查

示例：
```python
from typing import Any


def process_data(items: list[str], limit: int = 10) -> dict[str, Any]:
    """处理数据项并返回结果。

    Args:
        items: 要处理的字符串列表。
        limit: 最大处理数量。

    Returns:
        处理结果字典。

    Raises:
        ValueError: 当 items 为空时抛出。
    """
    if not items:
        raise ValueError("items 不能为空")
    return {"count": min(len(items), limit)}
```

### JavaScript / TypeScript
- 使用 ESLint 推荐规则
- 优先 `const`，其次 `let`，避免 `var`
- 优先 `async/await`，避免链式 `then/catch` 滥用
- 文件命名使用 `kebab-case`

### 通用
- 命名需语义清晰，避免缩写堆叠
- 注释优先解释“为什么”，非必要不写“是什么”
- 必须有错误处理，日志信息应可定位问题
- 禁止硬编码密钥、Token、密码

## 测试要求

### 单元测试
- 覆盖率目标: 80%+
- 测试文件命名: `tests/test_*.py`
- 使用 pytest fixtures 管理测试数据
- Mock 外部依赖

### 集成测试
- 使用测试数据库和存储桶
- 测试完整的 API 流程
- 验证错误处理和边界情况

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_d1_manager.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 提交规范

### Commit Message 格式

遵循 Conventional Commits 规范:

```
<类型>: <描述>

[可选的正文]

[可选的脚注]
```

### 类型 (Type)
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构（不是新功能也不是修复）
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化

### 示例

```bash
# 新功能
feat: 添加批量查询支持

实现批量查询功能以提高性能，支持一次查询多个表。

Closes #123

# Bug 修复
fix: 修复文件上传时的编码问题

修正了非 ASCII 文件名上传失败的问题。

# 文档更新
docs: 更新 API 使用示例

添加了 R2 上传的完整代码示例。

# 重构
refactor: 简化路由匹配逻辑

使用正则表达式替代字符串匹配，提高可维护性。
```

## 进度追踪

当前阶段: **环境配置和项目初始化**

- [x] 验证项目需求
- [x] 创建项目文档结构
- [ ] 安装必要的依赖
- [ ] 配置开发工具
- [ ] 实现核心功能模块
- [ ] 编写单元测试
- [ ] 集成测试验证
- [ ] 部署配置
- [ ] 文档完善

参考 `.github/PROJECT.md` 查看详细的功能需求和实现计划。
