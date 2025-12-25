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
                file_path = (repo_root / Path(file_info.path)).as_posix()
                self._repo_files.add(file_path)
                module_root = file_path.split('/')[:2]
                if module_root:
                    self._module_roots.add('/'.join(module_root))
        else:
            repo_root = self.agent.repo_path
            for file_path in repo_root.rglob('*.py'):
                rel_path = file_path.relative_to(repo_root).as_posix()
                self._repo_files.add((repo_root / rel_path).as_posix())
                parts = rel_path.split('/')
                if parts:
                    self._module_roots.add('/'.join(parts[:2]))

        self._index_initialized = True

        try:
            analysis = self.agent.get_repository_manifest()
        except AttributeError:
            analysis = None

        if analysis:
            repo_root = Path(analysis.root)
            for file_info in analysis.files:
                file_path = (repo_root / Path(file_info.path)).as_posix()
                self._repo_files.add(file_path)
                module_root = file_path.split('/')[:2]
                if module_root:
                    self._module_roots.add('/'.join(module_root))
        else:
            repo_root = self.agent.repo_path
            for file_path in repo_root.rglob('*.py'):
                rel_path = file_path.relative_to(repo_root).as_posix()
                self._repo_files.add((repo_root / rel_path).as_posix())
                parts = rel_path.split('/')
                if parts:
                    self._module_roots.add('/'.join(parts[:2]))

        self._index_initialized = True

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
            List of Tasks with dependencies and priorities
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

        return tasks

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
        """Build prompt for task decomposition."""
        # Extract component names for file path generation
        new_component_names = [c.get('name', '') for c in design.new_components]

        prompt = f"""Decompose the following design plan into executable tasks.

Design Plan:
- Approach: {design.technical_approach}
- New Components: {', '.join(new_component_names)}
- Modified Components: {len(design.modified_components)}
- Steps: {len(design.implementation_steps)}

Implementation Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(design.implementation_steps))}

IMPORTANT: For each task, you MUST specify a concrete target_file path.
- For new components, use pattern: src/<module_name>/<component_name>.py and ensure <module_name> exists in {sorted(self._module_roots)}
- For modifications, specify the exact file path to modify and ensure it matches one of {sorted(self._repo_files)[:30]}

CRITICAL: DO NOT generate any test-related tasks (add_test). Test generation will be handled separately.
Focus ONLY on implementation tasks: create_file, modify_file, add_function, modify_function.

Please decompose into tasks with:
1. Task ID: Unique identifier (e.g., "task_1", "task_2")
2. Description: What to do
3. Task Type: ONLY use (create_file, modify_file, add_function, modify_function) - NO test tasks
4. Target File: REQUIRED - Concrete file path (e.g., "src/analyzer/requirement_parser.py")
5. Target Symbol: Function/class to work on (if applicable)
6. Dependencies: Other task IDs this depends on
7. Priority: 0-10 (higher = more important)
8. Estimated Tokens: Estimated LLM tokens needed

Respond ONLY with a JSON array of tasks. Do NOT wrap in markdown code blocks.
Example format:
[
  {{
    "task_id": "task_1",
    "description": "Create requirement parser",
    "task_type": "create_file",
    "target_file": "src/analyzer/requirement_parser.py",
    "target_symbol": "RequirementParser",
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
                    if normalized_file not in self._repo_files:
                        # File doesn't exist, should be create_file
                        task_type = "create_file"
                        print(f"[INFO] Adjusted task type from 'modify_file' to 'create_file' for {validated_file} (file doesn't exist)")

                # If LLM says create_file but file exists, change to modify_file
                elif task_type == "create_file":
                    normalized_file = validated_file.replace('\\', '/').lstrip('/')
                    if normalized_file in self._repo_files:
                        # File exists, should be modify_file
                        task_type = "modify_file"
                        print(f"[INFO] Adjusted task type from 'create_file' to 'modify_file' for {validated_file} (file exists)")

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
        """Fallback design without LLM."""
        return DesignPlan(
            requirement_analysis=analysis,
            technical_approach="Implement based on requirement analysis",
            implementation_steps=["Analyze requirement", "Implement solution", "Add tests"]
        )

    def _heuristic_decomposition(self, design: DesignPlan) -> List[Task]:
        """Fallback task decomposition without LLM."""
        tasks = []

        # Generate tasks from new components
        for i, component in enumerate(design.new_components):
            component_name = component.get('name', f'component_{i}')
            component_type = component.get('type', 'module')

            # Generate appropriate file path
            if component_type == 'class':
                file_path = f"src/{component_name.lower()}.py"
            elif component_type == 'module':
                file_path = f"src/{component_name.lower()}/{component_name.lower()}.py"
            else:
                file_path = f"src/{component_name.lower()}.py"

            tasks.append(Task(
                task_id=f"task_{i}",
                description=f"Create {component_name}",
                task_type="create_file",
                target_file=file_path,
                target_symbol=component_name,
                priority=len(design.new_components) - i
            ))

        # If no new components, use implementation steps
        if not tasks:
            for i, step in enumerate(design.implementation_steps):
                tasks.append(Task(
                    task_id=f"task_{i}",
                    description=step,
                    task_type="modify_file",
                    target_file=f"src/implementation_{i}.py",
                    priority=len(design.implementation_steps) - i
                ))

        return tasks

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


