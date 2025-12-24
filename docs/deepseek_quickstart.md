# DeepSeek 快速开始

## 5 分钟快速上手

### 1. 配置 API Key

编辑 `.env` 文件：
```bash
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 2. 安装依赖

```bash
uv pip install openai python-dotenv
```

### 3. 运行示例

```bash
# 运行 DeepSeek 演示
uv run python examples/deepseek_demo.py
```

## 基本使用

### Python API

```python
import os
from dotenv import load_dotenv
from intentgraph.agent import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

# 加载配置
load_dotenv()

# 初始化 DeepSeek
deepseek = DeepSeekProvider(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-coder"  # 代码专用模型
)

# 创建工作流
workflow = CodingAgentWorkflow(
    repo_path=".",
    llm_provider=deepseek,
    enable_cache=True
)

# 实现功能
result = workflow.implement_feature("添加日志功能")
print(f"状态: {result.status}")
print(f"Token: {result.token_usage:,}")
```

### CLI 命令

```bash
# 设置环境变量
export DEEPSEEK_API_KEY="sk-your-key"

# 实现新功能
intentgraph agent-new-feature "添加用户登录" \
  --provider deepseek \
  --model deepseek-coder

# 修改代码
intentgraph agent-modify "User.register" "添加验证" \
  --provider deepseek
```

## 模型选择

| 模型 | 用途 | 示例 |
|------|------|------|
| `deepseek-chat` | 需求分析、设计 | 理解需求、生成方案 |
| `deepseek-coder` | 代码生成、修改 | 写代码、改代码、测试 |

## 完整示例

```python
from pathlib import Path
from intentgraph.agent import (
    CodingAgentWorkflow,
    RequirementAnalyzer,
    CodeGenerator,
    ContextManager,
)
from intentgraph.agent.llm_provider import DeepSeekProvider
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent

# 初始化
agent = EnhancedCodebaseAgent(Path("."))
context_mgr = ContextManager(agent)

# DeepSeek Coder 用于代码生成
deepseek = DeepSeekProvider(
    api_key="sk-your-key",
    model="deepseek-coder"
)

# 需求分析
analyzer = RequirementAnalyzer(agent, deepseek)
analysis = analyzer.analyze_requirement("添加缓存功能")

# 设计方案
design = analyzer.design_solution(analysis)

# 代码生成
generator = CodeGenerator(agent, context_mgr, deepseek)
# ... 生成代码
```

## 性能对比

### vs GPT-4

| 指标 | DeepSeek Coder | GPT-4 |
|------|---------------|-------|
| 代码质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 成本 | $0.14/M | $30/M |
| 速度 | 快 | 中等 |

### Token 消耗

| 任务 | Token | 成本 (DeepSeek) |
|------|-------|----------------|
| 新功能 | ~17KB | $0.0024 |
| 代码修改 | ~6KB | $0.0008 |
| 测试生成 | ~3KB | $0.0004 |

## 常用命令

```bash
# 查看帮助
intentgraph agent-new-feature --help

# 使用 DeepSeek
intentgraph agent-new-feature "需求" --provider deepseek

# 指定模型
intentgraph agent-new-feature "需求" \
  --provider deepseek \
  --model deepseek-coder

# Token 估算
intentgraph agent-estimate "需求"
```

## 故障排除

### API Key 错误
```bash
# 检查 .env 文件
cat .env | grep DEEPSEEK

# 或设置环境变量
export DEEPSEEK_API_KEY="sk-your-key"
```

### 导入错误
```bash
# 安装 openai 包
uv pip install openai
```

### 连接错误
```bash
# 检查网络连接
curl https://api.deepseek.com

# 或使用代理
export HTTP_PROXY="http://proxy:port"
```

## 更多资源

- 📖 [完整指南](deepseek_guide.md)
- 💻 [示例代码](../examples/deepseek_demo.py)
- 🌐 [DeepSeek 官网](https://platform.deepseek.com)
- 📚 [API 文档](https://platform.deepseek.com/docs)

## 下一步

1. ✅ 运行演示程序
2. ✅ 尝试自己的需求
3. ✅ 查看完整文档
4. ✅ 探索高级功能

