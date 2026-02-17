"""
Claude provider for NEXUS SDK using Anthropic API.
"""

import time
from typing import Any

from nexus_sdk.providers.base import ModelProvider, _sanitize_error
from nexus_sdk.types import TaskResult

# Model tier mapping
TIER_TO_MODEL = {
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

# Pricing per 1M tokens (input/output)
CLAUDE_PRICING = {
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    # Legacy model IDs
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.25, "output": 1.25},
}


class ClaudeProvider(ModelProvider):
    """Claude provider using Anthropic API."""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self._api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Any = None

    def __repr__(self) -> str:
        return f"ClaudeProvider(api_key='***', timeout={self.timeout})"

    def __getstate__(self) -> dict:
        raise TypeError("Provider objects containing API keys cannot be serialized")

    def _get_client(self) -> Any:
        """Lazy-load Anthropic client (only when needed)."""
        if self._client is None:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(
                    api_key=self._api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError as e:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install nexus-agent-sdk[claude]"
                ) from e
        return self._client

    def get_model_tier(self, model: str) -> str:
        """Map tier to actual Claude model ID."""
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
        """Execute a prompt using Claude API."""
        start = time.time()

        # Map tier to model ID
        if model == "default":
            model = "sonnet"
        actual_model = self.get_model_tier(model)

        try:
            client = self._get_client()

            # Build request
            messages = [{"role": "user", "content": prompt}]
            request_kwargs: dict[str, Any] = {
                "model": actual_model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system_prompt:
                request_kwargs["system"] = system_prompt

            # Make API call
            response = client.messages.create(**request_kwargs)

            # Extract result
            output = response.content[0].text
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens

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
        """Get pricing for Claude models."""
        return CLAUDE_PRICING.get(model, CLAUDE_PRICING["sonnet"])

    def list_models(self) -> list[str]:
        """List available Claude models."""
        return list(TIER_TO_MODEL.values())
