# EnhancedCodeGenerator 使用说明

## 概述

EnhancedCodeGenerator 是对原 CodeGenerator 的完全重写，使用直接文件操作替代 JSON 解析方式，提供更可靠的代码生成和文件管理。

## 主要改进

### 1. 不再使用 JSON 解析

**原来的方式（有问题）：**
```python
# 原 CodeGenerator 要求 LLM 返回 JSON 格式
response = llm.call(prompt)
data = json.loads(response)  # 经常失败！
code = data['code']
```

**新的方式（更可靠）：**
```python
# EnhancedCodeGenerator 直接提取代码
response = llm.call(prompt)
code = extract_code_from_response(response)  # 从 markdown 代码块提取
```

### 2. 集成文件操作

**原来的方式：**
```python
# 生成代码
impl = generator.implement_new_feature(design, task)
# 需要手动写入文件
with open(impl.file_path, 'w') as f:
    f.write(impl.generated_code)
```

**新的方式：**
```python
# 生成并自动写入文件
impl = generator.implement_new_feature(design, task)
# 文件已经写入，包含验证和错误处理
```

### 3. 自动语法验证

```python
# 生成代码前自动验证
validation = file_tools._validate_python_code(code)
if not validation['valid']:
    # 自动重试或报错
    retry_with_error_message(validation['errors'])
```

## 使用方法

### 基本使用

```python
from pathlib import Path
from intentgraph.agent.enhanced_code_generator import EnhancedCodeGenerator
from intentgraph.agent.context_manager import ContextManager
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent

# 初始化
workspace = Path(".")
agent = EnhancedCodebaseAgent(workspace)
context_manager = ContextManager(agent)

generator = EnhancedCodeGenerator(
    agent=agent,
    context_manager=context_manager,
    workspace_root=workspace,
    llm_provider=your_llm_provider
)

# 实现新功能
implementation = generator.implement_new_feature(
    design=design_plan,
    task=task
)

# 文件已自动创建
print(f"Created: {implementation.file_path}")
print(f"Code length: {len(implementation.generated_code)}")
```

### 在 Workflow 中使用

```python
from intentgraph.agent.workflow import CodingAgentWorkflow

# 创建 workflow（自动使用 EnhancedCodeGenerator）
workflow = CodingAgentWorkflow(
    repo_path=Path("."),
    llm_provider=your_llm_provider
)

# 实现功能
result = workflow.implement_feature("添加数字求和功能")

# 检查结果
if result.status == WorkflowStatus.COMPLETED:
    print(f"Files created: {result.files_created}")
else:
    print(f"Errors: {result.errors}")
```

## 代码提取逻辑

EnhancedCodeGenerator 使用多层策略提取代码：

### 1. Python 代码块（优先）
```
```python
def hello():
    print("Hello")
```
```

### 2. 通用代码块
```
```
def hello():
    print("Hello")
```
```

### 3. 智能识别
```
这是一些说明文字

def hello():
    print("Hello")

class MyClass:
    pass
```

自动识别以 `def`, `class`, `import` 等开头的代码行。

## 错误处理

### 自动重试机制

```python
# 最多重试 3 次
for attempt in range(max_retries):
    try:
        code = generate_code()
        validate_syntax(code)
        write_file(code)
        break  # 成功
    except Exception as e:
        if attempt == max_retries - 1:
            # 最后一次失败，返回模板
            return generate_template()
        # 重试，带上错误信息
        prompt += f"\nPREVIOUS ERROR: {e}"
```

### 语法验证

```python
# 使用 AST 验证
try:
    ast.parse(code)
    # 语法正确
except SyntaxError as e:
    # 语法错误，重试或报错
    print(f"Syntax error at line {e.lineno}: {e.msg}")
```

## 与原 CodeGenerator 的对比

| 特性 | 原 CodeGenerator | EnhancedCodeGenerator |
|------|-----------------|----------------------|
| 响应格式 | 必须是 JSON | 任意格式（自动提取） |
| 代码提取 | JSON 解析 | 正则 + 智能识别 |
| 文件操作 | 手动 | 自动集成 |
| 语法验证 | 可选 | 自动 |
| 错误处理 | 基础 | 完善的重试机制 |
| 可靠性 | 低（JSON 解析失败） | 高（多层提取策略） |

## 配置选项

```python
generator = EnhancedCodeGenerator(
    agent=agent,
    context_manager=context_manager,
    workspace_root=workspace,
    llm_provider=llm_provider
)

# 实现功能时的选项
implementation = generator.implement_new_feature(
    design=design,
    task=task,
    context=None,        # 自动提取上下文
    max_retries=3        # 最大重试次数
)
```

## 调试信息

EnhancedCodeGenerator 提供详细的调试输出：

```
[DEBUG] Extracting code from response (length: 1234)
[DEBUG] Response preview: def hello()...
[DEBUG] Found Python code block (length: 567)
[INFO] Implementation succeeded on attempt 1
[INFO] File written: src/hello.py
```

## 最佳实践

### 1. 提供清晰的任务描述

```python
task = Task(
    task_id="task_1",
    description="Create a calculator module with add, subtract, multiply, divide functions",
    task_type="create_file",
    target_file="src/calculator.py"
)
```

### 2. 使用上下文

```python
# 提供上下文可以生成更好的代码
context = context_manager.extract_precise_context(
    target="existing_function",
    token_budget=3500
)

implementation = generator.implement_new_feature(
    design=design,
    task=task,
    context=context  # 提供上下文
)
```

### 3. 检查结果

```python
implementation = generator.implement_new_feature(design, task)

# 检查生成的代码
if implementation.generated_code:
    print("✓ Code generated")
else:
    print("✗ No code generated")

# 检查文件路径
if implementation.file_path:
    print(f"✓ File: {implementation.file_path}")
else:
    print("✗ No file path")
```

## 故障排除

### 问题 1: 没有生成代码

**原因：** LLM 响应中没有代码块

**解决：**
- 检查 LLM prompt 是否明确要求返回代码
- 查看调试输出了解 LLM 响应内容
- 尝试不同的 LLM 模型

### 问题 2: 语法错误

**原因：** LLM 生成的代码有语法错误

**解决：**
- 自动重试机制会尝试修复
- 检查 prompt 是否足够清晰
- 增加 max_retries 次数

### 问题 3: 文件写入失败

**原因：** 文件已存在或权限问题

**解决：**
- 检查文件是否已存在
- 确认有写入权限
- 查看 FileOperationResult 的错误信息

## 示例：完整流程

```python
from pathlib import Path
from intentgraph.agent.workflow import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

# 1. 初始化
workspace = Path(".")
llm = DeepSeekProvider(api_key="your-key")

workflow = CodingAgentWorkflow(
    repo_path=workspace,
    llm_provider=llm
)

# 2. 实现功能
result = workflow.implement_feature(
    "创建一个计算器模块，包含加减乘除功能"
)

# 3. 检查结果
if result.status == WorkflowStatus.COMPLETED:
    print("✓ 功能实现成功")
    print(f"创建的文件: {result.files_created}")
    print(f"Token 使用: {result.token_usage}")
    print(f"执行时间: {result.execution_time:.2f}s")
else:
    print("✗ 功能实现失败")
    print(f"错误: {result.errors}")
```

## 总结

EnhancedCodeGenerator 通过以下方式解决了原 CodeGenerator 的问题：

1. ✓ 不再依赖 JSON 解析
2. ✓ 自动文件操作和验证
3. ✓ 更好的错误处理
4. ✓ 详细的调试信息
5. ✓ 更高的可靠性

现在可以放心使用，不会再出现 "JSON 解析失败" 的问题！

