"""
DebugInvestigator — semantic debug investigation using the NEXUS knowledge base.

Combines error search, task correlation, code change detection, and
directive similarity analysis into a structured investigation report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nexus_sdk.knowledge.types import DebugReport

if TYPE_CHECKING:
    from nexus_sdk.knowledge.client import NexusClient


class DebugInvestigator:
    """Semantic debug investigation over NEXUS's knowledge base.

    Example:
        >>> from nexus_sdk.knowledge import NexusClient, DebugInvestigator
        >>> client = NexusClient()
        >>> client.authenticate("my-passphrase")
        >>> debugger = DebugInvestigator(client)
        >>>
        >>> # Investigate an error
        >>> report = debugger.investigate(
        ...     error="ML router returning wrong agents for frontend tasks",
        ...     file_path="src/ml/router.py",
        ...     domain="backend",
        ... )
        >>>
        >>> # Check for proven fixes
        >>> if report.has_proven_fix:
        ...     print(f"Proven fix found: {report.proven_fix.content[:100]}")
        ... else:
        ...     print(f"Novel error — {len(report.past_errors)} similar past errors found")
        >>>
        >>> # Print structured summary
        >>> print(report.summary())
        >>>
        >>> # Access risk and cost analysis
        >>> print(f"Risk: {report.risk_level}")
        >>> print(f"Estimated cost: ${report.cost_estimate.get('predicted', 0):.2f}")
    """

    def __init__(self, client: NexusClient):
        self.client = client

    def investigate(
        self,
        error: str,
        file_path: str = "",
        domain: str = "",
    ) -> DebugReport:
        """Run a full semantic debug investigation.

        The investigation has 4 phases:
        1. Search error_resolution chunks (threshold 0.30, wider net)
        2. Search task_outcome chunks (threshold 0.35)
        3. Search code_change chunks for affected files
        4. Run directive-level similarity analysis (cost/risk estimation)

        Args:
            error: Error description, message, or stack trace
            file_path: Optional file path to focus investigation
            domain: Optional domain filter — frontend, backend, devops, security, testing

        Returns:
            DebugReport with past errors, related tasks, code changes, and analysis
        """
        raw = self.client.debug(
            error=error,
            file_path=file_path,
            domain=domain,
        )
        return DebugReport.from_dict(raw)

    def quick_check(self, error: str) -> bool:
        """Quick check if a proven fix exists for this error.

        Useful for CI/CD pipelines or pre-flight checks before
        launching a full investigation.

        Args:
            error: Error description

        Returns:
            True if a proven fix exists (>70% similarity match)
        """
        raw = self.client.debug(error=error)
        return bool(raw.get("has_proven_fix", False))
