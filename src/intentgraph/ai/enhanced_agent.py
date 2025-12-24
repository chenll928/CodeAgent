"""
Enhanced CodebaseAgent with call chain tracing and architecture understanding.

This module extends the base CodebaseAgent with advanced capabilities for:
- Call chain tracing (upstream/downstream dependencies)
- Architecture comprehension (layers, modules, patterns)
- Precise code location
- Module boundary detection
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from uuid import UUID

from .agent import CodebaseAgent, AgentContext
from ..application.analyzer import RepositoryAnalyzer
from ..domain.models import AnalysisResult, FileInfo, CodeSymbol, FunctionDependency


@dataclass
class CallChainNode:
    """Represents a node in the call chain."""
    symbol_name: str
    file_path: str
    line_number: int
    symbol_type: str  # 'function', 'class', 'method'
    depth: int = 0


@dataclass
class CallChain:
    """Complete call chain with upstream and downstream paths."""
    target: CallChainNode
    upstream: List[List[CallChainNode]] = field(default_factory=list)  # Callers
    downstream: List[List[CallChainNode]] = field(default_factory=list)  # Callees
    entry_points: List[CallChainNode] = field(default_factory=list)  # Top-level callers
    leaf_nodes: List[CallChainNode] = field(default_factory=list)  # Bottom-level callees


@dataclass
class EntryPoint:
    """Represents an entry point (top-level caller)."""
    symbol_name: str
    file_path: str
    line_number: int
    call_depth: int  # How many levels to reach target


@dataclass
class CodeLocation:
    """Precise code location with context."""
    file_path: str
    symbol_name: str
    symbol_type: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    relevance_score: float = 1.0


@dataclass
class ArchitectureMap:
    """High-level architecture understanding."""
    layers: Dict[str, List[str]]  # layer_name -> [file_paths]
    modules: Dict[str, List[str]]  # module_name -> [file_paths]
    key_abstractions: List[str]  # Important classes/concepts
    design_patterns: Dict[str, List[str]]  # pattern -> [locations]
    entry_points: List[str]  # Main entry points (CLI, API, etc.)
    core_components: List[str]  # Central components


@dataclass
class ModuleBoundaries:
    """Module boundaries and interfaces."""
    module_name: str
    public_interface: List[CodeSymbol]  # Exported symbols
    internal_symbols: List[CodeSymbol]  # Private symbols
    dependencies: List[str]  # Other modules this depends on
    dependents: List[str]  # Modules that depend on this


class EnhancedCodebaseAgent(CodebaseAgent):
    """
    Enhanced CodebaseAgent with advanced code analysis capabilities.

    Extends the base agent with:
    - Call chain tracing (upstream/downstream)
    - Architecture understanding
    - Precise code location
    - Module boundary detection
    """

    def __init__(self, repo_path: Path, agent_context: Dict[str, Any] = None):
        """Initialize enhanced agent with full analysis."""
        super().__init__(repo_path, agent_context)

        # Perform full analysis for enhanced capabilities
        self._analysis_result: Optional[AnalysisResult] = None
        self._dependency_graph: Dict[str, List[str]] = {}
        self._reverse_dependency_graph: Dict[str, List[str]] = {}
        self._symbol_index: Dict[str, List[CodeLocation]] = {}

        # Lazy initialization
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure full analysis is performed (lazy initialization)."""
        if not self._initialized:
            self._perform_full_analysis()
            self._build_dependency_graphs()
            self._build_symbol_index()
            self._initialized = True

    def _perform_full_analysis(self):
        """Perform full repository analysis."""
        analyzer = RepositoryAnalyzer(
            language_filter=['python'],  # Start with Python
            include_tests=False
        )
        self._analysis_result = analyzer.analyze(self.repo_path)

    def _build_dependency_graphs(self):
        """Build forward and reverse dependency graphs."""
        if not self._analysis_result:
            return

        # Build file-level dependency graph
        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)
            self._dependency_graph[file_path] = [str(dep) for dep in file_info.dependencies]

            # Build reverse graph
            for dep in file_info.dependencies:
                dep_path = str(dep)
                if dep_path not in self._reverse_dependency_graph:
                    self._reverse_dependency_graph[dep_path] = []
                self._reverse_dependency_graph[dep_path].append(file_path)

    def _build_symbol_index(self):
        """Build searchable symbol index."""
        if not self._analysis_result:
            return

        for file_info in self._analysis_result.files:
            for symbol in file_info.symbols:
                location = CodeLocation(
                    file_path=str(file_info.path),
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    signature=symbol.signature,
                    docstring=symbol.docstring
                )

                if symbol.name not in self._symbol_index:
                    self._symbol_index[symbol.name] = []
                self._symbol_index[symbol.name].append(location)
