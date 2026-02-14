"""
Cost tracker with budget enforcement and persistent storage.
"""

import time
from typing import Protocol

from nexus_sdk.cost.budget import BudgetEnforcement, BudgetEnforcer, BudgetLimits
from nexus_sdk.cost.pricing import calculate_cost, downgrade_model


class CostStorage(Protocol):
    """Protocol for cost storage backends."""

    def record_event(
        self,
        timestamp: float,
        model: str,
        agent: str,
        project: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        session_id: str,
    ) -> None:
        """Record a cost event."""
        ...

    def get_monthly_cost(self) -> float:
        """Get current month's total cost."""
        ...

    def get_daily_breakdown(self, days: int) -> list[dict[str, float | int | str]]:
        """Get daily cost breakdown."""
        ...


class InMemoryCostStorage:
    """In-memory cost storage (no persistence)."""

    def __init__(self) -> None:
        self.events: list[dict[str, float | int | str]] = []

    def record_event(
        self,
        timestamp: float,
        model: str,
        agent: str,
        project: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        session_id: str,
    ) -> None:
        """Record a cost event in memory."""
        self.events.append({
            "timestamp": timestamp,
            "model": model,
            "agent": agent,
            "project": project,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "session_id": session_id,
        })

    def get_monthly_cost(self) -> float:
        """Get current month's total cost."""
        now = time.time()
        t = time.localtime(now)
        month_start = time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1))
        return sum(
            float(e["cost_usd"])
            for e in self.events
            if float(e["timestamp"]) >= month_start
        )

    def get_daily_breakdown(self, days: int) -> list[dict[str, float | int | str]]:
        """Get daily cost breakdown."""
        cutoff = time.time() - (days * 86400)
        daily: dict[str, dict[str, float | int]] = {}
        for event in self.events:
            if float(event["timestamp"]) < cutoff:
                continue
            date = time.strftime("%Y-%m-%d", time.localtime(float(event["timestamp"])))
            if date not in daily:
                daily[date] = {"cost": 0.0, "calls": 0}
            daily[date]["cost"] += float(event["cost_usd"])
            daily[date]["calls"] += 1
        return [
            {"date": k, "cost": v["cost"], "calls": v["calls"]}
            for k, v in sorted(daily.items(), reverse=True)
        ]


class CostTracker:
    """Cost tracker with budget enforcement.

    Tracks costs per model/agent/project and enforces budget limits.
    """

    def __init__(
        self,
        storage: CostStorage | None = None,
        budget_limits: BudgetLimits | None = None,
    ):
        """Initialize cost tracker.

        Args:
            storage: Storage backend (defaults to in-memory)
            budget_limits: Budget limits (defaults to standard limits)
        """
        self.storage = storage or InMemoryCostStorage()
        self.budget_limits = budget_limits or BudgetLimits()
        self.enforcer = BudgetEnforcer(self.budget_limits)

        # In-memory session tracking
        self.session_start = time.time()
        self.session_cost = 0.0
        self.by_model: dict[str, float] = {}
        self.by_agent: dict[str, float] = {}
        self.by_project: dict[str, float] = {}
        self.call_count = 0

    def record(
        self,
        model: str,
        agent_name: str,
        tokens_in: int,
        tokens_out: int,
        project: str = "",
        session_id: str = "",
    ) -> BudgetEnforcement:
        """Record a cost event and return enforcement actions.

        Args:
            model: Model identifier
            agent_name: Agent that made the call
            tokens_in: Input tokens
            tokens_out: Output tokens
            project: Optional project name
            session_id: Optional session identifier

        Returns:
            BudgetEnforcement with alerts and actions
        """
        cost = calculate_cost(model, tokens_in, tokens_out)

        # Update in-memory
        self.session_cost += cost
        self.by_model[model] = self.by_model.get(model, 0.0) + cost
        self.by_agent[agent_name] = self.by_agent.get(agent_name, 0.0) + cost
        if project:
            self.by_project[project] = self.by_project.get(project, 0.0) + cost
        self.call_count += 1

        # Persist
        self.storage.record_event(
            timestamp=time.time(),
            model=model,
            agent=agent_name,
            project=project,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            session_id=session_id,
        )

        # Enforcement
        return self.enforcer.enforce(
            hourly_rate=self.hourly_rate,
            session_cost=self.session_cost,
            monthly_cost=self.storage.get_monthly_cost(),
        )

    def get_effective_model(self, requested_model: str) -> str:
        """Get the model to actually use considering budget enforcement.

        Args:
            requested_model: The requested model

        Returns:
            Actual model to use (may be downgraded)
        """
        if self.enforcer.is_downgrade_active:
            return downgrade_model(requested_model)
        return requested_model

    @property
    def total_cost(self) -> float:
        """Total session cost."""
        return self.session_cost

    @property
    def hourly_rate(self) -> float:
        """Current hourly spend rate."""
        elapsed = time.time() - self.session_start
        if elapsed < 60:
            return 0.0
        return self.session_cost / (elapsed / 3600)

    @property
    def over_budget(self) -> bool:
        """Check if currently over budget."""
        return self.hourly_rate > self.budget_limits.hourly_hard_cap

    def get_summary(self) -> dict[str, float | int | bool | dict[str, float]]:
        """Get cost summary."""
        return {
            "session_cost": round(self.session_cost, 4),
            "hourly_rate": round(self.hourly_rate, 4),
            "call_count": self.call_count,
            "monthly_cost": round(self.storage.get_monthly_cost(), 4),
            "over_budget": self.over_budget,
            "downgrade_active": self.enforcer.is_downgrade_active,
            "by_model": self.by_model,
            "by_agent": self.by_agent,
            "by_project": self.by_project,
        }
