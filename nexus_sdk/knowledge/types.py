"""
Types for knowledge search and debug investigation results.

Anti-corruption layer — consumers depend on these types, not raw HTTP responses.
"""

from dataclasses import dataclass, field


@dataclass
class KnowledgeChunk:
    """A single knowledge chunk returned from semantic search."""

    content: str
    chunk_type: str  # error_resolution, task_outcome, conversation, code_change
    source_id: str
    score: float  # weighted similarity score
    raw_similarity: float  # raw cosine similarity
    metadata: dict[str, str | float | int | list[str]] = field(default_factory=dict)

    @property
    def is_error_resolution(self) -> bool:
        return self.chunk_type == "error_resolution"

    @property
    def is_task_outcome(self) -> bool:
        return self.chunk_type == "task_outcome"

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeChunk":
        """Parse from API response dict."""
        return cls(
            content=data.get("content", ""),
            chunk_type=data.get("chunk_type", ""),
            source_id=data.get("source_id", ""),
            score=data.get("score", 0.0),
            raw_similarity=data.get("raw_similarity", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SearchResult:
    """Result of a semantic search query."""

    query: str
    mode: str
    results: list[KnowledgeChunk]
    count: int

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        """Parse from API response dict."""
        return cls(
            query=data.get("query", ""),
            mode=data.get("mode", "all"),
            results=[KnowledgeChunk.from_dict(r) for r in data.get("results", [])],
            count=data.get("count", 0),
        )

    @property
    def has_results(self) -> bool:
        return self.count > 0

    @property
    def top_match(self) -> KnowledgeChunk | None:
        """Return highest-scoring result, or None."""
        return self.results[0] if self.results else None


@dataclass
class DebugReport:
    """Result of a semantic debug investigation."""

    error: str
    file_path: str
    domain: str
    past_errors: list[KnowledgeChunk]
    related_tasks: list[KnowledgeChunk]
    recent_code_changes: list[KnowledgeChunk]
    directive_analysis: dict
    has_proven_fix: bool
    proven_fix: KnowledgeChunk | None

    @classmethod
    def from_dict(cls, data: dict) -> "DebugReport":
        """Parse from API response dict."""
        proven_fix_raw = data.get("proven_fix")
        return cls(
            error=data.get("error", ""),
            file_path=data.get("file_path", ""),
            domain=data.get("domain", ""),
            past_errors=[KnowledgeChunk.from_dict(r) for r in data.get("past_errors", [])],
            related_tasks=[KnowledgeChunk.from_dict(r) for r in data.get("related_tasks", [])],
            recent_code_changes=[KnowledgeChunk.from_dict(r) for r in data.get("recent_code_changes", [])],
            directive_analysis=data.get("directive_analysis", {}),
            has_proven_fix=data.get("has_proven_fix", False),
            proven_fix=KnowledgeChunk.from_dict(proven_fix_raw) if proven_fix_raw else None,
        )

    @property
    def risk_level(self) -> str:
        """Risk level from directive analysis."""
        return str(self.directive_analysis.get("risk", "unknown"))

    @property
    def similar_directives(self) -> list[dict]:
        """Past similar directives from analysis."""
        result: list[dict] = self.directive_analysis.get("similar_directives", [])
        return result

    @property
    def cost_estimate(self) -> dict:
        """Predicted cost from directive analysis."""
        result: dict = self.directive_analysis.get("cost_estimate", {})
        return result

    def summary(self) -> str:
        """Human-readable summary of the investigation."""
        lines = [f"Debug Investigation: {self.error[:80]}"]
        if self.file_path:
            lines.append(f"File: {self.file_path}")
        lines.append(f"Risk: {self.risk_level}")
        lines.append(f"Past errors found: {len(self.past_errors)}")
        lines.append(f"Related tasks: {len(self.related_tasks)}")
        lines.append(f"Recent code changes: {len(self.recent_code_changes)}")
        if self.has_proven_fix and self.proven_fix:
            lines.append(f"Proven fix available ({self.proven_fix.raw_similarity:.0%} match)")
        return "\n".join(lines)


@dataclass
class KnowledgeStatus:
    """Status of the RAG knowledge base."""

    total_chunks: int
    by_type: dict[str, int]
    ready: bool

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeStatus":
        """Parse from API response dict."""
        return cls(
            total_chunks=data.get("total_chunks", 0),
            by_type=data.get("by_type", {}),
            ready=data.get("ready", False),
        )
