"""
Gemini provider for NEXUS SDK using LangChain integration.
"""

import time
from typing import Any

from nexus_sdk.providers.base import ModelProvider
from nexus_sdk.types import TaskResult

# Model tier mapping
TIER_TO_MODEL = {
    "opus": "gemini-2.5-pro",
    "sonnet": "gemini-2.0-flash",
    "haiku": "gemini-2.0-flash",
}

# Pricing per 1M tokens (input/output)
GEMINI_PRICING = {
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}


class GeminiProvider(ModelProvider):
    """Gemini provider using LangChain integration."""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        """Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._llm: Any = None

    def _get_llm(self, model: str) -> Any:
        """Lazy-load Gemini LLM via LangChain."""
        if self._llm is None or self._llm.model != model:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError as e:
                raise ImportError(
                    "langchain-google-genai package not installed. "
                    "Install with: pip install nexus-agent-sdk[gemini]"
                ) from e
        return self._llm

    def get_model_tier(self, model: str) -> str:
        """Map tier to actual Gemini model ID."""
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
        """Execute a prompt using Gemini via LangChain."""
        start = time.time()

        # Map tier to model ID
        if model == "default":
            model = "sonnet"
        actual_model = self.get_model_tier(model)

        try:
            llm = self._get_llm(actual_model)

            # Combine system and user prompts
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Make API call
            response = await llm.ainvoke(full_prompt)

            # Extract result
            output = response.content if hasattr(response, "content") else str(response)

            # LangChain doesn't expose token counts for Gemini easily
            # Estimate: ~4 chars per token
            tokens_in = len(full_prompt) // 4
            tokens_out = len(output) // 4

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
                metadata={"note": "Token counts are estimated (4 chars/token)"},
            )

        except Exception as e:
            elapsed = time.time() - start
            return TaskResult(
                status="error",
                output="",
                error_type="api_error",
                error_detail=str(e),
                elapsed_seconds=elapsed,
                model=actual_model,
            )

    def get_pricing(self, model: str) -> dict[str, float]:
        """Get pricing for Gemini models."""
        return GEMINI_PRICING.get(model, GEMINI_PRICING["gemini-2.0-flash"])

    def list_models(self) -> list[str]:
        """List available Gemini models."""
        return list(TIER_TO_MODEL.values())
