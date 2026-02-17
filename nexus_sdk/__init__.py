"""
NEXUS Agent SDK - Multi-agent orchestration with swappable AI providers.

Includes:
- Agent registry with provider-agnostic execution (Claude, OpenAI, Gemini)
- Cost tracking and budget enforcement
- Local-first knowledge store with per-user SQLite RAG (no server required)
- Server-backed knowledge search and debug investigation (via NEXUS server API)
"""

from nexus_sdk.agents.names import get_agent_name, get_team_names
from nexus_sdk.agents.registry import Agent, AgentRegistry
from nexus_sdk.config import NexusConfig
from nexus_sdk.knowledge.client import NexusClient
from nexus_sdk.knowledge.debug import DebugInvestigator
from nexus_sdk.knowledge.local_search import (
    LocalChunk,
    LocalDebugInvestigator,
    LocalDebugReport,
    LocalKnowledgeSearch,
    LocalSearchResult,
)
from nexus_sdk.knowledge.local_store import LocalKnowledgeStore
from nexus_sdk.knowledge.search import KnowledgeSearch
from nexus_sdk.knowledge.types import DebugReport, KnowledgeChunk, KnowledgeStatus, SearchResult
from nexus_sdk.types import AgentConfig, Decision, TaskResult

__version__ = "0.3.0"

__all__ = [
    # Config
    "NexusConfig",
    # Types
    "TaskResult",
    "Decision",
    "AgentConfig",
    # Agents
    "AgentRegistry",
    "Agent",
    "get_agent_name",
    "get_team_names",
    # Local-first knowledge (new in v0.3.0)
    "LocalKnowledgeStore",
    "LocalKnowledgeSearch",
    "LocalDebugInvestigator",
    "LocalChunk",
    "LocalSearchResult",
    "LocalDebugReport",
    # Server-backed knowledge (v0.2.0)
    "NexusClient",
    "KnowledgeSearch",
    "DebugInvestigator",
    "SearchResult",
    "DebugReport",
    "KnowledgeChunk",
    "KnowledgeStatus",
]
