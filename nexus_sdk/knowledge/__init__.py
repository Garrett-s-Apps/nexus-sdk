"""
NEXUS Knowledge — semantic search and debug investigation.

Two modes of operation:
1. **Local-first** (recommended): LocalKnowledgeSearch + LocalDebugInvestigator
   — fully offline, per-user SQLite, no server required.
2. **Server-backed**: NexusClient + KnowledgeSearch + DebugInvestigator
   — HTTP client to a running NEXUS server instance.
"""

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

__all__ = [
    # Local-first (no server required)
    "LocalKnowledgeStore",
    "LocalKnowledgeSearch",
    "LocalDebugInvestigator",
    "LocalChunk",
    "LocalSearchResult",
    "LocalDebugReport",
    # Server-backed (requires NEXUS server)
    "NexusClient",
    "KnowledgeSearch",
    "DebugInvestigator",
]
