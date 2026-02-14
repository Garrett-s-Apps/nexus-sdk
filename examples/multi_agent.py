"""
Multi-agent orchestration example for NEXUS SDK.

Demonstrates a small engineering team working together on a feature.
"""

import asyncio
import os

from nexus_sdk import AgentRegistry, get_team_names
from nexus_sdk.providers.claude import ClaudeProvider


async def main() -> None:
    """Run multi-agent example."""
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Initialize provider
    provider = ClaudeProvider(api_key=api_key)

    # Create agent registry
    registry = AgentRegistry(provider=provider, cost_tracking=True)

    # Get diverse team names
    team = get_team_names(
        ["vp_engineering", "senior_engineer", "qa_lead"], seed=42
    )

    # Register agents
    vp = registry.register(
        id="vp",
        name=team["vp_engineering"]["name"],
        role="VP of Engineering",
        model="opus",  # Use most capable model for planning
    )

    engineer = registry.register(
        id="engineer",
        name=team["senior_engineer"]["name"],
        role="Senior Software Engineer",
        model="sonnet",  # Use balanced model for implementation
    )

    qa = registry.register(
        id="qa",
        name=team["qa_lead"]["name"],
        role="QA Lead",
        model="haiku",  # Use fast model for quick validation
    )

    print("🏢 Engineering Team Assembled:")
    print(f"  VP: {team['vp_engineering']['name']} ({team['vp_engineering']['pronouns']})")
    print(f"  Engineer: {team['senior_engineer']['name']} ({team['senior_engineer']['pronouns']})")
    print(f"  QA: {team['qa_lead']['name']} ({team['qa_lead']['pronouns']})")

    # Feature to build
    feature = "Add input validation to a user registration form"

    # Phase 1: VP creates plan
    print(f"\n📋 {vp.name} is planning the feature...")
    plan_result = await vp.execute(
        f"Create a technical plan for: {feature}\n\n"
        "Output a JSON plan with: summary, approach, validation_rules, test_cases"
    )
    print(f"✓ Plan created (${plan_result.cost_usd:.6f})")

    # Phase 2: Engineer implements
    print(f"\n💻 {engineer.name} is implementing...")
    impl_result = await engineer.execute(
        f"Implement this feature based on plan:\n\n"
        f"Plan:\n{plan_result.output[:500]}...\n\n"
        f"Write complete Python code for input validation."
    )
    print(f"✓ Implementation complete (${impl_result.cost_usd:.6f})")

    # Phase 3: QA validates
    print(f"\n🧪 {qa.name} is testing...")
    qa_result = await qa.execute(
        f"Quick validation of this implementation:\n\n"
        f"{impl_result.output[:500]}...\n\n"
        f"Check: Does it handle edge cases? Any bugs? Pass/Fail verdict."
    )
    print(f"✓ QA review complete (${qa_result.cost_usd:.6f})")

    # Summary
    total_cost = plan_result.cost_usd + impl_result.cost_usd + qa_result.cost_usd
    total_tokens_in = (
        plan_result.tokens_in + impl_result.tokens_in + qa_result.tokens_in
    )
    total_tokens_out = (
        plan_result.tokens_out + impl_result.tokens_out + qa_result.tokens_out
    )

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Feature: {feature}")
    print(f"Team: {vp.name}, {engineer.name}, {qa.name}")
    print(f"Total tokens: {total_tokens_in:,} in, {total_tokens_out:,} out")
    print(f"Total cost: ${total_cost:.6f}")
    print(f"\nQA Verdict:\n{qa_result.output[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
