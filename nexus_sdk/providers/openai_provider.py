"""
OpenAI provider for NEXUS SDK.
"""

import time
from typing import Any

from nexus_sdk.providers.base import ModelProvider, _sanitize_error
from nexus_sdk.types import TaskResult

# Model tier mapping (for tier-based routing)
TIER_TO_MODEL = {
    "opus": "o3",  # Map "opus" tier to o3 reasoning model
    "sonnet": "gpt-4o",
    "haiku": "gpt-4o-mini",
}

# Pricing per 1M tokens (input/output)
OPENAI_PRICING = {
    "o3": {"input": 10.0, "output": 40.0},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


class OpenAIProvider(ModelProvider):
    """OpenAI provider using OpenAI SDK."""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self._api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Any = None

    def __repr__(self) -> str:
        return f"OpenAIProvider(api_key='***', timeout={self.timeout})"

    def __getstate__(self) -> dict:
        raise TypeError("Provider objects containing API keys cannot be serialized")

    def _get_client(self) -> Any:
        """Lazy-load OpenAI client (only when needed)."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self._api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError as e:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install nexus-agent-sdk[openai]"
                ) from e
        return self._client

    def get_model_tier(self, model: str) -> str:
        """Map tier to actual OpenAI model ID."""
        return TIER_TO_MODEL.get(model, model)

    async def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "default",
        tools: list[str] | None = None,
        max_tokens: int = 4096,
        **kwargs: str,
    ) -> TaskResult:
        """Execute a prompt using OpenAI API."""
        start = time.time()

        # Map tier to model ID
        if model == "default":
            model = "sonnet"  # Default to GPT-4o
        actual_model = self.get_model_tier(model)

        try:
            client = self._get_client()

            # Build messages
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Make API call
            response = client.chat.completions.create(
                model=actual_model,
                messages=messages,
                max_tokens=max_tokens,
            )

            # Extract result
            output = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0

            # Calculate cost
            pricing = self.get_pricing(actual_model)
            cost_usd = (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000

            elapsed = time.time() - start

            return TaskResult(
                status="success",
                output=output,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                model=actual_model,
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            elapsed = time.time() - start
            return TaskResult(
                status="error",
                output="",
                error_type="api_error",
                error_detail=_sanitize_error(e),
                elapsed_seconds=elapsed,
                model=actual_model,
            )

    def get_pricing(self, model: str) -> dict[str, float]:
        """Get pricing for OpenAI models."""
        return OPENAI_PRICING.get(model, OPENAI_PRICING["gpt-4o"])

    def list_models(self) -> list[str]:
        """List available OpenAI models."""
        return list(TIER_TO_MODEL.values())
