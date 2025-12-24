# DeepSeek LLM Provider 使用指南

## 概述

DeepSeek 是一个强大的 AI 模型提供商，提供了专门优化的代码生成模型。本指南介绍如何在 IntentGraph AI 编码 Agent 中使用 DeepSeek API。

## 特点

### DeepSeek 优势
- 🚀 **高性能**: 专门优化的代码生成能力
- 💰 **性价比高**: 相比 GPT-4 更经济实惠
- 🔧 **代码专用模型**: DeepSeek Coder 专为代码任务优化
- 🌐 **OpenAI 兼容**: API 接口兼容 OpenAI 格式

### 可用模型
1. **deepseek-chat**: 通用对话模型，适合需求分析和设计
2. **deepseek-coder**: 代码专用模型，适合代码生成和修改

## 配置

### 1. 获取 API Key

访问 [DeepSeek Platform](https://platform.deepseek.com) 注册并获取 API Key。

### 2. 配置环境变量

在项目根目录创建或编辑 `.env` 文件：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 安装依赖

```bash
# 安装 openai 包（DeepSeek API 兼容 OpenAI）
uv pip install openai python-dotenv
```

## 使用方法

### 方法 1: Python API

#### 基本使用

```python
from intentgraph.agent.llm_provider import DeepSeekProvider

# 初始化 DeepSeek Provider
deepseek = DeepSeekProvider(
    api_key="sk-your-api-key",
    base_url="https://api.deepseek.com",
    model="deepseek-coder"  # 或 "deepseek-chat"
)

# 发送对话请求
response = deepseek.chat(
    prompt="请写一个 Python 函数实现快速排序",
    max_tokens=500,
    temperature=0.7
)

print(response)
```

#### 从环境变量加载

```python
import os
from dotenv import load_dotenv
from intentgraph.agent.llm_provider import DeepSeekProvider

# 加载 .env 文件
load_dotenv()

# 从环境变量获取配置
deepseek = DeepSeekProvider(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    model="deepseek-coder"
)
```

#### 与需求分析器集成

```python
from pathlib import Path
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from intentgraph.agent import RequirementAnalyzer
from intentgraph.agent.llm_provider import DeepSeekProvider

# 初始化
agent = EnhancedCodebaseAgent(Path("."))
deepseek = DeepSeekProvider(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-coder"
)

# 创建分析器
analyzer = RequirementAnalyzer(agent, deepseek)

# 分析需求
analysis = analyzer.analyze_requirement("添加用户认证功能")
print(f"需求类型: {analysis.requirement_type}")
print(f"复杂度: {analysis.estimated_complexity}")

# 设计方案
design = analyzer.design_solution(analysis)
print(f"技术方案: {design.technical_approach}")
```

#### 完整工作流

```python
from pathlib import Path
from intentgraph.agent import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

# 初始化 DeepSeek
deepseek = DeepSeekProvider(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-coder"
)

# 创建工作流
workflow = CodingAgentWorkflow(
    repo_path=Path("./project"),
    llm_provider=deepseek,
    enable_cache=True
)

# 实现功能
result = workflow.implement_feature("添加日志记录功能")

# 查看结果
print(f"状态: {result.status}")
print(f"Token 使用: {result.token_usage:,}")
print(f"文件创建: {result.files_created}")
```

### 方法 2: CLI 命令

```bash
# 设置环境变量
export DEEPSEEK_API_KEY="sk-your-api-key"

# 实现新功能
intentgraph agent-new-feature "添加用户登录功能" \
  --api-key $DEEPSEEK_API_KEY \
  --model deepseek-coder

# 修改代码
intentgraph agent-modify "User.register" "添加邮箱验证" \
  --api-key $DEEPSEEK_API_KEY

# Token 估算
intentgraph agent-estimate "添加缓存功能"
```

## 模型选择建议

### DeepSeek Chat
**适用场景**:
- 需求分析和理解
- 技术方案设计
- 文档生成
- 通用对话

**示例**:
```python
deepseek_chat = DeepSeekProvider(
    api_key=api_key,
    model="deepseek-chat"
)

# 用于需求分析
analyzer = RequirementAnalyzer(agent, deepseek_chat)
```

### DeepSeek Coder
**适用场景**:
- 代码生成
- 代码修改
- 测试生成
- 代码审查

**示例**:
```python
deepseek_coder = DeepSeekProvider(
    api_key=api_key,
    model="deepseek-coder"
)

# 用于代码生成
generator = CodeGenerator(agent, context_manager, deepseek_coder)
```

## 性能对比

### Token 消耗

| 操作 | DeepSeek Coder | GPT-4 | 节省 |
|------|---------------|-------|------|
| 需求分析 | ~2KB | ~2KB | 相同 |
| 代码生成 | ~4KB | ~4KB | 相同 |
| 测试生成 | ~3KB | ~3KB | 相同 |

### 成本对比

| 模型 | 输入价格 | 输出价格 | 相对 GPT-4 |
|------|---------|---------|-----------|
| DeepSeek Coder | $0.14/M tokens | $0.28/M tokens | ~10x 便宜 |
| GPT-4 | $30/M tokens | $60/M tokens | 基准 |

### 质量对比

| 任务类型 | DeepSeek Coder | GPT-4 |
|---------|---------------|-------|
| 代码生成 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 代码理解 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 需求分析 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 测试生成 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 运行示例

### 运行演示程序

```bash
# 确保已设置 .env 文件
cat .env
# DEEPSEEK_API_KEY=sk-your-key
# DEEPSEEK_BASE_URL=https://api.deepseek.com

# 运行 DeepSeek 演示
uv run python examples/deepseek_demo.py
```

### 演示内容

演示程序包含 5 个示例：

1. **基本使用**: DeepSeek Provider 初始化和简单对话
2. **需求分析**: 与 RequirementAnalyzer 集成
3. **代码生成**: 与 CodeGenerator 集成
4. **完整工作流**: 端到端功能实现
5. **模型对比**: Chat vs Coder 模型对比

## 最佳实践

### 1. 模型选择

```python
# 需求分析阶段：使用 Chat 模型
analyzer = RequirementAnalyzer(
    agent,
    DeepSeekProvider(api_key=key, model="deepseek-chat")
)

# 代码生成阶段：使用 Coder 模型
generator = CodeGenerator(
    agent,
    context_manager,
    DeepSeekProvider(api_key=key, model="deepseek-coder")
)
```

### 2. 缓存使用

```python
# 启用缓存以节省 API 调用
workflow = CodingAgentWorkflow(
    repo_path=Path("."),
    llm_provider=deepseek,
    enable_cache=True  # 重要！
)
```

### 3. Token 优化

```python
# 先估算 Token 使用
estimate = workflow.get_token_usage_estimate(requirement)
print(f"预计 Token: {estimate['total']:,}")

# 如果超出预算，考虑分解需求
if estimate['total'] > 20000:
    print("需求过于复杂，建议分解")
```

### 4. 错误处理

```python
try:
    result = workflow.implement_feature(requirement)
    if result.status == WorkflowStatus.FAILED:
        print(f"失败原因: {result.errors}")
except Exception as e:
    print(f"API 调用失败: {e}")
```

## 常见问题

### Q: DeepSeek API Key 在哪里获取？
A: 访问 https://platform.deepseek.com 注册账号并获取 API Key。

### Q: DeepSeek 支持哪些模型？
A: 主要支持 `deepseek-chat` (通用) 和 `deepseek-coder` (代码专用)。

### Q: 如何切换不同的 LLM 提供者？
A: 只需更换 `llm_provider` 参数：
```python
# 使用 DeepSeek
workflow = CodingAgentWorkflow(repo_path, DeepSeekProvider(...))

# 使用 OpenAI
workflow = CodingAgentWorkflow(repo_path, OpenAIProvider(...))
```

### Q: DeepSeek 的 API 限制是什么？
A: 具体限制请查看 DeepSeek 官方文档。通常包括：
- 每分钟请求数限制
- 每天 Token 限制
- 单次请求最大 Token 数

### Q: 如何监控 API 使用情况？
A: 使用内置的日志功能：
```python
from intentgraph.agent import get_logger

logger = get_logger()
metrics = logger.get_metrics_summary()
print(f"总 Token: {metrics['total_tokens']:,}")
```

## 参考资源

- 📖 [DeepSeek 官方文档](https://platform.deepseek.com/docs)
- 💻 [示例代码](../examples/deepseek_demo.py)
- 🔧 [LLM Provider 源码](../src/intentgraph/agent/llm_provider.py)
- 📊 [性能对比](./complete_system_summary.md)

## 总结

DeepSeek 提供了高性价比的代码生成能力，特别适合：
- ✅ 预算有限的项目
- ✅ 大量代码生成需求
- ✅ 需要专业代码模型的场景

通过 IntentGraph 的统一接口，可以轻松切换不同的 LLM 提供者，选择最适合您需求的模型。

