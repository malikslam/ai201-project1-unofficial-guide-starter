"""Milestone 4 — semantic retrieval for The Unofficial Guide.

Embeds a user query with the same ``all-MiniLM-L6-v2`` model and returns the
top-k most similar review chunks from the ChromaDB collection, each with its
source-attribution metadata and cosine distance score.

Run directly to test retrieval against the evaluation-plan queries:

    python retrieve.py
"""
from __future__ import annotations

from dataclasses import dataclass

from embed_store import get_collection


@dataclass
class Result:
    text: str
    metadata: dict
    distance: float


def retrieve(query: str, k: int = 4, where: dict | None = None) -> list[Result]:
    """Return the top-k review chunks most similar to ``query``.

    ``where`` optionally filters by metadata (e.g. {"school": "Texas A&M"} or
    {"source": "philip-ritchey_texasA&M_reviews.pdf"}).
    """
    collection = get_collection()
    res = collection.query(
        query_texts=[query],
        n_results=k,
        where=where or None,
    )
    return [
        Result(text=doc, metadata=meta, distance=dist)
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


# The 3 in-scope evaluation-plan queries used to validate retrieval (M4).
TEST_QUERIES = [
    "What is the workload like in Donald Lafond's networking classes at FSCJ?",
    "Is Philip Ritchey at Texas A&M an easy or a hard grader?",
    "What do students say about Aakash Tyagi's exams and teaching?",
]


def main() -> None:
    for q in TEST_QUERIES:
        print("=" * 90)
        print(f"QUERY: {q}")
        print("=" * 90)
        for r in retrieve(q, k=4):
            m = r.metadata
            print(f"\n[dist {r.distance:.3f}] {m.get('professor')} "
                  f"({m.get('school')}) — {m.get('course')} {m.get('date')} "
                  f"| {m.get('source')}")
            print(f"  {r.text[:280]}")
        print()


if __name__ == "__main__":
    main()
