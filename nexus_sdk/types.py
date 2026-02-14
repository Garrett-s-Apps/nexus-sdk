"""
Core types for NEXUS SDK.

Anti-corruption layer - canonical types independent of any AI provider.
"""

import json
from dataclasses import dataclass, field


@dataclass
class TaskResult:
    """Unified result type for all provider integrations.

    Every provider (Claude, OpenAI, Gemini, local models) returns a TaskResult.
    Consumers never depend on provider-specific response shapes.
    """

    status: str  # "success", "error", "timeout", "unavailable"
    output: str
    error_type: str = ""  # "timeout", "cli_not_found", "api_error", "circuit_open"
    error_detail: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    model: str = ""
    agent: str = ""
    elapsed_seconds: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Check if the task succeeded."""
        return self.status == "success"

    def to_dict(self) -> dict[str, str | int | float]:
        """Convert to dictionary for serialization."""
        return {
            "output": self.output,
            "status": self.status,
            "error_type": self.error_type,
            "error_detail": self.error_detail,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": self.cost_usd,
            "model": self.model,
            "agent": self.agent,
            "elapsed_seconds": self.elapsed_seconds,
        }


@dataclass
class Decision:
    """Agent decision - whether to act and what action to take."""

    act: bool
    task_id: str = ""
    reason: str = ""
    action: str = ""
    context: dict[str, str] = field(default_factory=dict)

    @classmethod
    def idle(cls, reason: str = "nothing to do") -> "Decision":
        """Create an idle decision (no action)."""
        return cls(act=False, reason=reason)

    @classmethod
    def from_json(cls, raw: str) -> "Decision":
        """Parse decision from JSON string (with optional markdown code fence)."""
        try:
            cleaned = raw.strip()
            # Strip markdown code fences if present
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            data = json.loads(cleaned)
            return cls(
                act=data.get("act", False),
                task_id=data.get("task_id", ""),
                reason=data.get("reason", ""),
                action=data.get("action", ""),
                context=data.get("context", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return cls.idle(f"parse error: {raw[:200]}")


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    id: str
    name: str
    title: str
    role: str
    model: str
    reports_to: str = ""
    direct_reports: list[str] = field(default_factory=list)
    org: str = ""
    produces: list[str] = field(default_factory=list)
    specialty: str = ""
    provider: str = "default"
