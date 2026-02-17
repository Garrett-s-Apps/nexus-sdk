# Spec: NEXUS SDK Knowledge Module

**Version:** 1.0
**Date:** 2026-02-17
**Status:** Implemented
**Affects:** nexus-sdk (v0.2.0)
**Dependencies:** nexus server (localhost:4200 with RAG endpoints)

## Summary

Add a `knowledge/` module to the NEXUS SDK that provides programmatic access to semantic search and debug investigation capabilities. This enables anyone to use NEXUS's RAG knowledge base from any Python application — no Claude Code required.

## Motivation

The NEXUS SDK's purpose is to operate NEXUS without Claude Code. Before this change, the SDK provided:
- Agent registry with provider-agnostic execution (Claude/OpenAI/Gemini)
- Cost tracking and budget enforcement

But it was missing access to NEXUS's most valuable capability: institutional memory. The RAG knowledge base, semantic search, and debug investigation were only accessible through the nexus-plugin (Claude Code) or direct Python imports (server-side only).

With this change, any Python application can:
1. Search past errors, task outcomes, code changes, and conversations
2. Run semantic debug investigations with proven-fix detection
3. Check knowledge base health and status

## Module Structure

```
nexus_sdk/knowledge/
├── __init__.py     — exports NexusClient, KnowledgeSearch, DebugInvestigator
├── types.py        — KnowledgeChunk, SearchResult, DebugReport, KnowledgeStatus
├── client.py       — NexusClient: HTTP client wrapping NEXUS server API
├── search.py       — KnowledgeSearch: typed wrapper for semantic search
└── debug.py        — DebugInvestigator: typed wrapper for debug investigation
```

## Types

### KnowledgeChunk
A single knowledge chunk from the RAG store.

| Field | Type | Description |
|-------|------|-------------|
| content | str | Chunk text content |
| chunk_type | str | error_resolution, task_outcome, conversation, code_change |
| source_id | str | Unique source identifier |
| score | float | Weighted similarity score |
| raw_similarity | float | Raw cosine similarity |
| metadata | dict | Additional metadata (agent, cost, files, etc.) |

### SearchResult
Result of a semantic search query.

| Field | Type | Description |
|-------|------|-------------|
| query | str | Original search query |
| mode | str | Search mode used |
| results | list[KnowledgeChunk] | Ranked results |
| count | int | Number of results |
| has_results | bool (property) | True if count > 0 |
| top_match | KnowledgeChunk? (property) | Highest-scoring result |

### DebugReport
Result of a semantic debug investigation.

| Field | Type | Description |
|-------|------|-------------|
| error | str | Error description |
| file_path | str | Affected file |
| domain | str | Domain classification |
| past_errors | list[KnowledgeChunk] | Similar past errors |
| related_tasks | list[KnowledgeChunk] | Related task outcomes |
| recent_code_changes | list[KnowledgeChunk] | Recent code changes |
| directive_analysis | dict | Directive similarity analysis |
| has_proven_fix | bool | True if match >= 70% |
| proven_fix | KnowledgeChunk? | Highest-confidence past fix |
| risk_level | str (property) | Risk from directive analysis |
| summary() | str (method) | Human-readable summary |

### KnowledgeStatus
RAG knowledge base status.

| Field | Type | Description |
|-------|------|-------------|
| total_chunks | int | Total chunks stored |
| by_type | dict[str, int] | Counts per chunk type |
| ready | bool | True if knowledge base is operational |

## NexusClient

HTTP client wrapping the NEXUS server API using only stdlib (`urllib`). No external HTTP dependencies required.

**Authentication:**
```python
client = NexusClient(base_url="http://localhost:4200")
client.authenticate("my-passphrase")
```

**Methods:**
| Method | Endpoint | Returns |
|--------|----------|---------|
| `search()` | POST /ml/rag/search | dict (raw) |
| `debug()` | POST /ml/debug | dict (raw) |
| `knowledge_status()` | GET /ml/rag/status | dict (raw) |
| `send_message()` | POST /message | dict |
| `health()` | GET /health | dict |
| `get_state()` | GET /state | dict |
| `get_agents()` | GET /agents | dict |
| `get_cost()` | GET /cost | dict |
| `ml_status()` | GET /ml/status | dict |
| `find_similar()` | POST /ml/similar | dict |

## Usage Patterns

### Standalone Python Script
```python
from nexus_sdk import NexusClient, KnowledgeSearch, DebugInvestigator

client = NexusClient()
client.authenticate(os.environ["NEXUS_PASSPHRASE"])
search = KnowledgeSearch(client)
debugger = DebugInvestigator(client)

# Search past errors
result = search.errors("timeout connecting to database")
if result.has_results:
    print(f"Found {result.count} similar past errors")

# Debug investigation
report = debugger.investigate("API returning 500 on /users endpoint")
if report.has_proven_fix:
    print(f"Apply proven fix: {report.proven_fix.content}")
```

### CI/CD Integration
```python
# Pre-flight check: has this error been solved before?
if debugger.quick_check(error_from_test_suite):
    print("Known issue — check knowledge base for resolution")
```

### Custom Dashboard
```python
# Expose knowledge base metrics
status = search.status()
dashboard_data = {
    "total_knowledge": status.total_chunks,
    "error_resolutions": status.by_type.get("error_resolution", 0),
    "ready": status.ready,
}
```

## Design Decisions

1. **stdlib-only HTTP** — Uses `urllib` instead of `requests`/`httpx` to avoid adding dependencies to the SDK. The SDK should be zero-dependency beyond pydantic-settings (already required for config).

2. **Raw + Typed layers** — `NexusClient` returns raw dicts for flexibility. `KnowledgeSearch` and `DebugInvestigator` return typed dataclasses for developer ergonomics. Consumers choose their preferred abstraction level.

3. **No async** — The client uses synchronous `urllib` to match the simplest use case (scripts, notebooks, CI). Async support can be added later with `aiohttp` if needed.

4. **Dataclasses over Pydantic** — Knowledge types use stdlib dataclasses to avoid coupling the types layer to pydantic. The config layer already uses pydantic-settings, but types should be portable.

## Exports (v0.2.0)

```python
from nexus_sdk import (
    # Existing (v0.1.0)
    NexusConfig, TaskResult, Decision, AgentConfig,
    AgentRegistry, Agent, get_agent_name, get_team_names,
    # New (v0.2.0)
    NexusClient, KnowledgeSearch, DebugInvestigator,
    SearchResult, DebugReport, KnowledgeChunk, KnowledgeStatus,
)
```
