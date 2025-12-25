# 在其他项目中使用 IntentGraph AI Agent

## 快速开始

### 1. 安装 IntentGraph

```bash
# 方式 1: 从源码安装（推荐）
cd E:\cll\ai\modelLearn\agentCoder
uv venv
uv pip install -e E:\cll\ai\modelLearn\CodeAgent

cd /path/to/CodeAgent
uv pip install -e .

# 方式 2: 直接安装（如果已发布）
pip install intentgraph
```

### 2. 配置 DeepSeek API

在你的项目根目录创建 `.env` 文件：

```bash
# 在你的项目目录
cd /path/to/your-project

# 创建 .env 文件
cat > .env << EOF
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
EOF
```

### 3. 初始化项目分析

```bash
# 在你的项目目录
cd /path/to/your-project

# 分析代码库（首次使用必须）
intentgraph analyze . --output intentgraph.json
```

## 使用方式

### 方式 1: CLI 命令（推荐）

#### 实现新功能

```bash
# 基本用法
intentgraph agent-new-feature "添加用户登录功能" --provider deepseek --api-key $DEEPSEEK_API_KEY

intentgraph agent-new-feature "" --provider deepseek --api-key $DEEPSEEK_API_KEY

# 完整参数
intentgraph agent-new-feature "添加用户认证，支持邮箱和手机号登录" \
  --repo /path/to/your-project \
  --provider deepseek \
  --model deepseek-coder \
  --api-key $DEEPSEEK_API_KEY \
  --token-budget 30000
```

#### 修改现有代码

```bash
# 修改指定函数
intentgraph agent-modify "User.register" "添加邮箱验证步骤" \
  --provider deepseek \
  --api-key $DEEPSEEK_API_KEY

# 修改类方法
intentgraph agent-modify "DatabaseConnection.connect" "添加连接池支持" \
  --provider deepseek
```

#### Token 估算

```bash
# 估算需求的 Token 消耗
intentgraph agent-estimate "添加缓存功能" \
  --repo /path/to/your-project
```

### 方式 2: Python API

在你的项目中创建脚本：

```python
# my_project/scripts/ai_helper.py
import os
from pathlib import Path
from dotenv import load_dotenv
from intentgraph.agent import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

# 加载配置
load_dotenv()

# 初始化 DeepSeek
deepseek = DeepSeekProvider(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-coder"
)

# 创建工作流
workflow = CodingAgentWorkflow(
    repo_path=Path("."),  # 当前项目目录
    llm_provider=deepseek,
    enable_cache=True
)

# 实现功能
result = workflow.implement_feature(
    "添加用户登录功能，支持邮箱和手机号"
)

# 查看结果
print(f"状态: {result.status}")
print(f"创建文件: {result.files_created}")
print(f"生成测试: {result.tests_generated}")
print(f"Token 使用: {result.token_usage:,}")
```

运行脚本：
```bash
cd /path/to/your-project
python scripts/ai_helper.py
```

## 完整工作流示例

### 场景：为 Web 项目添加用户认证

```bash
# 1. 进入项目目录
cd ~/projects/my-web-app

# 2. 首次使用：分析代码库
intentgraph analyze . --output intentgraph.json

# 3. 估算 Token 消耗
intentgraph agent-estimate "添加用户认证功能，支持 JWT token"

# 4. 实现功能
intentgraph agent-new-feature \
  "添加用户认证功能，包括：
  1. 用户注册（邮箱+密码）
  2. 用户登录（返回 JWT token）
  3. Token 验证中间件
  4. 密码加密存储" \
  --provider deepseek \
  --model deepseek-coder \
  --api-key $DEEPSEEK_API_KEY

# 5. 查看生成的文件
ls -la auth/  # 查看新创建的认证模块
ls -la tests/ # 查看生成的测试

# 6. 如需修改某个函数
intentgraph agent-modify "AuthService.login" \
  "添加登录失败次数限制，5次后锁定账户" \
  --provider deepseek
```

## 实际项目集成

### 项目结构示例

```
your-project/
├── .env                    # DeepSeek API 配置
├── intentgraph.json        # 代码分析结果（自动生成）
├── src/
│   ├── auth/              # AI 生成的认证模块
│   ├── models/
│   └── utils/
├── tests/
│   └── test_auth.py       # AI 生成的测试
└── scripts/
    └── ai_helper.py       # 自定义 AI 辅助脚本
```

### 集成到开发流程

#### 1. 需求分析阶段

```bash
# 分析需求复杂度和 Token 消耗
intentgraph agent-estimate "你的需求描述"
```

#### 2. 代码实现阶段

```bash
# 使用 AI 生成初始代码
intentgraph agent-new-feature "需求描述" --provider deepseek
```

#### 3. 代码审查阶段

```bash
# 修改和优化生成的代码
intentgraph agent-modify "ClassName.method" "优化建议" --provider deepseek
```

#### 4. 测试阶段

生成的测试文件会自动创建在 `tests/` 目录，可以直接运行：

```bash
pytest tests/test_*.py
```

## 高级用法

### 1. 批量处理需求

