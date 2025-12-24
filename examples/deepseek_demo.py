"""
DeepSeek LLM Provider 使用示例

演示如何使用 DeepSeek API 进行代码生成和分析。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from intentgraph.agent import (
    CodingAgentWorkflow,
    RequirementAnalyzer,
    CodeGenerator,
    ContextManager,
)
from intentgraph.agent.llm_provider import DeepSeekProvider
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent


def load_deepseek_config():
    """从 .env 文件加载 DeepSeek 配置"""
    load_dotenv()
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY not found in environment. "
            "Please set it in .env file or environment variables."
        )
    
    return api_key, base_url


def demo_deepseek_basic():
    """演示 DeepSeek Provider 基本使用"""
    print("=" * 80)
    print("Demo 1: DeepSeek Provider 基本使用")
    print("=" * 80)
    
    # 加载配置
    api_key, base_url = load_deepseek_config()
    
    # 初始化 DeepSeek Provider
    deepseek = DeepSeekProvider(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-chat"  # 或 "deepseek-coder" 用于代码任务
    )
    
    print(f"\n✓ DeepSeek Provider 初始化成功")
    print(f"  Base URL: {base_url}")
    print(f"  Model: deepseek-chat")
    
    # 测试简单对话
    print("\n[测试 1] 简单对话")
    print("-" * 80)
    prompt = "请用一句话解释什么是依赖注入？"
    response = deepseek.chat(prompt, max_tokens=200)
    print(f"问题: {prompt}")
    print(f"回答: {response}")
    
    # 测试代码生成
    print("\n[测试 2] 代码生成")
    print("-" * 80)
    prompt = """请生成一个 Python 函数，实现二分查找算法。
