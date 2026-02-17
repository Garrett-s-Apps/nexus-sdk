"""
NEXUS Knowledge — semantic search and debug investigation over the NEXUS knowledge base.

Provides programmatic access to NEXUS's RAG system without requiring Claude Code.
"""

from nexus_sdk.knowledge.client import NexusClient
from nexus_sdk.knowledge.search import KnowledgeSearch
from nexus_sdk.knowledge.debug import DebugInvestigator

__all__ = [
    "NexusClient",
    "KnowledgeSearch",
    "DebugInvestigator",
]
