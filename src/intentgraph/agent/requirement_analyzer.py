"""
Requirement Analyzer for AI Coding Agent.

This module provides requirement understanding capabilities:
- Requirement parsing and analysis
- Solution design generation
- Task decomposition

Uses LLM for intelligent requirement interpretation.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import re

from ..ai.enhanced_agent import EnhancedCodebaseAgent, ArchitectureMap


class RequirementType(str, Enum):
    """Types of requirements."""
    NEW_FEATURE = "new_feature"
    MODIFY_EXISTING = "modify_existing"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"


@dataclass
class RequirementAnalysis:
    """Results of requirement analysis."""
    requirement_text: str
    requirement_type: RequirementType
    affected_scope: List[str] = field(default_factory=list)  # Files/modules affected
    key_entities: List[str] = field(default_factory=list)  # Classes/functions involved
    technical_constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    estimated_complexity: str = "medium"  # 'low', 'medium', 'high'


@dataclass
class DesignPlan:
    """Technical design plan for implementation."""
    requirement_analysis: RequirementAnalysis
    technical_approach: str
    new_components: List[Dict[str, str]] = field(default_factory=list)  # name, type, purpose
    modified_components: List[Dict[str, str]] = field(default_factory=list)
    integration_points: List[Dict[str, str]] = field(default_factory=list)
    interface_definitions: List[Dict[str, str]] = field(default_factory=list)
    implementation_steps: List[str] = field(default_factory=list)
    potential_risks: List[str] = field(default_factory=list)


@dataclass
class Task:
    """Individual implementation task."""
    task_id: str
    description: str
    task_type: str  # 'create_file', 'modify_file', 'add_function', 'modify_function' (NO 'add_test' - tests handled separately)
    target_file: Optional[str] = None
    target_symbol: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Other task IDs
    priority: int = 0  # Higher = more important
    estimated_tokens: int = 4000


class RequirementAnalyzer:
    """
    Requirement Analyzer for understanding and decomposing requirements.

    This class uses LLM to:
    1. Parse and analyze requirements
    2. Generate technical design plans
    3. Decompose into executable tasks

    Token usage per operation:
    - analyze_requirement: ~2KB
    - design_solution: ~5KB
    - decompose_tasks: ~3KB
    """

    def __init__(
        self,
        agent: EnhancedCodebaseAgent,
        llm_provider: Optional[Any] = None
    ):
        """
        Initialize requirement analyzer.

        Args:
            agent: EnhancedCodebaseAgent for codebase context
            llm_provider: LLM provider instance (OpenAI, Anthropic, etc.)
        """
        self.agent = agent
        self.llm_provider = llm_provider
        self._architecture_cache: Optional[ArchitectureMap] = None
        self._repo_files: Set[str] = set()
        self._module_roots: Set[str] = set()
        self._index_initialized = False

    def _ensure_repo_index(self) -> None:
        """Load repository file and module metadata once for task validation."""
        if self._index_initialized:
            return

        try:
            analysis = self.agent.get_repository_manifest()
        except AttributeError:
            analysis = None

        if analysis:
            repo_root = Path(analysis.root)
            for file_info in analysis.files:
                # FIX: Store relative path instead of absolute path for consistent comparison
                rel_path = Path(file_info.path).as_posix()
                self._repo_files.add(rel_path)
                module_root = rel_path.split('/')[:2]
                if module_root:
                    self._module_roots.add('/'.join(module_root))
        else:
            repo_root = self.agent.repo_path
            for file_path in repo_root.rglob('*.py'):
                # FIX: Store relative path instead of absolute path
                rel_path = file_path.relative_to(repo_root).as_posix()
                self._repo_files.add(rel_path)
                parts = rel_path.split('/')
                if parts:
                    self._module_roots.add('/'.join(parts[:2]))

        self._index_initialized = True
        print(f"[DEBUG] Indexed {len(self._repo_files)} files from repository")

    def analyze_requirement(
        self,
        requirement: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RequirementAnalysis:
        """
        Analyze requirement and extract key information.

        LLM Call Point 1: ~2KB Token
        Input: Requirement text + Architecture summary
        Output: Requirement type, scope, entities

        Args:
            requirement: Natural language requirement description
            context: Additional context (user preferences, constraints)

        Returns:
            RequirementAnalysis with parsed information
        """
        self._ensure_repo_index()
        # Get architecture summary for context
        architecture = self._get_architecture_summary()

        # Prepare prompt
        prompt = self._build_analysis_prompt(requirement, architecture, context)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=1000)
            analysis = self._parse_analysis_response(response, requirement)
        else:
            # Fallback: Basic heuristic analysis
            analysis = self._heuristic_analysis(requirement)

        return analysis

    def design_solution(
        self,
        analysis: RequirementAnalysis,
        similar_patterns: Optional[List[Dict[str, Any]]] = None
    ) -> DesignPlan:
        """
        Generate technical design plan for the requirement.

        LLM Call Point 2: ~5KB Token
        Input: Requirement analysis + Similar patterns + Interface definitions
        Output: Technical approach, components, integration points

        Args:
            analysis: RequirementAnalysis from analyze_requirement
            similar_patterns: Similar code patterns for reference

        Returns:
            DesignPlan with technical design
        """
        self._ensure_repo_index()

        # Find similar patterns if not provided
        if similar_patterns is None:
            similar_patterns = self._find_similar_implementations(analysis)

        # Get relevant interfaces
        interfaces = self._get_relevant_interfaces(analysis)

        # Prepare prompt
        prompt = self._build_design_prompt(analysis, similar_patterns, interfaces)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=2000)
            design = self._parse_design_response(response, analysis)
        else:
            # Fallback: Basic design plan
            design = self._heuristic_design(analysis)

        return design

    def decompose_tasks(
        self,
        design: DesignPlan,
        dependency_info: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """
        Decompose design plan into executable tasks.

        LLM Call Point 3: ~3KB Token
        Input: Design plan + Dependency graph
        Output: Task list with dependencies and priorities

        Args:
            design: DesignPlan from design_solution
            dependency_info: Dependency information from codebase

        Returns:
            List of Tasks with dependencies and priorities (deduplicated)
        """
        self._ensure_repo_index()

        # Get dependency information
        if dependency_info is None:
            dependency_info = self._extract_dependency_info(design)

        # Prepare prompt
        prompt = self._build_decomposition_prompt(design, dependency_info)

        # Call LLM
        if self.llm_provider:
            response = self._call_llm(prompt, max_tokens=1500)
            tasks = self._parse_tasks_response(response, design)
        else:
            # Fallback: Basic task decomposition
            tasks = self._heuristic_decomposition(design)

        # Deduplicate tasks by target_file
        tasks = self._deduplicate_tasks(tasks)

        return tasks

    def _deduplicate_tasks(self, tasks: List[Task]) -> List[Task]:
        """Remove duplicate tasks targeting the same file."""
        seen_files = set()
        deduplicated = []

        for task in tasks:
            if task.target_file not in seen_files:
                deduplicated.append(task)
                seen_files.add(task.target_file)
            else:
                print(f"[INFO] Skipping duplicate task for {task.target_file}: {task.description}")

        return deduplicated

    def _normalize_file_path(self, component_name: str, component_type: str, module_name: str = None) -> str:
        """
        Normalize file path according to Python conventions.

        Rules:
        1. Use snake_case for file names
        2. Organize by module: src/<module>/<file>.py
        3. Follow PEP 8 naming conventions

        Args:
            component_name: Component name (e.g., "AuthService", "UserModel")
            component_type: Type of component ("class", "module", etc.)
            module_name: Optional module name (e.g., "auth", "api")

        Returns:
            Normalized file path (e.g., "src/auth/auth_service.py")
        """
        # Convert CamelCase to snake_case
        # Insert underscore before uppercase letters (except first)
        file_name = re.sub(r'(?<!^)(?=[A-Z])', '_', component_name).lower()

        # Determine module name if not provided
        if not module_name:
            # Extract uppercase letters (e.g., AuthService -> AS -> as)
            module_name = ''.join(c for c in component_name if c.isupper()).lower()
            if not module_name or len(module_name) < 2:
                # Fallback: use first word (e.g., auth_service -> auth)
                module_name = file_name.split('_')[0]

        # Build path
        return f"src/{module_name}/{file_name}.py"

    # ===== Helper Methods =====

    def _get_architecture_summary(self) -> Dict[str, Any]:
        """Get architecture summary for context."""
        if self._architecture_cache is None:
            arch_map = self.agent.understand_architecture()
            self._architecture_cache = arch_map

        return {
            "layers": list(self._architecture_cache.layers.keys()),
            "modules": list(self._architecture_cache.modules.keys()),
            "key_abstractions": self._architecture_cache.key_abstractions[:10],
            "design_patterns": list(self._architecture_cache.design_patterns.keys())
        }

    def _build_analysis_prompt(
        self,
        requirement: str,
        architecture: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for requirement analysis."""
        file_inventory = '\n'.join(sorted({Path(p).name for p in self._repo_files})[:50])
        prompt = f"""Analyze the following software requirement and extract key information.

IMPORTANT: Keep the analysis simple and direct. If the requirement is straightforward (like "add a sum function"),
don't over-complicate it. Focus on what the user actually asked for.

Requirement:
{requirement}

Codebase Architecture:
- Layers: {', '.join(architecture.get('layers', []))}
- Modules: {', '.join(architecture.get('modules', [])[:5])}
- Key Abstractions: {', '.join(architecture.get('key_abstractions', [])[:5])}

Repository Snapshot (file names only):
{file_inventory}

Please analyze and provide:
1. Requirement Type: (new_feature, modify_existing, bug_fix, refactor, test_generation)
2. Affected Scope: Which files/modules will be affected (be specific and realistic)
3. Key Entities: Classes, functions, or concepts involved (match the requirement's scope)
4. Technical Constraints: Any technical limitations or requirements
5. Success Criteria: How to verify the requirement is met
6. Estimated Complexity: (low, medium, high) - simple functions should be "low"

Respond in JSON format:
{{
    "requirement_type": "...",
    "affected_scope": ["...", "..."],
    "key_entities": ["...", "..."],
    "technical_constraints": ["...", "..."],
    "success_criteria": ["...", "..."],
    "estimated_complexity": "..."
}}
"""
        return prompt

    def _build_design_prompt(
        self,
        analysis: RequirementAnalysis,
        similar_patterns: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for solution design."""
        prompt = f"""Design a technical solution for the following requirement.

IMPORTANT: Keep the design simple and proportional to the requirement complexity.
- For low complexity: Simple, direct implementation (e.g., a single function or class)
- For medium complexity: Moderate design with a few components
- For high complexity: Comprehensive architecture

Requirement Analysis:
- Original Requirement: {analysis.requirement_text}
- Type: {analysis.requirement_type}
- Scope: {', '.join(analysis.affected_scope)}
- Key Entities: {', '.join(analysis.key_entities)}
- Complexity: {analysis.estimated_complexity}

Similar Patterns in Codebase:
{self._format_similar_patterns(similar_patterns)}

Relevant Interfaces:
{self._format_interfaces(interfaces)}

Repository Guardrails:
- Only modify existing files from this list:
{chr(10).join(f"  - {p}" for p in sorted(self._repo_files)[:50])}
- New files must live under these module roots:
{chr(10).join(f"  - {m}" for m in sorted(self._module_roots)[:20])}
- Do not invent arbitrary directories.

Please provide a technical design including:
1. Technical Approach: High-level approach (keep it simple for simple requirements)
2. New Components: Components to create (name, type, purpose) - only what's necessary
3. Modified Components: Existing components to modify (if any)
4. Integration Points: Where new code integrates with existing code
5. Interface Definitions: Key interfaces and signatures
6. Implementation Steps: Ordered steps for implementation (2-5 steps for simple requirements)
7. Potential Risks: Risks and mitigation strategies

Respond in JSON format with these fields.
"""
        return prompt

    def _build_decomposition_prompt(
        self,
        design: DesignPlan,
        dependency_info: Dict[str, Any]
    ) -> str:
        """Build prompt for task decomposition with strict file path constraints."""
        # Extract component names for file path generation
        new_component_names = [c.get('name', '') for c in design.new_components]

        # Format pre-defined file paths
        predefined_paths = []
        for comp in design.new_components:
            name = comp.get('name', '')
            file = comp.get('file', '')
            desc = comp.get('description', '')
            predefined_paths.append(f"  - {name}: {file} ({desc})")

        prompt = f"""Decompose the following design plan into executable tasks.

Design Plan:
- Approach: {design.technical_approach}
- New Components: {', '.join(new_component_names)}
- Modified Components: {len(design.modified_components)}

Implementation Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(design.implementation_steps))}

