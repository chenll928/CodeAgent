"""
Context Manager for AI Coding Agent.

This module provides precise context extraction and token optimization
without requiring LLM calls. It leverages IntentGraph's dependency analysis
to provide layered context loading, impact analysis, and intelligent compression.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import re

from ..ai.enhanced_agent import (
    EnhancedCodebaseAgent,
    CallChain,
    CallChainNode,
    CodeLocation,
)
from ..domain.models import CodeSymbol


class ContextLayer(str, Enum):
    """Context layers for progressive loading."""
    CORE = "core"  # Target code + signature (1KB)
    DEPENDENCIES = "dependencies"  # Direct dependencies (2KB)
    CALL_CHAIN = "call_chain"  # Call chain analysis (3KB)
    PATTERNS = "patterns"  # Similar patterns (4KB)


@dataclass
class CodeChange:
    """Represents a code change for impact analysis."""
    target_symbol: str
    target_file: str
    change_type: str  # 'signature_change', 'implementation_change', 'deletion', 'addition'
    description: str
    line_range: Tuple[int, int]


@dataclass
class ImpactAnalysis:
    """Results of impact analysis for a code change."""
    change: CodeChange
    direct_callers: List[CodeLocation] = field(default_factory=list)
    indirect_callers: List[CodeLocation] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)
    risk_level: str = "low"  # 'low', 'medium', 'high'
    breaking_changes: List[str] = field(default_factory=list)
    migration_notes: List[str] = field(default_factory=list)


@dataclass
class PreciseContext:
    """Precise context optimized for token budget."""
    target_code: Dict[str, Any]
    direct_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    call_chain: Optional[Dict[str, Any]] = None
    similar_patterns: List[Dict[str, Any]] = field(default_factory=list)
    impact_analysis: Optional[ImpactAnalysis] = None
    token_estimate: int = 0
    layers_included: List[ContextLayer] = field(default_factory=list)


class ContextManager:
    """
    Context Manager for precise context extraction and token optimization.
    
    This class provides NO-LLM context management capabilities:
    - Call chain tracing based on dependency graphs
    - Layered context loading with token budgets
    - Impact analysis for code changes
    - Intelligent context compression
    - Relevance scoring and filtering
    """

    def __init__(self, agent: EnhancedCodebaseAgent):
        """
        Initialize context manager with an enhanced agent.
        
        Args:
            agent: EnhancedCodebaseAgent instance with full analysis
        """
        self.agent = agent
        self._token_estimates = {
            ContextLayer.CORE: 1000,
            ContextLayer.DEPENDENCIES: 2000,
            ContextLayer.CALL_CHAIN: 3000,
            ContextLayer.PATTERNS: 4000,
        }

    def trace_call_chain(
        self,
        symbol: str,
        depth: int = 3,
        direction: str = "both"
    ) -> CallChain:
        """
        Trace call chain for a symbol (NO LLM).
        
        Uses IntentGraph's dependency graph to trace:
        - Upstream: Who calls this function
        - Downstream: What this function calls
        
        Args:
            symbol: Symbol name to trace
            depth: Maximum depth to trace
            direction: "upstream", "downstream", or "both"
            
        Returns:
            CallChain with complete call paths and line numbers
        """
        return self.agent.get_call_chain(symbol, direction=direction, max_depth=depth)

    def extract_precise_context(
        self,
        target: str,
        token_budget: int,
        task_type: str = "general"
    ) -> PreciseContext:
        """
        Extract precise context with layered loading (NO LLM).
        
        Progressively loads context layers based on token budget:
        - Layer 1 (1KB): Target code + signature
        - Layer 2 (2KB): + Direct dependencies
        - Layer 3 (3KB): + Call chain
        - Layer 4 (4KB): + Similar patterns
        
        Args:
            target: Target symbol name
            token_budget: Maximum tokens to use
            task_type: Type of task for context optimization
            
        Returns:
            PreciseContext with optimized content
        """
        context = PreciseContext(target_code={})
        remaining_budget = token_budget
        
        # Layer 1: Core context (always include)
        target_code = self._get_target_code(target)
        if not target_code:
            return context
            
        context.target_code = target_code
        context.layers_included.append(ContextLayer.CORE)
        remaining_budget -= self._token_estimates[ContextLayer.CORE]
        context.token_estimate += self._token_estimates[ContextLayer.CORE]

        # Layer 2: Direct dependencies (if budget allows)
        if remaining_budget >= self._token_estimates[ContextLayer.DEPENDENCIES]:
            dependencies = self._get_direct_dependencies(target)
            context.direct_dependencies = dependencies
            context.layers_included.append(ContextLayer.DEPENDENCIES)
            remaining_budget -= self._token_estimates[ContextLayer.DEPENDENCIES]
            context.token_estimate += self._token_estimates[ContextLayer.DEPENDENCIES]

        # Layer 3: Call chain (if budget allows)
        if remaining_budget >= self._token_estimates[ContextLayer.CALL_CHAIN]:
            call_chain_data = self._get_call_chain_context(target, depth=2)
            context.call_chain = call_chain_data
            context.layers_included.append(ContextLayer.CALL_CHAIN)
            remaining_budget -= self._token_estimates[ContextLayer.CALL_CHAIN]
            context.token_estimate += self._token_estimates[ContextLayer.CALL_CHAIN]

        # Layer 4: Similar patterns (if budget allows)
        if remaining_budget >= self._token_estimates[ContextLayer.PATTERNS]:
            patterns = self._find_similar_patterns(target, limit=3)
            context.similar_patterns = patterns
            context.layers_included.append(ContextLayer.PATTERNS)
            context.token_estimate += min(remaining_budget, self._token_estimates[ContextLayer.PATTERNS])

        return context

    def analyze_impact(self, change: CodeChange) -> ImpactAnalysis:
        """
        Analyze impact of a code change (NO LLM).

        Uses dependency graph algorithms to determine:
        - Direct impact: Immediate callers and callees
        - Indirect impact: Transitive dependencies
        - Risk assessment: Breaking change detection

        Args:
            change: CodeChange to analyze

        Returns:
            ImpactAnalysis with affected code and risk level
        """
        analysis = ImpactAnalysis(change=change)

        # Find direct callers
        call_chain = self.agent.get_call_chain(
            change.target_symbol,
            direction="upstream",
            max_depth=1
        )

        # Extract direct callers from call chain
        for path in call_chain.upstream:
            if len(path) > 1:  # Has callers
                caller_node = path[1]  # First caller
                analysis.direct_callers.append(CodeLocation(
                    file_path=caller_node.file_path,
                    symbol_name=caller_node.symbol_name,
                    symbol_type=caller_node.symbol_type,
                    line_start=caller_node.line_number,
                    line_end=caller_node.line_number
                ))

        # Find indirect callers (depth 2+)
        extended_chain = self.agent.get_call_chain(
            change.target_symbol,
            direction="upstream",
            max_depth=3
        )

        for path in extended_chain.upstream:
            if len(path) > 2:  # Has indirect callers
                for node in path[2:]:
                    analysis.indirect_callers.append(CodeLocation(
                        file_path=node.file_path,
                        symbol_name=node.symbol_name,
                        symbol_type=node.symbol_type,
                        line_start=node.line_number,
                        line_end=node.line_number
                    ))

        # Find affected test files
        analysis.affected_tests = self._find_affected_tests(change.target_file)

        # Assess risk level
        analysis.risk_level = self._assess_risk_level(
            change.change_type,
            len(analysis.direct_callers),
            len(analysis.indirect_callers)
        )

        # Detect breaking changes
        if change.change_type == "signature_change":
            analysis.breaking_changes.append(
                f"Signature change in {change.target_symbol} may break {len(analysis.direct_callers)} direct callers"
            )
            analysis.migration_notes.append(
                f"Update all callers of {change.target_symbol} to match new signature"
            )
        elif change.change_type == "deletion":
            analysis.breaking_changes.append(
                f"Deletion of {change.target_symbol} will break {len(analysis.direct_callers)} callers"
            )
            analysis.migration_notes.append(
                f"Provide alternative implementation or migration path for {change.target_symbol}"
            )

        return analysis

    def compress_context(
        self,
        context: Dict[str, Any],
        target_size: int
    ) -> Dict[str, Any]:
        """
        Intelligently compress context to target size (NO LLM).

        Compression strategies:
        1. Remove comments and docstrings
        2. Compress whitespace
        3. Keep only function signatures
        4. Use symbol references instead of full code

        Args:
            context: Context dictionary to compress
            target_size: Target size in tokens

        Returns:
            Compressed context dictionary
        """
        compressed = {}

        for key, value in context.items():
            if key == "target_code":
                # Keep target code but remove comments
                if isinstance(value, dict) and "code" in value:
                    compressed[key] = {
                        **value,
                        "code": self._remove_comments(value["code"])
                    }
                else:
                    compressed[key] = value

            elif key == "direct_dependencies":
                # Only keep signatures, not implementations
                compressed[key] = [
                    {
                        "name": dep.get("name", ""),
                        "signature": dep.get("signature", ""),
                        "file": dep.get("file", "")
                    }
                    for dep in value
                ] if isinstance(value, list) else []

            elif key == "call_chain":
                # Compress call chain to essential info
                compressed[key] = self._compress_call_chain(value)

            elif key == "similar_patterns":
                # Use symbol references instead of full code
                compressed[key] = [
                    {
                        "file": p.get("file", ""),
                        "symbol": p.get("symbol", ""),
                        "line": p.get("line", 0)
                    }
                    for p in value
                ] if isinstance(value, list) else []
            else:
                compressed[key] = value

        return compressed

    def rank_context_relevance(
        self,
        contexts: List[Dict[str, Any]],
        task: str,
        target: str
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rank contexts by relevance (NO LLM).

        Scoring factors:
        - Semantic similarity (50%): Keyword matching
        - Dependency strength (30%): Direct vs indirect dependencies
        - Code quality (20%): Documentation, naming conventions

        Args:
            contexts: List of context dictionaries
            task: Task description
            target: Target symbol name

        Returns:
            List of (context, score) tuples sorted by relevance
        """
        scores = []

        for ctx in contexts:
            # Semantic similarity (keyword matching)
            semantic_score = self._semantic_similarity(ctx, task)

            # Dependency strength
            dependency_score = self._dependency_strength(ctx, target)

            # Code quality
            quality_score = self._code_quality(ctx)

            # Weighted total
            total_score = (
                0.5 * semantic_score +
                0.3 * dependency_score +
                0.2 * quality_score
            )

            scores.append((ctx, total_score))

        # Sort by score descending
        return sorted(scores, key=lambda x: x[1], reverse=True)

    def filter_and_denoise(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter and denoise search results (NO LLM).

        Filtering options:
        - exclude_tests: Remove test files
        - min_similarity: Minimum similarity threshold
        - same_layer_only: Only same architectural layer
        - limit: Maximum number of results

        Args:
            results: List of result dictionaries
            filters: Filter configuration

        Returns:
            Filtered and denoised results
        """
        filtered = results

        # Filter test files
        if filters.get("exclude_tests", True):
            filtered = [
                r for r in filtered
                if not self._is_test_file(r.get("file", ""))
            ]

        # Similarity threshold
        if "min_similarity" in filters:
            min_sim = filters["min_similarity"]
            filtered = [
                r for r in filtered
                if r.get("similarity", 0) >= min_sim
            ]

        # Same layer filtering
        if filters.get("same_layer_only", False) and "target" in filters:
            target_layer = self._get_layer(filters["target"])
            filtered = [
                r for r in filtered
                if self._get_layer(r.get("file", "")) == target_layer
            ]

        # Limit results
        if "limit" in filters:
            filtered = filtered[:filters["limit"]]

        return filtered

    # ===== Helper Methods =====

    def _get_target_code(self, symbol: str) -> Dict[str, Any]:
        """Get target code with metadata."""
        self.agent._ensure_initialized()

        if symbol not in self.agent._symbol_index:
            return {}

        location = self.agent._symbol_index[symbol][0]

        # Read actual code from file
        code_content = self._read_code_range(
            location.file_path,
            location.line_start,
            location.line_end
        )

        return {
            "symbol": symbol,
            "file": location.file_path,
            "type": location.symbol_type,
            "line_range": [location.line_start, location.line_end],
            "signature": location.signature,
            "docstring": location.docstring,
            "code": code_content
        }

    def _get_direct_dependencies(self, symbol: str) -> List[Dict[str, Any]]:
        """Get direct dependencies (callees)."""
        callees = self.agent._find_callees(symbol)

        dependencies = []
        for callee in callees[:5]:  # Limit to top 5
            dependencies.append({
                "name": callee.symbol_name,
                "file": callee.file_path,
                "type": callee.symbol_type,
                "line": callee.line_start,
                "signature": callee.signature
            })

        return dependencies

    def _get_call_chain_context(self, symbol: str, depth: int) -> Dict[str, Any]:
        """Get call chain context."""
        call_chain = self.agent.get_call_chain(symbol, direction="both", max_depth=depth)

        return {
            "upstream": [
                {
                    "symbol": node.symbol_name,
                    "file": node.file_path,
                    "line": node.line_number,
                    "depth": node.depth
                }
                for path in call_chain.upstream[:3]  # Top 3 paths
                for node in path[1:]  # Skip target itself
            ],
            "downstream": [
                {
                    "symbol": node.symbol_name,
                    "file": node.file_path,
                    "line": node.line_number,
                    "depth": node.depth
                }
                for path in call_chain.downstream[:3]
                for node in path[1:]
            ],
            "entry_points": [
                {
                    "symbol": ep.symbol_name,
                    "file": ep.file_path,
                    "line": ep.line_number
                }
                for ep in call_chain.entry_points[:3]
            ]
        }

    def _find_similar_patterns(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """Find similar code patterns."""
        # Use agent's pattern matching
        locations = self.agent.find_similar_patterns(symbol)

        patterns = []
        for loc in locations[:limit]:
            patterns.append({
                "symbol": loc.symbol_name,
                "file": loc.file_path,
                "type": loc.symbol_type,
                "line": loc.line_start,
                "signature": loc.signature,
                "relevance": loc.relevance_score
            })

        return patterns

    def _find_affected_tests(self, target_file: str) -> List[str]:
        """Find test files that might be affected."""
        affected_tests = []

        # Look for corresponding test files
        file_path = Path(target_file)
        file_name = file_path.stem

        # Common test patterns
        test_patterns = [
            f"test_{file_name}.py",
            f"{file_name}_test.py",
            f"tests/test_{file_name}.py",
            f"tests/{file_name}_test.py",
        ]

        for pattern in test_patterns:
            test_path = file_path.parent / pattern
            if test_path.exists():
                affected_tests.append(str(test_path))

        return affected_tests

    def _assess_risk_level(
        self,
        change_type: str,
        direct_callers: int,
        indirect_callers: int
    ) -> str:
        """Assess risk level of a change."""
        if change_type in ["deletion", "signature_change"]:
            if direct_callers > 10 or indirect_callers > 20:
                return "high"
            elif direct_callers > 3 or indirect_callers > 10:
                return "medium"
        elif change_type == "implementation_change":
            if direct_callers > 20:
                return "medium"

        return "low"

    def _remove_comments(self, code: str) -> str:
        """Remove comments and docstrings from code."""
        if not code:
            return code

        # Remove single-line comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)

        # Remove docstrings (simplified)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)

        # Remove extra whitespace
        lines = [line.rstrip() for line in code.split('\n') if line.strip()]

        return '\n'.join(lines)

    def _compress_call_chain(self, call_chain: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Compress call chain to essential information."""
        if not call_chain:
            return {}

        return {
            "upstream_count": len(call_chain.get("upstream", [])),
            "downstream_count": len(call_chain.get("downstream", [])),
            "entry_points": call_chain.get("entry_points", [])[:2],  # Top 2 only
        }

    def _semantic_similarity(self, context: Dict[str, Any], task: str) -> float:
        """Calculate semantic similarity using keyword matching."""
        if not task:
            return 0.5

        # Extract keywords from task
        task_keywords = set(task.lower().split())

        # Extract text from context
        context_text = ""
        if "symbol" in context:
            context_text += context["symbol"].lower() + " "
        if "docstring" in context and context["docstring"]:
            context_text += context["docstring"].lower() + " "
        if "signature" in context and context["signature"]:
            context_text += context["signature"].lower() + " "

        context_words = set(context_text.split())

        # Calculate overlap
        if not context_words:
            return 0.0

        overlap = len(task_keywords & context_words)
        return min(1.0, overlap / len(task_keywords))

    def _dependency_strength(self, context: Dict[str, Any], target: str) -> float:
        """Calculate dependency strength."""
        # Direct dependency = 1.0
        if context.get("symbol") == target:
            return 1.0

        # Check if in direct dependencies
        deps = context.get("dependencies", [])
        if any(d.get("name") == target for d in deps):
            return 0.8

        # Check if in call chain
        call_chain = context.get("call_chain", {})
        if call_chain:
            upstream = call_chain.get("upstream", [])
            downstream = call_chain.get("downstream", [])
            if any(n.get("symbol") == target for n in upstream + downstream):
                return 0.5

        return 0.1

    def _code_quality(self, context: Dict[str, Any]) -> float:
        """Assess code quality based on documentation and naming."""
        score = 0.5  # Base score

        # Has docstring
        if context.get("docstring"):
            score += 0.2

        # Has type hints in signature
        signature = context.get("signature", "")
        if "->" in signature or ":" in signature:
            score += 0.2

        # Good naming (not too short, not private)
        symbol = context.get("symbol", "")
        if len(symbol) > 3 and not symbol.startswith("_"):
            score += 0.1

        return min(1.0, score)

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        file_lower = file_path.lower()
        return (
            "test" in file_lower or
            file_lower.startswith("tests/") or
            "/tests/" in file_lower
        )

    def _get_layer(self, file_path: str) -> str:
        """Determine architectural layer from file path."""
        file_lower = file_path.lower()

        if "domain" in file_lower or "model" in file_lower:
            return "domain"
        elif "application" in file_lower or "service" in file_lower:
            return "application"
        elif "adapter" in file_lower or "infrastructure" in file_lower:
            return "infrastructure"
        elif "api" in file_lower or "controller" in file_lower:
            return "api"
        elif "cli" in file_lower:
            return "cli"

        return "other"

    def _read_code_range(
        self,
        file_path: str,
        start_line: int,
        end_line: int
    ) -> str:
        """Read specific line range from a file."""
        try:
            # Handle both absolute and relative paths
            if not Path(file_path).is_absolute():
                file_path = self.agent.repo_path / file_path

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Line numbers are 1-based
                return ''.join(lines[start_line-1:end_line])
        except Exception as e:
            return f"# Error reading file: {e}"

