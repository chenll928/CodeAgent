"""
Enhanced Code Generator - Direct File Operations (No JSON Parsing).

Replaces the original CodeGenerator's JSON-based approach with direct
file operations for more reliable code generation and modification.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import re
import ast

from .requirement_analyzer import DesignPlan, Task
from .context_manager import ContextManager, PreciseContext
from .file_tools import FileTools, FileOperationResult, FileOperationStatus
from ..ai.enhanced_agent import EnhancedCodebaseAgent
from .code_validator import CodeValidator
from .code_auto_fixer import CodeAutoFixer
from .improved_retry_strategy import ImprovedRetryStrategy
from .improved_prompts import ImprovedPromptTemplates


@dataclass
class CodeImplementation:
    """Results of code implementation."""
    task: Task
    generated_code: str
    file_path: str
    integration_notes: List[str] = field(default_factory=list)
    imports_needed: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    test_suggestions: List[str] = field(default_factory=list)


@dataclass
class CodeModification:
    """Represents a modification to existing code."""
    file_path: str
    symbol_name: str
    original_code: str
    modified_code: str
    change_description: str
    affected_callers: List[str] = field(default_factory=list)
    migration_guide: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Generated test suite."""
    implementation: CodeImplementation
    test_file_path: str
    test_code: str
    test_cases: List[Dict[str, str]] = field(default_factory=list)
    coverage_notes: List[str] = field(default_factory=list)


