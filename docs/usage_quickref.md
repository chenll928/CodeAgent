# 在其他项目中使用 - 快速参考

## 一分钟快速开始

```bash
# 1. 进入你的项目
cd /path/to/your-project

# 2. 配置 API Key
echo "DEEPSEEK_API_KEY=sk-your-key" > .env

# 3. 分析代码库
intentgraph analyze . --output intentgraph.json

# 4. 实现功能
intentgraph agent-new-feature "你的需求" --provider deepseek
```

## 常用命令

### 实现新功能
```bash
intentgraph agent-new-feature "添加用户登录" \
  --provider deepseek \
  --api-key $DEEPSEEK_API_KEY
```

### 修改代码
```bash
intentgraph agent-modify "User.register" "添加验证" \
  --provider deepseek
```

### Token 估算
```bash
intentgraph agent-estimate "你的需求"
```

## Python API

```python
from pathlib import Path
from intentgraph.agent import CodingAgentWorkflow
from intentgraph.agent.llm_provider import DeepSeekProvider

# 初始化
deepseek = DeepSeekProvider(api_key="sk-xxx", model="deepseek-coder")
workflow = CodingAgentWorkflow(Path("."), deepseek, enable_cache=True)

# 实现功能
result = workflow.implement_feature("你的需求")
print(f"状态: {result.status}")
```

## 项目结构

```
your-project/
├── .env                    # API 配置
├── intentgraph.json        # 分析结果
├── src/                    # 你的代码
└── tests/                  # 生成的测试
```

## 支持的提供者

| 提供者 | 模型 | 用途 |
|--------|------|------|
| deepseek | deepseek-coder | 代码生成 |
| deepseek | deepseek-chat | 需求分析 |
| openai | gpt-4 | 通用 |
| anthropic | claude-3 | 通用 |

## 完整示例

```bash
# 在你的 Django 项目中
cd ~/projects/my-django-app

# 分析
intentgraph analyze . --output intentgraph.json

# 添加功能
intentgraph agent-new-feature \
  "添加用户认证：
  1. 用户注册（邮箱+密码）
  2. 用户登录（JWT token）
  3. 密码加密（bcrypt）" \
  --provider deepseek \
  --model deepseek-coder

# 查看生成的文件
ls -la auth/
ls -la tests/test_auth.py

# 运行测试
pytest tests/test_auth.py
```

## 最佳实践

1. ✅ 首次使用先分析代码库
2. ✅ 使用 deepseek-coder 生成代码
3. ✅ 启用缓存提升速度
4. ✅ 详细描述需求
5. ✅ 审查生成的代码

## 故障排除

### API Key 错误
```bash
# 检查配置
cat .env | grep DEEPSEEK
```

### 分析失败
```bash
# 重新分析
rm intentgraph.json
intentgraph analyze . --output intentgraph.json
```

### 导入错误
```bash
# 安装依赖
pip install intentgraph openai python-dotenv
```

## 获取帮助

```bash
intentgraph --help
intentgraph agent-new-feature --help
```

## 更多资源

- 📖 [完整指南](usage_in_other_projects.md)
- 💻 [示例脚本](../examples/use_in_other_project.py)
- 🚀 [DeepSeek 指南](deepseek_guide.md)

