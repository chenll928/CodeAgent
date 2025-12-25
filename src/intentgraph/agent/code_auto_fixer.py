"""
Code Auto-Fixer Module

This module provides automatic fixing capabilities for common syntax errors
in LLM-generated code.
"""

import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class CodeAutoFixer:
    """Automatic fixer for common syntax errors in generated code."""
    
    @staticmethod
    def fix_unclosed_brackets(code: str) -> str:
        """Attempt to fix unclosed brackets, braces, and parentheses."""
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            paren_open = line.count('(') - line.count(')')
            bracket_open = line.count('[') - line.count(']')
            brace_open = line.count('{') - line.count('}')
            
            is_continuation = line.rstrip().endswith('\\')
            next_line_continues = i + 1 < len(lines) and lines[i + 1].strip().startswith((')', ']', '}', ','))
            
            if not is_continuation and not next_line_continues:
                if paren_open > 0:
                    line = line.rstrip() + ')' * paren_open
                if bracket_open > 0:
                    line = line.rstrip() + ']' * bracket_open
                if brace_open > 0:
                    line = line.rstrip() + '}' * brace_open
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def fix_incomplete_statements(code: str) -> str:
        """Fix incomplete statements like assignments without values."""
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if '=' in stripped and stripped.endswith('='):
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
                    fixed_lines.append(line)
                else:
                    line = line.rstrip() + ' None'
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def fix_unterminated_strings(code: str) -> str:
        """Attempt to fix unterminated string literals."""
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            quote_count = len(re.findall(r'(?<!\\)"', line))
            
            if quote_count % 2 == 1 and not line.rstrip().endswith('"'):
                if 'f"' in line or 'f\'' in line:
                    if '{' in line and not '}' in line:
                        line = line.rstrip() + '}"'
                    else:
                        line = line.rstrip() + '"'
                else:
                    line = line.rstrip() + '"'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def fix_fstring_braces(code: str) -> str:
        """Fix unmatched braces in f-strings."""
        def fix_fstring_match(match):
            fstring = match.group()
            open_braces = fstring.count('{') - fstring.count('{{')
            close_braces = fstring.count('}') - fstring.count('}}')
            
            if open_braces > close_braces:
                missing = open_braces - close_braces
                if fstring.endswith('"'):
                    fstring = fstring[:-1] + '}' * missing + '"'
                elif fstring.endswith("'"):
                    fstring = fstring[:-1] + '}' * missing + "'"
            
            return fstring
        
        code = re.sub(r'f"[^"]*"', fix_fstring_match, code)
        code = re.sub(r"f'[^']*'", fix_fstring_match, code)
        
        return code
    
    @staticmethod
    def fix_missing_colons(code: str) -> str:
        """Fix missing colons after function/class definitions and control structures."""
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            needs_colon = False
            
            if re.match(r'^\s*def\s+\w+\s*\([^)]*\)\s*$', line):
                needs_colon = True
            elif re.match(r'^\s*class\s+\w+(?:\([^)]*\))?\s*$', line):
                needs_colon = True
            elif re.match(r'^\s*(?:if|elif|else|for|while|try|except|finally|with)\s+.*[^:]$', line):
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith(('and', 'or', ')')):
                    needs_colon = True
            
            if needs_colon:
                line = line.rstrip() + ':'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def fix_quadruple_quotes(code: str) -> str:
        """Fix quadruple or more quotes in docstrings."""
        code = re.sub(r'"{4,}', '"""', code)
        code = re.sub(r"'{4,}", "'''", code)
        return code
    
    @staticmethod
    def apply_all_fixes(code: str) -> Tuple[str, List[str]]:
        """Apply all available fixes to the code."""
        applied_fixes = []
        original_code = code
        
        fixes = [
            ('quadruple_quotes', CodeAutoFixer.fix_quadruple_quotes),
            ('unterminated_strings', CodeAutoFixer.fix_unterminated_strings),
            ('fstring_braces', CodeAutoFixer.fix_fstring_braces),
            ('unclosed_brackets', CodeAutoFixer.fix_unclosed_brackets),
            ('incomplete_statements', CodeAutoFixer.fix_incomplete_statements),
            ('missing_colons', CodeAutoFixer.fix_missing_colons),
        ]
        
        for fix_name, fix_func in fixes:
            try:
                fixed_code = fix_func(code)
                if fixed_code != code:
                    applied_fixes.append(fix_name)
                    code = fixed_code
            except Exception as e:
                logger.warning(f"Fix {fix_name} failed: {e}")
        
        if code != original_code:
            logger.info(f"Applied {len(applied_fixes)} fixes: {', '.join(applied_fixes)}")
        
        return code, applied_fixes

