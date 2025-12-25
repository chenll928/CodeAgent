"""
Enhanced Code Validator Module

This module provides comprehensive code validation and auto-fixing capabilities
to address syntax errors in LLM-generated code.
"""

import ast
import re
from typing import List, Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CodeValidator:
    """Enhanced code validator with syntax checking and common issue detection."""
    
    @staticmethod
    def validate_syntax(code: str, filename: str = '<string>') -> Tuple[bool, List[str]]:
        """
        Validate Python syntax.
        
        Args:
            code: Python code to validate
            filename: Filename for error reporting
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        try:
            ast.parse(code, filename=filename)
            return True, []
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f" - Text: {e.text.strip()}"
            errors.append(error_msg)
            logger.warning(f"Syntax error in {filename}: {error_msg}")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected validation error in {filename}: {e}")
            return False, errors
    
    @staticmethod
    def check_common_issues(code: str) -> List[str]:
        """
        Check for common syntax issues that might not be caught by AST.
        
        Args:
            code: Python code to check
            
        Returns:
            List of issue descriptions
        """
        issues = []
        
        # Check unmatched brackets
        if code.count('(') != code.count(')'):
            issues.append(f"Unmatched parentheses: {code.count('(')} open, {code.count(')')} close")
        if code.count('{') != code.count('}'):
            issues.append(f"Unmatched braces: {code.count('{')} open, {code.count('}')} close")
        if code.count('[') != code.count(']'):
            issues.append(f"Unmatched brackets: {code.count('[')} open, {code.count(']')} close")
        
        # Check f-strings for unmatched braces
        fstring_pattern = r'f["\'].*?["\']'
        for match in re.finditer(fstring_pattern, code, re.DOTALL):
            fstring = match.group()
            # Count braces in f-string (excluding escaped ones)
            brace_open = len(re.findall(r'(?<!\\)\{', fstring))
            brace_close = len(re.findall(r'(?<!\\)\}', fstring))
            if brace_open != brace_close:
                issues.append(f"Unmatched braces in f-string at position {match.start()}: {fstring[:50]}...")
        
        # Check for incomplete statements
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check for incomplete assignments
            if '=' in stripped and stripped.endswith('='):
                issues.append(f"Line {i}: Incomplete assignment statement")
            # Check for incomplete function definitions
            if stripped.startswith('def ') and not stripped.endswith(':'):
                if i < len(lines) and not lines[i].strip().startswith('"""'):
                    issues.append(f"Line {i}: Function definition missing colon")
        
        # Check for unterminated strings
        quote_count = 0
        triple_quote_count = 0
        in_string = False
        escape_next = False
        
        for char in code:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                quote_count += 1
        
        if quote_count % 2 != 0:
            issues.append("Possible unterminated string (odd number of quotes)")
        
        return issues
    
    @staticmethod
    def validate_with_details(code: str, filename: str = '<string>') -> Dict[str, Any]:
        """
        Comprehensive validation with detailed results.
        
        Args:
            code: Python code to validate
            filename: Filename for error reporting
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': False,
            'syntax_errors': [],
            'common_issues': [],
            'warnings': [],
            'code_length': len(code),
            'line_count': len(code.split('\n'))
        }
        
        # Syntax validation
        is_valid, syntax_errors = CodeValidator.validate_syntax(code, filename)
        result['is_valid'] = is_valid
        result['syntax_errors'] = syntax_errors
        
        # Common issues check
        result['common_issues'] = CodeValidator.check_common_issues(code)
        
        # Additional warnings
        if not code.strip():
            result['warnings'].append("Code is empty")
        elif len(code) < 10:
            result['warnings'].append("Code is suspiciously short")
        
        return result

