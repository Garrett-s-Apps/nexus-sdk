"""
Local Embeddings — lightweight embedding generation for per-user RAG.

Tiered approach (same as NEXUS server):
1. sentence-transformers (all-MiniLM-L6-v2) — best quality
2. scikit-learn TF-IDF — decent fallback
3. Deterministic hash — always works, no deps

All tiers produce 384-dim float32 vectors for consistency.
Uses struct (not pickle) for safe serialization to SQLite BLOB.
"""

import hashlib
import math
import struct
from typing import Optional

_DIMS = 384
_STRUCT_FMT = f"<{_DIMS}f"  # little-endian, 384 floats

# --- Tier detection -----------------------------------------------------------

_model: Optional[object] = None
_tfidf: Optional[object] = None
_tier: str = "hash"


def _init_tier() -> str:
    """Detect best available embedding backend."""
    global _model, _tfidf, _tier

    # Tier 1: sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _tier = "transformer"
        return _tier
    except Exception:
        pass

    # Tier 2: TF-IDF
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        _tfidf = TfidfVectorizer(max_features=_DIMS)
        _tier = "tfidf"
        return _tier
    except Exception:
        pass

    # Tier 3: hash (always available)
    _tier = "hash"
    return _tier


_init_tier()


# --- Public API ---------------------------------------------------------------

def encode(text: str) -> list[float]:
    """Encode text into a 384-dim float vector.

    Automatically uses the best available backend.
    """
    if _tier == "transformer" and _model is not None:
        vec = _model.encode(text, show_progress_bar=False)  # type: ignore[union-attr]
        return [float(v) for v in vec[:_DIMS]]

    if _tier == "tfidf" and _tfidf is not None:
        try:
            matrix = _tfidf.transform([text])  # type: ignore[union-attr]
            arr = matrix.toarray()[0]
            padded = list(arr[:_DIMS]) + [0.0] * max(0, _DIMS - len(arr))
            return padded[:_DIMS]
        except Exception:
            pass

    return _hash_embedding(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def to_bytes(vec: list[float]) -> bytes:
    """Serialize a 384-dim vector to bytes for SQLite BLOB storage.

    Uses struct packing (safe, no arbitrary code execution).
    """
    if len(vec) != _DIMS:
        raise ValueError(f"Expected {_DIMS}-dim vector, got {len(vec)}")
    return struct.pack(_STRUCT_FMT, *vec)


def from_bytes(data: bytes) -> list[float]:
    """Deserialize bytes back to a 384-dim vector.

    Uses struct unpacking (safe, deterministic).
    """
    if len(data) != struct.calcsize(_STRUCT_FMT):
        raise ValueError(f"Expected {struct.calcsize(_STRUCT_FMT)} bytes, got {len(data)}")
    return list(struct.unpack(_STRUCT_FMT, data))


def classify_domain(text: str) -> str:
    """Classify text into a domain tag based on keyword matching.

    Returns: frontend, backend, devops, security, testing, or empty string.
    """
    lower = text.lower()
    domain_keywords: dict[str, list[str]] = {
        "frontend": ["react", "vue", "angular", "css", "html", "component", "ui", "ux",
                      "tailwind", "styled", "dom", "browser", "jsx", "tsx"],
        "backend": ["api", "endpoint", "database", "sql", "server", "fastapi", "flask",
                     "django", "route", "middleware", "orm", "migration"],
        "devops": ["docker", "kubernetes", "ci/cd", "deploy", "terraform", "ansible",
                    "pipeline", "github actions", "cloudflare", "nginx"],
        "security": ["auth", "jwt", "token", "encrypt", "password", "cors", "csrf",
                      "xss", "injection", "vulnerability", "permission"],
        "testing": ["test", "pytest", "jest", "mock", "fixture", "coverage", "assert",
                     "spec", "e2e", "integration"],
    }
    scores: dict[str, int] = {}
    for domain, keywords in domain_keywords.items():
        scores[domain] = sum(1 for kw in keywords if kw in lower)

    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else ""


def get_tier() -> str:
    """Return the current embedding tier name."""
    return _tier


# --- Internal -----------------------------------------------------------------

def _hash_embedding(text: str) -> list[float]:
    """Deterministic hash-based pseudo-embedding (tier 3 fallback).

    Produces consistent 384-dim vectors from text content.
    Not semantically meaningful but enables deduplication.
    """
    vec: list[float] = []
    for i in range(_DIMS):
        h = hashlib.md5(
            f"{text[:500]}:{i}".encode(), usedforsecurity=False
        ).hexdigest()[:8]
        val = (int(h, 16) / 0xFFFFFFFF) * 2 - 1  # normalize to [-1, 1]
        vec.append(val)
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec
