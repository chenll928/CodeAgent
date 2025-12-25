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

        # Initialize new components
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
        Implement a new feature based on design and task with enhanced retry logic.

        LLM Call Point 4: ~4KB Token
        Input: Design plan + Task + Precise context
        Output: New code + Integration points

        Args:
            design: DesignPlan from requirement analyzer
            task: Specific task to implement
            context: Precise context (auto-extracted if not provided)
            max_retries: Maximum number of retry attempts

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

        # Validate task type matches file existence
        if task.task_type == "modify_file":
            if not self.agent.file_exists(task.target_file):
                print(f"[INFO] Adjusted task type from 'modify_file' to 'create_file' for {task.target_file} (file doesn't exist)")

        # Build enhanced prompt using new template
        base_prompt = self._build_enhanced_implementation_prompt(design, task, context)

        # Use improved retry strategy
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
                print(f"[INFO] Implementation succeeded on attempt {result['attempts']}")
                if result['fixes_applied']:
                    print(f"[INFO] Auto-fixes applied: {', '.join(result['fixes_applied'])}")

                # Parse the successful code
                implementation = self._create_implementation_from_code(
                    code=result['code'],
                    task=task
                )
                return implementation
            else:
                print(f"[ERROR] All {result['attempts']} attempts failed")
                print(f"[ERROR] Errors: {result['errors'][-3:]}")  # Show last 3 errors
                print(f"[WARN] Returning basic template")
                return self._generate_template(task)
        else:
            # Fallback: Basic template
            return self._generate_template(task)

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
        test_type: str = "unit",
        max_retries: int = 3
    ) -> TestSuite:
        """
        Generate test suite for implementation with retry logic.

        LLM Call Point 6: ~3KB Token
        Input: Implementation code + Interface definitions
        Output: Unit tests + Integration tests

        Args:
            implementation: CodeImplementation to test
            test_type: Type of tests ('unit', 'integration', 'both')
            max_retries: Maximum number of retry attempts

        Returns:
            TestSuite with generated tests
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Prepare prompt
                prompt = self._build_test_prompt(implementation, test_type)

                # Add retry context if this is a retry
                if attempt > 0:
                    prompt += f"\n\nPREVIOUS ATTEMPT FAILED: {last_error}\nPlease fix the issue and ensure valid JSON with proper escaping."

                # Call LLM
                if self.llm_provider:
                    response = self._call_llm(prompt, max_tokens=1500)
                    test_suite = self._parse_test_response(response, implementation)
                else:
                    # Fallback: Basic test template
                    test_suite = self._generate_test_template(implementation)

                # Validate syntax
                try:
                    compile(test_suite.test_code, test_suite.test_file_path, 'exec')
                    print(f"[INFO] Test generation succeeded on attempt {attempt + 1}")
                    return test_suite
                except SyntaxError as exc:
                    last_error = f"Syntax error: {exc}"
                    print(f"[WARN] Test compilation failed on attempt {attempt + 1}: {exc}")

                    # Try to fix common syntax errors
                    fixed_code = self._fix_common_syntax_errors(test_suite.test_code)
                    if fixed_code != test_suite.test_code:
                        test_suite.test_code = fixed_code
                        try:
                            compile(test_suite.test_code, test_suite.test_file_path, 'exec')
                            print(f"[INFO] Auto-fixed syntax error on attempt {attempt + 1}")
                            return test_suite
                        except:
                            pass

                    if attempt == max_retries - 1:
                        raise SyntaxError(f"Generated tests for {test_suite.test_file_path} failed to compile after {max_retries} attempts: {exc}")

            except Exception as e:
                last_error = str(e)
                print(f"[ERROR] Test generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Final fallback: return basic template
                    print(f"[WARN] All retry attempts failed, returning basic template")
                    return self._generate_test_template(implementation)

        # Should not reach here, but just in case
        return self._generate_test_template(implementation)

    # ===== Prompt Building Methods =====

    def _build_enhanced_implementation_prompt(
        self,
        design: DesignPlan,
        task: Task,
        context: Optional[PreciseContext]
    ) -> str:
        """Build enhanced prompt for new feature implementation using improved templates."""
        context_str = self._format_context(context) if context else "No context available"
        existing_paths = '\n'.join(sorted(self.agent.list_repo_files())[:50])

        additional_requirements = f"""
