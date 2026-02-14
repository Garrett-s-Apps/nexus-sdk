"""
Cost tracking and budget enforcement example.

Shows how NEXUS SDK automatically tracks costs and enforces budgets.
"""

import asyncio
import os

from nexus_sdk.cost.budget import BudgetLimits
from nexus_sdk.cost.tracker import CostTracker
from nexus_sdk.providers.claude import ClaudeProvider


async def main() -> None:
    """Run cost tracking example."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Set up cost tracker with custom budget
    budget = BudgetLimits(
        hourly_target=0.50,  # $0.50/hr target
        hourly_hard_cap=1.00,  # $1/hr triggers downgrade
        session_hard_cap=2.00,  # $2 total kills session
    )
    tracker = CostTracker(budget_limits=budget)

    # Initialize provider
    provider = ClaudeProvider(api_key=api_key)

    # Make several calls and track costs
    tasks = [
        "Explain quantum computing in one sentence.",
        "What is the capital of France?",
        "Write a haiku about programming.",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n[Task {i}] {task}")

        # Get effective model (may be downgraded if over budget)
        requested_model = "sonnet"
        effective_model = tracker.get_effective_model(requested_model)
        if effective_model != requested_model:
            print(f"⚠️  Budget enforcement: {requested_model} → {effective_model}")

        # Execute
        result = await provider.execute(prompt=task, model=effective_model)

        # Record cost
        enforcement = tracker.record(
            model=result.model,
            agent_name="example",
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )

        # Display enforcement actions
        if enforcement.alerts:
            for alert in enforcement.alerts:
                print(f"💰 {alert}")

        if enforcement.kill_session:
            print("❌ Session terminated by budget enforcement")
            break

        print(f"✅ Cost: ${result.cost_usd:.6f} | Total: ${tracker.total_cost:.6f}")

    # Final summary
    print("\n" + "=" * 60)
    print("COST SUMMARY")
    print("=" * 60)
    summary = tracker.get_summary()
    print(f"Session cost:    ${summary['session_cost']:.4f}")
    print(f"Hourly rate:     ${summary['hourly_rate']:.4f}/hr")
    print(f"Total calls:     {summary['call_count']}")
    print(f"Over budget:     {summary['over_budget']}")
    print(f"Downgrade active: {summary['downgrade_active']}")


if __name__ == "__main__":
    asyncio.run(main())
