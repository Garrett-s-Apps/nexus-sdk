"""
Local Knowledge Search & Debug — fully offline semantic search and debug investigation.

Operates entirely on the user's local SQLite knowledge base.
No HTTP calls, no shared state, no cloud egress.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from nexus_sdk.knowledge import embeddings
from nexus_sdk.knowledge.local_store import LocalKnowledgeStore


# --- Result types -------------------------------------------------------------

@dataclass
class LocalChunk:
    """A single knowledge chunk with similarity score."""
    chunk_type: str
    content: str
    source_id: str = ""
    domain_tag: str = ""
    project: str = ""
    metadata: dict = field(default_factory=dict)
    similarity: float = 0.0
    created_at: float = 0.0

    @property
    def score(self) -> float:
        """Weighted score (same weights as NEXUS server)."""
        weights = {
            "error_resolution": 1.3,
            "task_outcome": 1.1,
            "conversation": 1.0,
            "code_change": 0.9,
            "directive_summary": 1.0,
        }
        w = weights.get(self.chunk_type, 1.0)
        # Recency boost: chunks < 7 days old get up to 10% boost
        age_days = (time.time() - self.created_at) / 86400 if self.created_at else 999
        recency = 1.0 + max(0, (7 - age_days) / 70)
        return self.similarity * w * recency


@dataclass
class LocalSearchResult:
    """Result from a local knowledge search."""
    results: list[LocalChunk] = field(default_factory=list)
    query: str = ""
    mode: str = "all"

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0


@dataclass
class LocalDebugReport:
    """Result from a local debug investigation."""
    past_errors: list[LocalChunk] = field(default_factory=list)
    related_tasks: list[LocalChunk] = field(default_factory=list)
    code_changes: list[LocalChunk] = field(default_factory=list)
    proven_fix: LocalChunk | None = None

    @property
    def has_proven_fix(self) -> bool:
        return self.proven_fix is not None and self.proven_fix.similarity >= 0.70

    def summary(self) -> str:
        lines = [f"Past errors: {len(self.past_errors)}"]
        lines.append(f"Related tasks: {len(self.related_tasks)}")
        lines.append(f"Code changes: {len(self.code_changes)}")
        if self.has_proven_fix and self.proven_fix:
            lines.append(f"Proven fix: {self.proven_fix.content[:100]}...")
        else:
            lines.append("No proven fix found")
        return "\n".join(lines)


# --- Mode-to-chunk-type mapping -----------------------------------------------

_MODE_MAP: dict[str, list[str]] = {
    "all": [],
    "errors": ["error_resolution"],
    "tasks": ["task_outcome"],
    "code": ["code_change"],
    "conversations": ["conversation"],
}


# --- LocalKnowledgeSearch -----------------------------------------------------

class LocalKnowledgeSearch:
    """Fully offline semantic search over a user's local knowledge base.

    Example:
        >>> from nexus_sdk.knowledge.local_search import LocalKnowledgeSearch
        >>> search = LocalKnowledgeSearch()
        >>> search.init()
        >>> result = search.query("rate limiter implementation")
        >>> for chunk in result.results:
        ...     print(f"[{chunk.score:.0%}] {chunk.chunk_type}: {chunk.content[:80]}")
    """

    def __init__(self, db_path: str = ""):
        self.store = LocalKnowledgeStore(db_path)

    def init(self) -> None:
        """Initialize the local knowledge database."""
        self.store.init()

    def query(
        self,
        query: str,
        mode: str = "all",
        domain: str = "",
        project: str = "",
        top_k: int = 5,
        threshold: float = 0.35,
    ) -> LocalSearchResult:
        """Search local knowledge by semantic similarity.

        Args:
            query: Natural language search query
            mode: all, errors, tasks, code, conversations
            domain: Optional domain filter
            project: Optional project filter
            top_k: Max results
            threshold: Minimum similarity score
        """
        query_vec = embeddings.encode(query)
        chunk_types = _MODE_MAP.get(mode, [])

        # Pre-filter by SQL
        chunk_type_filter = chunk_types[0] if len(chunk_types) == 1 else None
        rows = self.store.get_chunks_filtered(
            chunk_type=chunk_type_filter,
            domain_tag=domain or None,
            project=project or None,
            limit=500,
        )

        # Score by cosine similarity
        scored: list[LocalChunk] = []
        for row in rows:
            if chunk_types and row["chunk_type"] not in chunk_types:
                continue
            row_vec = embeddings.from_bytes(row["embedding"])
            sim = embeddings.cosine_similarity(query_vec, row_vec)
            if sim >= threshold:
                import json
                meta = row.get("metadata", "{}")
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                scored.append(LocalChunk(
                    chunk_type=row["chunk_type"],
                    content=row["content"],
                    source_id=row.get("source_id", ""),
                    domain_tag=row.get("domain_tag", ""),
                    project=row.get("project", ""),
                    metadata=meta,
                    similarity=sim,
                    created_at=row.get("created_at", 0.0),
                ))

        scored.sort(key=lambda c: c.score, reverse=True)
        return LocalSearchResult(
            results=scored[:top_k],
            query=query,
            mode=mode,
        )

    def errors(self, query: str, domain: str = "", top_k: int = 5) -> LocalSearchResult:
        """Search only error_resolution chunks (permanent retention)."""
        return self.query(query, mode="errors", domain=domain, top_k=top_k)

    def tasks(self, query: str, domain: str = "", top_k: int = 5) -> LocalSearchResult:
        """Search only task_outcome chunks (90-day retention)."""
        return self.query(query, mode="tasks", domain=domain, top_k=top_k)

    def code_changes(self, query: str, domain: str = "", top_k: int = 5) -> LocalSearchResult:
        """Search only code_change chunks (30-day retention)."""
        return self.query(query, mode="code", domain=domain, top_k=top_k)

    def conversations(self, query: str, domain: str = "", top_k: int = 5) -> LocalSearchResult:
        """Search only conversation chunks (30-day retention)."""
        return self.query(query, mode="conversations", domain=domain, top_k=top_k)

    def status(self) -> dict[str, int]:
        """Get chunk counts by type."""
        return self.store.count_chunks()

    # --- Ingestion helpers ----------------------------------------------------

    def ingest(
        self,
        chunk_type: str,
        content: str,
        source_id: str = "",
        domain: str = "",
        project: str = "",
        metadata: dict | None = None,
    ) -> None:
        """Ingest a knowledge chunk into the local store.

        Automatically generates embedding and classifies domain if not provided.
        """
        if not domain:
            domain = embeddings.classify_domain(content)
        vec = embeddings.encode(content)
        vec_bytes = embeddings.to_bytes(vec)
        self.store.store_chunk(
            chunk_type=chunk_type,
            content=content,
            embedding=vec_bytes,
            source_id=source_id,
            metadata=metadata,
            domain_tag=domain,
            project=project,
        )

    def ingest_error(self, content: str, source_id: str = "", project: str = "") -> None:
        """Shorthand: ingest an error resolution (permanent retention)."""
        self.ingest("error_resolution", content, source_id=source_id, project=project)

    def ingest_task(self, content: str, source_id: str = "", project: str = "") -> None:
        """Shorthand: ingest a task outcome (90-day retention)."""
        self.ingest("task_outcome", content, source_id=source_id, project=project)

    def ingest_code_change(self, content: str, source_id: str = "", project: str = "") -> None:
        """Shorthand: ingest a code change (30-day retention)."""
        self.ingest("code_change", content, source_id=source_id, project=project)

    def prune(self) -> int:
        """Remove expired chunks based on retention policies."""
        return self.store.prune_old_chunks()

    def close(self) -> None:
        """Close the database connection."""
        self.store.close()


# --- LocalDebugInvestigator ---------------------------------------------------

class LocalDebugInvestigator:
    """Fully offline debug investigation over local knowledge.

    Example:
        >>> from nexus_sdk.knowledge.local_search import LocalDebugInvestigator
        >>> debugger = LocalDebugInvestigator()
        >>> debugger.init()
        >>> report = debugger.investigate("JWT token validation failing")
        >>> if report.has_proven_fix:
        ...     print(f"Fix: {report.proven_fix.content[:100]}")
    """

    def __init__(self, db_path: str = ""):
        self.search = LocalKnowledgeSearch(db_path)

    def init(self) -> None:
        """Initialize the local knowledge database."""
        self.search.init()

    def investigate(
        self,
        error: str,
        domain: str = "",
        project: str = "",
    ) -> LocalDebugReport:
        """Run a 3-phase local debug investigation.

        Phase 1: Search error_resolution chunks (threshold 0.30)
        Phase 2: Search task_outcome chunks (threshold 0.35)
        Phase 3: Search code_change chunks (threshold 0.30)

        Args:
            error: Error description, message, or stack trace
            domain: Optional domain filter
            project: Optional project filter
        """
        # Phase 1: past errors (wider net)
        errors = self.search.query(
            error, mode="errors", domain=domain, project=project,
            top_k=10, threshold=0.30,
        )

        # Phase 2: related tasks
        tasks = self.search.query(
            error, mode="tasks", domain=domain, project=project,
            top_k=5, threshold=0.35,
        )

        # Phase 3: code changes
        code = self.search.query(
            error, mode="code", domain=domain, project=project,
            top_k=5, threshold=0.30,
        )

        # Detect proven fix (>70% similarity in error_resolution)
        proven_fix = None
        for chunk in errors.results:
            if chunk.similarity >= 0.70:
                proven_fix = chunk
                break

        return LocalDebugReport(
            past_errors=errors.results,
            related_tasks=tasks.results,
            code_changes=code.results,
            proven_fix=proven_fix,
        )

    def quick_check(self, error: str) -> bool:
        """Quick check if a proven fix exists locally.

        Returns True if an error_resolution chunk matches >70% similarity.
        """
        errors = self.search.query(
            error, mode="errors", top_k=1, threshold=0.70,
        )
        return errors.has_results

    def close(self) -> None:
        """Close the database connection."""
        self.search.close()
