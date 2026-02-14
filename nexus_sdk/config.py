"""
NEXUS SDK configuration using pydantic-settings.

Supports: environment variables > YAML file > code defaults
"""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseSettings):
    """Configuration for a single AI provider."""

    api_key: str = Field(default="", description="API key for the provider")
    base_url: str = Field(default="", description="Optional base URL for self-hosted")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class BudgetConfig(BaseSettings):
    """Budget enforcement configuration."""

    enabled: bool = Field(default=True, description="Enable cost tracking")
    hourly_target: float = Field(default=1.00, description="Target hourly rate in USD")
    hourly_hard_cap: float = Field(default=2.50, description="Hard cap triggers downgrade")
    session_warning: float = Field(default=5.00, description="Session warning threshold")
    session_hard_cap: float = Field(default=15.00, description="Session kill threshold")
    monthly_target: float = Field(default=160.00, description="Monthly target in USD")
    monthly_hard_cap: float = Field(default=250.00, description="Monthly hard cap in USD")


class NexusConfig(BaseSettings):
    """Main NEXUS SDK configuration.

    Loads from environment variables with NEXUS_ prefix.
    Example: NEXUS_DEFAULT_PROVIDER=claude
    """

    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    default_provider: str = Field(
        default="claude",
        description="Default provider to use (claude, openai, gemini)",
    )

    # Cost tracking
    cost_tracking_enabled: bool = Field(default=True, description="Enable cost tracking")
    budget: BudgetConfig = Field(default_factory=BudgetConfig)

    # Storage
    storage_backend: str = Field(
        default="sqlite",
        description="Storage backend for memory and costs (sqlite, memory, redis)",
    )
    storage_path: str = Field(
        default="~/.nexus",
        description="Path for SQLite databases",
    )

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get provider-specific configuration from environment.

        Looks for NEXUS_{PROVIDER}_API_KEY, NEXUS_{PROVIDER}_BASE_URL, etc.
        """
        prefix = f"NEXUS_{provider.upper()}_"
        import os

        config: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix) :].lower()
                config[config_key] = value
        return config
