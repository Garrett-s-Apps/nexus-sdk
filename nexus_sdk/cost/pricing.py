"""
Model pricing database for all providers.

Centralized pricing to avoid duplication across provider implementations.
"""

# Pricing per 1M tokens (input/output) in USD
MODEL_PRICING = {
    # Claude (Anthropic)
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.25, "output": 1.25},
    # OpenAI
    "o3": {"input": 10.0, "output": 40.0},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Gemini
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # Claude Code CLI (Max subscription - $0 API cost)
    "claude-code:opus": {"input": 0.0, "output": 0.0},
    "claude-code:sonnet": {"input": 0.0, "output": 0.0},
    "claude-code:haiku": {"input": 0.0, "output": 0.0},
}

# Model downgrade map for budget enforcement
DOWNGRADE_MAP = {
    "opus": "sonnet",
    "claude-opus-4-20250514": "claude-sonnet-4-5-20250929",
    "o3": "gpt-4o",
    "gemini-2.5-pro": "gemini-2.0-flash",
    "sonnet": "haiku",
    "claude-sonnet-4-5-20250929": "claude-haiku-4-5-20251001",
    "gpt-4o": "gpt-4o-mini",
    "gemini-2.0-flash": "gemini-2.0-flash",  # Can't go lower
    "haiku": "haiku",  # Can't go lower
    "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
    "gpt-4o-mini": "gpt-4o-mini",
}


def get_pricing(model: str) -> dict[str, float]:
    """Get pricing for a model, with fallback to sonnet."""
    return MODEL_PRICING.get(model, MODEL_PRICING["sonnet"])


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Calculate cost for a model invocation."""
    pricing = get_pricing(model)
    return (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000


def downgrade_model(model: str) -> str:
    """Get the downgraded version of a model for budget enforcement."""
    return DOWNGRADE_MAP.get(model, model)