Design Plan:
- Approach: {design.technical_approach}
- New Components: {', '.join(c.get('name', '') for c in design.new_components)}

Task Details:
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
- Follow the existing code style and patterns from the context
- Do not introduce new directories outside those listed above
"""

        return self.prompt_templates.get_code_generation_prompt(
            task_description=task.description,
            context=context_str,
            file_path=task.target_file or "new_file.py",
            additional_requirements=additional_requirements
        )

    def _create_implementation_from_code(
        self,
        code: str,
        task: Task
    ) -> CodeImplementation:
        """Create CodeImplementation object from validated code."""
        file_path = task.target_file
        if not file_path or file_path == "unknown":
            file_path = self._generate_default_file_path(task)

        return CodeImplementation(
            task=task,
            generated_code=code,
            file_path=file_path,
            integration_notes=["Code generated with enhanced validation"],
            imports_needed=[],
            dependencies=[]
        )

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

CRITICAL INSTRUCTIONS FOR JSON FORMAT:
- Respond ONLY with a JSON object
- Do NOT wrap in markdown code blocks (no ```json or ```)
- Escape ALL special characters in the "code" field:
  * Use \\n for newlines (not actual newlines)
  * Use \\" for quotes inside strings
  * Use \\\\ for backslashes
  * Use \\t for tabs
- Ensure all docstrings use exactly three quotes (not four)
- The entire code must be a single escaped string
- Test your JSON is valid before responding

ALTERNATIVE: If JSON escaping is too complex, you can also respond with a Python code block:
```python
# Your complete code here
```

Use this exact format:
{{
    "code": "import os\\n\\ndef example():\\n    \\"\\"\\"Example function.\\"\\"\\"\\n    return True",
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

CRITICAL INSTRUCTIONS:
- Respond ONLY with a JSON object
- Do NOT wrap in markdown code blocks (no ```json or ```)
- Escape ALL special characters in strings:
  * Use \\n for newlines (not actual newlines)
  * Use \\" for quotes inside strings
  * Use \\\\ for backslashes
- Ensure all docstrings use exactly three quotes (not four)
- Test your JSON is valid before responding

Use this exact format:
{{
    "test_code": "import pytest\\n\\ndef test_example():\\n    \\"\\"\\"Test description.\\"\\"\\"\\n    assert True",
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
        # Try code block extraction first (more reliable)
        code_from_block = self._extract_code_block(response)

        try:
            # Clean and extract JSON from response
            json_str = self._clean_json_response(response)
            print(f"[DEBUG] Cleaned JSON string (first 300 chars): {json_str[:300]}")

            data = json.loads(json_str)

            # Extract code (handle both "code" and "generated_code" keys)
            code = data.get("code") or data.get("generated_code", "")

            # If no code in JSON but we found code block, use that
            if not code and code_from_block:
                print("[DEBUG] No code in JSON, using extracted code block")
                code = code_from_block

            # Ensure we have a valid file path
            file_path = task.target_file
            if not file_path or file_path == "unknown":
                file_path = self._generate_default_file_path(task)

            print(f"[DEBUG] Successfully parsed implementation:")
            print(f"  - File path: {file_path}")
            print(f"  - Code length: {len(code)} chars")
            print(f"  - Has code: {bool(code)}")

            return CodeImplementation(
                task=task,
                generated_code=code,
                file_path=file_path,
                integration_notes=data.get("integration_notes", []),
                imports_needed=data.get("imports", []),
                dependencies=data.get("dependencies", [])
            )
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON decode failed: {e}, falling back to code block extraction")
            if code_from_block:
                file_path = task.target_file or self._generate_default_file_path(task)
                print(f"[INFO] Using extracted code block: {len(code_from_block)} chars")
                return CodeImplementation(
                    task=task,
                    generated_code=code_from_block,
                    file_path=file_path,
                    integration_notes=["Extracted from code block"],
                    imports_needed=[],
                    dependencies=[]
                )
            print("[ERROR] No code found in response")
            return self._generate_template(task)
        except Exception as e:
            print(f"[ERROR] Unexpected error parsing implementation: {e}")
            if code_from_block:
                file_path = task.target_file or self._generate_default_file_path(task)
                print(f"[INFO] Using extracted code block as fallback: {len(code_from_block)} chars")
                return CodeImplementation(
                    task=task,
                    generated_code=code_from_block,
                    file_path=file_path,
                    integration_notes=["Extracted from code block (error fallback)"],
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
        """Clean LLM response to extract valid JSON with auto-repair."""
        import re

        # Remove markdown code blocks
        response = response.strip()

        print(f"[DEBUG _clean_json] Original response length: {len(response)}")
        print(f"[DEBUG _clean_json] First 200 chars: {response[:200]}")

        # Remove ```json and ``` markers (handle multiple variations)
        # Use \A and \Z to match absolute start/end of string, not line boundaries
        # This prevents accidentally removing content from within the JSON
        response = re.sub(r'\A```(?:json)?\s*\n?', '', response)
        response = re.sub(r'\n?\s*```\Z', '', response)
        response = response.strip()

        print(f"[DEBUG _clean_json] After removing markers length: {len(response)}")
        print(f"[DEBUG _clean_json] After removing markers first 200 chars: {response[:200]}")

        # Try to find JSON object with nested structures
        # This pattern handles nested braces better - but we need to be careful with strings
        brace_count = 0
        start_idx = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(response):
            # Handle string state
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            # Only count braces outside of strings
            if not in_string:
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        # Found complete JSON object
                        json_str = response[start_idx:i+1]
                        # Validate it's actually JSON-like
                        try:
                            json.loads(json_str)
                            print(f"[DEBUG _clean_json] Successfully found valid JSON via brace counting")
                            return json_str
                        except Exception as e:
                            # Try to repair the JSON before giving up
                            print(f"[DEBUG _clean_json] Brace counting found JSON-like structure but failed to parse: {str(e)[:100]}")
                            repaired = self._try_repair_json(json_str)
                            if repaired:
                                print(f"[DEBUG _clean_json] Successfully repaired JSON")
                                return repaired
                            # Continue searching for other potential JSON objects
                            start_idx = -1
                            continue

        print(f"[DEBUG _clean_json] Brace counting failed, trying regex fallback...")

        # Fallback: try to find the largest JSON-like structure
        # Look for patterns like {"key": "value", ...}
        json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_obj_pattern, response, re.DOTALL)
        print(f"[DEBUG _clean_json] Regex found {len(matches)} potential JSON objects")

        if matches:
            # Try each match to see if it's valid JSON
            for idx, match in enumerate(sorted(matches, key=len, reverse=True)):
                try:
                    json.loads(match)
                    print(f"[DEBUG _clean_json] Successfully validated match #{idx} (length: {len(match)})")
                    return match
                except Exception as e:
                    print(f"[DEBUG _clean_json] Match #{idx} failed validation: {e}")
                    # Try to repair
                    repaired = self._try_repair_json(match)
                    if repaired:
                        print(f"[DEBUG _clean_json] Successfully repaired match #{idx}")
                        return repaired
                    continue

        # Last resort: return as-is
        print(f"[DEBUG _clean_json] All parsing attempts failed, returning as-is (length: {len(response)})")
        return response

    def _try_repair_json(self, json_str: str) -> Optional[str]:
        """Attempt to repair malformed JSON string."""
        import re

        try:
            # Already valid
            json.loads(json_str)
            return json_str
        except:
            pass

        # Common repair strategies
        repairs = [
            # Fix quadruple quotes in docstrings ("""" -> """)
            lambda s: re.sub(r'"{4,}', '"""', s),

            # Fix unescaped newlines in strings (but not \\n)
            lambda s: self._fix_unescaped_newlines(s),

            # Fix trailing commas before closing braces
            lambda s: re.sub(r',(\s*[}\]])', r'\1', s),

            # Fix missing commas between array/object elements
            lambda s: re.sub(r'"\s*\n\s*"', '",\n"', s),
        ]

        for repair_fn in repairs:
            try:
                repaired = repair_fn(json_str)
                json.loads(repaired)
                return repaired
            except:
                continue

        return None

    def _fix_unescaped_newlines(self, json_str: str) -> str:
        """Fix unescaped newlines within JSON string values."""
        import re

        # This is complex - we need to find string values and escape newlines
        # Simple approach: find "key": "value" patterns and fix value
        def fix_string_value(match):
            key = match.group(1)
            value = match.group(2)
            # Escape unescaped newlines (not already \\n)
            value = re.sub(r'(?<!\\)\\n', r'\\n', value)
            # Escape unescaped quotes
            value = re.sub(r'(?<!\\)"', r'\"', value)
            return f'"{key}": "{value}"'

        # Match "key": "value" where value might have issues
        pattern = r'"([^"]+)":\s*"([^"]*)"'
        try:
            return re.sub(pattern, fix_string_value, json_str)
        except:
            return json_str

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
        """Extract code from response using multiple strategies."""
        import re

        # Strategy 1: Extract from JSON "code" field (even if JSON is malformed)
        # This handles cases where JSON parsing failed but the code field is intact
        try:
            # Match "code": "..." pattern with proper escape handling
            # This regex handles escaped quotes and newlines within the string
            code_pattern = r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(code_pattern, response, re.DOTALL)
            if match:
                code_str = match.group(1)
                # Unescape common escape sequences
                code_str = code_str.replace('\\n', '\n')
                code_str = code_str.replace('\\t', '\t')
                code_str = code_str.replace('\\"', '"')
                code_str = code_str.replace('\\\\', '\\')
                # Verify it's substantial code (not just a placeholder)
                if len(code_str) > 50 and ('def ' in code_str or 'class ' in code_str or 'import ' in code_str):
                    print(f"[DEBUG] Extracted code from JSON 'code' field: {len(code_str)} chars")
                    return code_str.strip()
        except Exception as e:
            print(f"[DEBUG] JSON field extraction failed: {e}")

        # Strategy 2: Find Python code blocks in markdown
        code_pattern = r'```(?:python)?\s*(.*?)\s*```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            # Return the longest code block (likely the main implementation)
            longest = max(matches, key=len)
            if len(longest) > 50:
                print(f"[DEBUG] Extracted Python code block: {len(longest)} chars")
                return longest.strip()

        # Strategy 3: Check if entire response looks like code
        lines = response.strip().split('\n')
        if len(lines) > 3:
            code_indicators = ['def ', 'class ', 'import ', 'from ', 'async def', '@']
            code_lines = [l for l in lines if any(l.strip().startswith(ind) for ind in code_indicators)]
            # If at least 20% of lines are code indicators, treat as code
            if len(code_lines) >= max(2, len(lines) * 0.2):
                print(f"[DEBUG] Treating entire response as code: {len(response)} chars")
                return response.strip()

        print("[DEBUG] No code found in response")
        return ""

    def _fix_common_syntax_errors(self, code: str) -> str:
        """Attempt to fix common syntax errors in generated code."""
        import re

        original_code = code

        # Fix 1: Quadruple quotes in docstrings ("""" -> """)
        code = re.sub(r'"{4,}', '"""', code)

        # Fix 2: Unterminated string literals - look for lines ending with odd number of quotes
        lines = code.split('\n')
        fixed_lines = []
        for line in lines:
            # Count unescaped quotes
            quote_count = len(re.findall(r'(?<!\\)"', line))
            # If odd number of quotes and line doesn't end with quote, might be unterminated
            if quote_count % 2 == 1 and not line.rstrip().endswith('"'):
                # Try to close the string
                line = line.rstrip() + '"'
            fixed_lines.append(line)
        code = '\n'.join(fixed_lines)

        # Fix 3: Missing colons after def/class/if/for/while/try/except/finally
        code = re.sub(r'(def\s+\w+\s*\([^)]*\))\s*$', r'\1:', code, flags=re.MULTILINE)
        code = re.sub(r'(class\s+\w+(?:\([^)]*\))?)\s*$', r'\1:', code, flags=re.MULTILINE)

        # Fix 4: Extra quotes around docstrings that are already quoted
        code = re.sub(r'""""{3,}', '"""', code)
        code = re.sub(r"'''{3,}", "'''", code)

        if code != original_code:
            print(f"[DEBUG] Applied syntax fixes to code")

        return code

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


