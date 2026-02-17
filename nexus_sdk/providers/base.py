"""
Base provider interface for NEXUS SDK.

All AI providers must implement this interface.
"""

import re
from abc import ABC, abstractmethod

from nexus_sdk.types import TaskResult


def _sanitize_error(error: Exception) -> str:
    """Remove potential secrets from error messages before storing."""
    msg = str(error)
    # Redact API keys (Anthropic sk-ant-, OpenAI sk-, Google AI AIza)
    msg = re.sub(r'(sk-ant-[a-zA-Z0-9_-]{10,})', '[REDACTED_KEY]', msg)
    msg = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[REDACTED_KEY]', msg)
    msg = re.sub(r'(AIza[a-zA-Z0-9_-]{30,})', '[REDACTED_KEY]', msg)
    # Redact Bearer tokens
    msg = re.sub(r'(Bearer\s+)[a-zA-Z0-9._-]+', r'\1[REDACTED]', msg)
    # Redact generic api_key/api-key patterns in URLs or JSON
    msg = re.sub(r'(api[_-]?key["\s:=]+)[^\s,}"\']+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    return msg[:500]


class ModelProvider(ABC):
    """Abstract base class for AI model providers.

    Implementations: ClaudeProvider, OpenAIProvider, GeminiProvider, LocalProvider
    """

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "default",
        tools: list[str] | None = None,
        max_tokens: int = 4096,
        **kwargs: str,
    ) -> TaskResult:
        """Execute a prompt and return unified result.

        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt
            model: Model identifier (provider-specific or tier like "opus"/"sonnet"/"haiku")
            tools: Optional list of tool names to enable
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            TaskResult with status, output, tokens, and cost
        """
        pass

    @abstractmethod
    def get_pricing(self, model: str) -> dict[str, float]:
        """Return pricing per 1M tokens.

        Returns:
            {"input": float, "output": float} - cost per 1M tokens
        """
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def get_model_tier(self, model: str) -> str:
        """Map model to tier (opus/sonnet/haiku).

        Override in provider implementations for tier-based routing.
        Default: return the model as-is.
        """
        return model
