# Phase 3 & 4 实现文档

## 概述

本文档介绍 Phase 3（需求理解模块）和 Phase 4（代码生成模块）的实现和使用方法。

## 核心模块

### 1. RequirementAnalyzer（需求分析器）

负责理解和分解需求，包括：
- 需求解析和分类
- 技术方案设计
- 任务分解

**主要方法：**

```python
from intentgraph.agent import RequirementAnalyzer

analyzer = RequirementAnalyzer(agent, llm_provider)

# 1. 分析需求
analysis = analyzer.analyze_requirement("添加用户登录功能")
# 返回: RequirementAnalysis（需求类型、影响范围、关键实体等）

# 2. 设计方案
design = analyzer.design_solution(analysis)
# 返回: DesignPlan（技术方案、组件设计、实现步骤等）

# 3. 分解任务
tasks = analyzer.decompose_tasks(design)
# 返回: List[Task]（可执行任务列表，包含依赖关系）
```

### 2. CodeGenerator（代码生成器）

负责生成和修改代码，包括：
- 新功能实现
- 存量代码修改
- 测试用例生成

**主要方法：**

```python
from intentgraph.agent import CodeGenerator

generator = CodeGenerator(agent, context_manager, llm_provider)

# 1. 实现新功能
implementation = generator.implement_new_feature(design, task)
# 返回: CodeImplementation（生成的代码、集成说明等）

# 2. 修改现有代码
modification = generator.modify_existing_code(
    target="User.register",
    modification_desc="添加邮箱验证"
)
# 返回: CodeModification（修改后的代码、迁移指南等）

# 3. 生成测试
test_suite = generator.generate_tests(implementation)
# 返回: TestSuite（测试代码、测试用例说明等）
```

### 3. ContextManager（上下文管理器）

已在 Phase 2 实现，提供精准上下文提取：

```python
from intentgraph.agent import ContextManager

context_mgr = ContextManager(agent)

# 提取精准上下文
context = context_mgr.extract_precise_context(
    target="function_name",
    token_budget=5000
)

# 分析影响
impact = context_mgr.analyze_impact(code_change)
```

## 完整工作流示例

### 场景 1: 新增功能

```python
from pathlib import Path
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from intentgraph.agent import (
    ContextManager,
    RequirementAnalyzer,
    CodeGenerator,
)
from intentgraph.agent.llm_provider import OpenAIProvider

# 初始化
repo_path = Path("./my_project")
agent = EnhancedCodebaseAgent(repo_path)
context_manager = ContextManager(agent)

# 配置 LLM（可选，不配置则使用启发式方法）
llm_provider = OpenAIProvider(api_key="your-api-key", model="gpt-4")

analyzer = RequirementAnalyzer(agent, llm_provider)
generator = CodeGenerator(agent, context_manager, llm_provider)

# 步骤 1: 分析需求
requirement = "添加用户登录功能，支持邮箱和手机号登录"
analysis = analyzer.analyze_requirement(requirement)

print(f"需求类型: {analysis.requirement_type}")
print(f"影响范围: {analysis.affected_scope}")
print(f"复杂度: {analysis.estimated_complexity}")

# 步骤 2: 设计方案
design = analyzer.design_solution(analysis)

print(f"技术方案: {design.technical_approach}")
print(f"新组件: {design.new_components}")
print(f"实现步骤: {design.implementation_steps}")

# 步骤 3: 分解任务
tasks = analyzer.decompose_tasks(design)

print(f"任务数量: {len(tasks)}")
for task in tasks:
    print(f"  - {task.description} (优先级: {task.priority})")

# 步骤 4: 实现每个任务
for task in tasks:
    implementation = generator.implement_new_feature(design, task)
    
    print(f"\n生成文件: {implementation.file_path}")
    print(f"代码:\n{implementation.generated_code}")
    
    # 步骤 5: 生成测试
    test_suite = generator.generate_tests(implementation)
    print(f"\n测试文件: {test_suite.test_file_path}")
    print(f"测试代码:\n{test_suite.test_code}")
```