要求：
1. 函数名为 binary_search
2. 接受一个排序列表和目标值
3. 返回目标值的索引，如果不存在返回 -1
4. 包含类型提示和文档字符串
"""
    response = deepseek.chat(prompt, max_tokens=500)
    print(f"生成的代码:\n{response}")


def demo_deepseek_with_requirement_analyzer():
    """演示 DeepSeek 与需求分析器集成"""
    print("\n\n" + "=" * 80)
    print("Demo 2: DeepSeek + 需求分析器")
    print("=" * 80)
    
    # 加载配置
    api_key, base_url = load_deepseek_config()
    
    # 初始化组件
    repo_path = Path(".")
    agent = EnhancedCodebaseAgent(repo_path)
    
    # 使用 DeepSeek Coder 模型（更适合代码任务）
    deepseek = DeepSeekProvider(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-coder"
    )
    
    analyzer = RequirementAnalyzer(agent, deepseek)
    
    print(f"\n✓ 使用 DeepSeek Coder 模型")
    
    # 分析需求
    print("\n[步骤 1] 分析需求")
    print("-" * 80)
    requirement = "添加一个缓存装饰器，支持 TTL 和 LRU 淘汰策略"
    
    analysis = analyzer.analyze_requirement(requirement)
    
    print(f"需求: {requirement}")
    print(f"类型: {analysis.requirement_type}")
    print(f"复杂度: {analysis.estimated_complexity}")
    print(f"关键实体: {', '.join(analysis.key_entities) if analysis.key_entities else '无'}")
    
    # 设计方案
    print("\n[步骤 2] 设计方案")
    print("-" * 80)
    design = analyzer.design_solution(analysis)
    
    print(f"技术方案: {design.technical_approach}")
    print(f"实现步骤: {len(design.implementation_steps)} 步")
    for i, step in enumerate(design.implementation_steps, 1):
        print(f"  {i}. {step}")


def demo_deepseek_with_code_generator():
    """演示 DeepSeek 与代码生成器集成"""
    print("\n\n" + "=" * 80)
    print("Demo 3: DeepSeek + 代码生成器")
    print("=" * 80)
    
    # 加载配置
    api_key, base_url = load_deepseek_config()
    
    # 初始化组件
    repo_path = Path(".")
    agent = EnhancedCodebaseAgent(repo_path)
    context_manager = ContextManager(agent)
    
    # 使用 DeepSeek Coder
    deepseek = DeepSeekProvider(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-coder"
    )
    
    generator = CodeGenerator(agent, context_manager, deepseek)
    
    print(f"\n✓ 使用 DeepSeek Coder 进行代码生成")
    
    # 创建一个简单的任务
    from intentgraph.agent import Task, DesignPlan, RequirementAnalysis, RequirementType
    
    analysis = RequirementAnalysis(
        requirement_text="添加日志装饰器",
        requirement_type=RequirementType.NEW_FEATURE,
        estimated_complexity="low"
    )
    
    design = DesignPlan(
        requirement_analysis=analysis,
        technical_approach="创建一个装饰器函数，记录函数调用信息"
    )
    
    task = Task(
        task_id="task_1",
        description="实现日志装饰器",
        task_type="create_file",
        target_file="utils/decorators.py"
    )
    
    # 生成代码
    print("\n[生成代码]")
    print("-" * 80)
    implementation = generator.implement_new_feature(design, task)
    
    print(f"文件: {implementation.file_path}")
    print(f"导入: {', '.join(implementation.imports_needed) if implementation.imports_needed else '无'}")
    print(f"\n生成的代码:")
    print("-" * 80)
    print(implementation.generated_code)


def demo_deepseek_complete_workflow():
    """演示 DeepSeek 完整工作流"""
    print("\n\n" + "=" * 80)
    print("Demo 4: DeepSeek 完整工作流")
    print("=" * 80)
    
    # 加载配置
    api_key, base_url = load_deepseek_config()
    
    # 初始化 DeepSeek Provider
    deepseek = DeepSeekProvider(
        api_key=api_key,
        base_url=base_url,
        model="deepseek-coder"
    )
    
    print(f"\n✓ 使用 DeepSeek Coder 模型")
    
    # 初始化工作流
    workflow = CodingAgentWorkflow(
        repo_path=Path("."),
        llm_provider=deepseek,
        enable_cache=True
    )
    
    print(f"✓ 工作流初始化完成（已启用缓存）")
    
    # 执行完整工作流
    print("\n[执行工作流]")
    print("-" * 80)
    requirement = "添加一个性能监控装饰器，记录函数执行时间"
    
    print(f"需求: {requirement}")
    print(f"执行中...")
    
    result = workflow.implement_feature(requirement)
    
    # 显示结果
    print(f"\n[结果]")
    print("-" * 80)
    print(f"状态: {result.status.value}")
    print(f"执行时间: {result.execution_time:.2f}s")
    print(f"Token 使用: {result.token_usage:,}")
    
    if result.files_created:
        print(f"\n创建的文件:")
        for file in result.files_created:
            print(f"  • {file}")
    
    if result.tests_generated:
        print(f"\n生成的测试:")
        for test in result.tests_generated:
            print(f"  • {test}")
    
    if result.errors:
        print(f"\n错误:")
        for error in result.errors:
            print(f"  ✗ {error}")


def demo_deepseek_models_comparison():
    """演示不同 DeepSeek 模型的对比"""
    print("\n\n" + "=" * 80)
    print("Demo 5: DeepSeek 模型对比")
    print("=" * 80)
    
    # 加载配置
    api_key, base_url = load_deepseek_config()
    
    models = [
        ("deepseek-chat", "通用对话模型"),
        ("deepseek-coder", "代码专用模型")
    ]
    
    prompt = "请写一个 Python 函数计算斐波那契数列的第 n 项"
    
    for model_name, description in models:
        print(f"\n[模型: {model_name}]")
        print(f"描述: {description}")
        print("-" * 80)
        
        provider = DeepSeekProvider(
            api_key=api_key,
            base_url=base_url,
            model=model_name
        )
        
        response = provider.chat(prompt, max_tokens=300)
        print(f"回答:\n{response}\n")


if __name__ == "__main__":
    try:
        # 运行所有演示
        demo_deepseek_basic()
        demo_deepseek_with_requirement_analyzer()
        demo_deepseek_with_code_generator()
        demo_deepseek_complete_workflow()
        demo_deepseek_models_comparison()
        
        print("\n\n" + "=" * 80)
        print("所有 DeepSeek 演示完成！")
        print("=" * 80)
        print("\n提示:")
        print("1. DeepSeek Coder 模型更适合代码生成任务")
        print("2. DeepSeek Chat 模型适合通用对话和需求分析")
        print("3. 可以通过 .env 文件配置 API Key 和 Base URL")
        print("4. DeepSeek API 兼容 OpenAI 接口格式")
        
    except ValueError as e:
        print(f"\n配置错误: {e}")
        print("\n请确保 .env 文件中设置了 DEEPSEEK_API_KEY")
    except Exception as e:
        print(f"\n运行错误: {e}")
        import traceback
        traceback.print_exc()

