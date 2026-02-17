# Spec: NEXUS SDK Knowledge Module

**Version:** 2.0
**Date:** 2026-02-17
**Status:** Implemented
**Affects:** nexus-sdk (v0.3.0)
**Dependencies:** None (local-first mode) | nexus server localhost:4200 (server-backed mode)

## Summary

The `knowledge/` module provides two modes of operation:

1. **Local-first** (recommended): Per-user SQLite knowledge store with embedded semantic search. No server required. Each user's knowledge base lives at `~/.nexus/knowledge.db` and only learns from that user's projects.
2. **Server-backed**: HTTP client to a running NEXUS server instance for shared organizational knowledge.

## Motivation

The NEXUS SDK's purpose is to operate NEXUS without Claude Code. v0.2.0 added server-backed knowledge search, but this still required a running NEXUS server. v0.3.0 adds fully offline, local-first knowledge storage so any Python application can build and search its own institutional memory — no server, no shared state, no cloud egress.

Key design principle: **each user's RAG and ML store is local and only learns from that user's projects**.

## Module Structure

```
nexus_sdk/knowledge/
├── __init__.py         — exports all public classes (local-first + server-backed)
├── embeddings.py       — local embedding generation (sentence-transformers → TF-IDF → hash)
├── local_store.py      — LocalKnowledgeStore: per-user SQLite with retention policies
├── local_search.py     — LocalKnowledgeSearch + LocalDebugInvestigator (fully offline)
├── types.py            — KnowledgeChunk, SearchResult, DebugReport, KnowledgeStatus
├── client.py           — NexusClient: HTTP client wrapping NEXUS server API
├── search.py           — KnowledgeSearch: server-backed typed wrapper
└── debug.py            — DebugInvestigator: server-backed typed wrapper
```

## Local-First Architecture

### Embedding Tiers

The SDK detects the best available embedding backend at import time:

| Tier | Backend | Quality | Requirement |
|------|---------|---------|-------------|
| 1 | sentence-transformers (all-MiniLM-L6-v2) | Best | `pip install sentence-transformers` |
| 2 | scikit-learn TF-IDF | Good | `pip install scikit-learn` |
| 3 | Deterministic hash | Deduplication only | None (stdlib) |

All tiers produce 384-dim float32 vectors. Serialization uses `struct.pack`/`struct.unpack` for safe, deterministic binary encoding (no unsafe deserialization).

### Knowledge Chunk Types

| Type | Retention | Weight | Description |
|------|-----------|--------|-------------|
| error_resolution | Permanent | 1.3x | Past errors and their fixes — never repeat mistakes |
| task_outcome | 90 days | 1.1x | Completed task results |
| directive_summary | 90 days | 1.0x | Summarized directives |
| conversation | 30 days | 1.0x | Conversation context |
| code_change | 30 days | 0.9x | Code modifications |

### Storage

- Database: `~/.nexus/knowledge.db` (configurable)
- Engine: SQLite with WAL mode and 5s busy timeout
- Isolation: Per-user, per-project filtering via `project` column
- Deduplication: UNIQUE constraint on `source_id` with upsert
- Domain classification: Auto-detected from content keywords (frontend, backend, devops, security, testing)

## Types

### LocalChunk
A knowledge chunk with similarity score from local search.

| Field | Type | Description |
|-------|------|-------------|
| chunk_type | str | error_resolution, task_outcome, etc. |
| content | str | Chunk text content |
| source_id | str | Unique source identifier |
| domain_tag | str | Auto-classified domain |
| project | str | Project identifier |
| similarity | float | Raw cosine similarity |
| score | float (property) | Weighted score (type weight x recency boost) |

### LocalSearchResult

| Field | Type | Description |
|-------|------|-------------|
| results | list[LocalChunk] | Ranked results |
| query | str | Original search query |
| mode | str | Search mode used |
| count | int (property) | Number of results |
| has_results | bool (property) | True if count > 0 |

### LocalDebugReport

