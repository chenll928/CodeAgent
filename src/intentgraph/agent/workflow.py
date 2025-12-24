"""
Workflow orchestrator for AI Coding Agent.

Provides end-to-end workflow automation for:
- New feature implementation
- Code modification
- Bug fixing
- Refactoring
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..ai.enhanced_agent import EnhancedCodebaseAgent
from .context_manager import ContextManager, CodeChange
from .requirement_analyzer import RequirementAnalyzer, RequirementType
from .code_generator import CodeGenerator
from .cache import CacheManager
from .logger import AgentLogger, get_logger


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    status: WorkflowStatus
    requirement: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tests_generated: List[str] = field(default_factory=list)
    token_usage: int = 0
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CodingAgentWorkflow:
    """
    End-to-end workflow orchestrator for AI Coding Agent.

    Coordinates RequirementAnalyzer, ContextManager, and CodeGenerator
    to provide complete automation from requirement to implementation.
    """

    def __init__(
        self,
        repo_path: Path,
        llm_provider: Optional[Any] = None,
        token_budget: int = 30000,
        enable_cache: bool = True,
        cache_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """Initialize workflow with components."""
        self.repo_path = repo_path
        self.token_budget = token_budget
        self.output_dir = Path(output_dir) if output_dir else repo_path

        # Initialize logger
        self.logger = get_logger()

        # Initialize cache
        self.cache = None
        if enable_cache:
            cache_path = cache_dir or (repo_path / ".intentgraph" / "cache")
            self.cache = CacheManager(cache_dir=cache_path)
            self.logger.logger.info(f"Cache enabled at {cache_path}")

        # Initialize components
        self.agent = EnhancedCodebaseAgent(repo_path)
        self.context_manager = ContextManager(self.agent)
        self.analyzer = RequirementAnalyzer(self.agent, llm_provider)
        self.generator = CodeGenerator(self.agent, self.context_manager, llm_provider)

    def implement_feature(self, requirement: str) -> WorkflowResult:
        """
        Complete workflow for new feature implementation.

        Steps: Analyze → Design → Decompose → Implement → Test
        """
        import time
        start_time = time.time()
        result = WorkflowResult(status=WorkflowStatus.RUNNING, requirement=requirement)

        # Start operation tracking
        self.logger.start_operation("implement_feature", requirement=requirement)

        try:
            # Check cache
            cache_key = None
            if self.cache:
                cache_key = CacheManager.generate_key("feature", requirement)
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    self.logger.log_cache_hit(cache_key)
                    self.logger.logger.info("Using cached result")
                    return cached_result
                self.logger.log_cache_miss(cache_key)

            # Step 1: Analyze requirement
            self.logger.logger.info("Step 1: Analyzing requirement")
            analysis = self.analyzer.analyze_requirement(requirement)
            result.token_usage += 2000  # Estimated

            # Step 2: Design solution
            self.logger.logger.info("Step 2: Designing solution")
            design = self.analyzer.design_solution(analysis)
            result.token_usage += 5000

            # Step 3: Decompose tasks
            self.logger.logger.info("Step 3: Decomposing tasks")
            tasks = self.analyzer.decompose_tasks(design)
            result.token_usage += 3000

            # Step 4: Implement each task
            for i, task in enumerate(tasks, 1):
                self.logger.logger.info(f"Step 4.{i}: Implementing task - {task.description}")

                impl = self.generator.implement_new_feature(design, task)

                # Validate implementation has required fields
                if not impl.generated_code or not impl.file_path:
                    raise ValueError(f"Invalid implementation for task {task.task_id}: missing code or file path")

                result.token_usage += 4000

                # Write implementation to file
                written_path = self._write_implementation(impl)
                result.files_created.append(written_path)

                # Step 5: Generate tests
                self.logger.logger.info(f"Step 5.{i}: Generating tests")
                test_suite = self.generator.generate_tests(impl)
                result.token_usage += 3000

                # Write tests to file
                test_path = self._write_tests(test_suite)
                result.tests_generated.append(test_path)

            result.status = WorkflowStatus.COMPLETED

            # Cache result
            if self.cache and cache_key:
                self.cache.set(cache_key, result, ttl_seconds=3600)

            # End operation tracking
            self.logger.end_operation(success=True, token_usage=result.token_usage)

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(e))
            self.logger.end_operation(success=False, error=str(e))
            self.logger.logger.exception("Feature implementation failed")

        result.execution_time = time.time() - start_time
        return result

    def modify_code(self, target: str, modification: str) -> WorkflowResult:
        """
        Complete workflow for code modification.

        Steps: Extract Context → Analyze Impact → Modify → Validate
        """
        import time
        start_time = time.time()
        result = WorkflowResult(status=WorkflowStatus.RUNNING, requirement=modification)

        try:
            # Step 1: Extract context
            context = self.context_manager.extract_precise_context(
                target=target,
                token_budget=5000
            )

            # Step 2: Analyze impact
            change = CodeChange(
                target_symbol=target,
                target_file=context.target_code.get("file", ""),
                change_type="implementation_change",
                description=modification,
                line_range=(0, 0)
            )
            impact = self.context_manager.analyze_impact(change)

            if impact.risk_level == "high":
                result.warnings.append(f"High risk modification: {len(impact.direct_callers)} callers affected")

            # Step 3: Generate modification
            mod = self.generator.modify_existing_code(target, modification, context)
            result.token_usage += 6000
            result.files_modified.append(mod.file_path or target)

            result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.errors.append(str(e))

        result.execution_time = time.time() - start_time
        return result

    def get_token_usage_estimate(self, requirement: str) -> Dict[str, int]:
        """Estimate token usage for a requirement."""
        analysis = self.analyzer.analyze_requirement(requirement)

        base_tokens = {
            "analysis": 2000,
            "design": 5000,
            "decomposition": 3000
        }

        # Estimate based on complexity
        if analysis.estimated_complexity == "high":
            base_tokens["implementation"] = 8000
            base_tokens["testing"] = 5000
        elif analysis.estimated_complexity == "medium":
            base_tokens["implementation"] = 4000
            base_tokens["testing"] = 3000
        else:
            base_tokens["implementation"] = 2000
            base_tokens["testing"] = 2000

        base_tokens["total"] = sum(base_tokens.values())
        return base_tokens

    def _write_implementation(self, impl: 'CodeImplementation') -> str:
        """Write implementation code to file system."""
        from .code_generator import CodeImplementation

        # Determine output path
        file_path = self.output_dir / impl.file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write code to file
        file_path.write_text(impl.generated_code, encoding='utf-8')
        self.logger.logger.info(f"Written implementation to {file_path}")

        return str(file_path)

    def _write_tests(self, test_suite: 'TestSuite') -> str:
        """Write test suite to file system."""
        from .code_generator import TestSuite

        # Determine output path
        test_path = self.output_dir / test_suite.test_file_path
        test_path.parent.mkdir(parents=True, exist_ok=True)

        # Write tests to file
        test_path.write_text(test_suite.test_code, encoding='utf-8')
        self.logger.logger.info(f"Written tests to {test_path}")

        return str(test_path)

