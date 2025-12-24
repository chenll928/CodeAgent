"""
Tests for Context Manager.

This module tests the context management capabilities including:
- Call chain tracing
- Layered context extraction
- Impact analysis
- Context compression
- Relevance ranking
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from src.intentgraph.agent.context_manager import (
    ContextManager,
    PreciseContext,
    ImpactAnalysis,
    CodeChange,
    ContextLayer,
)
from src.intentgraph.ai.enhanced_agent import (
    EnhancedCodebaseAgent,
    CallChain,
    CallChainNode,
    CodeLocation,
)


@pytest.fixture
def mock_agent():
    """Create a mock enhanced agent."""
    agent = Mock(spec=EnhancedCodebaseAgent)
    agent.repo_path = Path("/test/repo")
    agent._symbol_index = {
        "test_function": [
            CodeLocation(
                file_path="src/module.py",
                symbol_name="test_function",
                symbol_type="function",
                line_start=10,
                line_end=20,
                signature="def test_function(x: int) -> str",
                docstring="Test function docstring"
            )
        ]
    }
    return agent


@pytest.fixture
def context_manager(mock_agent):
    """Create a context manager instance."""
    return ContextManager(mock_agent)


class TestCallChainTracing:
    """Test call chain tracing functionality."""
    
    def test_trace_call_chain_upstream(self, context_manager, mock_agent):
        """Test tracing upstream call chain."""
        # Setup mock call chain
        target_node = CallChainNode("test_function", "src/module.py", 10, "function", 0)
        caller_node = CallChainNode("caller_func", "src/caller.py", 5, "function", 1)
        
        mock_chain = CallChain(
            target=target_node,
            upstream=[[target_node, caller_node]],
            entry_points=[caller_node]
        )
        mock_agent.get_call_chain.return_value = mock_chain
        
        # Test
        result = context_manager.trace_call_chain("test_function", depth=3, direction="upstream")
        
        # Verify
        assert result.target.symbol_name == "test_function"
        assert len(result.upstream) == 1
        assert result.upstream[0][1].symbol_name == "caller_func"
        mock_agent.get_call_chain.assert_called_once_with(
            "test_function",
            direction="upstream",
            max_depth=3
        )
    
    def test_trace_call_chain_downstream(self, context_manager, mock_agent):
        """Test tracing downstream call chain."""
        target_node = CallChainNode("test_function", "src/module.py", 10, "function", 0)
        callee_node = CallChainNode("helper_func", "src/helper.py", 15, "function", 1)
        
        mock_chain = CallChain(
            target=target_node,
            downstream=[[target_node, callee_node]],
            leaf_nodes=[callee_node]
        )
        mock_agent.get_call_chain.return_value = mock_chain
        
        result = context_manager.trace_call_chain("test_function", depth=2, direction="downstream")
        
        assert len(result.downstream) == 1
        assert result.downstream[0][1].symbol_name == "helper_func"


class TestPreciseContextExtraction:
    """Test precise context extraction with layered loading."""
    
    def test_extract_core_context_only(self, context_manager, mock_agent):
        """Test extraction with minimal token budget (core only)."""
        mock_agent._ensure_initialized = Mock()
        
        with patch.object(context_manager, '_get_target_code') as mock_get_target:
            mock_get_target.return_value = {
                "symbol": "test_function",
                "file": "src/module.py",
                "type": "function",
                "line_range": [10, 20],
                "signature": "def test_function(x: int) -> str",
                "code": "def test_function(x: int) -> str:\n    return str(x)"
            }
            
            result = context_manager.extract_precise_context("test_function", token_budget=1000)
            
            assert result.target_code["symbol"] == "test_function"
            assert ContextLayer.CORE in result.layers_included
            assert ContextLayer.DEPENDENCIES not in result.layers_included
            assert result.token_estimate <= 1000

    def test_extract_with_dependencies(self, context_manager, mock_agent):
        """Test extraction with enough budget for dependencies."""
        mock_agent._ensure_initialized = Mock()
        mock_agent._find_callees = Mock(return_value=[
            CodeLocation("src/helper.py", "helper_func", "function", 5, 10, "def helper_func()")
        ])

        with patch.object(context_manager, '_get_target_code') as mock_get_target:
            mock_get_target.return_value = {"symbol": "test_function", "file": "src/module.py"}

            result = context_manager.extract_precise_context("test_function", token_budget=5000)

            assert ContextLayer.CORE in result.layers_included
            assert ContextLayer.DEPENDENCIES in result.layers_included
            assert len(result.direct_dependencies) > 0

    def test_extract_with_call_chain(self, context_manager, mock_agent):
        """Test extraction with call chain layer."""
        mock_agent._ensure_initialized = Mock()
        mock_agent._find_callees = Mock(return_value=[])

        target_node = CallChainNode("test_function", "src/module.py", 10, "function", 0)
        mock_chain = CallChain(target=target_node, upstream=[], downstream=[])
        mock_agent.get_call_chain.return_value = mock_chain

        with patch.object(context_manager, '_get_target_code') as mock_get_target:
            mock_get_target.return_value = {"symbol": "test_function"}

            result = context_manager.extract_precise_context("test_function", token_budget=8000)

            assert ContextLayer.CALL_CHAIN in result.layers_included
            assert result.call_chain is not None


class TestImpactAnalysis:
    """Test impact analysis functionality."""

    def test_analyze_signature_change(self, context_manager, mock_agent):
        """Test impact analysis for signature change."""
        change = CodeChange(
            target_symbol="test_function",
            target_file="src/module.py",
            change_type="signature_change",
            description="Changed parameter type",
            line_range=(10, 20)
        )

        # Mock call chain with callers
        caller_node = CallChainNode("caller_func", "src/caller.py", 5, "function", 1)
        target_node = CallChainNode("test_function", "src/module.py", 10, "function", 0)

        mock_chain = CallChain(
            target=target_node,
            upstream=[[target_node, caller_node]],
            entry_points=[caller_node]
        )
        mock_agent.get_call_chain.return_value = mock_chain

        with patch.object(context_manager, '_find_affected_tests') as mock_tests:
            mock_tests.return_value = ["tests/test_module.py"]

            result = context_manager.analyze_impact(change)

            assert result.change == change
            assert len(result.direct_callers) > 0
            assert len(result.breaking_changes) > 0
            assert "signature" in result.breaking_changes[0].lower()
            assert result.risk_level in ["low", "medium", "high"]

    def test_analyze_deletion(self, context_manager, mock_agent):
        """Test impact analysis for deletion."""
        change = CodeChange(
            target_symbol="test_function",
            target_file="src/module.py",
            change_type="deletion",
            description="Removing deprecated function",
            line_range=(10, 20)
        )

        target_node = CallChainNode("test_function", "src/module.py", 10, "function", 0)
        mock_chain = CallChain(target=target_node, upstream=[], entry_points=[])
        mock_agent.get_call_chain.return_value = mock_chain

        with patch.object(context_manager, '_find_affected_tests') as mock_tests:
            mock_tests.return_value = []

            result = context_manager.analyze_impact(change)

            assert len(result.breaking_changes) > 0
            assert "deletion" in result.breaking_changes[0].lower()


class TestContextCompression:
    """Test context compression functionality."""

    def test_compress_target_code(self, context_manager):
        """Test compression of target code."""
        context = {
            "target_code": {
                "code": "def test():\n    # This is a comment\n    '''Docstring'''\n    return 42"
            }
        }

        result = context_manager.compress_context(context, target_size=500)

        assert "target_code" in result
        # Comments should be removed
        assert "#" not in result["target_code"]["code"]

    def test_compress_dependencies(self, context_manager):
        """Test compression of dependencies."""
        context = {
            "direct_dependencies": [
                {
                    "name": "helper",
                    "signature": "def helper(x)",
                    "file": "helper.py",
                    "code": "def helper(x):\n    return x * 2"
                }
            ]
        }

        result = context_manager.compress_context(context, target_size=500)

        # Should keep signature but not full code
        assert "direct_dependencies" in result
        assert result["direct_dependencies"][0]["signature"] == "def helper(x)"
        assert "code" not in result["direct_dependencies"][0]


class TestRelevanceRanking:
    """Test relevance ranking functionality."""

    def test_rank_by_semantic_similarity(self, context_manager):
        """Test ranking by semantic similarity."""
        contexts = [
            {"symbol": "user_login", "docstring": "Handle user authentication"},
            {"symbol": "process_data", "docstring": "Process data records"},
            {"symbol": "authenticate_user", "docstring": "Authenticate user credentials"}
        ]

        task = "implement user authentication"

        result = context_manager.rank_context_relevance(contexts, task, "user_login")

        # Should be sorted by relevance
        assert len(result) == 3
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        # First result should be most relevant
        assert result[0][1] >= result[1][1] >= result[2][1]

    def test_rank_by_dependency_strength(self, context_manager):
        """Test ranking considers dependency strength."""
        contexts = [
            {"symbol": "target_func", "dependencies": []},
            {"symbol": "caller_func", "dependencies": [{"name": "target_func"}]},
            {"symbol": "unrelated_func", "dependencies": []}
        ]

        result = context_manager.rank_context_relevance(contexts, "", "target_func")

        # Target itself should rank highest
        assert result[0][0]["symbol"] == "target_func"


class TestFilteringAndDenoising:
    """Test filtering and denoising functionality."""

    def test_filter_test_files(self, context_manager):
        """Test filtering out test files."""
        results = [
            {"file": "src/module.py", "symbol": "func1"},
            {"file": "tests/test_module.py", "symbol": "test_func1"},
            {"file": "src/helper.py", "symbol": "func2"}
        ]

        filtered = context_manager.filter_and_denoise(
            results,
            {"exclude_tests": True}
        )

        assert len(filtered) == 2
        assert all("test" not in r["file"].lower() for r in filtered)

    def test_filter_by_similarity(self, context_manager):
        """Test filtering by similarity threshold."""
        results = [
            {"file": "src/a.py", "similarity": 0.9},
            {"file": "src/b.py", "similarity": 0.5},
            {"file": "src/c.py", "similarity": 0.3}
        ]

        filtered = context_manager.filter_and_denoise(
            results,
            {"min_similarity": 0.6}
        )

        assert len(filtered) == 1
        assert filtered[0]["similarity"] >= 0.6

    def test_filter_same_layer(self, context_manager):
        """Test filtering by architectural layer."""
        results = [
            {"file": "src/domain/model.py"},
            {"file": "src/api/routes.py"},
            {"file": "src/domain/entity.py"}
        ]

        filtered = context_manager.filter_and_denoise(
            results,
            {"same_layer_only": True, "target": "src/domain/user.py"}
        )

        # Should only include domain layer files
        assert len(filtered) == 2
        assert all("domain" in r["file"] for r in filtered)

    def test_limit_results(self, context_manager):
        """Test limiting number of results."""
        results = [{"file": f"src/file{i}.py"} for i in range(10)]

        filtered = context_manager.filter_and_denoise(
            results,
            {"limit": 3}
        )

        assert len(filtered) == 3


class TestHelperMethods:
    """Test helper methods."""

    def test_is_test_file(self, context_manager):
        """Test test file detection."""
        assert context_manager._is_test_file("tests/test_module.py")
        assert context_manager._is_test_file("src/tests/test_helper.py")
        assert context_manager._is_test_file("test_integration.py")
        assert not context_manager._is_test_file("src/module.py")

    def test_get_layer(self, context_manager):
        """Test layer detection."""
        assert context_manager._get_layer("src/domain/model.py") == "domain"
        assert context_manager._get_layer("src/application/service.py") == "application"
        assert context_manager._get_layer("src/api/routes.py") == "api"
        assert context_manager._get_layer("src/cli/commands.py") == "cli"
        assert context_manager._get_layer("src/adapters/db.py") == "infrastructure"

    def test_remove_comments(self, context_manager):
        """Test comment removal."""
        code = '''def test():
    # This is a comment
    x = 1  # inline comment
    """Docstring"""
    return x'''

        result = context_manager._remove_comments(code)

        assert "#" not in result
        assert '"""' not in result

    def test_assess_risk_level(self, context_manager):
        """Test risk level assessment."""
        # High risk: signature change with many callers
        assert context_manager._assess_risk_level("signature_change", 15, 25) == "high"

        # Medium risk: signature change with some callers
        assert context_manager._assess_risk_level("signature_change", 5, 12) == "medium"

        # Low risk: implementation change with few callers
        assert context_manager._assess_risk_level("implementation_change", 2, 3) == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

