"""
Demo script for Phase 3 & 4: Requirement Understanding and Code Generation.

This script demonstrates the complete workflow:
1. Analyze requirement
2. Design solution
3. Decompose into tasks
4. Generate code
5. Generate tests
"""

from pathlib import Path
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from intentgraph.agent import (
    ContextManager,
    RequirementAnalyzer,
    CodeGenerator,
)


def demo_new_feature_workflow():
    """Demonstrate new feature implementation workflow."""
    print("=" * 80)
    print("Demo: New Feature Implementation Workflow")
    print("=" * 80)
    
    # Initialize components
    repo_path = Path(".")
    agent = EnhancedCodebaseAgent(repo_path)
    context_manager = ContextManager(agent)
    requirement_analyzer = RequirementAnalyzer(agent, llm_provider=None)
    code_generator = CodeGenerator(agent, context_manager, llm_provider=None)
    
    # Step 1: Analyze Requirement
    print("\n[Step 1] Analyzing Requirement...")
    requirement = "Add a new function to calculate the complexity score of a code symbol based on its dependencies"
    
    analysis = requirement_analyzer.analyze_requirement(requirement)
    print(f"  Type: {analysis.requirement_type}")
    print(f"  Complexity: {analysis.estimated_complexity}")
    print(f"  Key Entities: {', '.join(analysis.key_entities) if analysis.key_entities else 'None identified'}")
    
    # Step 2: Design Solution
    print("\n[Step 2] Designing Solution...")
    design = requirement_analyzer.design_solution(analysis)
    print(f"  Approach: {design.technical_approach}")
    print(f"  New Components: {len(design.new_components)}")
    print(f"  Implementation Steps: {len(design.implementation_steps)}")
    for i, step in enumerate(design.implementation_steps, 1):
        print(f"    {i}. {step}")
    
    # Step 3: Decompose Tasks
    print("\n[Step 3] Decomposing into Tasks...")
    tasks = requirement_analyzer.decompose_tasks(design)
    print(f"  Total Tasks: {len(tasks)}")
    for task in tasks:
        print(f"    - {task.task_id}: {task.description}")
        print(f"      Type: {task.task_type}, Priority: {task.priority}")
    
    # Step 4: Generate Code for First Task
    if tasks:
        print("\n[Step 4] Generating Code for First Task...")
        first_task = tasks[0]
        implementation = code_generator.implement_new_feature(design, first_task)
        print(f"  File: {implementation.file_path}")
        print(f"  Imports: {', '.join(implementation.imports_needed) if implementation.imports_needed else 'None'}")
        print(f"  Integration Notes: {len(implementation.integration_notes)}")
        print("\n  Generated Code Preview:")
        print("  " + "-" * 76)
        for line in implementation.generated_code.split('\n')[:10]:
            print(f"  {line}")
        if len(implementation.generated_code.split('\n')) > 10:
            print("  ...")
        print("  " + "-" * 76)
        
        # Step 5: Generate Tests
        print("\n[Step 5] Generating Tests...")
        test_suite = code_generator.generate_tests(implementation)
        print(f"  Test File: {test_suite.test_file_path}")
        print(f"  Test Cases: {len(test_suite.test_cases)}")
        print("\n  Test Code Preview:")
        print("  " + "-" * 76)
        for line in test_suite.test_code.split('\n')[:10]:
            print(f"  {line}")
        if len(test_suite.test_code.split('\n')) > 10:
            print("  ...")
        print("  " + "-" * 76)
    
    print("\n" + "=" * 80)
    print("New Feature Workflow Complete!")
    print("=" * 80)


def demo_modify_existing_workflow():
    """Demonstrate existing code modification workflow."""
    print("\n\n" + "=" * 80)
    print("Demo: Modify Existing Code Workflow")
    print("=" * 80)
    
    # Initialize components
    repo_path = Path(".")
    agent = EnhancedCodebaseAgent(repo_path)
    context_manager = ContextManager(agent)
    code_generator = CodeGenerator(agent, context_manager, llm_provider=None)
    
    # Step 1: Analyze Requirement
    print("\n[Step 1] Analyzing Modification Requirement...")
    target_symbol = "EnhancedCodebaseAgent.get_call_chain"
    modification_desc = "Add caching mechanism to improve performance for repeated calls"
    
    print(f"  Target: {target_symbol}")
    print(f"  Modification: {modification_desc}")
    
    # Step 2: Extract Context
    print("\n[Step 2] Extracting Precise Context...")
    context = context_manager.extract_precise_context(
        target=target_symbol,
        token_budget=5000,
        task_type="modify"
    )
    print(f"  Layers Included: {', '.join(str(layer.value) for layer in context.layers_included)}")
    print(f"  Token Estimate: {context.token_estimate}")
    print(f"  Direct Dependencies: {len(context.direct_dependencies)}")
    
    # Step 3: Analyze Impact
    print("\n[Step 3] Analyzing Impact...")
    from intentgraph.agent import CodeChange
    change = CodeChange(
        target_symbol=target_symbol,
        target_file=context.target_code.get("file", ""),
        change_type="implementation_change",
        description=modification_desc,
        line_range=(context.target_code.get("line_range", [0, 0])[0],
                   context.target_code.get("line_range", [0, 0])[1])
    )
    impact = context_manager.analyze_impact(change)
    print(f"  Risk Level: {impact.risk_level}")
    print(f"  Direct Callers: {len(impact.direct_callers)}")
    print(f"  Affected Tests: {len(impact.affected_tests)}")
    
    # Step 4: Generate Modified Code
    print("\n[Step 4] Generating Modified Code...")
    modification = code_generator.modify_existing_code(
        target=target_symbol,
        modification_desc=modification_desc,
        context=context
    )
    print(f"  File: {modification.file_path or 'N/A'}")
    print(f"  Change: {modification.change_description}")
    print(f"  Migration Guide: {len(modification.migration_guide)} steps")
    
    print("\n" + "=" * 80)
    print("Modify Existing Code Workflow Complete!")
    print("=" * 80)


def demo_context_extraction():
    """Demonstrate context extraction capabilities."""
    print("\n\n" + "=" * 80)
    print("Demo: Context Extraction Capabilities")
    print("=" * 80)
    
    repo_path = Path(".")
    agent = EnhancedCodebaseAgent(repo_path)
    context_manager = ContextManager(agent)
    
    # Test different token budgets
    target = "ContextManager.extract_precise_context"
    budgets = [1000, 3000, 5000, 8000]
    
    print(f"\nTarget: {target}")
    print("\nContext Layers by Token Budget:")
    print("-" * 80)
    
    for budget in budgets:
        context = context_manager.extract_precise_context(target, budget)
        layers = ', '.join(str(layer.value) for layer in context.layers_included)
        print(f"  Budget: {budget:5d} tokens -> Layers: {layers}")
        print(f"                        Estimate: {context.token_estimate} tokens")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        # Run all demos
        demo_new_feature_workflow()
        demo_modify_existing_workflow()
        demo_context_extraction()
        
        print("\n\n" + "=" * 80)
        print("All Demos Complete!")
        print("=" * 80)
        print("\nNote: These demos use fallback heuristics without LLM.")
        print("To use actual LLM capabilities, provide an LLM provider instance.")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()

