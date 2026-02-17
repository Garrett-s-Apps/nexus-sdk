"""
Example: Knowledge Search & Semantic Debug with NEXUS SDK

Shows how to use the SDK to search the NEXUS knowledge base and
run debug investigations — no Claude Code required.

Prerequisites:
- NEXUS server running at localhost:4200
- Valid passphrase for authentication
"""

import os

from nexus_sdk import DebugInvestigator, KnowledgeSearch, NexusClient


def main():
    # Connect to NEXUS server
    client = NexusClient(base_url="http://localhost:4200")
    passphrase = os.environ.get("NEXUS_PASSPHRASE", "")
    if passphrase:
        client.authenticate(passphrase)

    # -- Knowledge Search --
    search = KnowledgeSearch(client)

    # Check knowledge base status
    status = search.status()
    print(f"Knowledge base: {status.total_chunks} chunks")
    for chunk_type, count in status.by_type.items():
        print(f"  {chunk_type}: {count}")

    # Search all knowledge types
    result = search.query("rate limiter implementation")
    print(f"\nSearch: 'rate limiter' — {result.count} results")
    for chunk in result.results:
        print(f"  [{chunk.score:.0%}] {chunk.chunk_type}: {chunk.content[:80]}...")

    # Search only past errors
    errors = search.errors("authentication timeout")
    if errors.has_results:
        print(f"\nFound {errors.count} past auth timeout errors:")
        for e in errors.results:
            print(f"  [{e.raw_similarity:.0%}] {e.content[:100]}")

    # Search with domain filter
    backend_tasks = search.tasks("database migration", domain="backend")
    print(f"\nBackend DB tasks: {backend_tasks.count} results")

    # -- Debug Investigation --
    debugger = DebugInvestigator(client)

    # Quick check: does a proven fix exist?
    has_fix = debugger.quick_check("JWT token validation failing on refresh")
    print(f"\nProven fix for JWT issue: {has_fix}")

    # Full investigation
    report = debugger.investigate(
        error="ML router returning wrong agents for frontend tasks",
        file_path="src/ml/router.py",
        domain="backend",
    )

    print(f"\n--- Debug Report ---")
    print(report.summary())

    if report.has_proven_fix and report.proven_fix:
        print(f"\nProven fix ({report.proven_fix.raw_similarity:.0%} match):")
        print(f"  {report.proven_fix.content[:200]}")

    if report.similar_directives:
        print(f"\nSimilar past work:")
        for d in report.similar_directives[:3]:
            print(f"  [{d.get('similarity', 0):.0%}] {d.get('directive_text', '')[:60]}")

    cost_est = report.cost_estimate
    if cost_est.get("predicted"):
        print(f"\nEstimated fix cost: ${cost_est['predicted']:.2f}")


if __name__ == "__main__":
    main()
