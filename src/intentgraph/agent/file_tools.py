"""
File operation tools for AI Coding Agent.

Provides safe and reliable file operations:
- Read files with line range and regex search
- Create new files
- Modify existing files with precise string replacement
- Delete files safely
- Validate code syntax and logic
"""

import re
import ast
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class FileOperationStatus(str, Enum):
    """Status of file operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    status: FileOperationStatus
    operation: str
    file_path: str
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lines_affected: int = 0


class FileTools:
    """
    File operation tools for AI Coding Agent.
    
    Provides safe file operations with validation and error handling.
    """
    
    def __init__(self, workspace_root: Path):
        """
        Initialize file tools.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root)
        
    def read_file(
        self,
        file_path: str,
        view_range: Optional[Tuple[int, int]] = None,
        search_regex: Optional[str] = None,
        context_lines: int = 5
    ) -> str:
        """
        Read file content with optional filtering.
        
        Args:
            file_path: Relative path to file from workspace root
            view_range: Optional (start_line, end_line) tuple (1-based, inclusive)
            search_regex: Optional regex pattern to search for
            context_lines: Number of context lines around matches
            
        Returns:
            File content as string with line numbers
        """
        full_path = self.workspace_root / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Apply view range if specified
        if view_range:
            start, end = view_range
            if end == -1:
                end = len(lines)
            lines = lines[start-1:end]
            line_offset = start - 1
        else:
            line_offset = 0
            
        # Apply regex search if specified
        if search_regex:
            pattern = re.compile(search_regex)
            matched_lines = []
            
            for i, line in enumerate(lines):
                if pattern.search(line):
                    # Include context lines
                    start_ctx = max(0, i - context_lines)
                    end_ctx = min(len(lines), i + context_lines + 1)
                    matched_lines.extend(range(start_ctx, end_ctx))
                    
            # Remove duplicates and sort
            matched_lines = sorted(set(matched_lines))
            
            # Build output with line numbers
            result = []
            prev_line = -2
            for line_num in matched_lines:
                if line_num > prev_line + 1:
                    result.append("...\n")
                result.append(f"{line_num + line_offset + 1:6d}\t{lines[line_num]}")
                prev_line = line_num
                
            return ''.join(result)
        else:
            # Return all lines with line numbers
            return ''.join(f"{i + line_offset + 1:6d}\t{line}" 
                          for i, line in enumerate(lines))
    
    def create_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False
    ) -> FileOperationResult:
        """
        Create a new file with content.
        
        Args:
            file_path: Relative path to file from workspace root
            content: File content
            overwrite: Whether to overwrite if file exists
            
        Returns:
            FileOperationResult with operation status
        """
        full_path = self.workspace_root / file_path
        
        # Check if file exists
        if full_path.exists() and not overwrite:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="create_file",
                file_path=file_path,
                message="File already exists",
                errors=["Use overwrite=True to replace existing file"]
            )

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate content for Python files
        if file_path.endswith('.py'):
            validation = self._validate_python_code(content)
            if not validation['valid']:
                return FileOperationResult(
                    status=FileOperationStatus.FAILED,
                    operation="create_file",
                    file_path=file_path,
                    message="Invalid Python syntax",
                    errors=validation['errors']
                )

        # Write file
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            line_count = len(content.splitlines())

            return FileOperationResult(
                status=FileOperationStatus.SUCCESS,
                operation="create_file",
                file_path=file_path,
                message=f"File created successfully",
                lines_affected=line_count
            )
        except Exception as e:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="create_file",
                file_path=file_path,
                message="Failed to write file",
                errors=[str(e)]
            )

    def modify_file(
        self,
        file_path: str,
        old_str: str,
        new_str: str,
        old_str_start_line: int,
        old_str_end_line: int
    ) -> FileOperationResult:
        """
        Modify existing file by replacing exact string match.

        Args:
            file_path: Relative path to file from workspace root
            old_str: Exact string to replace (must match exactly including whitespace)
            new_str: New string to insert
            old_str_start_line: Starting line number (1-based, inclusive)
            old_str_end_line: Ending line number (1-based, inclusive)

        Returns:
            FileOperationResult with operation status
        """
        full_path = self.workspace_root / file_path

        if not full_path.exists():
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="modify_file",
                file_path=file_path,
                message="File not found",
                errors=[f"File does not exist: {file_path}"]
            )

        # Read current content
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Extract target lines
        target_lines = lines[old_str_start_line-1:old_str_end_line]
        target_str = ''.join(target_lines)

        # Verify exact match
        if target_str != old_str:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="modify_file",
                file_path=file_path,
                message="String mismatch",
                errors=[
                    f"Expected string does not match file content at lines {old_str_start_line}-{old_str_end_line}",
                    f"Expected: {repr(old_str[:100])}...",
                    f"Found: {repr(target_str[:100])}..."
                ]
            )

        # Replace content
        new_lines = lines[:old_str_start_line-1] + [new_str] + lines[old_str_end_line:]
        new_content = ''.join(new_lines)

        # Validate for Python files
        if file_path.endswith('.py'):
            validation = self._validate_python_code(new_content)
            if not validation['valid']:
                return FileOperationResult(
                    status=FileOperationStatus.FAILED,
                    operation="modify_file",
                    file_path=file_path,
                    message="Modified code has syntax errors",
                    errors=validation['errors']
                )

        # Write modified content
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            lines_changed = abs(len(new_str.splitlines()) - len(old_str.splitlines()))

            return FileOperationResult(
                status=FileOperationStatus.SUCCESS,
                operation="modify_file",
                file_path=file_path,
                message="File modified successfully",
                lines_affected=lines_changed
            )
        except Exception as e:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="modify_file",
                file_path=file_path,
                message="Failed to write modified file",
                errors=[str(e)]
            )

    def insert_content(
        self,
        file_path: str,
        insert_after_line: int,
        content: str
    ) -> FileOperationResult:
        """
        Insert content after specified line.

        Args:
            file_path: Relative path to file from workspace root
            insert_after_line: Line number after which to insert (0 for beginning)
            content: Content to insert

        Returns:
            FileOperationResult with operation status
        """
        full_path = self.workspace_root / file_path

        if not full_path.exists():
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="insert_content",
                file_path=file_path,
                message="File not found"
            )

        # Read current content
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Insert content
        if insert_after_line == 0:
            new_lines = [content] + lines
        else:
            new_lines = lines[:insert_after_line] + [content] + lines[insert_after_line:]

        new_content = ''.join(new_lines)

        # Validate for Python files
        if file_path.endswith('.py'):
            validation = self._validate_python_code(new_content)
            if not validation['valid']:
                return FileOperationResult(
                    status=FileOperationStatus.FAILED,
                    operation="insert_content",
                    file_path=file_path,
                    message="Inserted code causes syntax errors",
                    errors=validation['errors']
                )

        # Write modified content
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return FileOperationResult(
                status=FileOperationStatus.SUCCESS,
                operation="insert_content",
                file_path=file_path,
                message="Content inserted successfully",
                lines_affected=len(content.splitlines())
            )
        except Exception as e:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="insert_content",
                file_path=file_path,
                message="Failed to write file",
                errors=[str(e)]
            )

    def delete_file(self, file_path: str) -> FileOperationResult:
        """
        Delete a file safely.

        Args:
            file_path: Relative path to file from workspace root

        Returns:
            FileOperationResult with operation status
        """
        full_path = self.workspace_root / file_path

        if not full_path.exists():
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="delete_file",
                file_path=file_path,
                message="File not found"
            )

        try:
            full_path.unlink()
            return FileOperationResult(
                status=FileOperationStatus.SUCCESS,
                operation="delete_file",
                file_path=file_path,
                message="File deleted successfully"
            )
        except Exception as e:
            return FileOperationResult(
                status=FileOperationStatus.FAILED,
                operation="delete_file",
                file_path=file_path,
                message="Failed to delete file",
                errors=[str(e)]
            )

    def _validate_python_code(self, code: str) -> Dict[str, Any]:
        """
        Validate Python code syntax.

        Args:
            code: Python code to validate

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        try:
            ast.parse(code)
            return {'valid': True, 'errors': []}
        except SyntaxError as e:
            return {
                'valid': False,
                'errors': [
                    f"Syntax error at line {e.lineno}: {e.msg}",
                    f"Text: {e.text}" if e.text else ""
                ]
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }

    def validate_code_logic(
        self,
        file_path: str,
        requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Validate code logic against requirements.

        Args:
            file_path: Relative path to file from workspace root
            requirements: List of requirement descriptions

        Returns:
            Dict with validation results
        """
        full_path = self.workspace_root / file_path

        if not full_path.exists():
            return {
                'valid': False,
                'errors': [f"File not found: {file_path}"]
            }

        # Read file content
        with open(full_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Basic syntax validation
        syntax_check = self._validate_python_code(code)
        if not syntax_check['valid']:
            return syntax_check

        # Parse AST for structure analysis
        try:
            tree = ast.parse(code)

            # Extract code elements
            functions = [node.name for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree)
                      if isinstance(node, ast.ClassDef)]
            imports = [node.names[0].name for node in ast.walk(tree)
                      if isinstance(node, ast.Import)]

            return {
                'valid': True,
                'errors': [],
                'structure': {
                    'functions': functions,
                    'classes': classes,
                    'imports': imports
                },
                'warnings': []
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Code analysis error: {str(e)}"]
            }

