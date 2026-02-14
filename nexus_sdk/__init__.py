"""
NEXUS Agent SDK - Multi-agent orchestration with swappable AI providers.
"""

from nexus_sdk.agents.names import get_agent_name, get_team_names
from nexus_sdk.agents.registry import Agent, AgentRegistry
from nexus_sdk.config import NexusConfig
from nexus_sdk.types import AgentConfig, Decision, TaskResult

__version__ = "0.1.0"

__all__ = [
    "NexusConfig",
    "TaskResult",
    "Decision",
    "AgentConfig",
    "AgentRegistry",
    "Agent",
    "get_agent_name",
    "get_team_names",
]
