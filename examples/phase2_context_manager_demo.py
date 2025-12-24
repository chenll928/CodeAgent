"""
Demo script for Context Manager capabilities.

This script demonstrates the Phase 2 implementation of the AI Coding Agent:
- Call chain tracing
- Layered context extraction
- Impact analysis
- Context compression
- Relevance ranking and filtering
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from src.intentgraph.ai.enhanced_agent import EnhancedCodebaseAgent
from src.intentgraph.agent.context_manager import (
    ContextManager,
    CodeChange,
    ContextLayer,
)


console = Console()


def demo_call_chain_tracing(manager: ContextManager, symbol: str):
    """Demonstrate call chain tracing."""
    console.print(Panel.fit(
        f"[bold cyan]Call Chain Tracing for: {symbol}[/bold cyan]",
        border_style="cyan"
    ))
    
    # Trace call chain
    call_chain = manager.trace_call_chain(symbol, depth=3, direction="both")
    
    # Display upstream (callers)
    if call_chain.upstream:
        console.print("\n[bold green]Upstream (Callers):[/bold green]")
        tree = Tree(f"🎯 {symbol}")
        for path in call_chain.upstream[:3]:
            branch = tree
            for node in path[1:]:  # Skip target itself
                branch = branch.add(
                    f"📞 {node.symbol_name} ({node.file_path}:{node.line_number})"
                )
        console.print(tree)
    
    # Display downstream (callees)
    if call_chain.downstream:
        console.print("\n[bold yellow]Downstream (Callees):[/bold yellow]")
        tree = Tree(f"🎯 {symbol}")
        for path in call_chain.downstream[:3]:
            branch = tree
            for node in path[1:]:
                branch = branch.add(
                    f"🔧 {node.symbol_name} ({node.file_path}:{node.line_number})"
                )
        console.print(tree)
    
    # Display entry points
    if call_chain.entry_points:
        console.print("\n[bold magenta]Entry Points:[/bold magenta]")
        for ep in call_chain.entry_points[:3]:
            console.print(f"  🚪 {ep.symbol_name} in {ep.file_path}")


def demo_layered_context_extraction(manager: ContextManager, symbol: str):
    """Demonstrate layered context extraction."""
    console.print(Panel.fit(
        f"[bold cyan]Layered Context Extraction for: {symbol}[/bold cyan]",
        border_style="cyan"
    ))
    
    # Test different token budgets
    budgets = [1000, 3000, 6000, 10000]
    
    table = Table(title="Context Layers by Token Budget")
    table.add_column("Budget", style="cyan")
    table.add_column("Layers Included", style="green")
    table.add_column("Token Estimate", style="yellow")
    
    for budget in budgets:
        context = manager.extract_precise_context(symbol, token_budget=budget)
        layers = ", ".join([layer.value for layer in context.layers_included])
        table.add_row(
            f"{budget:,}",
            layers,
            f"{context.token_estimate:,}"
        )
    
    console.print(table)
    
    # Show detailed context for maximum budget
    console.print("\n[bold green]Detailed Context (10K budget):[/bold green]")
    context = manager.extract_precise_context(symbol, token_budget=10000)
    
    if context.target_code:
        console.print(f"\n  📄 Target: {context.target_code.get('symbol', 'N/A')}")
        console.print(f"     File: {context.target_code.get('file', 'N/A')}")
        console.print(f"     Type: {context.target_code.get('type', 'N/A')}")

    if context.direct_dependencies:
        console.print(f"\n  🔗 Dependencies: {len(context.direct_dependencies)}")
        for dep in context.direct_dependencies[:3]:
            console.print(f"     - {dep.get('name', 'N/A')} ({dep.get('file', 'N/A')})")

    if context.call_chain:
        upstream_count = len(context.call_chain.get('upstream', []))
        downstream_count = len(context.call_chain.get('downstream', []))
        console.print(f"\n  📞 Call Chain: {upstream_count} upstream, {downstream_count} downstream")


def demo_impact_analysis(manager: ContextManager, symbol: str):
    """Demonstrate impact analysis."""
    console.print(Panel.fit(
        f"[bold cyan]Impact Analysis for: {symbol}[/bold cyan]",
        border_style="cyan"
    ))

    # Create different types of changes
    changes = [
        CodeChange(
            target_symbol=symbol,
            target_file="src/module.py",
            change_type="signature_change",
            description="Changed parameter type from str to int",
            line_range=(10, 20)
        ),
        CodeChange(
            target_symbol=symbol,
            target_file="src/module.py",
            change_type="implementation_change",
            description="Optimized algorithm",
            line_range=(10, 20)
        ),
        CodeChange(
            target_symbol=symbol,
            target_file="src/module.py",
            change_type="deletion",
            description="Removing deprecated function",
            line_range=(10, 20)
        ),
    ]

    table = Table(title="Impact Analysis Results")
    table.add_column("Change Type", style="cyan")
    table.add_column("Direct Callers", style="yellow")
    table.add_column("Indirect Callers", style="yellow")
    table.add_column("Risk Level", style="red")
    table.add_column("Breaking Changes", style="magenta")

    for change in changes:
        analysis = manager.analyze_impact(change)

        risk_color = {
            "low": "green",
            "medium": "yellow",
            "high": "red"
        }.get(analysis.risk_level, "white")

        table.add_row(
            change.change_type,
            str(len(analysis.direct_callers)),
            str(len(analysis.indirect_callers)),
            f"[{risk_color}]{analysis.risk_level}[/{risk_color}]",
            str(len(analysis.breaking_changes))
        )

    console.print(table)

    # Show detailed analysis for signature change
    console.print("\n[bold green]Detailed Analysis (Signature Change):[/bold green]")
    analysis = manager.analyze_impact(changes[0])

    if analysis.direct_callers:
        console.print(f"\n  ⚠️  Direct Callers ({len(analysis.direct_callers)}):")
        for caller in analysis.direct_callers[:5]:
            console.print(f"     - {caller.symbol_name} in {caller.file_path}")

    if analysis.breaking_changes:
        console.print(f"\n  💥 Breaking Changes:")
        for bc in analysis.breaking_changes:
            console.print(f"     - {bc}")

    if analysis.migration_notes:
        console.print(f"\n  📝 Migration Notes:")
        for note in analysis.migration_notes:
            console.print(f"     - {note}")


def demo_context_compression(manager: ContextManager):
    """Demonstrate context compression."""
    console.print(Panel.fit(
        "[bold cyan]Context Compression[/bold cyan]",
        border_style="cyan"
    ))

    # Create sample context
    original_context = {
        "target_code": {
            "code": '''def example_function(x: int) -> str:
    """
    This is a detailed docstring.
    It explains what the function does.
    """
    # This is a comment
    result = str(x)  # inline comment
    return result''',
            "symbol": "example_function"
        },
        "direct_dependencies": [
            {
                "name": "helper",
                "signature": "def helper(x)",
                "file": "helper.py",
                "code": "def helper(x):\n    return x * 2",
                "docstring": "Helper function"
            }
        ],
        "call_chain": {
            "upstream": [{"symbol": "caller1"}, {"symbol": "caller2"}],
            "downstream": [{"symbol": "callee1"}, {"symbol": "callee2"}],
            "entry_points": [{"symbol": "main"}, {"symbol": "api_handler"}]
        }
    }

    # Compress
    compressed = manager.compress_context(original_context, target_size=500)

    console.print("\n[bold green]Original vs Compressed:[/bold green]")
    console.print(f"\n  Original code length: {len(original_context['target_code']['code'])} chars")
    console.print(f"  Compressed code length: {len(compressed['target_code']['code'])} chars")
    console.print(f"  Reduction: {100 * (1 - len(compressed['target_code']['code']) / len(original_context['target_code']['code'])):.1f}%")

    console.print("\n  Original dependencies: Full code included")
    console.print(f"  Compressed dependencies: Signatures only")
    console.print(f"  Fields kept: {list(compressed['direct_dependencies'][0].keys())}")


def demo_relevance_ranking(manager: ContextManager):
    """Demonstrate relevance ranking."""
    console.print(Panel.fit(
        "[bold cyan]Relevance Ranking[/bold cyan]",
        border_style="cyan"
    ))

    # Sample contexts
    contexts = [
        {
            "symbol": "authenticate_user",
            "docstring": "Authenticate user with email and password",
            "file": "src/auth/service.py"
        },
        {
            "symbol": "process_payment",
            "docstring": "Process payment transaction",
            "file": "src/payment/processor.py"
        },
        {
            "symbol": "login_handler",
            "docstring": "Handle user login request",
            "file": "src/api/auth.py"
        },
        {
            "symbol": "validate_credentials",
            "docstring": "Validate user credentials",
            "file": "src/auth/validator.py"
        }
    ]

    task = "implement user authentication and login"

    ranked = manager.rank_context_relevance(contexts, task, "authenticate_user")

    table = Table(title=f"Ranked by Relevance to: '{task}'")
    table.add_column("Rank", style="cyan")
    table.add_column("Symbol", style="green")
    table.add_column("File", style="yellow")
    table.add_column("Score", style="magenta")

    for i, (ctx, score) in enumerate(ranked, 1):
        table.add_row(
            str(i),
            ctx["symbol"],
            ctx["file"],
            f"{score:.3f}"
        )

    console.print(table)


def demo_filtering(manager: ContextManager):
    """Demonstrate filtering and denoising."""
    console.print(Panel.fit(
        "[bold cyan]Filtering and Denoising[/bold cyan]",
        border_style="cyan"
    ))

    # Sample results
    results = [
        {"file": "src/domain/user.py", "symbol": "User", "similarity": 0.9},
        {"file": "tests/test_user.py", "symbol": "test_user_creation", "similarity": 0.8},
        {"file": "src/domain/account.py", "symbol": "Account", "similarity": 0.7},
        {"file": "src/api/user_routes.py", "symbol": "create_user", "similarity": 0.6},
        {"file": "tests/integration/test_api.py", "symbol": "test_api", "similarity": 0.5},
        {"file": "src/domain/profile.py", "symbol": "Profile", "similarity": 0.4},
    ]

    # Apply different filters
    filters_config = [
        {"name": "No filters", "config": {}},
        {"name": "Exclude tests", "config": {"exclude_tests": True}},
        {"name": "Min similarity 0.6", "config": {"min_similarity": 0.6}},
        {"name": "Same layer (domain)", "config": {"same_layer_only": True, "target": "src/domain/user.py"}},
        {"name": "Top 3 only", "config": {"limit": 3}},
    ]

    table = Table(title="Filtering Results")
    table.add_column("Filter", style="cyan")
    table.add_column("Results", style="green")
    table.add_column("Files", style="yellow")

    for filter_def in filters_config:
        filtered = manager.filter_and_denoise(results, filter_def["config"])
        files = ", ".join([r["file"].split("/")[-1] for r in filtered[:3]])
        if len(filtered) > 3:
            files += f", ... (+{len(filtered) - 3})"

        table.add_row(
            filter_def["name"],
            str(len(filtered)),
            files
        )

    console.print(table)


def main():
    """Run all demos."""
    console.print(Panel.fit(
        "[bold magenta]Phase 2: Context Manager Demo[/bold magenta]\n"
        "Demonstrating NO-LLM context management capabilities",
        border_style="magenta"
    ))

    # Get repository path from user or use current directory
    import sys
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        repo_path = Path.cwd()

    console.print(f"\n[bold]Analyzing repository:[/bold] {repo_path}\n")

    try:
        # Initialize agent and context manager
        with console.status("[bold green]Initializing Enhanced Agent..."):
            agent = EnhancedCodebaseAgent(repo_path)
            agent._ensure_initialized()

        manager = ContextManager(agent)

        console.print("[bold green]✓[/bold green] Agent initialized\n")

        # Find a good symbol to demo with
        if agent._symbol_index:
            demo_symbol = list(agent._symbol_index.keys())[0]
            console.print(f"[bold]Using symbol for demos:[/bold] {demo_symbol}\n")

            # Run demos
            console.print("\n" + "="*80 + "\n")
            demo_call_chain_tracing(manager, demo_symbol)

            console.print("\n" + "="*80 + "\n")
            demo_layered_context_extraction(manager, demo_symbol)

            console.print("\n" + "="*80 + "\n")
            demo_impact_analysis(manager, demo_symbol)

            console.print("\n" + "="*80 + "\n")
            demo_context_compression(manager)

            console.print("\n" + "="*80 + "\n")
            demo_relevance_ranking(manager)

            console.print("\n" + "="*80 + "\n")
            demo_filtering(manager)

            console.print("\n" + "="*80 + "\n")
            console.print(Panel.fit(
                "[bold green]✓ All demos completed successfully![/bold green]",
                border_style="green"
            ))
        else:
            console.print("[bold red]No symbols found in repository[/bold red]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    main()

