"""
AI Coding Agent - File Operations Integration Example

This example demonstrates how to use the enhanced file operation tools
in the CodeAgent project.
"""

from pathlib import Path
from intentgraph.agent.file_tools import FileTools
from intentgraph.agent.enhanced_code_generator import EnhancedCodeGenerator
from intentgraph.agent.context_manager import ContextManager
from intentgraph.agent.requirement_analyzer import RequirementAnalyzer, DesignPlan, Task
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent


def example_1_read_file():
    """Example 1: Read file with different options."""
    print("=" * 60)
    print("Example 1: Reading Files")
    print("=" * 60)
    
    workspace = Path(".")
    file_tools = FileTools(workspace)
    
    # Read entire file
    print("\n1. Read entire file:")
    content = file_tools.read_file("src/intentgraph/agent/file_tools.py")
    print(content[:500])  # Show first 500 chars
    
    # Read specific line range
    print("\n2. Read lines 1-50:")
    content = file_tools.read_file(
        "src/intentgraph/agent/file_tools.py",
        view_range=(1, 50)
    )
    print(content)
    
    # Search with regex
    print("\n3. Search for class definitions:")
    content = file_tools.read_file(
        "src/intentgraph/agent/file_tools.py",
        search_regex=r"^class\s+\w+",
        context_lines=3
    )
    print(content)


def example_2_create_file():
    """Example 2: Create new file with validation."""
    print("\n" + "=" * 60)
    print("Example 2: Creating Files")
    print("=" * 60)
    
    workspace = Path(".")
    file_tools = FileTools(workspace)
    
    # Create a simple Python file
    code = '''"""
Simple calculator module.
"""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b

if __name__ == "__main__":
    print(f"5 + 3 = {add(5, 3)}")
    print(f"5 - 3 = {subtract(5, 3)}")
'''
    
    result = file_tools.create_file(
        file_path="examples/calculator.py",
        content=code
    )
    
    print(f"\nStatus: {result.status}")
    print(f"Message: {result.message}")
    print(f"Lines affected: {result.lines_affected}")
    if result.errors:
        print(f"Errors: {result.errors}")


def example_3_modify_file():
    """Example 3: Modify existing file."""
    print("\n" + "=" * 60)
    print("Example 3: Modifying Files")
    print("=" * 60)
    
    workspace = Path(".")
    file_tools = FileTools(workspace)
    
    # First, read the file to see what we're modifying
    print("\n1. Reading current content:")
    content = file_tools.read_file(
        "examples/calculator.py",
        view_range=(5, 8)
    )
    print(content)
    
    # Modify the add function to include logging
    old_code = '''def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
    
    new_code = '''def add(a: int, b: int) -> int:
    """Add two numbers with logging."""
    result = a + b
    print(f"Adding {a} + {b} = {result}")
    return result
'''
    
    result = file_tools.modify_file(
        file_path="examples/calculator.py",
        old_str=old_code,
        new_str=new_code,
        old_str_start_line=5,
        old_str_end_line=7
    )
    
    print(f"\n2. Modification result:")
    print(f"Status: {result.status}")
    print(f"Message: {result.message}")
    print(f"Lines affected: {result.lines_affected}")


def example_4_insert_content():
    """Example 4: Insert content into file."""
    print("\n" + "=" * 60)
    print("Example 4: Inserting Content")
    print("=" * 60)
    
    workspace = Path(".")
    file_tools = FileTools(workspace)
    
    # Insert a new function
    new_function = '''
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

'''
    
    result = file_tools.insert_content(
        file_path="examples/calculator.py",
        insert_after_line=12,  # After subtract function
        content=new_function
    )
    
    print(f"\nStatus: {result.status}")
    print(f"Message: {result.message}")
    print(f"Lines affected: {result.lines_affected}")


def example_5_validate_code():
    """Example 5: Validate code logic."""
    print("\n" + "=" * 60)
    print("Example 5: Validating Code")
    print("=" * 60)
    
    workspace = Path(".")
    file_tools = FileTools(workspace)
    
    requirements = [
        "Must have add function",
        "Must have subtract function",
        "Must have multiply function"
    ]
    
    result = file_tools.validate_code_logic(
        file_path="examples/calculator.py",
        requirements=requirements
    )
    
    print(f"\nValidation result:")
    print(f"Valid: {result['valid']}")
    if result.get('structure'):
        print(f"Functions found: {result['structure']['functions']}")
        print(f"Classes found: {result['structure']['classes']}")
    if result.get('errors'):
        print(f"Errors: {result['errors']}")


def example_6_enhanced_generator():
    """Example 6: Use enhanced code generator."""
    print("\n" + "=" * 60)
    print("Example 6: Enhanced Code Generator")
    print("=" * 60)
    
    workspace = Path(".")
    
    # Initialize components
    agent = EnhancedCodebaseAgent(workspace)
    context_manager = ContextManager(agent)
    generator = EnhancedCodeGenerator(
        agent=agent,
        context_manager=context_manager,
        workspace_root=workspace
    )
    
    # Create a simple task
    task = Task(
        task_id="task_1",
        description="Create a simple greeting module",
        task_type="create_file"
    )
    
    # Create a simple design plan
    design = DesignPlan(
        requirement="Create greeting functionality",
        architecture_overview="Simple module with greeting functions",
        components=[],
        file_structure={},
        dependencies=[],
        estimated_complexity="low"
    )
    
    print("\nNote: This example requires LLM integration.")
    print("In production, this would generate and write code automatically.")


if __name__ == "__main__":
    print("AI Coding Agent - File Operations Examples")
    print("=" * 60)
    
    # Run examples
    try:
        example_1_read_file()
    except Exception as e:
        print(f"Example 1 error: {e}")
    
    try:
        example_2_create_file()
    except Exception as e:
        print(f"Example 2 error: {e}")
    
    try:
        example_3_modify_file()
    except Exception as e:
        print(f"Example 3 error: {e}")
    
    try:
        example_4_insert_content()
    except Exception as e:
        print(f"Example 4 error: {e}")
    
    try:
        example_5_validate_code()
    except Exception as e:
        print(f"Example 5 error: {e}")
    
    try:
        example_6_enhanced_generator()
    except Exception as e:
        print(f"Example 6 error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")