class EnhancedCodeGenerator:
    """
    Enhanced Code Generator using direct file operations.
    
    Key differences from original CodeGenerator:
    1. No JSON parsing - extracts code directly from LLM response
    2. Uses FileTools for all file operations
    3. Automatic syntax validation before writing
    4. Better error handling and retry logic
    5. Direct code extraction from markdown code blocks
    
    Token usage per operation:
    - implement_new_feature: ~4KB
    - modify_existing_code: ~6KB
    - generate_tests: ~3KB
    """
    
    def __init__(
        self,
        agent: EnhancedCodebaseAgent,
        context_manager: ContextManager,
        workspace_root: Path,
        llm_provider: Optional[Any] = None
    ):
        """
        Initialize enhanced code generator.

        Args:
            agent: EnhancedCodebaseAgent for codebase context
            context_manager: ContextManager for precise context
            workspace_root: Root directory of workspace
            llm_provider: LLM provider instance
        """
        self.agent = agent
        self.context_manager = context_manager
        self.workspace_root = Path(workspace_root)
        self.llm_provider = llm_provider
        self.file_tools = FileTools(workspace_root)

        # Initialize new validation and fixing components
        self.validator = CodeValidator()
        self.auto_fixer = CodeAutoFixer()
        self.retry_strategy = ImprovedRetryStrategy(max_attempts=3, enable_auto_fix=True)
        self.prompt_templates = ImprovedPromptTemplates()
    
    def implement_new_feature(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext] = None,
        max_retries: int = 3
    ) -> CodeImplementation:
        """
        Implement a new feature and write to file system with enhanced validation.

        This method:
        1. Generates code using LLM with improved prompts
        2. Validates syntax with detailed error reporting
        3. Auto-fixes common syntax errors
        4. Writes to file using FileTools
        5. Returns implementation result

        Args:
            design: Design plan for the feature
            task: Specific task to implement
            context: Optional precise context
            max_retries: Maximum retry attempts

        Returns:
            CodeImplementation with generated code and file info
        """
        # Ensure repository context is initialized
        self.context_manager.agent._ensure_initialized()

        # Extract precise context if not provided
        if context is None and task.target_symbol:
            context = self.context_manager.extract_precise_context(
                target=task.target_symbol,
                token_budget=3500,
                task_type="new_feature"
            )

        # Validate task type matches file existence
        if task.task_type == "modify_file":
            if not self.agent.file_exists(task.target_file):
                print(f"[INFO] File {task.target_file} doesn't exist, treating as create_file")
                task.task_type = "create_file"

        # Build enhanced prompt
        base_prompt = self._build_enhanced_implementation_prompt(design, task, context)

        # Use improved retry strategy with auto-fixing
        if self.llm_provider:
            def llm_call(prompt: str) -> str:
                return self._call_llm(prompt, max_tokens=2000)

            result = self.retry_strategy.generate_with_retry(
                llm_call_func=llm_call,
                base_prompt=base_prompt,
                filename=task.target_file or '<string>',
                previous_errors=None
            )

            if result['success']:
                code = result['code']
                print(f"[INFO] Implementation succeeded on attempt {result['attempts']}")
                if result['fixes_applied']:
                    print(f"[INFO] Auto-fixes applied: {', '.join(result['fixes_applied'])}")
            else:
                print(f"[ERROR] All {result['attempts']} attempts failed")
                print(f"[ERROR] Last errors: {result['errors'][-3:]}")
                print(f"[WARN] Using basic template")
                code = self._generate_template_code(task)
        else:
            # Fallback: Basic template
            code = self._generate_template_code(task)

        # Create implementation object
        implementation = CodeImplementation(
            task=task,
            generated_code=code,
            file_path=task.target_file or self._infer_file_path(task, design),
            integration_notes=["Generated with enhanced validation and auto-fixing"]
        )

        # Write to file using FileTools
        try:
            file_result = self.file_tools.create_file(
                file_path=implementation.file_path,
                content=implementation.generated_code,
                overwrite=(task.task_type == "modify_file")
            )

            if file_result.status != FileOperationStatus.SUCCESS:
                raise IOError(f"Failed to write file: {file_result.message}")

            print(f"[INFO] File written: {implementation.file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to write file: {e}")
            # Still return implementation even if file write fails

        return implementation

    def modify_existing_code(
        self,
        target: str,
        modification_desc: str,
        context: Optional[PreciseContext] = None
    ) -> CodeModification:
        """
        Modify existing code using file operations.

        Args:
            target: Target symbol to modify
            modification_desc: Description of modification
            context: Precise context (auto-extracted if not provided)

        Returns:
            CodeModification with changes
        """
        # Extract context if not provided
        if context is None:
            context = self.context_manager.extract_precise_context(
                target=target,
                token_budget=5000,
                task_type="modification"
            )

        # Build prompt
        prompt = self._build_modification_prompt(target, modification_desc, context)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=2000)
            modified_code = self._extract_code_from_response(response)
        else:
            raise ValueError("LLM provider required for code modification")

        # Get file path from context
        file_path = context.target_code.get('file', '')

        # Read original code
        original_code = context.target_code.get('code', '')

        return CodeModification(
            file_path=file_path,
            symbol_name=target,
            original_code=original_code,
            modified_code=modified_code,
            change_description=modification_desc
        )

    def generate_tests(
        self,
        implementation: CodeImplementation,
        max_retries: int = 3
    ) -> TestSuite:
        """
        Generate test suite for implementation with enhanced validation.

        Args:
            implementation: CodeImplementation to test
            max_retries: Maximum retry attempts

        Returns:
            TestSuite with test code
        """
        # Build enhanced test prompt
        base_prompt = self.prompt_templates.get_test_generation_prompt(
            code=implementation.generated_code,
            file_path=implementation.file_path,
            test_type="unit"
        )

        # Use improved retry strategy
        if self.llm_provider:
            def llm_call(prompt: str) -> str:
                return self._call_llm(prompt, max_tokens=1500)

            result = self.retry_strategy.generate_with_retry(
                llm_call_func=llm_call,
                base_prompt=base_prompt,
                filename=self._get_test_file_path(implementation.file_path),
                previous_errors=None
            )

            if result['success']:
                test_code = result['code']
                print(f"[INFO] Test generation succeeded on attempt {result['attempts']}")
                if result['fixes_applied']:
                    print(f"[INFO] Auto-fixes applied: {', '.join(result['fixes_applied'])}")
            else:
                print(f"[WARN] Test generation failed, using template")
                test_code = self._generate_test_template(implementation)
        else:
            test_code = self._generate_test_template(implementation)

        # Determine test file path
        test_file_path = self._get_test_file_path(implementation.file_path)

        return TestSuite(
            implementation=implementation,
            test_file_path=test_file_path,
            test_code=test_code,
            coverage_notes=["Generated with enhanced validation"]
        )

    # ===== Helper Methods =====

    def _build_enhanced_implementation_prompt(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext]
    ) -> str:
        """
        Build enhanced prompt using improved templates.

        This method uses the ImprovedPromptTemplates to generate
        prompts that reduce syntax errors.
        """
        context_str = self._format_context(context) if context else "No context available"

        # Extract requirement text
        requirement_text = design.requirement_analysis.requirement_text if design.requirement_analysis else task.description

        # Build additional requirements section
        additional_requirements = f"""
DESIGN PLAN:
- Technical Approach: {design.technical_approach}
- New Components: {', '.join(c.get('name', '') for c in design.new_components)}

TASK DETAILS:
- Type: {task.task_type}
- Target Symbol: {task.target_symbol or 'N/A'}

CODEBASE CONTEXT:
{context_str}
"""

        if design.integration_points:
            integration_info = "\n".join([
                f"- {ip.get('name', 'unknown')}: {ip.get('purpose', '')}"
                for ip in design.integration_points[:3]
            ])
            additional_requirements += f"\nINTEGRATION POINTS:\n{integration_info}\n"

        # Use improved prompt template
        return self.prompt_templates.get_code_generation_prompt(
            task_description=requirement_text,
            context=context_str,
            file_path=task.target_file or "new_file.py",
            additional_requirements=additional_requirements
        )

    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract code from LLM response (no JSON parsing).

        Looks for:
        1. Python code blocks (```python ... ```)
        2. Generic code blocks (``` ... ```)
        3. Raw code if no blocks found

        Args:
            response: LLM response text

        Returns:
            Extracted code string
        """
        print(f"\n[DEBUG] Extracting code from response (length: {len(response)})")
        print(f"[DEBUG] Response preview: {response[:300]}")

        # Try to find Python code block
        python_pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(python_pattern, response, re.DOTALL | re.IGNORECASE)
        if matches:
            code = matches[0].strip()
            print(f"[DEBUG] Found Python code block (length: {len(code)})")
            return code

        # Try generic code block
        code_pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            code = matches[0].strip()
            print(f"[DEBUG] Found generic code block (length: {len(code)})")
            return code

        # Try to find code without markers
        # Look for lines that start with 'def ', 'class ', 'import ', etc.
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            stripped = line.strip()
            # Start of code
            if stripped.startswith(('def ', 'class ', 'import ', 'from ', '@')):
                in_code = True

            if in_code:
                code_lines.append(line)

        if code_lines:
            code = '\n'.join(code_lines).strip()
            print(f"[DEBUG] Extracted code without markers (length: {len(code)})")
            return code

        # Last resort: return entire response
        print(f"[WARN] Could not find code blocks, returning entire response")
        return response.strip()

    def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call LLM provider."""
        if not self.llm_provider:
            return ""

        try:
            if hasattr(self.llm_provider, 'chat'):
                response = self.llm_provider.chat(prompt, max_tokens=max_tokens)
            elif hasattr(self.llm_provider, 'complete'):
                response = self.llm_provider.complete(prompt, max_tokens=max_tokens)
            else:
                response = str(self.llm_provider(prompt))

            print(f"\n[DEBUG] LLM Response received (length: {len(response)})")
            return response
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _build_implementation_prompt(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext]
    ) -> str:
        """Build prompt for feature implementation."""
        from textwrap import dedent

        # Extract requirement text from design plan
        requirement_text = design.requirement_analysis.requirement_text if design.requirement_analysis else "No requirement specified"

        prompt = dedent(f"""
        You are an expert Python developer. Generate clean, production-ready code.

        REQUIREMENT:
        {requirement_text}

        TASK:
        {task.description}

        FILE: {task.target_file or 'to be determined'}

        TECHNICAL APPROACH:
        {design.technical_approach}
        """)

        if context and context.target_code:
            prompt += dedent(f"""

            CONTEXT:
            {self._format_context(context)}
            """)

        if design.integration_points:
            integration_info = "\n".join([f"- {ip.get('name', 'unknown')}: {ip.get('purpose', '')}"
                                         for ip in design.integration_points[:3]])
            prompt += dedent(f"""

            INTEGRATION POINTS:
            {integration_info}
            """)

        prompt += dedent("""

        INSTRUCTIONS:
        1. Generate complete, working Python code
        2. Include all necessary imports
        3. Add clear docstrings
        4. Follow PEP 8 style guidelines
        5. Handle errors appropriately
        6. Return ONLY the Python code in a ```python code block

        Generate the code now:
        """)

        return prompt

    def _build_modification_prompt(
        self,
        target: str,
        modification_desc: str,
        context: PreciseContext
    ) -> str:
        """Build prompt for code modification."""
        from textwrap import dedent

        original_code = context.target_code.get('code', '')

        prompt = dedent(f"""
        You are an expert Python developer. Modify the following code.

        TARGET: {target}
        FILE: {context.target_code.get('file', 'unknown')}

        MODIFICATION REQUEST:
        {modification_desc}

        ORIGINAL CODE:
        ```python
        {original_code}
        ```

        CONTEXT:
        {self._format_context(context)}

        INSTRUCTIONS:
        1. Modify the code according to the request
        2. Maintain backward compatibility if possible
        3. Keep the same function/class signature unless explicitly requested
        4. Add comments explaining changes
        5. Return ONLY the modified Python code in a ```python code block

        Generate the modified code now:
        """)

        return prompt

    def _build_test_prompt(self, implementation: CodeImplementation) -> str:
        """Build prompt for test generation."""
        from textwrap import dedent

        prompt = dedent(f"""
        You are an expert Python developer. Generate comprehensive tests.

        CODE TO TEST:
        ```python
        {implementation.generated_code}
        ```

        FILE: {implementation.file_path}

        INSTRUCTIONS:
        1. Generate pytest-compatible test code
        2. Test all functions and classes
        3. Include edge cases and error handling
        4. Use clear test names
        5. Add docstrings to tests
        6. Return ONLY the test code in a ```python code block

        Generate the test code now:
        """)

        return prompt

    def _format_context(self, context: Optional[PreciseContext]) -> str:
        """Format context for prompt."""
        if not context or not context.target_code:
            return "No context available"

        parts = []

        # Target code
        if context.target_code:
            parts.append(f"Target: {context.target_code.get('symbol', 'unknown')}")
            parts.append(f"File: {context.target_code.get('file', 'unknown')}")
            if context.target_code.get('signature'):
                parts.append(f"Signature: {context.target_code['signature']}")

        # Dependencies
        if context.direct_dependencies:
            deps = [d.get('name', '') for d in context.direct_dependencies[:3]]
            parts.append(f"Dependencies: {', '.join(deps)}")

        # Similar patterns
        if context.similar_patterns:
            patterns = [p.get('symbol', '') for p in context.similar_patterns[:2]]
            parts.append(f"Similar patterns: {', '.join(patterns)}")

        return "\n".join(parts)

    def _generate_template_code(self, task: Task) -> str:
        """Generate basic template code as fallback."""
        from textwrap import dedent

        template = dedent(f'''
        """
        {task.description}

        This is a template implementation.
        TODO: Implement the actual functionality.
        """

        def main():
            """Main function."""
            # TODO: Implement
            pass

        if __name__ == "__main__":
            main()
        ''').strip()

        return template

    def _generate_test_template(self, implementation: CodeImplementation) -> str:
        """Generate basic test template."""
        from textwrap import dedent

        module_name = Path(implementation.file_path).stem

        template = dedent(f'''
        """
        Tests for {module_name}.
        """

        import pytest
        from {module_name} import *

        def test_basic():
            """Basic test."""
            # TODO: Implement test
            assert True
        ''').strip()

        return template

    def _get_test_file_path(self, file_path: str) -> str:
        """Get test file path for a source file."""
        path = Path(file_path)

        # If in src/, put tests in tests/
        if 'src' in path.parts:
            parts = list(path.parts)
            src_idx = parts.index('src')
            parts[src_idx] = 'tests'
            parts[-1] = f"test_{path.name}"
            return str(Path(*parts))

        # Otherwise, add test_ prefix
        return str(path.parent / f"test_{path.name}")

    def _infer_file_path(self, task: Task, design: DesignPlan) -> str:
        """Infer file path from task and design."""
        # Try to get from task
        if task.target_file:
            return task.target_file

        # Try to infer from task description
        desc_lower = task.description.lower()

        # Look for file mentions
        if 'file' in desc_lower:
            # Try to extract filename
            words = task.description.split()
            for word in words:
                if word.endswith('.py'):
                    return word

        # Default: create in src/ directory
        # Use task_id as filename
        safe_name = task.task_id.replace('task_', '').replace('-', '_')
        return f"src/{safe_name}.py"