| Field | Type | Description |
|-------|------|-------------|
| past_errors | list[LocalChunk] | Similar past errors |
| related_tasks | list[LocalChunk] | Related task outcomes |
| code_changes | list[LocalChunk] | Related code changes |
| proven_fix | LocalChunk? | Highest-confidence past fix |
| has_proven_fix | bool (property) | True if match >= 70% |
| summary() | str (method) | Human-readable summary |

### Server-Backed Types

KnowledgeChunk, SearchResult, DebugReport, KnowledgeStatus remain unchanged from v0.2.0 for server-backed usage.

## Usage Patterns

### Local-First (No Server Required)

```python
from nexus_sdk import LocalKnowledgeSearch, LocalDebugInvestigator

# Initialize local knowledge store
search = LocalKnowledgeSearch()  # uses ~/.nexus/knowledge.db
search.init()

# Ingest knowledge from your project
search.ingest_error(
    "Fix: JWT token refresh needs 30s timeout to prevent race condition",
    source_id="err-jwt-timeout",
    project="my-api",
)
search.ingest_task(
    "Implemented rate limiter with sliding window algorithm",
    source_id="task-rate-limiter",
    project="my-api",
)

# Search your local knowledge
result = search.errors("JWT token failing")
for chunk in result.results:
    print(f"[{chunk.similarity:.0%}] {chunk.content[:80]}")

# Debug investigation
debugger = LocalDebugInvestigator()
debugger.init()
report = debugger.investigate("JWT refresh token failing with timeout")
if report.has_proven_fix:
    print(f"Apply proven fix: {report.proven_fix.content}")

# Maintenance
search.prune()  # remove expired chunks per retention policy
search.close()
```

### CI/CD Integration

```python
debugger = LocalDebugInvestigator()
debugger.init()
if debugger.quick_check(error_from_test_suite):
    print("Known issue — check local knowledge base for resolution")
debugger.close()
```

### Server-Backed (Requires NEXUS Server)

```python
from nexus_sdk import NexusClient, KnowledgeSearch, DebugInvestigator

client = NexusClient(base_url="http://localhost:4200")
client.authenticate(os.environ["NEXUS_PASSPHRASE"])
search = KnowledgeSearch(client)
debugger = DebugInvestigator(client)

result = search.errors("timeout connecting to database")
report = debugger.investigate("API returning 500 on /users endpoint")
```

## Design Decisions

1. **Local-first by default** — Users should not need a running server to benefit from institutional memory. The SDK stores knowledge in their own SQLite database, isolated per user and per project.

2. **Safe serialization** — Embedding vectors are serialized with `struct.pack`/`struct.unpack` (fixed-format binary), avoiding unsafe deserialization patterns entirely. Produces deterministic 1536-byte BLOBs.

3. **Tiered embeddings** — Graceful degradation from sentence-transformers (best quality) through TF-IDF (decent) to hash (always works). Users get the best quality their environment supports without configuration.

4. **Retention policies** — Error resolutions are permanent (never repeat mistakes). Other types expire based on utility half-life. `prune()` enforces these policies.

5. **Domain auto-classification** — Content is automatically tagged with domain (frontend, backend, devops, security, testing) based on keyword matching, enabling filtered searches without manual tagging.

6. **No data sharing** — Each user's knowledge base is completely isolated. No data is sent to external services, no state is shared between users. This is a foundational architectural decision.

## Exports (v0.3.0)

```python
from nexus_sdk import (
    # Existing (v0.1.0)
    NexusConfig, TaskResult, Decision, AgentConfig,
    AgentRegistry, Agent, get_agent_name, get_team_names,
    # Local-first knowledge (v0.3.0)
    LocalKnowledgeStore, LocalKnowledgeSearch, LocalDebugInvestigator,
    LocalChunk, LocalSearchResult, LocalDebugReport,
    # Server-backed knowledge (v0.2.0)
    NexusClient, KnowledgeSearch, DebugInvestigator,
    SearchResult, DebugReport, KnowledgeChunk, KnowledgeStatus,
)
```
