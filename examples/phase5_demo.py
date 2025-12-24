"""
Demo script for Phase 5: Integration and Optimization.

Demonstrates:
1. Complete workflow orchestration
2. Caching mechanism
3. Logging and monitoring
4. Performance optimization
"""

from pathlib import Path
from intentgraph.agent import (
    CodingAgentWorkflow,
    WorkflowStatus,
    CacheManager,
    configure_logger,
    get_logger,
)


def demo_workflow_orchestration():
    """Demonstrate complete workflow orchestration."""
    print("=" * 80)
    print("Demo 1: Complete Workflow Orchestration")
    print("=" * 80)
    
    # Configure logger
    configure_logger(log_file=Path("agent.log"))
    logger = get_logger()
    
    # Initialize workflow
    repo_path = Path(".")
    workflow = CodingAgentWorkflow(repo_path, enable_cache=True)
    
    # Test 1: New feature implementation
    print("\n[Test 1] New Feature Implementation")
    print("-" * 80)
    requirement = "Add a function to calculate code complexity score"
    
    result = workflow.implement_feature(requirement)
    
    print(f"Status: {result.status.value}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Token Usage: {result.token_usage:,}")
    print(f"Files Created: {len(result.files_created)}")
    print(f"Tests Generated: {len(result.tests_generated)}")
    
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")
    
    # Test 2: Code modification
    print("\n[Test 2] Code Modification")
    print("-" * 80)
    target = "CodingAgentWorkflow.implement_feature"
    modification = "Add progress callback support"
    
    result = workflow.modify_code(target, modification)
    
    print(f"Status: {result.status.value}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Token Usage: {result.token_usage:,}")
    print(f"Files Modified: {len(result.files_modified)}")
    
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    # Display metrics
    print("\n[Metrics Summary]")
    print("-" * 80)
    metrics = logger.get_metrics_summary()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")


def demo_caching_mechanism():
    """Demonstrate caching mechanism."""
    print("\n\n" + "=" * 80)
    print("Demo 2: Caching Mechanism")
    print("=" * 80)
    
    # Initialize cache
    cache_dir = Path(".intentgraph/cache")
    cache = CacheManager(cache_dir=cache_dir, ttl_seconds=3600)
    
    # Test cache operations
    print("\n[Test 1] Cache Set and Get")
    print("-" * 80)
    
    key = "test_requirement"
    value = {"analysis": "test", "complexity": "medium"}
    
    cache.set(key, value)
    print(f"✓ Cached: {key}")
    
    retrieved = cache.get(key)
    print(f"✓ Retrieved: {retrieved}")
    print(f"Match: {retrieved == value}")
    
    # Test cache miss
    print("\n[Test 2] Cache Miss")
    print("-" * 80)
    
    missing = cache.get("nonexistent_key")
    print(f"Result: {missing}")
    
    # Test cache statistics
    print("\n[Test 3] Cache Statistics")
    print("-" * 80)
    
    stats = cache.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2%}" if "rate" in key else f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Test cache with workflow
    print("\n[Test 4] Cache with Workflow")
    print("-" * 80)
    
    workflow = CodingAgentWorkflow(Path("."), enable_cache=True)
    requirement = "Add logging to all methods"
    
    # First call (cache miss)
    print("First call (should be cache miss)...")
    import time
    start = time.time()
    result1 = workflow.implement_feature(requirement)
    time1 = time.time() - start
    print(f"  Time: {time1:.2f}s")
    
    # Second call (cache hit)
    print("Second call (should be cache hit)...")
    start = time.time()
    result2 = workflow.implement_feature(requirement)
    time2 = time.time() - start
    print(f"  Time: {time2:.2f}s")
    print(f"  Speedup: {time1/time2:.1f}x faster")


def demo_token_estimation():
    """Demonstrate token usage estimation."""
    print("\n\n" + "=" * 80)
    print("Demo 3: Token Usage Estimation")
    print("=" * 80)
    
    workflow = CodingAgentWorkflow(Path("."))
    
    requirements = [
        "Add user authentication",
        "Fix memory leak in cache",
        "Refactor database connection pool",
        "Add comprehensive logging",
    ]
    
    print("\nToken Estimates:")
    print("-" * 80)
    print(f"{'Requirement':<40} {'Total Tokens':>15} {'Estimated Cost':>15}")
    print("-" * 80)
    
    for req in requirements:
        estimate = workflow.get_token_usage_estimate(req)
        total = estimate["total"]
        cost = total * 0.00003  # GPT-4 pricing
        print(f"{req:<40} {total:>15,} ${cost:>14.4f}")
    
    print("-" * 80)


def demo_logging_and_monitoring():
    """Demonstrate logging and monitoring."""
    print("\n\n" + "=" * 80)
    print("Demo 4: Logging and Monitoring")
    print("=" * 80)
    
    # Configure logger with file output
    log_file = Path("agent_demo.log")
    configure_logger(log_file=log_file)
    logger = get_logger()
    
    print(f"\n✓ Logger configured (output: {log_file})")
    
    # Simulate operations
    print("\n[Simulating Operations]")
    print("-" * 80)
    
    operations = [
        ("analyze_requirement", True, 2000),
        ("design_solution", True, 5000),
        ("implement_feature", True, 4000),
        ("generate_tests", False, 3000),  # Simulate failure
    ]
    
    for op_name, success, tokens in operations:
        logger.start_operation(op_name)
        import time
        time.sleep(0.1)  # Simulate work
        
        if success:
            logger.end_operation(success=True, token_usage=tokens)
            print(f"✓ {op_name}: Success ({tokens} tokens)")
        else:
            logger.end_operation(success=False, error="Simulated error")
            print(f"✗ {op_name}: Failed")
    
    # Display metrics
    print("\n[Metrics Summary]")
    print("-" * 80)
    
    metrics = logger.get_metrics_summary()
    print(f"Total Operations: {metrics['total_operations']}")
    print(f"Successful: {metrics['successful_operations']}")
    print(f"Failed: {metrics['failed_operations']}")
    print(f"Success Rate: {metrics['success_rate']:.1%}")
    print(f"Total Duration: {metrics['total_duration']:.2f}s")
    print(f"Average Duration: {metrics['average_duration']:.2f}s")
    print(f"Total Tokens: {metrics['total_tokens']:,}")
    print(f"Average Tokens: {metrics['average_tokens']:.0f}")
    
    # Export metrics
    metrics_file = Path("agent_metrics.json")
    logger.export_metrics(metrics_file)
    print(f"\n✓ Metrics exported to {metrics_file}")


if __name__ == "__main__":
    try:
        demo_workflow_orchestration()
        demo_caching_mechanism()
        demo_token_estimation()
        demo_logging_and_monitoring()
        
        print("\n\n" + "=" * 80)
        print("All Phase 5 Demos Complete!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()

