"""
Tests for Phase 3 & 4: Requirement Analyzer and Code Generator.
"""

import pytest
from pathlib import Path
from intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from intentgraph.agent import (
    ContextManager,
    RequirementAnalyzer,
    RequirementAnalysis,
    RequirementType,
    DesignPlan,
    Task,
    CodeGenerator,
    CodeImplementation,
    CodeModification,
    TestSuite,
)


@pytest.fixture
def agent():
    """Create enhanced agent for testing."""
    repo_path = Path(".")
    return EnhancedCodebaseAgent(repo_path)


@pytest.fixture
def context_manager(agent):
    """Create context manager for testing."""
    return ContextManager(agent)


@pytest.fixture
def requirement_analyzer(agent):
    """Create requirement analyzer for testing."""
    return RequirementAnalyzer(agent, llm_provider=None)


@pytest.fixture
def code_generator(agent, context_manager):
    """Create code generator for testing."""
    return CodeGenerator(agent, context_manager, llm_provider=None)


class TestRequirementAnalyzer:
    """Tests for RequirementAnalyzer."""
    
    def test_analyze_new_feature_requirement(self, requirement_analyzer):
        """Test analyzing a new feature requirement."""
        requirement = "Add user authentication with email and password"
        analysis = requirement_analyzer.analyze_requirement(requirement)
        
        assert isinstance(analysis, RequirementAnalysis)
        assert analysis.requirement_text == requirement
        assert isinstance(analysis.requirement_type, RequirementType)
        assert analysis.estimated_complexity in ["low", "medium", "high"]
    
    def test_analyze_bug_fix_requirement(self, requirement_analyzer):
        """Test analyzing a bug fix requirement."""
        requirement = "Fix the memory leak in the cache manager"
        analysis = requirement_analyzer.analyze_requirement(requirement)
        
        assert isinstance(analysis, RequirementAnalysis)
        assert analysis.requirement_type == RequirementType.BUG_FIX
    
    def test_analyze_refactor_requirement(self, requirement_analyzer):
        """Test analyzing a refactor requirement."""
        requirement = "Refactor the database connection pool for better performance"
        analysis = requirement_analyzer.analyze_requirement(requirement)
        
        assert isinstance(analysis, RequirementAnalysis)
        assert analysis.requirement_type == RequirementType.REFACTOR
    
    def test_design_solution(self, requirement_analyzer):
        """Test designing a solution."""
        analysis = RequirementAnalysis(
            requirement_text="Add logging functionality",
            requirement_type=RequirementType.NEW_FEATURE,
            key_entities=["Logger", "LogHandler"],
            estimated_complexity="medium"
        )
        
        design = requirement_analyzer.design_solution(analysis)
        
        assert isinstance(design, DesignPlan)
        assert design.requirement_analysis == analysis
        assert isinstance(design.technical_approach, str)
        assert isinstance(design.implementation_steps, list)
    
    def test_decompose_tasks(self, requirement_analyzer):
        """Test task decomposition."""
        analysis = RequirementAnalysis(
            requirement_text="Add caching",
            requirement_type=RequirementType.NEW_FEATURE,
            estimated_complexity="low"
        )
        design = DesignPlan(
            requirement_analysis=analysis,
            technical_approach="Implement in-memory cache",
            implementation_steps=[
                "Create cache class",
                "Add cache methods",
                "Integrate with existing code"
            ]
        )
        
        tasks = requirement_analyzer.decompose_tasks(design)
        
        assert isinstance(tasks, list)
        assert len(tasks) > 0
        assert all(isinstance(task, Task) for task in tasks)
        assert all(hasattr(task, 'task_id') for task in tasks)
        assert all(hasattr(task, 'description') for task in tasks)


class TestCodeGenerator:
    """Tests for CodeGenerator."""
    
    def test_implement_new_feature(self, code_generator):
        """Test implementing a new feature."""
        analysis = RequirementAnalysis(
            requirement_text="Add helper function",
            requirement_type=RequirementType.NEW_FEATURE,
            estimated_complexity="low"
        )
        design = DesignPlan(
            requirement_analysis=analysis,
            technical_approach="Create utility function"
        )
        task = Task(
            task_id="task_1",
            description="Create helper function",
            task_type="create_file",
            target_file="utils/helper.py"
        )
        
        implementation = code_generator.implement_new_feature(design, task)
        
        assert isinstance(implementation, CodeImplementation)
        assert implementation.task == task
        assert isinstance(implementation.generated_code, str)
        assert len(implementation.generated_code) > 0
        assert implementation.file_path == task.target_file
    
    def test_modify_existing_code(self, code_generator):
        """Test modifying existing code."""
        target = "ContextManager.extract_precise_context"
        modification_desc = "Add validation for token budget"
        
        modification = code_generator.modify_existing_code(
            target=target,
            modification_desc=modification_desc
        )
        
        assert isinstance(modification, CodeModification)
        assert modification.symbol_name == target
        assert isinstance(modification.original_code, str)
        assert isinstance(modification.modified_code, str)
        assert isinstance(modification.change_description, str)
    
    def test_generate_tests(self, code_generator):
        """Test generating tests."""
        task = Task(
            task_id="task_1",
            description="Test task",
            task_type="create_file",
            target_file="src/module.py"
        )
        implementation = CodeImplementation(
            task=task,
            generated_code="def example():\n    return True",
            file_path="src/module.py"
        )
        
        test_suite = code_generator.generate_tests(implementation)
        
        assert isinstance(test_suite, TestSuite)
        assert test_suite.implementation == implementation
        assert isinstance(test_suite.test_file_path, str)
        assert "test" in test_suite.test_file_path.lower()
        assert isinstance(test_suite.test_code, str)
        assert len(test_suite.test_code) > 0

