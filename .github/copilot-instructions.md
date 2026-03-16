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

## 2. 隐私与安全规则

### 2.1 禁止在项目文件中出现用户私有域名
- 任何代码、配置、文档、注释、示例命令中，**禁止出现用户的私有域名或 IP**。
- 所有需要展示域名的地方，统一使用 `example.com` 作为占位符。
- 如果发现已有文件包含私有域名，必须立即替换为 `example.com`，并告知用户已清理。

## 3. 必读上下文
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

## 5. 配置与环境变量
- 本地配置统一使用 `.env`
- 必须维护 `.env.example` 作为变量模板
- CI/CD（GitHub Actions）变量与 Secrets 以 `.env.example` 为基准对齐
- `.env.example` 中用于 CI/CD 的变量，必须由用户写入 GitHub Actions 的 Variables 或 Secrets

## 5.1 自动化（GitHub Actions）
- Action 触发条件：仅在打 tag 时触发（`push tags`）
- 非 tag 的普通分支推送，不作为发布触发条件
- 涉及密钥或敏感配置时：
    - 敏感值写入 GitHub Actions Secrets
    - 非敏感配置写入 GitHub Actions Variables
- 每次新增或修改 `.env.example` 变量后，需提醒用户同步更新对应的 Actions Variables/Secrets

## 6. 测试与质量门槛

### 单元测试
- 目标覆盖率：`>= 80%`
- Python 测试命名：`tests/test_*.py`
- 使用 fixtures 管理测试数据
- 对外部依赖进行 Mock

### 集成测试
- 使用独立测试环境（测试库/测试桶）
- 覆盖关键业务流程与错误分支

### 常用命令
```bash
# Python
black src/
ruff check src/
pytest
pytest --cov=src --cov-report=html

# Node.js
npm run lint
npm test
```

## 7. 提交与发布规范

### Commit Message
遵循 Conventional Commits：
```text
<type>: <description>

[optional body]

[optional footer]
```

常用 `type`：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`perf`

### 发布流程
- 仅使用 tag 触发发布，版本格式：`vX.Y.Z`（如 `v1.2.0`）
- Release Notes 包含：主要变更、兼容性影响、升级说明

### 版本号升级规则
- `X`（主版本号）：不兼容变更
    - 设计架构重大调整且影响旧版本使用方式
    - API 不兼容修改、删除旧接口或改变旧行为
- `Y`（次版本号）：向后兼容的新功能
    - 新增 API、新增功能，但不影响旧版本能力
    - 对现有功能进行重构，但对外行为保持兼容
- `Z`（修订号）：向后兼容的问题修复
    - 修复 bug、UI 调整、性能优化
    - 内部实现优化且不改变对外行为

示例（当前版本 `v2.3.4`）：
- 不兼容改动 -> `v3.0.0`
- 兼容性新增 -> `v2.4.0`
- 兼容性修复 -> `v2.3.5`

### 发布执行流程（严格执行）
1. 确认本次发布 Todo 已全部完成。
2. 推断下一版本号（必须执行）：
    - 先读取当前最新 tag（如 `v0.2.4`）。
    - 按“版本号升级规则”判断本次变更属于 `X/Y/Z`。
    - 生成候选版本号并向用户确认（例如：`v0.3.0`）。
3. 运行单元测试并确保通过。
4. 提示用户进行本地测试，并等待用户回复。
5. 用户确认成功后，创建并推送 tag（Action 由打 tag 触发）。
6. 检查 GitHub Actions 执行结果并反馈状态。

### 版本号推断流程（发布前必做）
1. 获取当前最新版本：`git tag --sort=-v:refname | head -1`
2. 识别本次变更类型：
    - 存在不兼容行为/API 变更 -> `X`
    - 仅新增且向后兼容功能 -> `Y`
    - 仅修复/优化且向后兼容 -> `Z`
3. 计算目标版本：
    - `X`: `v(MAJOR+1).0.0`
    - `Y`: `vMAJOR.(MINOR+1).0`
    - `Z`: `vMAJOR.MINOR.(PATCH+1)`
4. 与用户确认版本号后再打 tag。

### 发布前检查清单（建议逐项确认）
1. 版本号检查：
    - 已完成“版本号推断流程”，并有明确的升级依据（X/Y/Z）。
    - 新 tag 符合 `vX.Y.Z` 语义化版本规范。
    - 新版本号大于当前最新已发布版本。
2. 变更范围检查：
    - 本次发布内容与 Todo 一致，无未确认的临时改动。
    - 已确认无敏感信息（密钥、Token、密码）进入仓库。
3. 质量门槛检查：
    - 单元测试全部通过。
    - 关键路径完成本地验证并由用户确认。
4. 发布说明检查：
    - Release Notes 包含主要变更、兼容性影响、升级说明。
5. 回滚预案检查：
    - 明确回滚策略（回滚 tag、回退版本、紧急修复分支）。
    - 出现故障时有可执行的应急负责人或处理路径。

推荐命令示例：
```bash
# 确认测试
pytest

# 打 tag 并推送
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 8. 输出要求（Copilot 回复风格）
- 先给结论，再给关键改动与验证结果
- 涉及多文件修改时，明确文件清单
- 若无法执行某项操作，需说明原因与替代方案
- 一次只推进一个主任务，超范围需求建议拆分

## 9. 开发环境约定
- Python 版本管理：`pyenv`
- Python 虚拟环境：`venv` 或 `uv`
- Node.js 版本管理：`nvm`
- 前端框架：`Vue.js`

## 10. 项目初始化与数据库迁移

### 10.1 初始化原则
- 新项目初始化时，先确认 Python 与 Node.js 版本，再安装依赖。
- 初始化完成后，必须先配置环境变量，再执行数据库迁移与服务启动。

### 10.2 Python 初始化（pyenv + venv/uv）
```bash
# 选择并固定 Python 版本
pyenv install 3.11.9
pyenv local 3.11.9

# 方式一：venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 方式二：uv（如项目使用 uv）
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 10.3 Node.js 初始化（nvm）
```bash
# 使用项目约定版本（或 .nvmrc）
nvm install
nvm use

# 安装依赖
npm ci
```

### 10.4 env 变量引入
- 复制 `.env.example` 生成本地 `.env`，禁止提交 `.env`。
- 应用启动前必须加载 `.env` 中变量；缺失关键变量时应直接报错并给出缺失项。
- 新增变量时同步更新：
    - `.env.example`
    - 项目文档（变量说明、默认值/示例值）
    - GitHub Actions Variables/Secrets（由用户写入）

推荐命令示例：
```bash
cp .env.example .env
```

### 10.5 数据库迁移流程
- 初始化阶段必须执行数据库迁移，确保本地结构与目标版本一致。
- 迁移脚本需可重复执行，避免不可逆破坏性变更。
- 迁移顺序：
    1. 拉取最新代码
    2. 配置 `.env`
    3. 执行迁移
    4. 执行迁移后验证（表结构/关键数据）

### 10.6 初始化完成验收
- 依赖安装成功（Python/Node）
- `.env` 配置完整且应用可读取
- 数据库迁移成功
- 单元测试可执行且通过

---
详细需求与实现计划以 `.github/PROJECT.md` 为准。
