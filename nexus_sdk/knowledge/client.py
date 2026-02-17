"""
NexusClient — HTTP client for the NEXUS server API.

Provides authenticated access to all NEXUS endpoints including
knowledge search, debug investigation, ML status, and agent management.

Works standalone without Claude Code — anyone with a running NEXUS server
can use this client from any Python application.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("nexus_sdk.client")


class NexusClient:
    """HTTP client for NEXUS server API.

    Example:
        >>> client = NexusClient(base_url="http://localhost:4200")
        >>> client.authenticate("my-passphrase")
        >>> results = client.search("rate limiter", mode="errors")
        >>> report = client.debug("ML router returning wrong agents")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:4200",
        session_token: str = "",
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.timeout = timeout

    def authenticate(self, passphrase: str) -> bool:
        """Authenticate with the NEXUS server.

        Args:
            passphrase: The NEXUS dashboard passphrase (plain or pre-hashed)

        Returns:
            True if authentication succeeded
        """
        data = self._post("/auth/login", {"passphrase": passphrase})
        if data and data.get("ok"):
            self.session_token = data.get("token", "")
            return True
        return False

    def _headers(self) -> dict[str, str]:
        """Build request headers with auth token."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        """Make an authenticated GET request."""
        url = f"{self.base_url}{path}"
        req = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw: dict[str, Any] = json.loads(resp.read().decode())
                return raw
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            logger.error("GET %s failed: %s", path, e)
            return {}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Make an authenticated POST request."""
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        req = Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw: dict[str, Any] = json.loads(resp.read().decode())
                return raw
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            logger.error("POST %s failed: %s", path, e)
            return {}

    # -- Knowledge Search --

    def search(
        self,
        query: str,
        mode: str = "all",
        domain: str = "",
        top_k: int = 5,
        threshold: float = 0.35,
    ) -> dict[str, Any]:
        """Semantic search over the NEXUS knowledge base.

        Args:
            query: Natural language search query
            mode: Search mode — all, errors, tasks, code, conversations
            domain: Domain filter — frontend, backend, devops, security, testing
            top_k: Maximum results to return
            threshold: Minimum similarity threshold

        Returns:
            Raw API response dict (use KnowledgeSearch for typed results)
        """
        return self._post("/ml/rag/search", {
            "query": query,
            "mode": mode,
            "domain": domain,
            "top_k": top_k,
            "threshold": threshold,
        })

    def debug(
        self,
        error: str,
        file_path: str = "",
        domain: str = "",
    ) -> dict[str, Any]:
        """Run a semantic debug investigation.

        Args:
            error: Error description, message, or stack trace
            file_path: Optional file path to focus investigation
            domain: Optional domain filter — frontend, backend, devops, security, testing

        Returns:
            Raw API response dict (use DebugInvestigator for typed results)
        """
        return self._post("/ml/debug", {
            "error": error,
            "file_path": file_path,
            "domain": domain,
        })

    def knowledge_status(self) -> dict[str, Any]:
        """Get RAG knowledge base status."""
        return self._get("/ml/rag/status")

    # -- Existing API --

    def send_message(self, message: str, source: str = "sdk") -> dict[str, Any]:
        """Send a message to the NEXUS engine."""
        return self._post("/message", {"message": message, "source": source})

    def health(self) -> dict[str, Any]:
        """Get server health status."""
        return self._get("/health")

    def get_state(self) -> dict[str, Any]:
        """Get current world state snapshot."""
        return self._get("/state")

    def get_agents(self) -> dict[str, Any]:
        """Get all registered agents."""
        return self._get("/agents")

    def get_cost(self) -> dict[str, Any]:
        """Get cost summary."""
        return self._get("/cost")

    def ml_status(self) -> dict[str, Any]:
        """Get ML learning system status."""
        return self._get("/ml/status")

    def find_similar(self, text: str) -> dict[str, Any]:
        """Find similar past directives."""
        return self._post("/ml/similar", {"message": text})
