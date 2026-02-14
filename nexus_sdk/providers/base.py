"""
Base provider interface for NEXUS SDK.

All AI providers must implement this interface.
"""

from abc import ABC, abstractmethod

from nexus_sdk.types import TaskResult


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
