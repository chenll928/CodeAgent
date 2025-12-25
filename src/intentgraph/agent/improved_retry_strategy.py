"""
Improved Retry Strategy Module

This module provides enhanced retry strategies with error feedback
for LLM code generation.
"""

import logging
from typing import Optional, Callable, List, Dict, Any
from .code_validator import CodeValidator
from .code_auto_fixer import CodeAutoFixer

logger = logging.getLogger(__name__)


class ImprovedRetryStrategy:
    """Enhanced retry strategy with error feedback and auto-fixing."""
    
    def __init__(self, max_attempts: int = 3, enable_auto_fix: bool = True):
        """
        Initialize retry strategy.
        
        Args:
            max_attempts: Maximum number of retry attempts
            enable_auto_fix: Whether to enable automatic code fixing
        """
        self.max_attempts = max_attempts
        self.enable_auto_fix = enable_auto_fix
        self.validator = CodeValidator()
        self.auto_fixer = CodeAutoFixer()
    
    def generate_with_retry(
        self,
        llm_call_func: Callable[[str], str],
        base_prompt: str,
        filename: str = '<string>',
        previous_errors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate code with retry and error feedback.
        
        Args:
            llm_call_func: Function to call LLM (takes prompt, returns code)
            base_prompt: Base prompt for code generation
            filename: Filename for error reporting
            previous_errors: Previous errors to include in prompt
            
        Returns:
            Dictionary with 'code', 'success', 'attempts', 'errors', 'fixes_applied'
        """
        errors_history = previous_errors or []
        
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Generation attempt {attempt}/{self.max_attempts}")
            
            # Build enhanced prompt with error feedback
            prompt = self._build_enhanced_prompt(base_prompt, errors_history, attempt)
            
            try:
                # Call LLM
                response = llm_call_func(prompt)
                
                # Extract code from response
                code = self._extract_code(response)
                
                if not code:
                    error_msg = "No code found in LLM response"
                    errors_history.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Validate syntax
                is_valid, syntax_errors = self.validator.validate_syntax(code, filename)
                
                if is_valid:
                    logger.info(f"✓ Code generation succeeded on attempt {attempt}")
                    return {
                        'code': code,
                        'success': True,
                        'attempts': attempt,
                        'errors': [],
                        'fixes_applied': []
                    }
                
                # Syntax errors found
                logger.warning(f"Syntax errors on attempt {attempt}: {syntax_errors}")
                errors_history.extend(syntax_errors)
                
                # Try auto-fix if enabled
                if self.enable_auto_fix:
                    fixed_code, fixes_applied = self.auto_fixer.apply_all_fixes(code)
                    
                    if fixes_applied:
                        # Validate fixed code
                        is_valid, new_errors = self.validator.validate_syntax(fixed_code, filename)
                        
                        if is_valid:
                            logger.info(f"✓ Auto-fix successful on attempt {attempt}")
                            logger.info(f"  Applied fixes: {', '.join(fixes_applied)}")
                            return {
                                'code': fixed_code,
                                'success': True,
                                'attempts': attempt,
                                'errors': syntax_errors,
                                'fixes_applied': fixes_applied
                            }
                        else:
                            logger.warning(f"Auto-fix applied but code still invalid: {new_errors}")
                            errors_history.extend(new_errors)
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                errors_history.append(error_msg)
                logger.error(f"Attempt {attempt} failed: {e}", exc_info=True)
        
        # All attempts failed
        logger.error(f"✗ All {self.max_attempts} attempts failed")
        return {
            'code': None,
            'success': False,
            'attempts': self.max_attempts,
            'errors': errors_history,
            'fixes_applied': []
        }
    
    def _build_enhanced_prompt(
        self,
        base_prompt: str,
        errors_history: List[str],
        attempt: int
    ) -> str:
        """Build enhanced prompt with error feedback."""
        if attempt == 1 or not errors_history:
            return base_prompt
        
        # Add error feedback for retry attempts
        error_feedback = "\n\n" + "=" * 60 + "\n"
        error_feedback += f"PREVIOUS ATTEMPT(S) FAILED - ATTEMPT #{attempt}\n"
        error_feedback += "=" * 60 + "\n\n"
        error_feedback += "The following errors were found in previous attempts:\n\n"
        
        for i, error in enumerate(errors_history[-5:], 1):  # Show last 5 errors
            error_feedback += f"{i}. {error}\n"
        
        error_feedback += "\n" + "-" * 60 + "\n"
        error_feedback += "CRITICAL: Please fix these specific errors:\n"
        error_feedback += "- Ensure ALL brackets (), {}, [] are properly closed\n"
        error_feedback += "- Ensure ALL strings are properly terminated\n"
        error_feedback += "- Ensure ALL f-strings have matching braces\n"
        error_feedback += "- Add colons after def, class, if, for, while, etc.\n"
        error_feedback += "- Use exactly three quotes for docstrings (not four)\n"
        error_feedback += "- Complete all statements (no incomplete assignments)\n"
        error_feedback += "-" * 60 + "\n\n"
        
        return base_prompt + error_feedback
    
    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response."""
        import re
        
        # Try to extract from code blocks
        code_pattern = r'```(?:python)?\s*(.*?)\s*```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()
        
        # If no code blocks, check if entire response is code
        lines = response.strip().split('\n')
        code_indicators = ['def ', 'class ', 'import ', 'from ', 'async def', '@']
        code_lines = [l for l in lines if any(l.strip().startswith(ind) for ind in code_indicators)]
        
        if len(code_lines) >= max(2, len(lines) * 0.2):
            return response.strip()
        
        return ""

