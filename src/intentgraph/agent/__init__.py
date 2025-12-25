"""
AI Coding Agent module for IntentGraph.

This module provides intelligent context management and code generation
capabilities built on top of IntentGraph's code analysis engine.
"""

from .context_manager import (
    ContextManager,
    PreciseContext,
    ImpactAnalysis,
    CodeChange,
    ContextLayer,
)

from .requirement_analyzer import (
    RequirementAnalyzer,
    RequirementAnalysis,
    RequirementType,
    DesignPlan,
    Task,
)

from .code_generator import (
    CodeImplementation,
    CodeModification,
    TestSuite,
)

# Import enhanced version (this is what's actually used)
from .enhanced_code_generator import EnhancedCodeGenerator

# For backward compatibility, also expose as CodeGenerator
CodeGenerator = EnhancedCodeGenerator

from .workflow import (
    CodingAgentWorkflow,
    WorkflowResult,
    WorkflowStatus,
)

from .cache import CacheManager
from .logger import AgentLogger, get_logger, configure_logger

__all__ = [
    # Context Manager
    "ContextManager",
    "PreciseContext",
    "ImpactAnalysis",
    "CodeChange",
    "ContextLayer",
    # Requirement Analyzer
    "RequirementAnalyzer",
    "RequirementAnalysis",
    "RequirementType",
    "DesignPlan",
    "Task",
    # Code Generator
    "CodeGenerator",
    "EnhancedCodeGenerator",
    "CodeImplementation",
    "CodeModification",
    "TestSuite",
    # Workflow
    "CodingAgentWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    # Cache & Logger
    "CacheManager",
    "AgentLogger",
    "get_logger",
    "configure_logger",
]

