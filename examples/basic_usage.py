"""
Basic usage example for NEXUS SDK.

Shows how to use a single provider with a simple prompt.
"""

import asyncio
import os

from nexus_sdk.agents.names import get_agent_name
from nexus_sdk.providers.claude import ClaudeProvider
from nexus_sdk.types import TaskResult


async def main() -> None:
    """Run basic example."""
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Initialize provider
    provider = ClaudeProvider(api_key=api_key)

    # Get a diverse agent name
    agent = get_agent_name("senior_engineer", seed=42)
    print(f"Agent: {agent['name']} ({agent['pronouns']})")

    # Execute a simple task
    print(f"\n{agent['name']} is executing task with Claude...")
    result: TaskResult = await provider.execute(
        prompt="Write a Python function that checks if a number is prime.",
        model="haiku",  # Use fastest/cheapest model
    )

    # Display results
    print(f"\n✓ Status: {result.status}")
    print(f"✓ Model: {result.model}")
    print(f"✓ Tokens: {result.tokens_in} in, {result.tokens_out} out")
    print(f"✓ Cost: ${result.cost_usd:.6f}")
    print(f"✓ Time: {result.elapsed_seconds:.2f}s")
    print(f"\n{agent['name']}'s Output:\n{result.output}")


if __name__ == "__main__":
    asyncio.run(main())
