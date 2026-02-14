"""
Provider swap example for NEXUS SDK.

Demonstrates executing the same task with different providers and comparing results.
"""

import asyncio
import os

from nexus_sdk import AgentRegistry, get_agent_name
from nexus_sdk.providers.claude import ClaudeProvider

# Uncomment when you have API keys:
# from nexus_sdk.providers.openai_provider import OpenAIProvider
# from nexus_sdk.providers.gemini import GeminiProvider


async def test_provider(provider_name: str, provider, task: str) -> dict:
    """Test a task with a specific provider."""
    agent_info = get_agent_name("senior_engineer", seed=42)

    registry = AgentRegistry(provider=provider)
    agent = registry.register(
        id="engineer",
        name=agent_info["name"],
        role="Senior Engineer",
        model="default",
    )

    print(f"\n🤖 Testing with {provider_name}...")
    result = await agent.execute(task)

    return {
        "provider": provider_name,
        "status": result.status,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": result.cost_usd,
        "model": result.model,
        "output_length": len(result.output),
    }


async def main() -> None:
    """Compare providers on the same task."""
    task = (
        "Write a Python function to validate an email address using regex. "
        "Include docstring and 2 test cases."
    )

    providers = []

    # Claude (always available in this example)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        providers.append(
            ("Claude", ClaudeProvider(api_key=anthropic_key))
        )
    else:
        print("⚠️  ANTHROPIC_API_KEY not set, skipping Claude")

    # OpenAI (optional)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        # Uncomment when OpenAIProvider is available:
        # providers.append(("OpenAI", OpenAIProvider(api_key=openai_key)))
        print("⚠️  OpenAI provider not yet imported (uncomment in code)")

    # Gemini (optional)
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        # Uncomment when GeminiProvider is available:
        # providers.append(("Gemini", GeminiProvider(api_key=google_key)))
        print("⚠️  Gemini provider not yet imported (uncomment in code)")

    if not providers:
        print("Error: No API keys configured. Set at least ANTHROPIC_API_KEY")
        return

    print(f"📝 Task: {task}")
    print(f"🔄 Testing {len(providers)} provider(s)...\n")

    # Run all providers
    results = []
    for name, provider in providers:
        result = await test_provider(name, provider, task)
        results.append(result)

    # Display comparison
    print("\n" + "=" * 80)
    print("📊 PROVIDER COMPARISON")
    print("=" * 80)
    header = (
        f"{'Provider':<15} {'Model':<25} {'Tokens In':<12} "
        f"{'Tokens Out':<12} {'Cost':<10} {'Output'}"
    )
    print(header)
    print("-" * 80)

    for r in results:
        row = (
            f"{r['provider']:<15} {r['model']:<25} "
            f"{r['tokens_in']:<12} {r['tokens_out']:<12} "
            f"${r['cost_usd']:<9.6f} {r['output_length']} chars"
        )
        print(row)

    print("\n💡 Observations:")
    print("  - Different providers may use different token counting")
    print("  - Costs vary significantly between providers and models")
    print("  - Output quality and style differ between providers")
    print("\n🎯 Choose based on your needs: cost, speed, quality, or features")


if __name__ == "__main__":
    asyncio.run(main())