🔴 CRITICAL FILE PATH RULES (MUST FOLLOW EXACTLY):
1. Use snake_case for ALL file names (e.g., auth_service.py, NOT AuthService.py)
2. You MUST use these EXACT pre-defined file paths:
{chr(10).join(predefined_paths)}

3. Each task creates ONE file with ONE of the above paths
4. NO duplicate target_file values
5. Focus ONLY on implementation, NOT analysis or documentation
6. DO NOT generate test-related tasks (add_test) - tests handled separately

Task Requirements:
- Task ID: Unique identifier (e.g., "task_1", "task_2")
- Description: What to implement (be specific)
- Task Type: ONLY use (create_file, modify_file, add_function, modify_function)
- Target File: MUST be one of the exact paths listed above
- Target Symbol: Class/function name to create
- Dependencies: Other task IDs this depends on
- Priority: 0-10 (higher = more important)
- Estimated Tokens: Estimated LLM tokens needed

Respond ONLY with a JSON array of tasks. Do NOT wrap in markdown code blocks.
Example format:
[
  {{
    "task_id": "task_1",
    "description": "Create UserModel class with password hashing",
    "task_type": "create_file",
    "target_file": "src/auth/user_model.py",
    "target_symbol": "UserModel",
    "dependencies": [],
    "priority": 10,
    "estimated_tokens": 4000
  }}
]
"""
        return prompt

    def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call LLM provider."""
        if not self.llm_provider:
            return "{}"

        try:
            # Generic LLM call - adapt based on provider
            if hasattr(self.llm_provider, 'chat'):
                response = self.llm_provider.chat(prompt, max_tokens=max_tokens)
            elif hasattr(self.llm_provider, 'complete'):
                response = self.llm_provider.complete(prompt, max_tokens=max_tokens)
            else:
                response = str(self.llm_provider(prompt))
            return response
        except Exception as e:
            print(f"LLM call failed: {e}")
            return "{}"

    def _parse_analysis_response(self, response: str, requirement: str) -> RequirementAnalysis:
        """Parse LLM response into RequirementAnalysis."""
        try:
            data = json.loads(response)
            return RequirementAnalysis(
                requirement_text=requirement,
                requirement_type=RequirementType(data.get("requirement_type", "new_feature")),
                affected_scope=data.get("affected_scope", []),
                key_entities=data.get("key_entities", []),
                technical_constraints=data.get("technical_constraints", []),
                success_criteria=data.get("success_criteria", []),
                estimated_complexity=data.get("estimated_complexity", "medium")
            )
        except:
            return self._heuristic_analysis(requirement)

    def _parse_design_response(self, response: str, analysis: RequirementAnalysis) -> DesignPlan:
        """Parse LLM response into DesignPlan."""
        try:
            data = json.loads(response)
            return DesignPlan(
                requirement_analysis=analysis,
                technical_approach=data.get("technical_approach", ""),
                new_components=data.get("new_components", []),
                modified_components=data.get("modified_components", []),
                integration_points=data.get("integration_points", []),
                interface_definitions=data.get("interface_definitions", []),
                implementation_steps=data.get("implementation_steps", []),
                potential_risks=data.get("potential_risks", [])
            )
        except Exception:
            return self._heuristic_design(analysis)

    def _parse_tasks_response(
        self,
        response: str,
        design: DesignPlan
    ) -> List[Task]:
        """Parse LLM response into Task list."""
        self._ensure_repo_index()

        try:
            cleaned_response = self._clean_json_response(response)
            data = json.loads(cleaned_response)

            tasks: List[Task] = []
            task_list = data if isinstance(data, list) else []

            for i, task_data in enumerate(task_list):
                target_file = task_data.get("target_file")
                if not target_file or target_file == "unknown":
                    target_file = self._generate_file_path(task_data, design, i)

                validated_file = self._validate_or_adjust_target_file(target_file)

                # Get task type from LLM response
                task_type = task_data.get("task_type", "modify_file")

                # Smart task type adjustment based on file existence
                # If LLM says modify_file but file doesn't exist, change to create_file
                if task_type == "modify_file":
                    normalized_file = validated_file.replace('\\', '/').lstrip('/')
                    print(f"[DEBUG] Checking modify_file: {normalized_file}")
                    print(f"[DEBUG] File in repo: {normalized_file in self._repo_files}")
                    if normalized_file not in self._repo_files:
                        # File doesn't exist, should be create_file
                        task_type = "create_file"
                        print(f"[INFO] Adjusted task type from 'modify_file' to 'create_file' for {validated_file} (file doesn't exist)")
                    else:
                        print(f"[INFO] File {normalized_file} exists, keeping task_type='modify_file'")

                # If LLM says create_file but file exists, change to modify_file
                elif task_type == "create_file":
                    normalized_file = validated_file.replace('\\', '/').lstrip('/')
                    print(f"[DEBUG] Checking create_file: {normalized_file}")
                    print(f"[DEBUG] File in repo: {normalized_file in self._repo_files}")
                    if normalized_file in self._repo_files:
                        # File exists, should be modify_file
                        task_type = "modify_file"
                        print(f"[INFO] Adjusted task type from 'create_file' to 'modify_file' for {validated_file} (file exists)")
                    else:
                        print(f"[INFO] File {normalized_file} doesn't exist, keeping task_type='create_file'")

                tasks.append(Task(
                    task_id=task_data.get("task_id", f"task_{i}"),
                    description=task_data.get("description", ""),
                    task_type=task_type,
                    target_file=validated_file,
                    target_symbol=task_data.get("target_symbol"),
                    dependencies=task_data.get("dependencies", []),
                    priority=task_data.get("priority", 0),
                    estimated_tokens=task_data.get("estimated_tokens", 4000)
                ))

            return tasks
        except Exception as e:
            print(f"Failed to parse tasks response: {e}")
            print(f"Response preview: {response[:200]}...")
            return self._heuristic_decomposition(design)

    def _validate_or_adjust_target_file(self, target_file: Optional[str]) -> str:
        """Ensure task target files map to existing files or valid module roots."""
        if not target_file:
            return "unknown"

        normalized = target_file.replace('\\', '/').lstrip('/')

        if normalized in self._repo_files:
            return normalized

        if '/' in normalized:
            module = '/'.join(normalized.split('/')[:2])
        else:
            module = normalized

        if module in self._module_roots:
            return normalized

        # Fall back to best-effort by matching file name
        filename = Path(normalized).name
        for existing in self._repo_files:
            if existing.endswith(filename):
                return existing

        return normalized

    def _heuristic_analysis(self, requirement: str) -> RequirementAnalysis:
        """Fallback heuristic analysis without LLM."""
        req_lower = requirement.lower()

        # Determine type
        if "add" in req_lower or "new" in req_lower or "create" in req_lower:
            req_type = RequirementType.NEW_FEATURE
        elif "fix" in req_lower or "bug" in req_lower:
            req_type = RequirementType.BUG_FIX
        elif "refactor" in req_lower or "improve" in req_lower:
            req_type = RequirementType.REFACTOR
        elif "test" in req_lower:
            req_type = RequirementType.TEST_GENERATION
        else:
            req_type = RequirementType.MODIFY_EXISTING

        return RequirementAnalysis(
            requirement_text=requirement,
            requirement_type=req_type,
            affected_scope=["unknown"],
            key_entities=[],
            estimated_complexity="medium"
        )

    def _heuristic_design(self, analysis: RequirementAnalysis) -> DesignPlan:
        """Fallback design without LLM - generates concrete implementation plan."""
        # Extract meaningful component names from requirement
        requirement_lower = analysis.requirement_text.lower()

        # Determine component name based on requirement keywords
        component_name = None
        component_type = "module"

        # Common patterns for feature requirements
        if "登录" in requirement_lower or "login" in requirement_lower:
            component_name = "auth"
            new_components = [
                {
                    "name": "AuthService",
                    "type": "class",
                    "file": self._normalize_file_path("AuthService", "class", "auth"),
                    "description": "Authentication service with login/logout methods"
                },
                {
                    "name": "UserModel",
                    "type": "class",
                    "file": self._normalize_file_path("UserModel", "class", "auth"),
                    "description": "User model with password hashing"
                }
            ]
            steps = [
                "Create UserModel class with username, email, hashed_password fields",
                "Create AuthService class with login, logout, validate_password methods",
                "Add password hashing using bcrypt or similar"
            ]
        elif "注册" in requirement_lower or "register" in requirement_lower:
            component_name = "registration"
            new_components = [
                {
                    "name": "RegistrationService",
                    "type": "class",
                    "file": self._normalize_file_path("RegistrationService", "class", "registration"),
                    "description": "User registration service"
                }
            ]
            steps = ["Create registration service", "Add user validation"]
        elif "api" in requirement_lower or "接口" in requirement_lower:
            component_name = "api"
            new_components = [
                {
                    "name": "APIHandler",
                    "type": "class",
                    "file": self._normalize_file_path("APIHandler", "class", "api"),
                    "description": "API request handler"
                }
            ]
            steps = ["Create API handler", "Add endpoint routing"]
        else:
            # Generic feature - use key entities
            if analysis.key_entities:
                component_name = analysis.key_entities[0].lower().replace(" ", "_")
            else:
                component_name = "feature"

            new_components = [
                {
                    "name": f"{component_name.title()}Service",
                    "type": "class",
                    "file": self._normalize_file_path(f"{component_name.title()}Service", "class", component_name),
                    "description": f"{component_name} service implementation"
                }
            ]
            steps = [f"Implement {component_name} functionality"]

        return DesignPlan(
            requirement_analysis=analysis,
            technical_approach=f"Implement {component_name} feature with modular design",
            new_components=new_components,
            implementation_steps=steps
        )

    def _heuristic_decomposition(self, design: DesignPlan) -> List[Task]:
        """Fallback task decomposition without LLM - generates concrete tasks."""
        tasks = []
        task_id_counter = 0

        # Generate tasks from new components (preferred approach)
        if design.new_components:
            for component in design.new_components:
                component_name = component.get('name', f'component_{task_id_counter}')
                component_type = component.get('type', 'class')

                # Use file path from component if available
                file_path = component.get('file')
                if not file_path:
                    # Generate appropriate file path based on type
                    if component_type == 'class':
                        # Extract module name from component name (e.g., AuthService -> auth)
                        module_name = ''.join(c for c in component_name if c.isupper()).lower()
                        if not module_name:
                            module_name = component_name.lower()
                        file_path = f"src/{module_name}/{component_name.lower()}.py"
                    elif component_type == 'module':
                        file_path = f"src/{component_name.lower()}/{component_name.lower()}.py"
                    else:
                        file_path = f"src/{component_name.lower()}.py"

                tasks.append(Task(
                    task_id=f"task_{task_id_counter}",
                    description=f"Create {component_name} {component_type}",
                    task_type="create_file",
                    target_file=file_path,
                    target_symbol=component_name,
                    priority=len(design.new_components) - task_id_counter,
                    estimated_tokens=4000
                ))
                task_id_counter += 1

        # If no new components but have implementation steps, try to extract meaningful tasks
        elif design.implementation_steps:
            # Try to extract concrete actions from steps
            for i, step in enumerate(design.implementation_steps):
                step_lower = step.lower()

                # Skip abstract steps
                if any(skip in step_lower for skip in ["analyze", "document", "add tests", "test"]):
                    continue

                # Try to extract component name from step
                component_name = self._extract_component_name(step)
                if not component_name:
                    component_name = f"feature_{i}"

                # Determine task type and file path
                if "create" in step_lower or "implement" in step_lower:
                    task_type = "create_file"
                    file_path = f"src/{component_name.lower()}.py"
                elif "modify" in step_lower or "update" in step_lower:
                    task_type = "modify_file"
                    # Try to find existing file
                    file_path = self._find_best_match_file(component_name)
                    if not file_path:
                        file_path = f"src/{component_name.lower()}.py"
                else:
                    task_type = "create_file"
                    file_path = f"src/{component_name.lower()}.py"

                tasks.append(Task(
                    task_id=f"task_{task_id_counter}",
                    description=step,
                    task_type=task_type,
                    target_file=file_path,
                    target_symbol=component_name,
                    priority=len(design.implementation_steps) - i,
                    estimated_tokens=4000
                ))
                task_id_counter += 1

        # Fallback: create at least one task
        if not tasks:
            requirement_text = design.requirement_analysis.requirement_text
            component_name = self._extract_component_name(requirement_text) or "feature"

            tasks.append(Task(
                task_id="task_0",
                description=f"Implement {requirement_text}",
                task_type="create_file",
                target_file=f"src/{component_name.lower()}.py",
                target_symbol=component_name.title(),
                priority=10,
                estimated_tokens=4000
            ))

        return tasks

    def _find_best_match_file(self, component_name: str) -> Optional[str]:
        """Find best matching file for a component name."""
        component_lower = component_name.lower()

        # Direct match
        for file_path in self._repo_files:
            if component_lower in file_path.lower():
                return file_path

        return None

    def _find_similar_implementations(self, analysis: RequirementAnalysis) -> List[Dict[str, Any]]:
        """Find similar implementations in codebase."""
        patterns = []
        for entity in analysis.key_entities[:3]:
            locations = self.agent.find_similar_patterns(entity)
            for loc in locations[:2]:
                patterns.append({
                    "symbol": loc.symbol_name,
                    "file": loc.file_path,
                    "signature": loc.signature
                })
        return patterns

    def _get_relevant_interfaces(self, analysis: RequirementAnalysis) -> List[Dict[str, Any]]:
        """Get relevant interfaces from codebase."""
        interfaces = []
        for entity in analysis.key_entities[:3]:
            try:
                locations = self.agent.locate_implementation(entity)
                for loc in locations[:2]:
                    interfaces.append({
                        "name": loc.symbol_name,
                        "signature": loc.signature,
                        "file": loc.file_path
                    })
            except:
                pass
        return interfaces

    def _extract_dependency_info(self, design: DesignPlan) -> Dict[str, Any]:
        """Extract dependency information for task decomposition."""
        return {
            "new_components": [c.get("name") for c in design.new_components],
            "modified_components": [c.get("name") for c in design.modified_components]
        }

    def _format_similar_patterns(self, patterns: List[Dict[str, Any]]) -> str:
        """Format similar patterns for prompt."""
        if not patterns:
            return "None found"
        return "\n".join(f"- {p.get('symbol')} in {p.get('file')}" for p in patterns[:3])

    def _format_interfaces(self, interfaces: List[Dict[str, Any]]) -> str:
        """Format interfaces for prompt."""
        if not interfaces:
            return "None found"
        return "\n".join(f"- {i.get('name')}: {i.get('signature', 'N/A')}" for i in interfaces[:3])

    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON."""
        import re

        # Remove markdown code blocks
        response = response.strip()

        # Remove ```json and ``` markers
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]

        if response.endswith('```'):
            response = response[:-3]

        response = response.strip()

        # Try to extract JSON array or object
        json_pattern = r'(\[.*\]|\{.*\})'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            return match.group(1)

        return response

    def _generate_file_path(self, task_data: Dict[str, Any], design: DesignPlan, index: int) -> str:
        """Generate file path for task when not specified."""
        task_type = task_data.get("task_type", "modify_file")
        description = task_data.get("description", "").lower()
        target_symbol = task_data.get("target_symbol", "")

        # Try to extract component name from description or symbol
        component_name = target_symbol or self._extract_component_name(description)

        if task_type == "create_file":
            # For new files, use src directory
            if component_name:
                return f"src/{component_name.lower()}.py"
            else:
                return f"src/component_{index}.py"

        elif task_type == "add_test":
            # For tests, use tests directory
            if component_name:
                return f"tests/test_{component_name.lower()}.py"
            else:
                return f"tests/test_component_{index}.py"

        else:
            # For modifications, try to find from design plan
            for component in design.modified_components:
                comp_name = component.get('name', '')
                if comp_name.lower() in description:
                    return component.get('file', f"src/{comp_name.lower()}.py")

            # Fallback
            if component_name:
                return f"src/{component_name.lower()}.py"
            else:
                return f"src/modified_{index}.py"

    def _extract_component_name(self, description: str) -> str:
        """Extract component name from description."""
        import re

        # Look for patterns like "Create X", "Implement Y", "Add Z"
        patterns = [
            r'create\s+(\w+)',
            r'implement\s+(\w+)',
            r'add\s+(\w+)',
            r'build\s+(\w+)',
            r'develop\s+(\w+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)

        # If no pattern matches, try to get first capitalized word
        words = description.split()
        for word in words:
            if word and word[0].isupper():
                return word

        return ""


