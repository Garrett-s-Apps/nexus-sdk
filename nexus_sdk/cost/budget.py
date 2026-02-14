"""
Budget enforcement logic.
"""

from dataclasses import dataclass, field


@dataclass
class BudgetLimits:
    """Budget limits for cost enforcement."""

    hourly_target: float = 1.00
    hourly_hard_cap: float = 2.50
    session_warning: float = 5.00
    session_hard_cap: float = 15.00
    monthly_target: float = 160.00
    monthly_hard_cap: float = 250.00


@dataclass
class BudgetEnforcement:
    """Budget enforcement actions to take."""

    alerts: list[str] = field(default_factory=list)
    downgrade: bool = False
    kill_session: bool = False


class BudgetEnforcer:
    """Enforces budget limits and returns actions to take."""

    def __init__(self, limits: BudgetLimits):
        """Initialize budget enforcer.

        Args:
            limits: Budget limits to enforce
        """
        self.limits = limits
        self._alerts_sent: set[str] = set()
        self._downgrade_active = False

    def enforce(
        self,
        hourly_rate: float,
        session_cost: float,
        monthly_cost: float,
    ) -> BudgetEnforcement:
        """Enforce budget and return actions.

        Args:
            hourly_rate: Current hourly spend rate
            session_cost: Total session cost so far
            monthly_cost: Total monthly cost so far

        Returns:
            BudgetEnforcement with alerts and actions
        """
        actions = BudgetEnforcement()

        # Hourly rate warning
        if hourly_rate > self.limits.hourly_target and "hourly_warning" not in self._alerts_sent:
            actions.alerts.append(
                f"CFO Alert: Hourly rate ${hourly_rate:.2f}/hr exceeds "
                f"${self.limits.hourly_target:.2f}/hr target"
            )
            self._alerts_sent.add("hourly_warning")

        # Hourly hard cap - trigger model downgrade
        if hourly_rate > self.limits.hourly_hard_cap:
            actions.downgrade = True
            self._downgrade_active = True
            if "hourly_hard" not in self._alerts_sent:
                actions.alerts.append(
                    f"CFO ENFORCEMENT: Hourly rate ${hourly_rate:.2f}/hr exceeds hard cap. "
                    "Downgrading models."
                )
                self._alerts_sent.add("hourly_hard")

        # Session warning
        if (
            session_cost > self.limits.session_warning
            and "session_warning" not in self._alerts_sent
        ):
            actions.alerts.append(
                f"CFO Alert: Session cost ${session_cost:.2f} exceeds "
                f"${self.limits.session_warning:.2f} warning threshold"
            )
            self._alerts_sent.add("session_warning")

        # Session hard cap - kill
        if session_cost > self.limits.session_hard_cap:
            actions.kill_session = True
            actions.alerts.append(
                f"CFO ENFORCEMENT: Session cost ${session_cost:.2f} exceeds hard cap. Terminating."
            )

        # Monthly check
        if monthly_cost > self.limits.monthly_target and "monthly_warning" not in self._alerts_sent:
            actions.alerts.append(
                f"CFO Alert: Monthly cost ${monthly_cost:.2f} exceeds "
                f"${self.limits.monthly_target:.2f} target"
            )
            self._alerts_sent.add("monthly_warning")

        if monthly_cost > self.limits.monthly_hard_cap:
            actions.downgrade = True
            self._downgrade_active = True

        return actions

    @property
    def is_downgrade_active(self) -> bool:
        """Check if model downgrade is currently active."""
        return self._downgrade_active

    def reset_alerts(self) -> None:
        """Reset alert tracking (typically for new session)."""
        self._alerts_sent.clear()
