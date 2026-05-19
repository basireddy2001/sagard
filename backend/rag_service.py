"""
Lightweight in-memory RAG.

We use a deterministic hashed-token bag-of-words embedding so the demo runs
with zero external dependencies. The interface is intentionally identical to
what a real embedding-model client would expose, so swapping in OpenAI or
Voyage embeddings later is a one-line change in `_embed`.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

EMBED_DIM = 256
CHUNK_SIZE = 400  # characters per chunk
CHUNK_OVERLAP = 60


@dataclass
class Chunk:
    doc_id: int
    doc_title: str
    doc_type: str
    text: str
    vector: List[float]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9$%]+", text.lower())


def _embed(text: str) -> List[float]:
    """Deterministic hashed bag-of-words pseudo-embedding."""
    vec = [0.0] * EMBED_DIM
    for tok in _tokenize(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % EMBED_DIM
        vec[idx] += 1.0
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def chunk_text(text: str) -> List[str]:
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def build_index(documents: Iterable) -> List[Chunk]:
    """Documents are ORM Document rows. Returns a list of embedded chunks."""
    index: List[Chunk] = []
    for doc in documents:
        for piece in chunk_text(doc.content):
            index.append(
                Chunk(
                    doc_id=doc.id,
                    doc_title=doc.title,
                    doc_type=doc.doc_type,
                    text=piece,
                    vector=_embed(piece),
                )
            )
    return index


def retrieve(index: List[Chunk], query: str, k: int = 4) -> List[Tuple[Chunk, float]]:
    if not index:
        return []
    q_vec = _embed(query)
    scored = [(c, _cosine(c.vector, q_vec)) for c in index]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


# Canonical diligence questions we always ask the RAG layer for every company.
STANDARD_QUERIES = [
    "revenue growth and trajectory",
    "burn rate, runway, and cash position",
    "customer churn and net retention",
    "sales cycle and pipeline efficiency",
    "executive team turnover or departures",
    "competitive landscape and funding rounds",
    "product delivery, implementation, customer satisfaction",
]


def gather_context(index: List[Chunk]) -> List[dict]:
    """Run RAG for every standard query, return citations for the LLM."""
    out = []
    for q in STANDARD_QUERIES:
        hits = retrieve(index, q, k=2)
        out.append({
            "question": q,
            "evidence": [
                {
                    "doc_title": h.doc_title,
                    "doc_type": h.doc_type,
                    "excerpt": h.text,
                    "score": round(score, 3),
                }
                for h, score in hits
                if score > 0
            ],
        })
    return out
