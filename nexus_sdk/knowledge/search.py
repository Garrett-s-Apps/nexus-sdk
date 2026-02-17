"""
KnowledgeSearch — typed wrapper for semantic search over the NEXUS knowledge base.

Provides a clean Python API for searching past errors, task outcomes,
code changes, and conversations by semantic similarity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nexus_sdk.knowledge.types import KnowledgeStatus, SearchResult

if TYPE_CHECKING:
    from nexus_sdk.knowledge.client import NexusClient


class KnowledgeSearch:
    """Semantic search over NEXUS's RAG knowledge base.

    Example:
        >>> from nexus_sdk.knowledge import NexusClient, KnowledgeSearch
        >>> client = NexusClient()
        >>> client.authenticate("my-passphrase")
        >>> search = KnowledgeSearch(client)
        >>>
        >>> # Search all knowledge
        >>> result = search.query("rate limiter implementation")
        >>> for chunk in result.results:
        ...     print(f"[{chunk.score:.0%}] {chunk.chunk_type}: {chunk.content[:80]}")
        >>>
        >>> # Search only past errors
        >>> errors = search.errors("authentication timeout")
        >>> if errors.has_results:
        ...     print(f"Found {errors.count} similar past errors")
        >>>
        >>> # Check knowledge base status
        >>> status = search.status()
        >>> print(f"Knowledge base: {status.total_chunks} chunks, ready={status.ready}")
    """

    def __init__(self, client: NexusClient):
        self.client = client

    def query(
        self,
        query: str,
        mode: str = "all",
        domain: str = "",
        top_k: int = 5,
        threshold: float = 0.35,
    ) -> SearchResult:
        """Search the knowledge base with full control over parameters.

        Args:
            query: Natural language search query
            mode: Search mode — all, errors, tasks, code, conversations
            domain: Domain filter — frontend, backend, devops, security, testing
            top_k: Maximum results to return
            threshold: Minimum similarity threshold

        Returns:
            SearchResult with typed KnowledgeChunk results
        """
        raw = self.client.search(
            query=query,
            mode=mode,
            domain=domain,
            top_k=top_k,
            threshold=threshold,
        )
        return SearchResult.from_dict(raw)

    def errors(self, query: str, domain: str = "", top_k: int = 5) -> SearchResult:
        """Search only error_resolution chunks.

        These have permanent retention and highest retrieval weight (1.3x).
        """
        return self.query(query, mode="errors", domain=domain, top_k=top_k)

    def tasks(self, query: str, domain: str = "", top_k: int = 5) -> SearchResult:
        """Search only task_outcome chunks (90-day retention)."""
        return self.query(query, mode="tasks", domain=domain, top_k=top_k)

    def code_changes(self, query: str, domain: str = "", top_k: int = 5) -> SearchResult:
        """Search only code_change chunks (30-day retention)."""
        return self.query(query, mode="code", domain=domain, top_k=top_k)

    def conversations(self, query: str, domain: str = "", top_k: int = 5) -> SearchResult:
        """Search only conversation chunks (30-day retention)."""
        return self.query(query, mode="conversations", domain=domain, top_k=top_k)

    def status(self) -> KnowledgeStatus:
        """Get knowledge base status — chunk counts and readiness."""
        raw = self.client.knowledge_status()
        return KnowledgeStatus.from_dict(raw)
