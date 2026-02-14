"""
Custom provider example for NEXUS SDK.

Demonstrates how to implement a custom ModelProvider for any AI service.
This example shows a local model provider (for Ollama, LM Studio, vLLM, etc.)
"""

import asyncio
from typing import Any

from nexus_sdk import AgentRegistry, TaskResult, get_agent_name
from nexus_sdk.providers.base import ModelProvider


class LocalModelProvider(ModelProvider):
    """Example provider for local models (Ollama, LM Studio, etc.)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """Initialize local model provider.

        Args:
            base_url: URL of local model server
            model: Default model name
        """
        self.base_url = base_url
        self.default_model = model

    async def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "default",
        tools: list[str] | None = None,
        **kwargs: Any,
    ) -> TaskResult:
        """Execute prompt with local model.

        In a real implementation, this would make an HTTP request to the
        local model server. For this example, we'll simulate it.
        """
        # Real implementation would do:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.base_url}/api/generate",
        #         json={
        #             "model": self.default_model if model == "default" else model,
        #             "prompt": f"{system_prompt}\n\n{prompt}",
        #             "stream": False,
        #         }
        #     )
        #     data = response.json()
        #     return TaskResult(...)

        # Simulated response for example
        return TaskResult(
            status="success",
            output=f"[Simulated local model response to: {prompt[:50]}...]",
            tokens_in=len(prompt.split()),  # Rough approximation
            tokens_out=50,  # Simulated
            cost_usd=0.0,  # Local models are free!
            model=self.default_model if model == "default" else model,
        )

    def get_pricing(self, model: str) -> dict[str, float]:
        """Local models have zero cost."""
        return {"input_per_million": 0.0, "output_per_million": 0.0}

    def list_models(self) -> list[str]:
        """List available local models."""
        # Real implementation would query the server
        return ["llama2", "mistral", "codellama"]


async def main() -> None:
    """Demonstrate custom provider."""
    print("🏠 Local Model Provider Example\n")

    # Create custom provider
    provider = LocalModelProvider(
        base_url="http://localhost:11434",
        model="llama2"
    )

    # Create registry with custom provider
    registry = AgentRegistry(provider=provider, cost_tracking=True)

    # Get agent name
    agent_info = get_agent_name("senior_engineer", seed=42)

    # Register agent
    agent = registry.register(
        id="local_agent",
        name=agent_info["name"],
        role="Senior Engineer",
        model="llama2",
    )

    print(f"Agent: {agent_info['name']} ({agent_info['pronouns']})")
    print("Provider: Local Model (llama2)")
    print("Cost per task: $0.00 (local models are free!)\n")

    # Execute task
    task = "Write a Python function to check if a number is prime"
    print(f"Task: {task}")

    result = await agent.execute(task)

    print(f"\n✓ Status: {result.status}")
    print(f"✓ Model: {result.model}")
    print(f"✓ Tokens: {result.tokens_in} in, {result.tokens_out} out")
    print(f"✓ Cost: ${result.cost_usd:.6f}")
    print(f"\nOutput:\n{result.output}")

    print("\n" + "=" * 60)
    print("💡 Key Takeaways:")
    print("  - Implement ModelProvider ABC for any AI service")
    print("  - Local models = $0 cost")
    print("  - Same API works with Claude, OpenAI, Gemini, local, etc.")
    print("  - Swap providers without changing application code")


if __name__ == "__main__":
    asyncio.run(main())