```python
# batch_implement.py
from intentgraph.agent import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

deepseek = DeepSeekProvider(api_key="sk-xxx", model="deepseek-coder")
workflow = CodingAgentWorkflow(".", deepseek, enable_cache=True)

requirements = [
    "添加用户注册功能",
    "添加用户登录功能",
    "添加密码重置功能",
]

for req in requirements:
    print(f"\n处理: {req}")
    result = workflow.implement_feature(req)
    print(f"状态: {result.status}, Token: {result.token_usage}")
```

### 2. 自定义工作流

```python
# custom_workflow.py
from intentgraph.agent import (
    RequirementAnalyzer,
    CodeGenerator,
    ContextManager,
)
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from intentgraph.agent.llm_provider import DeepSeekProvider

# 初始化组件
agent = EnhancedCodebaseAgent(".")
context_mgr = ContextManager(agent)
deepseek = DeepSeekProvider(api_key="sk-xxx", model="deepseek-coder")

# 需求分析
analyzer = RequirementAnalyzer(agent, deepseek)
analysis = analyzer.analyze_requirement("你的需求")
print(f"需求类型: {analysis.requirement_type}")
print(f"复杂度: {analysis.estimated_complexity}")

# 设计方案
design = analyzer.design_solution(analysis)
print(f"技术方案: {design.technical_approach}")

# 任务分解
tasks = analyzer.decompose_tasks(design)
print(f"任务数: {len(tasks)}")

# 代码生成
generator = CodeGenerator(agent, context_mgr, deepseek)
for task in tasks:
    impl = generator.implement_new_feature(design, task)
    print(f"生成: {impl.file_path}")
```

### 3. 集成到 CI/CD

```yaml
# .github/workflows/ai-code-review.yml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install IntentGraph
        run: pip install intentgraph
      
      - name: Analyze Changes
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          intentgraph analyze . --output analysis.json
          # 可以添加自定义分析脚本
```

## 最佳实践

### 1. 首次使用

```bash
# 在项目根目录
cd /path/to/your-project

# 分析代码库
intentgraph analyze . --output intentgraph.json

# 测试 API 连接
intentgraph agent-estimate "测试需求"
```

### 2. 需求描述技巧

**好的需求描述**：
```bash
intentgraph agent-new-feature \
  "添加用户认证功能：
  1. 实现 JWT token 生成和验证
  2. 支持邮箱+密码登录
  3. 密码使用 bcrypt 加密
  4. Token 有效期 24 小时
  5. 提供登录、登出、刷新 token 接口" \
  --provider deepseek
```

**避免模糊描述**：
```bash
# ❌ 不好
intentgraph agent-new-feature "添加登录" --provider deepseek

# ✅ 好
intentgraph agent-new-feature "添加用户登录功能，使用 JWT 认证" --provider deepseek
```

### 3. 缓存利用

```python
# 启用缓存可以大幅提升重复需求的处理速度
workflow = CodingAgentWorkflow(
    repo_path=".",
    llm_provider=deepseek,
    enable_cache=True  # 重要！
)
```

### 4. Token 预算管理

```bash
# 先估算
intentgraph agent-estimate "复杂需求"

# 如果超出预算，分解需求
intentgraph agent-new-feature "需求第一部分" --token-budget 15000
intentgraph agent-new-feature "需求第二部分" --token-budget 15000
```

## 常见问题

### Q: 如何在多个项目中使用？

A: 每个项目独立配置：
```bash
# 项目 A
cd ~/projects/project-a
intentgraph analyze . --output intentgraph.json
intentgraph agent-new-feature "需求" --provider deepseek

# 项目 B
cd ~/projects/project-b
intentgraph analyze . --output intentgraph.json
intentgraph agent-new-feature "需求" --provider deepseek
```

### Q: 生成的代码需要修改吗？

A: 建议审查后使用：
1. 检查生成的代码逻辑
2. 运行生成的测试
3. 根据需要微调
4. 提交代码审查

### Q: 如何处理大型需求？

A: 分解为小需求：
```bash
# 分解大需求
intentgraph agent-new-feature "用户模块 - 注册功能" --provider deepseek
intentgraph agent-new-feature "用户模块 - 登录功能" --provider deepseek
intentgraph agent-new-feature "用户模块 - 权限管理" --provider deepseek
```

### Q: 支持哪些编程语言？

A: 目前主要支持 Python，其他语言通过 IntentGraph 的解析器支持。

## 完整示例项目

查看示例项目：
```bash
# 克隆示例
git clone https://github.com/your-org/intentgraph-examples
cd intentgraph-examples/web-app-example

# 查看如何使用
cat README.md
```

## 获取帮助

```bash
# 查看命令帮助
intentgraph --help
intentgraph agent-new-feature --help
intentgraph agent-modify --help

# 查看文档
cat docs/deepseek_guide.md
cat docs/deepseek_quickstart.md
```

## 总结

使用 IntentGraph + DeepSeek 在其他项目中的步骤：

1. ✅ 安装 IntentGraph
2. ✅ 配置 DeepSeek API Key
3. ✅ 分析目标项目代码库
4. ✅ 使用 CLI 命令或 Python API
5. ✅ 审查和测试生成的代码
6. ✅ 集成到开发流程

**核心命令**：
```bash
intentgraph analyze .
intentgraph agent-new-feature "需求" --provider deepseek
intentgraph agent-modify "Target" "修改" --provider deepseek
```