### 场景 2: 修改存量代码

```python
# 步骤 1: 提取上下文
target = "User.register"
context = context_manager.extract_precise_context(
    target=target,
    token_budget=5000
)

print(f"上下文层级: {context.layers_included}")
print(f"Token 估算: {context.token_estimate}")

# 步骤 2: 分析影响
from intentgraph.agent import CodeChange

change = CodeChange(
    target_symbol=target,
    target_file=context.target_code["file"],
    change_type="signature_change",
    description="添加邮箱验证参数",
    line_range=(10, 30)
)

impact = context_manager.analyze_impact(change)
print(f"风险等级: {impact.risk_level}")
print(f"直接调用者: {len(impact.direct_callers)}")
print(f"受影响测试: {impact.affected_tests}")

# 步骤 3: 生成修改
modification = generator.modify_existing_code(
    target=target,
    modification_desc="添加邮箱验证步骤",
    context=context
)

print(f"\n修改说明: {modification.change_description}")
print(f"修改后代码:\n{modification.modified_code}")
print(f"\n迁移指南:")
for step in modification.migration_guide:
    print(f"  - {step}")
```

## LLM Provider 配置

### OpenAI

```python
from intentgraph.agent.llm_provider import OpenAIProvider

llm = OpenAIProvider(
    api_key="your-openai-api-key",
    model="gpt-4",  # 或 "gpt-3.5-turbo"
    temperature=0.7
)
```

### Anthropic (Claude)

```python
from intentgraph.agent.llm_provider import AnthropicProvider

llm = AnthropicProvider(
    api_key="your-anthropic-api-key",
    model="claude-3-sonnet-20240229",
    temperature=0.7
)
```

### 不使用 LLM（启发式方法）

```python
# 传入 None 或不传入 llm_provider
analyzer = RequirementAnalyzer(agent, llm_provider=None)
generator = CodeGenerator(agent, context_manager, llm_provider=None)

# 将使用基于规则的启发式方法
```

## Token 消耗估算

根据设计文档，每个操作的 Token 消耗：

| 操作 | Token 消耗 | 说明 |
|------|-----------|------|
| analyze_requirement | ~2KB | 需求解析 |
| design_solution | ~5KB | 方案设计 |
| decompose_tasks | ~3KB | 任务分解 |
| implement_new_feature | ~4KB | 代码生成 |
| modify_existing_code | ~6KB | 代码修改 |
| generate_tests | ~3KB | 测试生成 |

**完整需求实现**: 约 25-30KB Token

## 运行示例

```bash
# 运行完整演示
python examples/phase3_phase4_demo.py

# 运行测试
pytest tests/test_phase3_phase4.py -v
```

## 核心优势

1. **Token 高效**: 通过精准上下文提取，节省 90% Token 消耗
2. **上下文精准**: 基于调用链和依赖图，提供 95%+ 精准度
3. **架构理解**: 自动理解代码库架构和模块边界
4. **需求转换**: 自动将需求转换为技术方案和可执行任务
5. **代码生成**: 生成符合现有架构和代码风格的代码

## 注意事项

1. 首次使用需要完整分析代码库（运行 `intentgraph analyze`）
2. LLM Provider 需要有效的 API Key
3. 不使用 LLM 时，功能会降级为基于规则的启发式方法
4. 生成的代码建议人工审查后再使用
5. 大型代码库建议使用更大的 token_budget

## 扩展开发

### 自定义 LLM Provider

```python
from intentgraph.agent.llm_provider import LLMProvider

class CustomLLMProvider(LLMProvider):
    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        # 实现你的 LLM 调用逻辑
        pass
    
    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        # 实现你的 LLM 调用逻辑
        pass
```

### 自定义 Prompt 模板

可以继承 RequirementAnalyzer 或 CodeGenerator 并重写 `_build_*_prompt` 方法来自定义 Prompt。

