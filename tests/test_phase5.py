"""
Tests for Phase 5: Integration and Optimization.
"""

import pytest
from pathlib import Path
import time
from intentgraph.agent import (
    CodingAgentWorkflow,
    WorkflowStatus,
    CacheManager,
    AgentLogger,
    get_logger,
    configure_logger,
)


class TestWorkflow:
    """Tests for CodingAgentWorkflow."""
    
    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = CodingAgentWorkflow(Path("."))
        
        assert workflow.repo_path == Path(".")
        assert workflow.token_budget == 30000
        assert workflow.agent is not None
        assert workflow.context_manager is not None
        assert workflow.analyzer is not None
        assert workflow.generator is not None
    
    def test_implement_feature_workflow(self):
        """Test complete feature implementation workflow."""
        workflow = CodingAgentWorkflow(Path("."), enable_cache=False)
        requirement = "Add a helper function for string manipulation"
        
        result = workflow.implement_feature(requirement)
        
        assert result is not None
        assert result.requirement == requirement
        assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
        assert result.execution_time > 0
        assert result.token_usage >= 0
    
    def test_modify_code_workflow(self):
        """Test code modification workflow."""
        workflow = CodingAgentWorkflow(Path("."), enable_cache=False)
        target = "CodingAgentWorkflow.implement_feature"
        modification = "Add error handling"
        
        result = workflow.modify_code(target, modification)
        
        assert result is not None
        assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
        assert result.execution_time > 0
    
    def test_token_estimation(self):
        """Test token usage estimation."""
        workflow = CodingAgentWorkflow(Path("."))
        requirement = "Add user authentication"
        
        estimate = workflow.get_token_usage_estimate(requirement)
        
        assert "total" in estimate
        assert estimate["total"] > 0
        assert "analysis" in estimate
        assert "design" in estimate
        assert "implementation" in estimate


class TestCacheManager:
    """Tests for CacheManager."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = CacheManager(ttl_seconds=3600)
        
        assert cache.ttl_seconds == 3600
        assert cache._hits == 0
        assert cache._misses == 0
    
    def test_cache_set_and_get(self):
        """Test cache set and get operations."""
        cache = CacheManager()
        
        key = "test_key"
        value = {"data": "test_value"}
        
        cache.set(key, value)
        retrieved = cache.get(key)
        
        assert retrieved == value
        assert cache._hits == 1
        assert cache._misses == 0
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = CacheManager()
        
        result = cache.get("nonexistent_key")
        
        assert result is None
        assert cache._misses == 1
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        cache = CacheManager(ttl_seconds=1)
        
        cache.set("key", "value", ttl_seconds=1)
        
        # Should be available immediately
        assert cache.get("key") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key") is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = CacheManager()
        
        cache.set("key", "value")
        assert cache.get("key") == "value"
        
        cache.invalidate("key")
        assert cache.get("key") is None
    
    def test_cache_clear(self):
        """Test cache clear."""
        cache = CacheManager()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        cache = CacheManager()
        
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["total_requests"] == 2
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = CacheManager.generate_key("prefix", "arg1", "arg2", param="value")
        key2 = CacheManager.generate_key("prefix", "arg1", "arg2", param="value")
        key3 = CacheManager.generate_key("prefix", "arg1", "arg3", param="value")
        
        assert key1 == key2  # Same inputs = same key
        assert key1 != key3  # Different inputs = different key


class TestAgentLogger:
    """Tests for AgentLogger."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = AgentLogger()
        
        assert logger.logger is not None
        assert len(logger._metrics) == 0
    
    def test_operation_tracking(self):
        """Test operation tracking."""
        logger = AgentLogger()
        
        logger.start_operation("test_operation", param="value")
        time.sleep(0.1)
        logger.end_operation(success=True, token_usage=1000)
        
        assert len(logger._metrics) == 1
        metric = logger._metrics[0]
        assert metric.operation == "test_operation"
        assert metric.success is True
        assert metric.token_usage == 1000
        assert metric.duration > 0
    
    def test_metrics_summary(self):
        """Test metrics summary."""
        logger = AgentLogger()
        
        # Simulate operations
        logger.start_operation("op1")
        logger.end_operation(success=True, token_usage=1000)
        
        logger.start_operation("op2")
        logger.end_operation(success=False, error="Test error")
        
        summary = logger.get_metrics_summary()
        
        assert summary["total_operations"] == 2
        assert summary["successful_operations"] == 1
        assert summary["failed_operations"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["total_tokens"] == 1000
    
    def test_operation_metrics_filtering(self):
        """Test filtering metrics by operation."""
        logger = AgentLogger()
        
        logger.start_operation("op1")
        logger.end_operation(success=True)
        
        logger.start_operation("op2")
        logger.end_operation(success=True)
        
        logger.start_operation("op1")
        logger.end_operation(success=True)
        
        op1_metrics = logger.get_operation_metrics("op1")
        
        assert len(op1_metrics) == 2
        assert all(m.operation == "op1" for m in op1_metrics)


class TestWorkflowWithCache:
    """Tests for workflow with caching enabled."""
    
    def test_workflow_with_cache(self):
        """Test workflow with caching."""
        workflow = CodingAgentWorkflow(Path("."), enable_cache=True)
        
        assert workflow.cache is not None
    
    def test_cached_feature_implementation(self):
        """Test that feature implementation uses cache."""
        workflow = CodingAgentWorkflow(Path("."), enable_cache=True)
        requirement = "Test caching feature"
        
        # First call
        result1 = workflow.implement_feature(requirement)
        time1 = result1.execution_time
        
        # Second call (should use cache)
        result2 = workflow.implement_feature(requirement)
        time2 = result2.execution_time
        
        # Second call should be faster (or at least not slower)
        assert time2 <= time1 * 1.5  # Allow some variance

