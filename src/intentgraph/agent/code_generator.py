"""
Code Generator for AI Coding Agent.

This module provides code generation capabilities:
- New feature implementation
- Existing code modification
- Test generation

Uses LLM for intelligent code generation.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json
from textwrap import dedent

from .requirement_analyzer import DesignPlan, Task
from .context_manager import ContextManager, PreciseContext
from ..ai.enhanced_agent import EnhancedCodebaseAgent


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


class CodeGenerator:
    """
    Code Generator for implementing features and modifications.

    This class uses LLM to:
    1. Generate new feature implementations
    2. Modify existing code safely
    3. Generate comprehensive tests

    Token usage per operation:
    - implement_new_feature: ~4KB
    - modify_existing_code: ~6KB
    - generate_tests: ~3KB
    """

    def __init__(
        self,
        agent: EnhancedCodebaseAgent,
        context_manager: ContextManager,
        llm_provider: Optional[Any] = None
    ):
        """
        Initialize code generator.

        Args:
            agent: EnhancedCodebaseAgent for codebase context
            context_manager: ContextManager for precise context
            llm_provider: LLM provider instance
        """
        self.agent = agent
        self.context_manager = context_manager
        self.llm_provider = llm_provider

    def implement_new_feature(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext] = None
    ) -> CodeImplementation:
        """
        Implement a new feature based on design and task.

        LLM Call Point 4: ~4KB Token
        Input: Design plan + Task + Precise context
        Output: New code + Integration points

        Args:
            design: DesignPlan from requirement analyzer
            task: Specific task to implement
            context: Precise context (auto-extracted if not provided)

        Returns:
            CodeImplementation with generated code
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

        if task.task_type == "modify_file" and not self.agent.file_exists(task.target_file):
            raise FileNotFoundError(f"Workflow specified modification task for missing file: {task.target_file}")

        # Prepare prompt
        prompt = self._build_implementation_prompt(design, task, context)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=2000)

            if task.task_type == "modify_file" and not self.agent.file_exists(task.target_file):
                raise ValueError(f"Target file {task.target_file} does not exist for modification task")

            implementation = self._parse_implementation_response(response, task)
        else:
            # Fallback: Basic template
            implementation = self._generate_template(task)

        try:
            compile(implementation.generated_code, task.target_file or '<string>', 'exec')
        except SyntaxError as exc:
            raise SyntaxError(f"Generated code for {task.target_file} failed to compile: {exc}")

        return implementation

    def modify_existing_code(
        self,
        target: str,
        modification_desc: str,
        context: Optional[PreciseContext] = None
    ) -> CodeModification:
        """
        Modify existing code safely.

        LLM Call Point 5: ~6KB Token
        Input: Target code + Call chain + Impact analysis + Modification description
        Output: Modified code + Migration guide

        Args:
            target: Target symbol to modify
            modification_desc: Description of modification
            context: Precise context (auto-extracted if not provided)

        Returns:
            CodeModification with changes and migration guide
        """
        # Extract precise context with impact analysis
        if context is None:
            context = self.context_manager.extract_precise_context(
                target=target,
                token_budget=5000,
                task_type="modify"
            )

        # Get original code
        original_code = context.target_code.get("code", "")

        # Prepare prompt
        prompt = self._build_modification_prompt(target, modification_desc, context)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=2500)
            modification = self._parse_modification_response(response, target, original_code)
        else:
            # Fallback: Return original with note
            modification = CodeModification(
                file_path=context.target_code.get("file", ""),
                symbol_name=target,
                original_code=original_code,
                modified_code=original_code,
                change_description=modification_desc
            )

        # Ensure file path is tracked
        if not modification.file_path and context.target_code.get("file"):
            modification.file_path = context.target_code["file"]

        return modification

    def generate_tests(
        self,
        implementation: CodeImplementation,
        test_type: str = "unit"
    ) -> TestSuite:
        """
        Generate test suite for implementation.

        LLM Call Point 6: ~3KB Token
        Input: Implementation code + Interface definitions
        Output: Unit tests + Integration tests

        Args:
            implementation: CodeImplementation to test
            test_type: Type of tests ('unit', 'integration', 'both')

        Returns:
            TestSuite with generated tests
        """
        # Prepare prompt
        prompt = self._build_test_prompt(implementation, test_type)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=1500)
            test_suite = self._parse_test_response(response, implementation)
        else:
            # Fallback: Basic test template
            test_suite = self._generate_test_template(implementation)

        try:
            compile(test_suite.test_code, test_suite.test_file_path, 'exec')
        except SyntaxError as exc:
            raise SyntaxError(f"Generated tests for {test_suite.test_file_path} failed to compile: {exc}")

        return test_suite

    # ===== Prompt Building Methods =====

    def _build_implementation_prompt(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext]
    ) -> str:
        """Build prompt for new feature implementation."""
        context_str = self._format_context(context) if context else "No context available"

        existing_paths = '\n'.join(sorted(self.agent.list_repo_files())[:50])

        prompt = f"""Implement the following task based on the design plan.

Design Plan:
- Approach: {design.technical_approach}
- New Components: {', '.join(c.get('name', '') for c in design.new_components)}

Task:
- Description: {task.description}
- Type: {task.task_type}
- Target File: {task.target_file or 'New file'}
- Target Symbol: {task.target_symbol or 'N/A'}

Context from Codebase:
{context_str}

Existing files for reference:
{existing_paths}

IMPORTANT:
- Only generate code for file: {task.target_file}
- Do not introduce new directories outside those listed above.

Please provide:
1. Complete implementation code
2. Required imports
3. Integration notes (how to integrate with existing code)
4. Dependencies (other modules/functions needed)

Respond ONLY with a JSON object. Do NOT wrap in markdown code blocks.
Use this exact format:
{{
    "code": "your complete code here",
    "imports": ["import statement 1", "import statement 2"],
    "integration_notes": ["note 1", "note 2"],
    "dependencies": ["dependency 1", "dependency 2"]
}}

Follow the existing code style and patterns from the context.
"""
        return prompt

    def _build_modification_prompt(
        self,
        target: str,
        modification_desc: str,
        context: PreciseContext
    ) -> str:
        """Build prompt for code modification."""
        original_code = context.target_code.get("code", "")
        call_chain_info = self._format_call_chain(context.call_chain)

        prompt = f"""Modify the following code according to the requirements.

Target: {target}
File: {context.target_code.get('file', 'unknown')}

Original Code:
```python
{original_code}
```

Modification Required:
{modification_desc}

Call Chain (Callers of this function):
{call_chain_info}

Impact Analysis:
{self._format_impact(context.impact_analysis)}

Please provide:
1. Modified code (complete function/class)
2. Change description
3. Affected callers (list of functions that may need updates)
4. Migration guide (steps to update callers)

Respond in JSON format:
{{
    "modified_code": "...",
    "change_description": "...",
    "affected_callers": ["...", "..."],
    "migration_guide": ["...", "..."]
}}

Ensure backward compatibility where possible.
"""
        return prompt

    def _build_test_prompt(
        self,
        implementation: CodeImplementation,
        test_type: str
    ) -> str:
        """Build prompt for test generation."""
        prompt = f"""Generate {test_type} tests for the following implementation.

Implementation:
File: {implementation.file_path}
Code:
```python
{implementation.generated_code}
```

Integration Notes:
{chr(10).join(f"- {note}" for note in implementation.integration_notes)}

Please provide:
1. Complete test code (using pytest)
2. Test cases (description of each test)
3. Coverage notes (what is tested and what might need manual testing)

Respond ONLY with a JSON object. Do NOT wrap in markdown code blocks.
Use this exact format:
{{
    "test_code": "your complete test code here",
    "test_cases": [
        {{"name": "test_function_name", "description": "what it tests"}},
        {{"name": "test_another", "description": "what it tests"}}
    ],
    "coverage_notes": ["note 1", "note 2"]
}}

Include edge cases and error handling tests.
"""
        return prompt

    # ===== Response Parsing Methods =====

    def _parse_implementation_response(
        self,
        response: str,
        task: Task
    ) -> CodeImplementation:
        """Parse LLM response into CodeImplementation."""
        try:
            # Clean and extract JSON from response
            json_str = self._clean_json_response(response)
            data = json.loads(json_str)

            # Extract code (handle both "code" and "generated_code" keys)
            code = data.get("code") or data.get("generated_code", "")

            # If no code in JSON, try to extract code blocks from response
            if not code:
                code = self._extract_code_block(response)

            # Ensure we have a valid file path
            file_path = task.target_file
            if not file_path or file_path == "unknown":
                file_path = self._generate_default_file_path(task)

            return CodeImplementation(
                task=task,
                generated_code=code,
                file_path=file_path,
                integration_notes=data.get("integration_notes", []),
                imports_needed=data.get("imports", []),
                dependencies=data.get("dependencies", [])
            )
        except Exception as e:
            print(f"Failed to parse implementation response: {e}")
            print(f"Response preview: {response[:200]}...")
            # Try to extract code directly from response
            code = self._extract_code_block(response)
            if code:
                file_path = task.target_file or self._generate_default_file_path(task)
                return CodeImplementation(
                    task=task,
                    generated_code=code,
                    file_path=file_path,
                    integration_notes=["Extracted from non-JSON response"],
                    imports_needed=[],
                    dependencies=[]
                )
            return self._generate_template(task)

    def _parse_modification_response(
        self,
        response: str,
        target: str,
        original_code: str
    ) -> CodeModification:
        """Parse LLM response into CodeModification."""
        try:
            data = json.loads(response)
            return CodeModification(
                file_path="",  # Will be filled by caller
                symbol_name=target,
                original_code=original_code,
                modified_code=data.get("modified_code", original_code),
                change_description=data.get("change_description", ""),
                affected_callers=data.get("affected_callers", []),
                migration_guide=data.get("migration_guide", [])
            )
        except:
            return CodeModification(
                file_path="",
                symbol_name=target,
                original_code=original_code,
                modified_code=original_code,
                change_description="Failed to parse modification"
            )

    def _parse_test_response(
        self,
        response: str,
        implementation: CodeImplementation
    ) -> TestSuite:
        """Parse LLM response into TestSuite."""
        try:
            # Clean and extract JSON from response
            json_str = self._clean_json_response(response)
            data = json.loads(json_str)

            # Extract test code
            test_code = data.get("test_code", "")

            # If no test code in JSON, try to extract from code blocks
            if not test_code:
                test_code = self._extract_code_block(response)

            test_file = self._get_test_file_path(implementation.file_path)
            return TestSuite(
                implementation=implementation,
                test_file_path=test_file,
                test_code=test_code,
                test_cases=data.get("test_cases", []),
                coverage_notes=data.get("coverage_notes", [])
            )
        except Exception as e:
            print(f"Failed to parse test response: {e}")
            print(f"Response preview: {response[:200]}...")
            # Try to extract test code directly
            test_code = self._extract_code_block(response)
            if test_code:
                test_file = self._get_test_file_path(implementation.file_path)
                return TestSuite(
                    implementation=implementation,
                    test_file_path=test_file,
                    test_code=test_code,
                    test_cases=[],
                    coverage_notes=["Extracted from non-JSON response"]
                )
            return self._generate_test_template(implementation)

    # ===== Helper Methods =====

    def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call LLM provider."""
        if not self.llm_provider:
            return "{}"

        try:
            if hasattr(self.llm_provider, 'chat'):
                response = self.llm_provider.chat(prompt, max_tokens=max_tokens)
            elif hasattr(self.llm_provider, 'complete'):
                response = self.llm_provider.complete(prompt, max_tokens=max_tokens)
            else:
                response = str(self.llm_provider(prompt))

            # Debug: Log response preview
            print(f"\n[DEBUG] LLM Response Preview (first 500 chars):")
            print(response[:500])
            print(f"[DEBUG] Response length: {len(response)} chars")

            return response
        except Exception as e:
            print(f"LLM call failed: {e}")
            import traceback
            traceback.print_exc()
            return "{}"

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

    def _format_call_chain(self, call_chain: Optional[Dict[str, Any]]) -> str:
        """Format call chain for prompt."""
        if not call_chain:
            return "No call chain information"

        parts = []

        upstream = call_chain.get("upstream", [])
        if upstream:
            parts.append("Callers:")
            for caller in upstream[:3]:
                parts.append(f"  - {caller.get('symbol')} in {caller.get('file')}")

        downstream = call_chain.get("downstream", [])
        if downstream:
            parts.append("Callees:")
            for callee in downstream[:3]:
                parts.append(f"  - {callee.get('symbol')} in {callee.get('file')}")

        return "\n".join(parts) if parts else "No call chain information"

    def _extract_json(self, response: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        import re

        # Try to find JSON in markdown code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            return matches[0]

        # Try to find JSON object directly
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            # Return the largest JSON object found
            return max(matches, key=len)

        # Return original response
        return response

    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON."""
        import re

        # Remove markdown code blocks
        response = response.strip()

        # Remove ```json and ``` markers (handle multiple variations)
        response = re.sub(r'^```(?:json)?\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        response = response.strip()

        # Try to find JSON object with nested structures
        # This pattern handles nested braces better
        brace_count = 0
        start_idx = -1

        for i, char in enumerate(response):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # Found complete JSON object
                    return response[start_idx:i+1]

        # Fallback: try simple regex
        json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        match = re.search(json_obj_pattern, response, re.DOTALL)
        if match:
            return match.group(0)

        # Last resort: return as-is
        return response

    def _generate_default_file_path(self, task: Task) -> str:
        """Generate a default file path when task doesn't have one."""
        task_type = task.task_type
        description = task.description.lower()

        # Extract potential file name from description
        import re
        words = re.findall(r'\b[a-z_]+\b', description)

        if task_type == "create_file":
            if task.target_symbol:
                return f"src/{task.target_symbol.lower()}.py"
            elif words:
                return f"src/{words[0]}.py"
            else:
                return "src/new_module.py"

        elif task_type == "add_test":
            if task.target_symbol:
                return f"tests/test_{task.target_symbol.lower()}.py"
            elif words:
                return f"tests/test_{words[0]}.py"
            else:
                return "tests/test_new_module.py"

        else:
            if task.target_symbol:
                return f"src/{task.target_symbol.lower()}.py"
            elif words:
                return f"src/{words[0]}.py"
            else:
                return "src/modified_module.py"

    def _extract_code_block(self, response: str) -> str:
        """Extract code from markdown code blocks."""
        import re

        # Try to find Python code blocks
        code_pattern = r'```(?:python)?\s*(.*?)\s*```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            # Return the first/largest code block
            return matches[0].strip()

        # If no code blocks, check if entire response looks like code
        lines = response.strip().split('\n')
        if len(lines) > 3 and any(line.strip().startswith(('def ', 'class ', 'import ', 'from ')) for line in lines):
            return response.strip()

        return ""

    def _format_impact(self, impact_analysis: Any) -> str:
        """Format impact analysis for prompt."""
        if not impact_analysis:
            return "No impact analysis available"

        parts = []
        parts.append(f"Risk Level: {impact_analysis.risk_level}")

        if impact_analysis.direct_callers:
            parts.append(f"Direct Callers: {len(impact_analysis.direct_callers)}")

        if impact_analysis.breaking_changes:
            parts.append("Breaking Changes:")
            for change in impact_analysis.breaking_changes[:2]:
                parts.append(f"  - {change}")

        return "\n".join(parts)

    def _generate_template(self, task: Task) -> CodeImplementation:
        """Generate basic code template."""
        template = f"""# TODO: Implement {task.description}

def placeholder():
    \"\"\"
    {task.description}
    \"\"\"
    pass
"""
        return CodeImplementation(
            task=task,
            generated_code=template,
            file_path=task.target_file or "new_file.py",
            integration_notes=["Manual implementation required"]
        )

    def _generate_test_template(self, implementation: CodeImplementation) -> TestSuite:
        """Generate basic test template."""
        test_file = self._get_test_file_path(implementation.file_path)
        template = f"""import pytest

# TODO: Add tests for {implementation.file_path}

def test_placeholder():
    \"\"\"Test placeholder.\"\"\"
    assert True
"""
        return TestSuite(
            implementation=implementation,
            test_file_path=test_file,
            test_code=template,
            coverage_notes=["Manual test implementation required"]
        )

    def _get_test_file_path(self, source_file: str) -> str:
        """Get corresponding test file path."""
        path = Path(source_file)
        file_name = path.stem

        test_dir = Path("tests") / path.parent.name if path.parent.name != "src" else Path("tests")
        normalized = (test_dir / f"test_{file_name}.py").as_posix()
        normalized = normalized.replace('tests/tests', 'tests')

        return normalized

    def get_code_style_guide(self) -> Dict[str, Any]:
        """Extract code style guide from existing codebase."""
        # Analyze existing code for style patterns
        style_guide = {
            "indentation": "4 spaces",
            "quotes": "double",
            "docstring_style": "google",
            "type_hints": True,
            "max_line_length": 100
        }

        # TODO: Implement actual style detection from codebase
        return style_guide

    def _build_file_inventory(self) -> List[str]:
        """Return a sorted list of repo files for guardrail prompts."""
        try:
            return sorted(self.agent.list_repo_files())
        except Exception:
            repo = self.agent.repo_path
            return sorted(str(p.relative_to(repo)) for p in repo.rglob('*.py'))

    def validate_generated_code(self, code: str) -> Dict[str, Any]:
        """Validate generated code for syntax and style."""
        validation = {
            "syntax_valid": True,
            "style_issues": [],
            "warnings": []
        }

        # Basic syntax check
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            validation["syntax_valid"] = False
            validation["warnings"].append(f"Syntax error: {e}")

        return validation


