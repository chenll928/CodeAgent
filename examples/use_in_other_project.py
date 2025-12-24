#!/usr/bin/env python3
"""
在其他项目中使用 IntentGraph AI Agent 的完整示例

这个脚本演示了如何在你的项目中集成和使用 IntentGraph AI Agent。
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def setup_environment():
    """设置环境和检查配置"""
    print("=" * 80)
    print("步骤 1: 环境设置和检查")
    print("=" * 80)
    
    # 加载 .env 文件
    load_dotenv()
    
    # 检查 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n❌ 错误: 未找到 DEEPSEEK_API_KEY")
        print("\n请在项目根目录创建 .env 文件并添加：")
        print("DEEPSEEK_API_KEY=sk-your-api-key-here")
        print("DEEPSEEK_BASE_URL=https://api.deepseek.com")
        sys.exit(1)
    
    print(f"✓ DeepSeek API Key: {api_key[:10]}...")
    print(f"✓ Base URL: {os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}")
    
    return api_key


def analyze_project(project_path: Path):
    """分析项目代码库"""
    print("\n" + "=" * 80)
    print("步骤 2: 分析项目代码库")
    print("=" * 80)
    
    from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
    
    print(f"\n分析项目: {project_path}")
    print("这可能需要几秒钟...")
    
    try:
        agent = EnhancedCodebaseAgent(project_path)
        print("✓ 代码库分析完成")
        return agent
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return None


def demo_requirement_analysis(agent, api_key):
    """演示需求分析"""
    print("\n" + "=" * 80)
    print("步骤 3: 需求理解和分析")
    print("=" * 80)
    
    from intentgraph.agent import RequirementAnalyzer
    from intentgraph.agent.llm_provider import DeepSeekProvider
    
    # 初始化 DeepSeek
    deepseek = DeepSeekProvider(
        api_key=api_key,
        model="deepseek-chat"  # 使用 chat 模型进行需求分析
    )
    
    analyzer = RequirementAnalyzer(agent, deepseek)
    
    # 示例需求
    requirement = """
    添加一个用户认证系统，包括：
    1. 用户注册（邮箱+密码）
    2. 用户登录（返回 JWT token）
    3. 密码加密存储（使用 bcrypt）
    4. Token 验证中间件
    """
    
    print(f"\n需求描述:")
    print(requirement)
    
    print("\n[分析中...]")
    analysis = analyzer.analyze_requirement(requirement)
    
    print(f"\n分析结果:")
    print(f"  需求类型: {analysis.requirement_type}")
    print(f"  复杂度: {analysis.estimated_complexity}")
    print(f"  关键实体: {', '.join(analysis.key_entities) if analysis.key_entities else '无'}")
    print(f"  影响范围: {', '.join(analysis.affected_scope) if analysis.affected_scope else '无'}")
    
    return analysis, analyzer


def demo_solution_design(analyzer, analysis):
    """演示方案设计"""
    print("\n" + "=" * 80)
    print("步骤 4: 技术方案设计")
    print("=" * 80)
    
    print("\n[设计中...]")
    design = analyzer.design_solution(analysis)
    
    print(f"\n设计方案:")
    print(f"  技术方案: {design.technical_approach}")
    print(f"\n  新组件: {len(design.new_components)} 个")
    for comp in design.new_components[:3]:
        print(f"    - {comp.get('name', 'N/A')}: {comp.get('purpose', 'N/A')}")
    
    print(f"\n  实现步骤: {len(design.implementation_steps)} 步")
    for i, step in enumerate(design.implementation_steps, 1):
        print(f"    {i}. {step}")
    
    return design


def demo_task_decomposition(analyzer, design):
    """演示任务分解"""
    print("\n" + "=" * 80)
    print("步骤 5: 任务分解")
    print("=" * 80)
    
    print("\n[分解中...]")
    tasks = analyzer.decompose_tasks(design)
    
    print(f"\n任务列表: {len(tasks)} 个任务")
    for task in tasks:
        print(f"\n  任务 {task.task_id}:")
        print(f"    描述: {task.description}")
        print(f"    类型: {task.task_type}")
        print(f"    优先级: {task.priority}")
        if task.target_file:
            print(f"    目标文件: {task.target_file}")
    
    return tasks


def demo_code_generation(agent, api_key, design, tasks):
    """演示代码生成"""
    print("\n" + "=" * 80)
    print("步骤 6: 代码生成")
    print("=" * 80)
    
    from intentgraph.agent import CodeGenerator, ContextManager
    from intentgraph.agent.llm_provider import DeepSeekProvider
    
    # 使用 DeepSeek Coder 进行代码生成
    deepseek = DeepSeekProvider(
        api_key=api_key,
        model="deepseek-coder"  # 代码专用模型
    )
    
    context_mgr = ContextManager(agent)
    generator = CodeGenerator(agent, context_mgr, deepseek)
    
    # 生成第一个任务的代码
    if tasks:
        task = tasks[0]
        print(f"\n生成任务: {task.description}")
        print("[生成中...]")
        
        implementation = generator.implement_new_feature(design, task)
        
        print(f"\n生成结果:")
        print(f"  文件: {implementation.file_path}")
        print(f"  导入: {', '.join(implementation.imports_needed) if implementation.imports_needed else '无'}")
        print(f"\n  代码预览:")
        print("  " + "-" * 76)
        for line in implementation.generated_code.split('\n')[:15]:
            print(f"  {line}")
        if len(implementation.generated_code.split('\n')) > 15:
            print("  ...")
        print("  " + "-" * 76)
        
        return implementation
    
    return None


def demo_complete_workflow(project_path: Path, api_key):
    """演示完整工作流"""
    print("\n" + "=" * 80)
    print("步骤 7: 完整工作流（推荐方式）")
    print("=" * 80)
    
    from intentgraph.agent import CodingAgentWorkflow
    from intentgraph.agent.llm_provider import DeepSeekProvider
    
    # 初始化
    deepseek = DeepSeekProvider(
        api_key=api_key,
        model="deepseek-coder"
    )
    
    workflow = CodingAgentWorkflow(
        repo_path=project_path,
        llm_provider=deepseek,
        enable_cache=True
    )
    
    print("\n使用完整工作流实现功能...")
    requirement = "添加一个简单的日志装饰器"
    
    print(f"需求: {requirement}")
    print("[执行中...]")
    
    result = workflow.implement_feature(requirement)
    
    print(f"\n执行结果:")
    print(f"  状态: {result.status.value}")
    print(f"  执行时间: {result.execution_time:.2f}s")
    print(f"  Token 使用: {result.token_usage:,}")
    
    if result.files_created:
        print(f"\n  创建的文件:")
        for file in result.files_created:
            print(f"    • {file}")
    
    if result.tests_generated:
        print(f"\n  生成的测试:")
        for test in result.tests_generated:
            print(f"    • {test}")
    
    if result.errors:
        print(f"\n  错误:")
        for error in result.errors:
            print(f"    ✗ {error}")


def show_cli_examples():
    """显示 CLI 命令示例"""
    print("\n" + "=" * 80)
    print("CLI 命令使用示例")
    print("=" * 80)
    
    print("\n在你的项目中可以直接使用以下命令：")
    
    print("\n1. 分析代码库:")
    print("   intentgraph analyze . --output intentgraph.json")
    
    print("\n2. 实现新功能:")
    print("   intentgraph agent-new-feature \"添加用户登录\" \\")
    print("     --provider deepseek \\")
    print("     --model deepseek-coder \\")
    print("     --api-key $DEEPSEEK_API_KEY")
    
    print("\n3. 修改代码:")
    print("   intentgraph agent-modify \"User.register\" \"添加验证\" \\")
    print("     --provider deepseek")
    
    print("\n4. Token 估算:")
    print("   intentgraph agent-estimate \"你的需求\"")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("IntentGraph AI Agent - 在其他项目中使用示例")
    print("=" * 80)
    
    try:
        # 1. 设置环境
        api_key = setup_environment()
        
        # 2. 分析项目（使用当前目录作为示例）
        project_path = Path(".")
        agent = analyze_project(project_path)
        
        if not agent:
            print("\n跳过后续步骤（分析失败）")
            return
        
        # 3. 需求分析
        analysis, analyzer = demo_requirement_analysis(agent, api_key)
        
        # 4. 方案设计
        design = demo_solution_design(analyzer, analysis)
        
        # 5. 任务分解
        tasks = demo_task_decomposition(analyzer, design)
        
        # 6. 代码生成
        demo_code_generation(agent, api_key, design, tasks)
        
        # 7. 完整工作流
        demo_complete_workflow(project_path, api_key)
        
        # 8. CLI 示例
        show_cli_examples()
        
        print("\n" + "=" * 80)
        print("演示完成！")
        print("=" * 80)
        
        print("\n下一步:")
        print("1. 在你的项目目录运行此脚本")
        print("2. 或使用 CLI 命令直接操作")
        print("3. 查看文档: docs/usage_in_other_projects.md")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

