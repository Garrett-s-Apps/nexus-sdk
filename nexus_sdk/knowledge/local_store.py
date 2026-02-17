"""
Local Knowledge Store — per-user SQLite-backed RAG storage.

Each user gets their own knowledge base at ~/.nexus/knowledge.db (configurable).
Only learns from that user's projects — no shared state, no cloud egress.

Mirrors the NEXUS server's knowledge_store.py but runs standalone in any Python app.
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta


class LocalKnowledgeStore:
    """Local SQLite knowledge store for RAG chunks.

    Each user's SDK instance stores knowledge in their own database.
    No data is shared between users or sent to external services.

    Example:
        >>> store = LocalKnowledgeStore()  # uses ~/.nexus/knowledge.db
        >>> store.init()
        >>> store.store_chunk("error_resolution", "Fix: add timeout", embedding_bytes)
        >>> chunks = store.get_chunks_filtered(chunk_type="error_resolution")
    """

    # Retention policies per chunk type
    RETENTION_DAYS: dict[str, int | None] = {
        "error_resolution": None,   # permanent — never repeat mistakes
        "task_outcome": 90,
        "directive_summary": 90,
        "conversation": 30,
        "code_change": 30,
    }

    def __init__(self, db_path: str = ""):
        if not db_path:
            nexus_dir = os.path.expanduser("~/.nexus")
            db_path = os.path.join(nexus_dir, "knowledge.db")
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    @property
    def _db(self) -> sqlite3.Connection:
        assert self._conn is not None, "LocalKnowledgeStore.init() must be called first"
        return self._conn

    def init(self) -> None:
        """Initialize the database. Must be called before any operations."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._create_tables()

    def _create_tables(self) -> None:
        c = self._db.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_type TEXT NOT NULL,
            source_id TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            metadata TEXT DEFAULT '{}',
            domain_tag TEXT DEFAULT '',
            project TEXT DEFAULT '',
            created_at REAL NOT NULL,
            UNIQUE(source_id)
        )""")
        # Add project column for per-project filtering
        try:
            c.execute("ALTER TABLE knowledge_chunks ADD COLUMN project TEXT DEFAULT ''")
        except Exception:
            pass
        c.execute("CREATE INDEX IF NOT EXISTS idx_chunks_type ON knowledge_chunks(chunk_type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON knowledge_chunks(source_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_chunks_domain ON knowledge_chunks(domain_tag)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_chunks_project ON knowledge_chunks(project)")
        self._db.commit()

    def store_chunk(
        self,
        chunk_type: str,
        content: str,
        embedding: bytes,
        source_id: str = "",
        metadata: dict | None = None,
        domain_tag: str = "",
        project: str = "",
    ) -> None:
        """Store a knowledge chunk.

        Args:
            chunk_type: error_resolution, task_outcome, conversation, code_change
            content: The text content of the chunk
            embedding: Serialized embedding vector (from LocalEmbeddings.to_bytes)
            source_id: Unique source identifier (deduplicates on upsert)
            metadata: Additional metadata dict
            domain_tag: Domain classification (frontend, backend, etc.)
            project: Project identifier for per-project filtering
        """
        if not source_id:
            import hashlib
            source_id = f"hash:{hashlib.md5(content[:500].encode(), usedforsecurity=False).hexdigest()[:12]}"

        with self._lock:
            self._db.cursor().execute(
                "INSERT INTO knowledge_chunks "
                "(chunk_type,source_id,content,embedding,metadata,domain_tag,project,created_at) "
                "VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(source_id) DO UPDATE SET "
                "content=excluded.content, embedding=excluded.embedding, "
                "metadata=excluded.metadata, domain_tag=excluded.domain_tag, "
                "project=excluded.project, created_at=excluded.created_at",
                (chunk_type, source_id, content[:4000], embedding,
                 json.dumps(metadata or {}), domain_tag, project, time.time()),
            )
            self._db.commit()

    def get_chunks_filtered(
        self,
        chunk_type: str | None = None,
        domain_tag: str | None = None,
        project: str | None = None,
        max_age_days: int | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Get chunks with SQL pre-filtering before similarity scoring."""
        conditions = []
        params: list[str | float] = []

        if chunk_type:
            conditions.append("chunk_type = ?")
            params.append(chunk_type)
        if domain_tag:
            conditions.append("domain_tag = ?")
            params.append(domain_tag)
        if project:
            conditions.append("project = ?")
            params.append(project)
        if max_age_days:
            cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).timestamp()
            conditions.append("created_at > ?")
            params.append(cutoff)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(float(limit))
        rows = self._db.execute(
            f"SELECT * FROM knowledge_chunks {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def count_chunks(self, project: str | None = None) -> dict[str, int]:
        """Count chunks by type, optionally filtered by project."""
        if project:
            rows = self._db.execute(
                "SELECT chunk_type, COUNT(*) as cnt FROM knowledge_chunks "
                "WHERE project = ? GROUP BY chunk_type",
                (project,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT chunk_type, COUNT(*) as cnt FROM knowledge_chunks GROUP BY chunk_type"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def prune_old_chunks(self) -> int:
        """Remove chunks based on type-specific retention policies.

        Returns the number of chunks deleted.
        """
        now = time.time()
        total_deleted = 0
        with self._lock:
            for chunk_type, retention_days in self.RETENTION_DAYS.items():
                if retention_days is None:
                    continue
                cutoff = now - (retention_days * 86400)
                cursor = self._db.cursor()
                cursor.execute(
                    "DELETE FROM knowledge_chunks WHERE created_at < ? AND chunk_type = ?",
                    (cutoff, chunk_type),
                )
                total_deleted += cursor.rowcount
            self._db.commit()
        return total_deleted

    def delete_project(self, project: str) -> int:
        """Delete all chunks for a specific project.

        Returns the number of chunks deleted.
        """
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(
                "DELETE FROM knowledge_chunks WHERE project = ?",
                (project,),
            )
            self._db.commit()
            deleted: int = cursor.rowcount
            return deleted

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