# ===== Call Chain Tracing =====

    def get_call_chain(
        self,
        symbol: str,
        direction: str = "both",
        max_depth: int = 3
    ) -> CallChain:
        """
        Get complete call chain for a symbol.

        Args:
            symbol: Symbol name to trace
            direction: "upstream" (callers), "downstream" (callees), or "both"
            max_depth: Maximum depth to trace

        Returns:
            CallChain with upstream and downstream paths
        """
        self._ensure_initialized()

        # Find target symbol
        if symbol not in self._symbol_index:
            return CallChain(
                target=CallChainNode(symbol, "not_found", 0, "unknown")
            )

        target_location = self._symbol_index[symbol][0]
        target_node = CallChainNode(
            symbol_name=symbol,
            file_path=target_location.file_path,
            line_number=target_location.line_start,
            symbol_type=target_location.symbol_type,
            depth=0
        )

        call_chain = CallChain(target=target_node)

        # Trace upstream (who calls this)
        if direction in ["upstream", "both"]:
            call_chain.upstream = self._trace_upstream(symbol, max_depth)
            call_chain.entry_points = self._find_entry_points_from_paths(call_chain.upstream)

        # Trace downstream (what this calls)
        if direction in ["downstream", "both"]:
            call_chain.downstream = self._trace_downstream(symbol, max_depth)
            call_chain.leaf_nodes = self._find_leaf_nodes_from_paths(call_chain.downstream)

        return call_chain

    def find_entry_points(self, symbol: str) -> List[EntryPoint]:
        """
        Find entry points (top-level callers) for a symbol.

        Args:
            symbol: Symbol name to find entry points for

        Returns:
            List of entry points with call depth
        """
        call_chain = self.get_call_chain(symbol, direction="upstream", max_depth=5)

        entry_points = []
        for ep in call_chain.entry_points:
            entry_points.append(EntryPoint(
                symbol_name=ep.symbol_name,
                file_path=ep.file_path,
                line_number=ep.line_number,
                call_depth=ep.depth
            ))

        return entry_points

    def find_leaf_dependencies(self, symbol: str) -> List[CodeLocation]:
        """
        Find leaf dependencies (bottom-level callees) for a symbol.

        Args:
            symbol: Symbol name to find leaf dependencies for

        Returns:
            List of leaf dependencies
        """
        call_chain = self.get_call_chain(symbol, direction="downstream", max_depth=5)

        leaf_deps = []
        for leaf in call_chain.leaf_nodes:
            leaf_deps.append(CodeLocation(
                file_path=leaf.file_path,
                symbol_name=leaf.symbol_name,
                symbol_type=leaf.symbol_type,
                line_start=leaf.line_number,
                line_end=leaf.line_number
            ))

        return leaf_deps

    def _trace_upstream(self, symbol: str, max_depth: int) -> List[List[CallChainNode]]:
        """Trace upstream callers using BFS."""
        if not self._analysis_result or symbol not in self._symbol_index:
            return []

        paths = []
        visited = set()

        # Start with the target symbol
        start_location = self._symbol_index[symbol][0]
        start_node = CallChainNode(
            symbol_name=symbol,
            file_path=start_location.file_path,
            line_number=start_location.line_start,
            symbol_type=start_location.symbol_type,
            depth=0
        )

        queue = deque([(symbol, [start_node], 0)])

        while queue:
            current_symbol, path, depth = queue.popleft()

            if depth >= max_depth:
                paths.append(path)
                continue

            # Find callers
            callers = self._find_callers(current_symbol)

            if not callers:
                # Reached entry point
                paths.append(path)
            else:
                for caller in callers:
                    caller_key = f"{caller.symbol_name}:{caller.file_path}"
                    if caller_key not in visited:
                        visited.add(caller_key)
                        caller_node = CallChainNode(
                            symbol_name=caller.symbol_name,
                            file_path=caller.file_path,
                            line_number=caller.line_start,
                            symbol_type=caller.symbol_type,
                            depth=depth + 1
                        )
                        new_path = path + [caller_node]
                        queue.append((caller.symbol_name, new_path, depth + 1))

        return paths[:10]  # Limit to top 10 paths

    def _trace_downstream(self, symbol: str, max_depth: int) -> List[List[CallChainNode]]:
        """Trace downstream callees using BFS."""
        if not self._analysis_result or symbol not in self._symbol_index:
            return []

        paths = []
        visited = set()

        # Start with the target symbol
        start_location = self._symbol_index[symbol][0]
        start_node = CallChainNode(
            symbol_name=symbol,
            file_path=start_location.file_path,
            line_number=start_location.line_start,
            symbol_type=start_location.symbol_type,
            depth=0
        )

        queue = deque([(symbol, [start_node], 0)])

        while queue:
            current_symbol, path, depth = queue.popleft()

            if depth >= max_depth:
                paths.append(path)
                continue

            # Find callees
            callees = self._find_callees(current_symbol)

            if not callees:
                # Reached leaf node
                paths.append(path)
            else:
                for callee in callees:
                    callee_key = f"{callee.symbol_name}:{callee.file_path}"
                    if callee_key not in visited:
                        visited.add(callee_key)
                        callee_node = CallChainNode(
                            symbol_name=callee.symbol_name,
                            file_path=callee.file_path,
                            line_number=callee.line_start,
                            symbol_type=callee.symbol_type,
                            depth=depth + 1
                        )
                        new_path = path + [callee_node]
                        queue.append((callee.symbol_name, new_path, depth + 1))

        return paths[:10]  # Limit to top 10 paths

    def _find_callers(self, symbol: str) -> List[CodeLocation]:
        """Find all symbols that call the given symbol."""
        callers = []

        if not self._analysis_result:
            return callers

        # Search through function dependencies
        for file_info in self._analysis_result.files:
            for dep in file_info.function_dependencies:
                # Find the target symbol by name (simplified)
                target_symbol = next((s for s in file_info.symbols if s.name == symbol), None)
                if not target_symbol:
                    continue

                # Check if this dependency points to our symbol
                if dep.to_symbol == target_symbol.id:
                    # Find the calling symbol
                    caller_symbol = next((s for s in file_info.symbols if s.id == dep.from_symbol), None)
                    if caller_symbol:
                        callers.append(CodeLocation(
                            file_path=str(file_info.path),
                            symbol_name=caller_symbol.name,
                            symbol_type=caller_symbol.symbol_type,
                            line_start=caller_symbol.line_start,
                            line_end=caller_symbol.line_end
                        ))

        return callers

    def _find_callees(self, symbol: str) -> List[CodeLocation]:
        """Find all symbols called by the given symbol."""
        callees = []

        if not self._analysis_result:
            return callees

        # Find the file containing this symbol
        for file_info in self._analysis_result.files:
            # Find the symbol in this file
            symbol_obj = next((s for s in file_info.symbols if s.name == symbol), None)
            if not symbol_obj:
                continue

            # Find all dependencies from this symbol
            for dep in file_info.function_dependencies:
                if dep.from_symbol == symbol_obj.id:
                    # Find the target symbol in the codebase
                    target_location = self._find_symbol_by_uuid(dep.to_symbol)
                    if target_location:
                        callees.append(target_location)

        return callees

    def _find_symbol_by_uuid(self, symbol_id: UUID) -> Optional[CodeLocation]:
        """Find a symbol by its UUID."""
        if not self._analysis_result:
            return None

        for file_info in self._analysis_result.files:
            for symbol in file_info.symbols:
                if symbol.id == symbol_id:
                    return CodeLocation(
                        file_path=str(file_info.path),
                        symbol_name=symbol.name,
                        symbol_type=symbol.symbol_type,
                        line_start=symbol.line_start,
                        line_end=symbol.line_end,
                        signature=symbol.signature,
                        docstring=symbol.docstring
                    )
        return None

    def _find_entry_points_from_paths(self, paths: List[List[CallChainNode]]) -> List[CallChainNode]:
        """Extract entry points from call paths."""
        entry_points = []
        seen = set()

        for path in paths:
            if path:
                # Entry point is the last node in the path (furthest upstream)
                entry_point = path[-1]
                key = f"{entry_point.symbol_name}:{entry_point.file_path}"
                if key not in seen:
                    seen.add(key)
                    entry_points.append(entry_point)

        return entry_points

    def _find_leaf_nodes_from_paths(self, paths: List[List[CallChainNode]]) -> List[CallChainNode]:
        """Extract leaf nodes from call paths."""
        leaf_nodes = []
        seen = set()

        for path in paths:
            if path:
                # Leaf node is the last node in the path (furthest downstream)
                leaf_node = path[-1]
                key = f"{leaf_node.symbol_name}:{leaf_node.file_path}"
                if key not in seen:
                    seen.add(key)
                    leaf_nodes.append(leaf_node)

        return leaf_nodes
