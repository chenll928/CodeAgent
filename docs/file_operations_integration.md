# AI 编码工具文件操作集成指南

## 概述

本文档说明如何在 CodeAgent 项目中集成类似 Amazon Q 的文件操作工具，实现 agent 对代码文件的安全读取、修改、创建和删除。

## 核心组件

### 1. FileTools - 文件操作工具类

位置：`src/intentgraph/agent/file_tools.py`

提供以下核心功能：

#### 1.1 读取文件 (read_file)

```python
from intentgraph.agent.file_tools import FileTools

file_tools = FileTools(workspace_root=Path("."))

# 读取整个文件
content = file_tools.read_file("src/example.py")

# 读取指定行范围
content = file_tools.read_file("src/example.py", view_range=(10, 50))

# 使用正则表达式搜索
content = file_tools.read_file(
    "src/example.py",
    search_regex=r"^class\s+\w+",
    context_lines=5
)
```

**特点：**
- 自动添加行号
- 支持行范围过滤
- 支持正则表达式搜索
- 自动显示上下文行

#### 1.2 创建文件 (create_file)

```python
result = file_tools.create_file(
    file_path="src/new_module.py",
    content=code_content,
    overwrite=False  # 防止覆盖已存在文件
)

if result.status == FileOperationStatus.SUCCESS:
    print(f"文件创建成功: {result.message}")
else:
    print(f"创建失败: {result.errors}")
```

**特点：**
- 自动创建父目录
- Python 文件自动语法验证
- 防止意外覆盖
- 返回详细操作结果

#### 1.3 修改文件 (modify_file)

```python
result = file_tools.modify_file(
    file_path="src/example.py",
    old_str="def old_function():\n    pass",
    new_str="def new_function():\n    return True",
    old_str_start_line=10,
    old_str_end_line=11
)
```

**特点：**
- 精确字符串匹配（包括空格）
- 必须指定行号范围避免歧义
- 修改前验证匹配
- 修改后验证语法
- 原子操作，失败不写入

#### 1.4 插入内容 (insert_content)

```python
result = file_tools.insert_content(
    file_path="src/example.py",
    insert_after_line=20,  # 0 表示文件开头
    content="def new_function():\n    pass\n"
)
```

#### 1.5 删除文件 (delete_file)

```python
result = file_tools.delete_file("src/old_file.py")
```

#### 1.6 验证代码 (validate_code_logic)

```python
result = file_tools.validate_code_logic(
    file_path="src/example.py",
    requirements=["Must have add function", "Must handle errors"]
)

print(f"Valid: {result['valid']}")
print(f"Functions: {result['structure']['functions']}")
print(f"Classes: {result['structure']['classes']}")
```

### 2. EnhancedCodeGenerator - 增强代码生成器

位置：`src/intentgraph/agent/enhanced_code_generator.py`

集成了文件操作和代码生成：

```python
from intentgraph.agent.enhanced_code_generator import EnhancedCodeGenerator

generator = EnhancedCodeGenerator(
    agent=agent,
    context_manager=context_manager,
    workspace_root=Path("."),
    llm_provider=llm_provider
)

# 实现功能并自动写入文件
enhanced_impl = generator.implement_and_write(
    design=design_plan,
    task=task,
    validate=True  # 自动验证语法
)

print(f"文件: {enhanced_impl.file_operation.file_path}")
print(f"状态: {enhanced_impl.file_operation.status}")
print(f"验证: {enhanced_impl.validation_result}")
```

## 集成到现有 Workflow

### 修改 workflow.py

```python
from .enhanced_code_generator import EnhancedCodeGenerator

class CodingAgentWorkflow:
    def __init__(self, repo_path: Path, ...):
        # 使用增强的生成器
        self.generator = EnhancedCodeGenerator(
            self.agent,
            self.context_manager,
            workspace_root=repo_path,
            llm_provider=llm_provider
        )
    
    def implement_feature(self, requirement: str) -> WorkflowResult:
        # ... 前面的步骤 ...
        
        # 使用增强的实现方法
        for task in tasks:
            enhanced_impl = self.generator.implement_and_write(
                design=design,
                task=task,
                validate=True
            )
            
            # 检查结果
            if enhanced_impl.file_operation.status == FileOperationStatus.SUCCESS:
                result.files_created.append(enhanced_impl.file_operation.file_path)
            else:
                result.errors.extend(enhanced_impl.file_operation.errors)
```

## 工作流程

### 完整的文件操作流程

```
1. 需求分析
   ↓
2. 设计方案
   ↓
3. 生成代码 (LLM)
   ↓
4. 语法验证 (AST Parse)
   ↓
5. 逻辑验证 (结构分析)
   ↓
6. 写入文件 (原子操作)
   ↓
7. 验证结果
```

### 错误处理机制

```python
try:
    # 尝试创建文件
    result = file_tools.create_file(path, content)
    
    if result.status != FileOperationStatus.SUCCESS:
        # 处理失败
        logger.error(f"Failed: {result.errors}")
        # 可以尝试回滚或重试
        
except Exception as e:
    # 异常处理
    logger.exception("Unexpected error")
```

## 保证代码逻辑正确的机制

### 1. 多层验证

```python
# 第一层：语法验证
syntax_check = file_tools._validate_python_code(code)

# 第二层：结构验证
structure = file_tools.validate_code_logic(file_path, requirements)

# 第三层：上下文验证
context = context_manager.extract_precise_context(target)
impact = context_manager.analyze_impact(change)
```

### 2. 测试驱动

```python
# 生成代码后自动生成测试
test_suite = generator.generate_tests(implementation)

# 运行测试验证
test_result = run_tests(test_suite)
```

### 3. 增量修改

```python
# 小步骤修改
for small_change in decompose_large_change(change):
    result = apply_change(small_change)
    if not validate(result):
        rollback(small_change)
        break
```

## 使用示例

查看完整示例：`examples/file_operations_demo.py`

运行示例：
```bash
python examples/file_operations_demo.py
```

## 最佳实践

1. **始终验证**：修改前后都要验证代码
2. **精确匹配**：使用 modify_file 时确保字符串完全匹配
3. **原子操作**：失败时不写入，保持文件完整性
4. **错误处理**：检查所有操作结果
5. **增量修改**：大改动分解为小步骤
6. **保留备份**：重要修改前备份文件

## 与 Amazon Q 工具对比

| 功能 | Amazon Q | CodeAgent FileTools |
|------|----------|---------------------|
| 读取文件 | view | read_file |
| 创建文件 | save-file | create_file |
| 修改文件 | str-replace-editor | modify_file |
| 删除文件 | remove-files | delete_file |
| 语法验证 | 内置 | _validate_python_code |
| 逻辑验证 | 上下文理解 | validate_code_logic |

## 下一步

1. 集成到 CLI 命令
2. 添加更多语言支持（JavaScript, Go 等）
3. 实现更智能的代码匹配算法
4. 添加自动测试生成
5. 实现代码审查功能

