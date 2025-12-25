"""
Improved Prompt Templates Module

This module provides enhanced prompt templates that reduce syntax errors
in LLM-generated code.
"""

from typing import List


class ImprovedPromptTemplates:
    """Enhanced prompt templates for better code generation."""
    
    @staticmethod
    def get_code_generation_prompt(
        task_description: str,
        context: str = "",
        file_path: str = "",
        additional_requirements: str = ""
    ) -> str:
        """
        Get improved prompt for code generation.
        
        Args:
            task_description: Description of the task
            context: Codebase context
            file_path: Target file path
            additional_requirements: Additional requirements
            
        Returns:
            Enhanced prompt string
        """
        prompt = f"""Generate Python code for the following task:

TASK: {task_description}

TARGET FILE: {file_path or 'New file'}

CONTEXT:
{context or 'No context provided'}

{additional_requirements}

CRITICAL SYNTAX RULES (MUST FOLLOW):
1. ✓ Ensure ALL brackets are properly closed: (), {{}}, []
2. ✓ Ensure ALL strings are properly terminated (quotes, triple quotes)
3. ✓ Ensure ALL f-strings have matching braces {{}}
4. ✓ Complete ALL statements - no incomplete lines (e.g., "x =" must have a value)
5. ✓ Add colons after: def, class, if, elif, else, for, while, try, except, finally, with
6. ✓ Use exactly THREE quotes for docstrings (not four): \"\"\" or '''
7. ✓ Escape special characters in strings: \\n, \\t, \\\", \\\\
8. ✓ Validate syntax before responding

CODE QUALITY REQUIREMENTS:
- Write clean, readable, well-documented code
- Follow PEP 8 style guidelines
- Include type hints where appropriate
- Add docstrings for functions and classes
- Handle errors appropriately

RESPONSE FORMAT:
Return ONLY valid Python code wrapped in ```python``` markers.
Do NOT include explanations outside the code block.

Example:
```python
def example_function(param: str) -> bool:
    \"\"\"
    Example function with proper syntax.
    
    Args:
        param: Description of parameter
        
    Returns:
        Boolean result
    \"\"\"
    result = param.strip()
    return bool(result)
```

IMPORTANT: Double-check your code for syntax errors before responding!
"""
        return prompt
    
    @staticmethod
    def get_code_fix_prompt(
        original_code: str,
        errors: List[str],
        attempt_number: int
    ) -> str:
        """
        Get prompt for fixing code with errors.
        
        Args:
            original_code: Code with errors
            errors: List of error messages
            attempt_number: Current attempt number
            
        Returns:
            Fix prompt string
        """
        errors_str = "\n".join(f"  {i+1}. {err}" for i, err in enumerate(errors))
        
        prompt = f"""The following code has syntax errors. Please fix them.

ATTEMPT #{attempt_number}

ORIGINAL CODE:
```python
{original_code}
```

ERRORS FOUND:
{errors_str}

INSTRUCTIONS:
1. Carefully read each error message
2. Locate the problematic line(s)
3. Fix the specific issues mentioned
4. Ensure no new errors are introduced
5. Return the complete fixed code

COMMON FIXES:
- Unclosed brackets: Add missing ), }}, or ]
- Unterminated strings: Add missing " or '
- F-string braces: Ensure {{}} are balanced
- Missing colons: Add : after def, class, if, etc.
- Incomplete statements: Complete assignments like "x = value"

RESPONSE FORMAT:
Return ONLY the fixed Python code in a code block:

```python
# Your fixed code here
```

DO NOT include explanations - only the corrected code!
"""
        return prompt
    
    @staticmethod
    def get_test_generation_prompt(
        code: str,
        file_path: str,
        test_type: str = "unit"
    ) -> str:
        """
        Get prompt for test generation.
        
        Args:
            code: Code to test
            file_path: Path to the code file
            test_type: Type of tests (unit, integration, both)
            
        Returns:
            Test generation prompt
        """
        prompt = f"""Generate {test_type} tests for the following code:

CODE TO TEST:
File: {file_path}

```python
{code}
```

TEST REQUIREMENTS:
1. Use pytest framework
2. Test normal cases and edge cases
3. Test error handling
4. Aim for high code coverage
5. Use descriptive test names
6. Add docstrings to test functions

CRITICAL SYNTAX RULES:
- Ensure ALL brackets are properly closed
- Ensure ALL strings are properly terminated
- Use exactly THREE quotes for docstrings
- Add colons after def statements
- Complete all statements

RESPONSE FORMAT:
Return ONLY valid Python test code:

```python
import pytest

def test_example():
    \"\"\"Test description.\"\"\"
    # Test implementation
    assert True
```

Generate comprehensive tests with proper syntax!
"""
        return prompt