# ===== Architecture Understanding =====

    def understand_architecture(self) -> ArchitectureMap:
        """
        Understand the overall architecture of the codebase.

        Returns:
            ArchitectureMap with layers, modules, patterns, etc.
        """
        self._ensure_initialized()

        if not self._analysis_result:
            return ArchitectureMap(
                layers={},
                modules={},
                key_abstractions=[],
                design_patterns={},
                entry_points=[],
                core_components=[]
            )

        # Detect layers based on directory structure and file purposes
        layers = self._detect_layers()

        # Detect modules based on directory grouping
        modules = self._detect_modules()

        # Extract key abstractions (important classes)
        key_abstractions = self._extract_key_abstractions()

        # Detect design patterns
        design_patterns = self._detect_design_patterns()

        # Find entry points (CLI, API, main functions)
        entry_points = self._find_architecture_entry_points()

        # Identify core components (most connected modules)
        core_components = self._identify_core_components()

        return ArchitectureMap(
            layers=layers,
            modules=modules,
            key_abstractions=key_abstractions,
            design_patterns=design_patterns,
            entry_points=entry_points,
            core_components=core_components
        )

    def get_module_boundaries(self, module_name: str) -> Optional[ModuleBoundaries]:
        """
        Get module boundaries and interfaces.

        Args:
            module_name: Name of the module (directory name)

        Returns:
            ModuleBoundaries with public/private interfaces
        """
        self._ensure_initialized()

        if not self._analysis_result:
            return None

        # Find files in this module
        module_files = [
            f for f in self._analysis_result.files
            if module_name in str(f.path)
        ]

        if not module_files:
            return None

        # Separate public and private symbols
        public_interface = []
        internal_symbols = []

        for file_info in module_files:
            for symbol in file_info.symbols:
                if symbol.is_exported and not symbol.is_private:
                    public_interface.append(symbol)
                else:
                    internal_symbols.append(symbol)

        # Find dependencies (other modules this depends on)
        dependencies = set()
        for file_info in module_files:
            for dep in file_info.dependencies:
                dep_str = str(dep)
                # Extract module name from dependency path
                if '/' in dep_str:
                    dep_module = dep_str.split('/')[0]
                    if dep_module != module_name:
                        dependencies.add(dep_module)

        # Find dependents (modules that depend on this)
        dependents = set()
        for file_info in self._analysis_result.files:
            if module_name not in str(file_info.path):
                for dep in file_info.dependencies:
                    if module_name in str(dep):
                        # Extract module name from file path
                        file_path_str = str(file_info.path)
                        if '/' in file_path_str:
                            dependent_module = file_path_str.split('/')[0]
                            dependents.add(dependent_module)

        return ModuleBoundaries(
            module_name=module_name,
            public_interface=public_interface,
            internal_symbols=internal_symbols,
            dependencies=list(dependencies),
            dependents=list(dependents)
        )

    def locate_implementation(self, feature_description: str) -> List[CodeLocation]:
        """
        Locate implementation based on feature description.

        Args:
            feature_description: Natural language description of feature

        Returns:
            List of code locations ranked by relevance
        """
        self._ensure_initialized()

        locations = []

        # Simple keyword matching (can be enhanced with semantic search)
        keywords = feature_description.lower().split()

        for symbol_name, symbol_locations in self._symbol_index.items():
            # Calculate relevance score
            relevance = 0.0
            symbol_lower = symbol_name.lower()

            for keyword in keywords:
                if keyword in symbol_lower:
                    relevance += 1.0

            if relevance > 0:
                for loc in symbol_locations:
                    loc.relevance_score = relevance / len(keywords)
                    locations.append(loc)

        # Sort by relevance
        locations.sort(key=lambda x: x.relevance_score, reverse=True)

        return locations[:10]  # Top 10 results

    def find_similar_patterns(self, pattern: str) -> List[CodeLocation]:
        """
        Find similar code patterns.

        Args:
            pattern: Pattern to search for (e.g., "authentication", "validation")

        Returns:
            List of code locations with similar patterns
        """
        return self.locate_implementation(pattern)

    def get_minimal_context(
        self,
        target: str,
        task_type: str,
        token_budget: int
    ) -> Dict[str, Any]:
        """
        Get minimal context for a target symbol optimized for token budget.

        Args:
            target: Target symbol name
            task_type: Type of task (bug_fixing, feature_development, etc.)
            token_budget: Maximum tokens to use

        Returns:
            Minimal context dictionary
        """
        self._ensure_initialized()

        if target not in self._symbol_index:
            return {"error": "Symbol not found"}

        context = {}
        remaining_budget = token_budget

        # Layer 1: Target code (always include)
        target_location = self._symbol_index[target][0]
        context["target"] = {
            "file": target_location.file_path,
            "symbol": target_location.symbol_name,
            "type": target_location.symbol_type,
            "line_range": [target_location.line_start, target_location.line_end],
            "signature": target_location.signature
        }
        remaining_budget -= 500  # Estimate 500 tokens

        # Layer 2: Direct dependencies (if budget allows)
        if remaining_budget > 1000:
            callees = self._find_callees(target)
            context["dependencies"] = [
                {"symbol": c.symbol_name, "file": c.file_path}
                for c in callees[:5]
            ]
            remaining_budget -= 1000

        # Layer 3: Call chain (if budget allows)
        if remaining_budget > 2000:
            call_chain = self.get_call_chain(target, direction="upstream", max_depth=2)
            context["callers"] = [
                {"symbol": ep.symbol_name, "file": ep.file_path}
                for ep in call_chain.entry_points[:3]
            ]

        return context

    # ===== Helper Methods for Architecture Understanding =====

    def _detect_layers(self) -> Dict[str, List[str]]:
        """Detect architectural layers based on directory structure."""
        layers = defaultdict(list)

        if not self._analysis_result:
            return dict(layers)

        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)

            # Common layer patterns
            if 'domain' in file_path or 'model' in file_path:
                layers['domain'].append(file_path)
            elif 'application' in file_path or 'service' in file_path:
                layers['application'].append(file_path)
            elif 'adapter' in file_path or 'infrastructure' in file_path:
                layers['infrastructure'].append(file_path)
            elif 'api' in file_path or 'controller' in file_path or 'route' in file_path:
                layers['api'].append(file_path)
            elif 'cli' in file_path or 'command' in file_path:
                layers['cli'].append(file_path)
            else:
                layers['other'].append(file_path)

        return dict(layers)

    def _detect_modules(self) -> Dict[str, List[str]]:
        """Detect modules based on directory grouping."""
        modules = defaultdict(list)

        if not self._analysis_result:
            return dict(modules)

        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)

            # Extract module name from path (first directory)
            parts = file_path.split('/')
            if len(parts) > 1:
                module_name = parts[0]
                modules[module_name].append(file_path)

        return dict(modules)

    def _extract_key_abstractions(self) -> List[str]:
        """Extract key abstractions (important classes)."""
        abstractions = []

        if not self._analysis_result:
            return abstractions

        # Count references to each class
        class_references = defaultdict(int)

        for file_info in self._analysis_result.files:
            for symbol in file_info.symbols:
                if symbol.symbol_type == 'class' and symbol.is_exported:
                    class_references[symbol.name] += 1

            # Count dependencies as references
            for dep in file_info.function_dependencies:
                # This is simplified - in real implementation, track class usage
                pass

        # Sort by reference count and take top abstractions
        sorted_classes = sorted(class_references.items(), key=lambda x: x[1], reverse=True)
        abstractions = [name for name, count in sorted_classes[:10]]

        return abstractions

    def _detect_design_patterns(self) -> Dict[str, List[str]]:
        """Detect design patterns in the codebase."""
        patterns = defaultdict(list)

        if not self._analysis_result:
            return dict(patterns)

        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)

            # Check for common patterns in file names and purposes
            if 'factory' in file_path.lower():
                patterns['factory'].append(file_path)
            elif 'builder' in file_path.lower():
                patterns['builder'].append(file_path)
            elif 'adapter' in file_path.lower():
                patterns['adapter'].append(file_path)
            elif 'repository' in file_path.lower():
                patterns['repository'].append(file_path)
            elif 'service' in file_path.lower():
                patterns['service'].append(file_path)
            elif 'controller' in file_path.lower():
                patterns['controller'].append(file_path)

            # Check file_purpose if available
            if hasattr(file_info, 'file_purpose') and file_info.file_purpose:
                purpose = file_info.file_purpose
                if purpose not in patterns:
                    patterns[purpose].append(file_path)

        return dict(patterns)

    def _find_architecture_entry_points(self) -> List[str]:
        """Find entry points in the architecture."""
        entry_points = []

        if not self._analysis_result:
            return entry_points

        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)

            # Check for common entry point patterns
            if 'main.py' in file_path or 'cli.py' in file_path:
                entry_points.append(file_path)
            elif 'app.py' in file_path or 'server.py' in file_path:
                entry_points.append(file_path)

            # Check for main function
            for symbol in file_info.symbols:
                if symbol.name == 'main' and symbol.symbol_type == 'function':
                    entry_points.append(f"{file_path}::{symbol.name}")

        return entry_points

    def _identify_core_components(self) -> List[str]:
        """Identify core components based on connectivity."""
        component_connections = defaultdict(int)

        if not self._analysis_result:
            return []

        # Count connections for each file
        for file_info in self._analysis_result.files:
            file_path = str(file_info.path)

            # Count outgoing dependencies
            component_connections[file_path] += len(file_info.dependencies)

            # Count incoming dependencies (from reverse graph)
            if file_path in self._reverse_dependency_graph:
                component_connections[file_path] += len(self._reverse_dependency_graph[file_path])

        # Sort by connection count
        sorted_components = sorted(component_connections.items(), key=lambda x: x[1], reverse=True)

        # Return top 10 most connected components
        return [comp for comp, count in sorted_components[:10]]
